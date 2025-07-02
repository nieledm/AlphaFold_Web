import paramiko
import threading
import time
from database import get_db_connection
from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER, \
                 ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, ALPHAFOLD_PARAMS, ALPHAFOLD_DB
from apps.logs.utils import log_action
from apps.emails.utils import send_processing_complete_email

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # para acessar app.py e database.py diretamente

from database import get_db_connection
from flask import Flask
from email.mime.text import MIMEText

from database import get_db_connection

# ==============================================================
# JOB MANAGER
# ==============================================================

def get_system_status(host, port, user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user)

    status = {}

    commands = {
        "cpu": "top -bn1 | grep 'Cpu(s)'",
        "mem": "free -h",
        "gpu": "nvidia-smi --query-gpu=name,memory.total,memory.free,utilization.gpu --format=csv,noheader,nounits",
        "disk": "df -h /str1"
    }

    for key, cmd in commands.items():
        try:
            stdin, stdout, _ = ssh.exec_command(cmd)
            result = stdout.read().decode().strip()
            status[key] = result
        except Exception as e:
            status[key] = f"Erro: {e}"

    ssh.close()
    return status

def parse_system_status(raw_status):
    parsed = {}
    
    try:
        # Parse CPU
        cpu_raw = raw_status.get('cpu', '')
        cpu_lines = cpu_raw.split('\n')
        cpu_info = {}
        
        # Parse CPU info (model, cores, frequency)
        for line in cpu_lines:
            if 'Model name:' in line:
                cpu_info['model'] = line.split(':')[1].strip()
            elif 'CPU(s):' in line:
                cpu_info['cores'] = line.split(':')[1].strip()
            elif 'CPU MHz:' in line or 'CPU max MHz:' in line:
                freq = float(line.split(':')[1].strip())
                cpu_info['frequency'] = f"{freq/1000:.2f} GHz"
        
        # Parse CPU usage - CORREÇÃO AQUI
        for line in cpu_lines:
            if '%Cpu(s):' in line or 'Cpu(s):' in line:
                try:
                    # Extrai o valor de %id (tempo ocioso)
                    idle = float(line.split(',')[3].strip().replace('%id', '').split()[0])
                    cpu_info['usage'] = round(100 - idle, 1)
                except (IndexError, ValueError) as e:
                    cpu_info['usage'] = 0.0  # Valor padrão em caso de erro
                    print(f"Erro ao parsear uso da CPU: {e}")
                break
        
        parsed['cpu'] = cpu_info
        
        # Restante do código permanece igual...
        # Parse Memória
        mem_raw = raw_status.get('mem', '')
        mem_lines = mem_raw.split('\n')
        mem_info = {}
        
        for line in mem_lines:
            if 'Mem:' in line:
                parts = line.split()
                try:
                    mem_info['total'] = parts[1]
                    mem_info['used'] = parts[2]
                    mem_info['free'] = parts[3]
                    # Converter valores para cálculo da porcentagem
                    total = float(parts[1].replace('Gi', '').replace('Mi', ''))
                    used = float(parts[2].replace('Gi', '').replace('Mi', ''))
                    mem_info['percent_used'] = round((used / total) * 100, 1)
                except (IndexError, ValueError) as e:
                    print(f"Erro ao parsear memória: {e}")
                break
        
        parsed['mem'] = mem_info
        
        # Parse GPU (similar ao original)
        gpu_raw = raw_status.get('gpu', '')
        gpu_lines = gpu_raw.split('\n')
        gpu_parsed = []
        for line in gpu_lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) == 4:
                try:
                    gpu_parsed.append({
                        'name': parts[0],
                        'memory_total': parts[1],
                        'memory_free': parts[2],
                        'utilization': parts[3].replace('%', '')
                    })
                except IndexError as e:
                    print(f"Erro ao parsear GPU: {e}")
        parsed['gpu'] = gpu_parsed
        
        # Parse Disco
        disk_raw = raw_status.get('disk', '')
        disk_lines = disk_raw.split('\n')
        disk_header = []
        disk_rows = []
        for i, line in enumerate(disk_lines):
            cols = line.split()
            if i == 0:
                disk_header = cols
            elif cols:
                disk_rows.append(cols)
        parsed['disk'] = {
            'header': disk_header,
            'rows': disk_rows
        }
        
    except Exception as e:
        print(f"Erro geral ao parsear status: {e}")
        parsed['error'] = str(e)
    
    return parsed

def get_job_counts():
    conn = get_db_connection()
    running = conn.execute("SELECT COUNT(*) FROM uploads WHERE status = 'PROCESSANDO'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM uploads WHERE status = 'PENDENTE'").fetchone()[0]
    conn.close()
    return running, pending

def get_pending_jobs():
    conn = get_db_connection()
    jobs = conn.execute("""
        SELECT uploads.base_name, uploads.created_at, users.name 
        FROM uploads 
        JOIN users ON uploads.user_id = users.id 
        WHERE uploads.status = 'PENDENTE' 
        ORDER BY uploads.created_at ASC
    """).fetchall()
    conn.close()
    return jobs  

# ==============================================================
# JOB MANAGER
# ==============================================================

MAX_CONTAINERS = 2

def get_running_container_count():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ALPHAFOLD_SSH_HOST, port=ALPHAFOLD_SSH_PORT, username=ALPHAFOLD_SSH_USER)
    stdin, stdout, _ = ssh.exec_command("docker ps | grep alphafold3 | wc -l")
    count = int(stdout.read().decode().strip())
    ssh.close()
    return count

def process_next_job():
    conn = get_db_connection()
    job = conn.execute(
        "SELECT * FROM uploads WHERE status = 'PENDENTE' ORDER BY created_at ASC LIMIT 1"
    ).fetchone()
    conn.close()

    if not job:
        return  # Nada a processar

    user_id = job["user_id"]
    base_name = job["base_name"]
    file_name = job["file_name"]

    # Pegando dados do usuário
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not user:
        log_action(None, "Erro fila", f"Usuário ID {user_id} não encontrado para job {base_name}")
        return

    user_name = user["name"].replace(" ", "")
    user_email = user["email"]

    input_dir = f"{ALPHAFOLD_INPUT_BASE}/{user_name}"
    output_dir = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name}"
    job_output_dir = f"{output_dir}/{base_name}"

    cmd = (
        f"docker run "
        f"--volume {input_dir}:/root/af_input "
        f"--volume {output_dir}:/root/af_output "
        f"--volume {ALPHAFOLD_PARAMS}:/root/models "
        f"--volume {ALPHAFOLD_DB}:/root/public_databases "
        f"--gpus all alphafold3 "
        f"python run_alphafold.py "
        f"--json_path=/root/af_input/{file_name} "
        f"--output_dir=/root/af_output/{base_name} "
    )

    # Atualiza status no banco
    conn = get_db_connection()
    conn.execute("UPDATE uploads SET status = 'PROCESSANDO' WHERE id = ?", (job["id"],))
    conn.commit()
    conn.close()

    # Executa remotamente
    def run_job():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(ALPHAFOLD_SSH_HOST, port=ALPHAFOLD_SSH_PORT, username=ALPHAFOLD_SSH_USER)
            ssh.exec_command(f"mkdir -p '{job_output_dir}'")

            stdin, stdout, stderr = ssh.exec_command(cmd)

            conn = get_db_connection()
            conn.execute("UPDATE uploads SET status = 'PROCESSANDO' WHERE id = ?", (job["id"],))
            conn.commit()
            conn.close()

            # Espera finalização
            while not stdout.channel.exit_status_ready():
                time.sleep(2)

            exit_status = stdout.channel.recv_exit_status()

            remote_cif = f"{job_output_dir}/alphafold_prediction/alphafold_prediction_model.cif"
            stdin, stdout, _ = ssh.exec_command(f'test -f "{remote_cif}" && echo OK || echo NO')
            result = stdout.read().decode().strip()

            conn = get_db_connection()
            if exit_status == 0 and result == "OK":
                conn.execute("UPDATE uploads SET status = 'COMPLETO' WHERE id = ?", (job["id"],))
                send_processing_complete_email(user_name, user_email, base_name, user_id)
                log_action(user_id, "Job concluído com sucesso", base_name)
            else:
                conn.execute("UPDATE uploads SET status = 'ERRO' WHERE id = ?", (job["id"],))
                log_action(user_id, "Erro no job", f"{base_name} - exit {exit_status}, exists={result}")
            conn.commit()
            conn.close()

        except Exception as e:
            log_action(user_id, "Erro exec fila", str(e))
        finally:
            ssh.close()

    t = threading.Thread(target=run_job)
    t.start()


def job_manager_loop():
    while True:
        try:
            running = get_running_container_count()
            if running < MAX_CONTAINERS:
                process_next_job()
        except Exception as e:
            print("[job_manager_loop] Erro:", e)
        time.sleep(10)  # Checa a cada 10s
