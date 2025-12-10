import paramiko
import threading
import time
import shlex
import pytz
from datetime import datetime, timedelta
from database import get_db_connection
from config import ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, ALPHAFOLD_PARAMS, ALPHAFOLD_DB, ALPHAFOLD_PREDICTION, app
from apps.logs.utils import log_action
from apps.emails.utils import send_processing_complete_email
from conections import get_ssh_connection
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # para acessar app.py e database.py diretamente
from flask import Flask, current_app
from email.mime.text import MIMEText
import subprocess
import sqlite3
from flask_socketio import SocketIO
from slurm.utils import run_remote_cmd

socketio = SocketIO(app, cors_allowed_origins="*")

os.environ['SCHEDULER_DISABLED'] = '1'

# ==============================================================
# SISTEMA DE MONITORAMENTO
# ==============================================================

def get_system_status(host, port, user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user)

    status = {}

    commands = {
        "cpu_info": "lscpu",
        "cpu_usage": "top -bn1 | grep 'Cpu(s)'",
        "mem": "free -h",
        "gpu": "nvidia-smi --query-gpu=name,memory.total,memory.free,utilization.gpu,utilization.memory --format=csv,noheader,nounits",
        "disk": "df -h /str1",
        "slurm_queue": "squeue -o '%i|%u|%j|%T|%b|%C|%m|%L' --noheader"
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
        cpu_info_raw = raw_status.get('cpu_info', '')
        cpu_lines = cpu_info_raw.split('\n')
        cpu_info = {}
        
        # Parse CPU info (model, cores, frequency)
        for line in cpu_lines:
            if 'Model name:' in line:
                cpu_info['model'] = line.split(':')[1].strip()
            elif 'CPU(s):' in line and 'NUMA' not in line:
                cpu_info['cores'] = line.split(':')[1].strip()
            elif 'CPU max MHz:' in line:
                try:
                    freq = float(line.split(':')[1].strip())
                    cpu_info['frequency'] = f"{freq/1000:.2f} GHz"
                except:
                    cpu_info['frequency'] = "N/D"

        # Parse CPU usage
        usage_raw = raw_status.get('cpu_usage', '')
        for line in usage_raw.split('\n'):
            if 'Cpu(s):' in line:
                try:
                    idle = float(line.split(',')[3].strip().replace('%id', '').split()[0])
                    cpu_info['usage'] = round(100 - idle, 1)
                except:
                    cpu_info['usage'] = 0.0
                break

        parsed['cpu'] = cpu_info

        
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
                    total = convert_mem_unit(parts[1])
                    used = convert_mem_unit(parts[2])
                    mem_info['percent_used'] = round((used / total) * 100, 1)
                except (IndexError, ValueError) as e:
                    print(f"Erro ao parsear memória: {e}")
                break        
        parsed['mem'] = mem_info
        
        # Parse GPU
        gpu_raw = raw_status.get('gpu', '')
        gpu_lines = gpu_raw.split('\n')
        gpu_parsed = []
        for line in gpu_lines:
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                try:
                    gpu_parsed.append({
                        'name': parts[0],
                        'memory_total': parts[1].replace(' MiB', '').strip(),
                        'memory_free': parts[2].replace(' MiB', '').strip(),
                        'utilization_memory': float(parts[4].replace('%', '').strip() or 0.0)
                    })
                except (IndexError, ValueError) as e:
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
                disk_header = cols[1:-2]  # Remove primeira (Filesystem) e última coluna (Mounted on)
            elif cols:
                disk_rows.append(cols[1:-1]) # Remove primeira (Filesystem) e última coluna (Mounted on)
        parsed['disk'] = {
            'header': disk_header,
            'rows': disk_rows
        }

        # Parse Fila Slurm
        slurm_raw = raw_status.get('slurm_queue', '')
        if slurm_raw:
            parsed['slurm_queue'] = parse_slurm_queue_output(slurm_raw)
        
    except Exception as e:
        print(f"Erro geral ao parsear status: {e}")
        parsed['error'] = str(e)
    
    return parsed

def convert_mem_unit(value):
    try:
        if 'Ti' in value:
            return float(value.replace('Ti', '')) * 1024  # converte para Gi
        elif 'Gi' in value:
            return float(value.replace('Gi', ''))
        elif 'Mi' in value:
            return float(value.replace('Mi', '')) / 1024
        else:
            return float(value)
    except:
        return 0.0

def parse_slurm_queue_output(output):
    """Parseia output do comando squeue"""
    jobs = []
    lines = output.strip().split('\n')
    
    for line in lines:
        parts = line.split('|')
        if len(parts) >= 8:
            jobs.append({
                'job_id': parts[0],
                'user': parts[1],
                'name': parts[2],
                'state': parts[3],
                'gres': parts[4],
                'cpus': parts[5],
                'mem': parts[6],
                'time': parts[7]
            })
    
    return jobs

def get_job_counts():
    """Obtém contagem de jobs por status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM uploads 
        GROUP BY status
    """)
    counts = dict(cursor.fetchall())
    conn.close()
    
    # Calcular contadores esperados
    running_count = counts.get('PROCESSANDO', 0)
    pending_count = counts.get('PENDENTE', 0)
    
    # Retorna os dois valores esperados
    return running_count, pending_count
    

def get_pending_jobs():
    """Obtém lista de jobs pendentes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT uploads.id, uploads.base_name, uploads.job_id, uploads.created_at, users.name 
        FROM uploads 
        JOIN users ON uploads.user_id = users.id 
        WHERE uploads.status = 'PENDENTE' 
        ORDER BY uploads.created_at ASC
    """)
    
    jobs = cursor.fetchall()
    conn.close()
    
    return [dict(zip(['id', 'base_name', 'job_id', 'created_at', 'user_name'], job)) for job in jobs] 

# ==============================================================
# MONITOR SLURM
# ==============================================================

# def get_slurm_job_status(job_id):
#     """Obtém status de um job no Slurm via SSH"""
#     try:
#         if not job_id or str(job_id).strip() == '':
#             print(f"[WARNING] Job ID vazio ou inválido: {job_id}")
#             return None
            
#         job_id_str = str(job_id).strip()
#         print(f"[DEBUG] Obtendo status do job Slurm: {job_id_str}")
        
#         # Primeiro tenta com squeue (jobs ativos)
#         cmd_squeue = f"squeue -j {job_id_str} -o %T --noheader"
#         exit_code, out_squeue, err_squeue = run_remote_cmd(cmd_squeue)
        
#         print(f"[DEBUG] squeue cmd: {cmd_squeue}")
#         print(f"[DEBUG] squeue exit: {exit_code}")
#         print(f"[DEBUG] squeue output: '{out_squeue}'")
#         print(f"[DEBUG] squeue error: '{err_squeue}'")
        
#         if exit_code == 0 and out_squeue and out_squeue.strip():
#             status = out_squeue.strip()
#             print(f"[DEBUG] Status do squeue: {status}")
#             return status
        
#         # Se não encontrou no squeue, tenta com sacct (jobs históricos)
#         cmd_sacct = f"sacct -j {job_id_str} -o State --noheader --parsable2"
#         exit_code, out_sacct, err_sacct = run_remote_cmd(cmd_sacct)
        
#         print(f"[DEBUG] sacct cmd: {cmd_sacct}")
#         print(f"[DEBUG] sacct exit: {exit_code}")
#         print(f"[DEBUG] sacct output: '{out_sacct}'")
#         print(f"[DEBUG] sacct error: '{err_sacct}'")
        
#         if exit_code == 0 and out_sacct and out_sacct.strip():
#             states = [s.strip() for s in out_sacct.strip().split('\n') if s.strip()]
#             if states:
#                 # Pega o primeiro estado válido
#                 for state in states:
#                     if state and state != '':
#                         status = state.split('+')[0]
#                         print(f"[DEBUG] Status do sacct: {status}")
#                         return status
        
#         print(f"[DEBUG] Nenhum status encontrado para job {job_id_str}")
#         return None
        
#     except Exception as e:
#         print(f"[ERROR] Erro ao obter status do job {job_id}: {e}")
#         import traceback
#         traceback.print_exc()
#         return None

def get_slurm_job_status(job_id):
    """Obtém status de um job no Slurm via SSH"""
    try:
        if not job_id or str(job_id).strip() == '':
            return None
            
        job_id_str = str(job_id).strip()
        
        # Primeiro tenta com squeue (jobs ativos)
        cmd_squeue = f"squeue -j {job_id_str} -o %T --noheader"
        exit_code, out_squeue, err_squeue = run_remote_cmd(cmd_squeue)
        
        # Se o comando falhou com "Invalid job id", o job não existe mais
        if "Invalid job id" in err_squeue:
            return None  # Job não existe mais no Slurm
        
        if exit_code == 0 and out_squeue and out_squeue.strip():
            return out_squeue.strip()
        
        # Se accounting estiver desabilitado, não tente sacct
        if "accounting storage is disabled" in err_squeue:
            return None
        
        # Tenta com sacct (jobs históricos) apenas se não houver erro de accounting
        cmd_sacct = f"sacct -j {job_id_str} -o State --noheader --parsable2"
        exit_code, out_sacct, err_sacct = run_remote_cmd(cmd_sacct)
        
        if exit_code == 0 and out_sacct and out_sacct.strip():
            states = [s.strip() for s in out_sacct.strip().split('\n') if s.strip()]
            if states:
                for state in states:
                    if state and state != '':
                        return state.split('+')[0]
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Erro ao obter status do job {job_id}: {e}")
        return None

def get_slurm_queue():
    """Obtém lista de jobs no Slurm via SSH"""
    try:
        cmd = "squeue -o '%i|%u|%j|%T|%b|%C|%m|%L|%P' --noheader"
        exit_code, out, err = run_remote_cmd(cmd) # <--- Usando SSH
        
        if exit_code == 0:
            return parse_slurm_queue_output(out)
        

        print(f"Erro ao obter fila Slurm via SSH: {err}")
        return []
    except Exception as e:
        print(f"Erro ao obter fila Slurm: {e}")
        return []

# def update_job_status_from_slurm():
#     """Atualiza status dos jobs no banco baseado no Slurm"""
#     try:
#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         # Busca jobs com job_id preenchido
#         cursor.execute("""
#             SELECT id, base_name, job_id, status, user_id
#             FROM uploads 
#             WHERE job_id IS NOT NULL AND status IN ('PENDENTE', 'PROCESSANDO')
#         """)
        
#         jobs = cursor.fetchall()
#         updated_count = 0
        
#         for job_id, base_name, slurm_job_id, current_status, user_id in jobs:
#             # Inicializar a variável
#             slurm_status = None
            
#             try:
#                 slurm_status = get_slurm_job_status(slurm_job_id)
#             except Exception as e:
#                 print(f"[ERROR] Erro ao obter status para job {slurm_job_id}: {e}")
#                 continue  # Pula para o próximo job
            
#             # DEBUG: Adicionar log para verificar o que está sendo retornado
#             print(f"[DEBUG1] Job {slurm_job_id} -> Slurm status: {slurm_status}")
            
#             # SE slurm_status for None ou vazio, pule este job
#             if not slurm_status:
#                 print(f"[DEBUG2] Status vazio para job {slurm_job_id}, pulando...")
#                 continue
            
#             # Inicializar new_status com o valor atual
#             new_status = current_status
            
#             # Mapear status Slurm para nossos status
#             if slurm_status in ['PENDING', 'PD', 'CF', 'S']:
#                 new_status = 'PENDENTE'
#             elif slurm_status in ['RUNNING', 'R', 'ST', 'CG']:
#                 new_status = 'PROCESSANDO'
#             elif slurm_status in ['COMPLETED', 'CD']:
#                 new_status = 'COMPLETO'
#             elif slurm_status in ['FAILED', 'F', 'TO', 'NF', 'CA', 'DL']:
#                 new_status = 'ERRO'
#             else:
#                 print(f"[DEBUG3] Status desconhecido: {slurm_status}, mantendo {current_status}")
            
#             # DEBUG: Mostrar mapeamento
#             print(f"[DEBUG4] Slurm status: {slurm_status}, Mapeando de {current_status} para: {new_status}")
            
#             # Atualizar se mudou
#             if new_status != current_status:
#                 updated_at = datetime.now().isoformat()
                
#                 cursor.execute(
#                     "UPDATE uploads SET status = ?, updated_at = ? WHERE id = ?",
#                     (new_status, updated_at, job_id)
#                 )
                
#                 # Log da mudança
#                 log_action(
#                     user_id, 
#                     f'Status atualizado: {current_status} → {new_status}', 
#                     f'Job {base_name} (Slurm: {slurm_job_id})'
#                 )
                
#                 print(f"[SLURM MONITOR] Job {base_name} atualizado: {current_status} -> {new_status}")
#                 updated_count += 1
                
#                 # Se terminou, verificar output
#                 if new_status in ['COMPLETO', 'ERRO']:
#                     check_job_output(slurm_job_id, base_name, user_id, new_status)
        
#         conn.commit()
#         conn.close()
        
#         if updated_count > 0:
#             print(f"[SLURM MONITOR] {updated_count} jobs atualizados")
            
#     except Exception as e:
#         print(f"[SLURM MONITOR] Erro ao atualizar status: {e}")
#         import traceback
#         traceback.print_exc()

def update_job_status_from_slurm():
    """Atualiza status dos jobs no banco baseado no Slurm"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Busca jobs com job_id preenchido
        cursor.execute("""
            SELECT id, base_name, job_id, status, user_id
            FROM uploads 
            WHERE job_id IS NOT NULL AND status IN ('PENDENTE', 'PROCESSANDO')
        """)
        
        jobs = cursor.fetchall()
        updated_count = 0
        
        for job_id, base_name, slurm_job_id, current_status, user_id in jobs:
            # SEMPRE inicializar slurm_status como None
            slurm_status = None
            
            try:
                slurm_status = get_slurm_job_status(slurm_job_id)
                print(f"[DEBUG] Job {slurm_job_id} -> Slurm status: {slurm_status}")
            except Exception as e:
                print(f"[ERROR] Erro ao obter status para job {slurm_job_id}: {e}")
                # Se deu erro, marca como ERRO para não ficar travado
                new_status = 'ERRO'
                
                cursor.execute(
                    "UPDATE uploads SET status = ?, updated_at = ?, error_log = ? WHERE id = ?",
                    (new_status, datetime.now().isoformat(), f"Erro ao obter status: {e}", job_id)
                )
                updated_count += 1
                continue  # Pula para o próximo job
            
            # SE slurm_status for None, vazio, ou erro no Slurm
            if not slurm_status:
                print(f"[WARNING] Status vazio para job {slurm_job_id}. Verificando se job existe...")
                
                # Se o job estava PROCESSANDO e agora não existe mais no Slurm, provavelmente terminou
                if current_status == 'PROCESSANDO':
                    # Verifica se o output foi gerado
                    if check_job_completed_on_server(base_name, user_id):
                        new_status = 'COMPLETO'
                    else:
                        new_status = 'ERRO'
                    
                    cursor.execute(
                        "UPDATE uploads SET status = ?, updated_at = ? WHERE id = ?",
                        (new_status, datetime.now().isoformat(), job_id)
                    )
                    
                    print(f"[AUTO-FIX] Job {base_name} marcado como {new_status} (não encontrado no Slurm)")
                    updated_count += 1
                
                continue  # Pula para o próximo job
            
            # Mapear status Slurm para nossos status
            new_status = current_status  # Mantém o atual por padrão
            
            if slurm_status in ['PENDING', 'PD', 'CF', 'S']:
                new_status = 'PENDENTE'
            elif slurm_status in ['RUNNING', 'R', 'ST', 'CG']:
                new_status = 'PROCESSANDO'
            elif slurm_status in ['COMPLETED', 'CD']:
                new_status = 'COMPLETO'
            elif slurm_status in ['FAILED', 'F', 'TO', 'NF', 'CA', 'DL']:
                new_status = 'ERRO'
            
            # Atualizar se mudou
            if new_status != current_status:
                updated_at = datetime.now().isoformat()
                
                cursor.execute(
                    "UPDATE uploads SET status = ?, updated_at = ? WHERE id = ?",
                    (new_status, updated_at, job_id)
                )
                
                # Log da mudança
                log_action(
                    user_id, 
                    f'Status atualizado: {current_status} → {new_status}', 
                    f'Job {base_name} (Slurm: {slurm_job_id})'
                )
                
                print(f"[SLURM MONITOR] Job {base_name} atualizado: {current_status} -> {new_status}")
                updated_count += 1
                
                # Se terminou, verificar output
                if new_status in ['COMPLETO', 'ERRO']:
                    check_job_output(slurm_job_id, base_name, user_id, new_status)
        
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            print(f"[SLURM MONITOR] {updated_count} jobs atualizados")
            
    except Exception as e:
        print(f"[SLURM MONITOR] Erro ao atualizar status: {e}")
        import traceback
        traceback.print_exc()

def check_job_completed_on_server(base_name, user_id):
    """Verifica se o job gerou output no servidor mesmo sem info do Slurm"""
    try:
        from conections import get_ssh_connection
        import paramiko
        
        user_name = None
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if user:
            user_name = user[0].replace(' ', '')
        conn.close()
        
        if not user_name:
            return False
            
        ssh = get_ssh_connection()
        
        # Verifica se o diretório de output existe e tem arquivos
        output_dir = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name}/{base_name}/{ALPHAFOLD_PREDICTION}"
        check_cmd = f"if [ -d \"{output_dir}\" ]; then find \"{output_dir}\" -name \"*.cif\" -o -name \"*.pdb\" | head -1 | wc -l; else echo 0; fi"
        
        stdin, stdout, stderr = ssh.exec_command(check_cmd)
        result = stdout.read().decode().strip()
        ssh.close()
        
        has_files = int(result) > 0 if result.isdigit() else False
        
        print(f"[CHECK OUTPUT] Job {base_name} tem arquivos de output: {has_files}")
        return has_files
        
    except Exception as e:
        print(f"[ERROR] Erro ao verificar output: {e}")
        return False

def check_job_output(job_id, base_name, user_id, status):
    """Verifica output do job terminado"""
    try:
        output_file = f"/tmp/slurm_scripts/af_{base_name}_*.out"
        
        # Procura arquivo de output
        import glob
        files = glob.glob(output_file)
        
        if files:
            with open(files[0], 'r') as f:
                output = f.read()
            
            # Verifica se houve erro no AlphaFold
            if status == 'CONCLUIDO' and 'ERROR' in output.upper():
                # Job terminou mas teve erro no AlphaFold
                conn = get_db_connection()
                conn.execute(
                    "UPDATE uploads SET status = 'ERRO', error_log = ? WHERE base_name = ?",
                    (output[-5000:], base_name)  # Salva últimos 5000 chars
                )
                conn.commit()
                conn.close()
                
                log_action(user_id, 'Erro no AlphaFold', base_name)
        
    except Exception as e:
        print(f"Erro ao verificar output do job {job_id}: {e}")

# ==============================================================
# GERENCIAMENTO DE PRIORIDADE
# ==============================================================

def get_next_job():
    """Obtém o próximo job a ser executado baseado em prioridade"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Prioridade: jobs mais antigos primeiro
    cursor.execute("""
        SELECT uploads.id, uploads.base_name, uploads.job_id, uploads.user_id, users.email
        FROM uploads 
        JOIN users ON uploads.user_id = users.id 
        WHERE uploads.status = 'PENDENTE' 
        AND uploads.job_id IS NOT NULL
        ORDER BY uploads.created_at ASC
        LIMIT 1
    """)
    
    job = cursor.fetchone()
    conn.close()
    
    if job:
        return {
            'id': job[0],
            'base_name': job[1],
            'job_id': job[2],
            'user_id': job[3],
            'email': job[4]
        }
    
    return None

def update_job_priority(job_id, priority_change):
    """Atualiza prioridade de um job"""
    conn = get_db_connection()
    
    # Implementação simples: atualizar created_at para mudar ordem
    if priority_change == 'up':
        # Aumenta prioridade (torna mais recente negativamente)
        new_date = (datetime.now() - timedelta(days=365)).isoformat()
    elif priority_change == 'down':
        # Diminui prioridade (torna mais antigo)
        new_date = (datetime.now() + timedelta(days=365)).isoformat()
    else:
        return False
    
    conn.execute(
        "UPDATE uploads SET created_at = ? WHERE id = ?",
        (new_date, job_id)
    )
    conn.commit()
    conn.close()
    
    return True

def cancel_job(job_id, user_id=None):
    """Cancela um job no Slurm"""
    try:
        # Primeiro obtém o job_id do Slurm
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT job_id, base_name FROM uploads WHERE id = ?",
            (job_id,)
        )
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return False, "Job não encontrado"
        
        slurm_job_id, base_name = result
        
        # Verifica permissão (se user_id fornecido)
        if user_id:
            cursor.execute(
                "SELECT user_id FROM uploads WHERE id = ?",
                (job_id,)
            )
            owner = cursor.fetchone()
            if owner and owner[0] != user_id:
                conn.close()
                return False, "Permissão negada: você não é o dono deste job"
        
        # Cancela no Slurm
        result = subprocess.run(
            ['scancel', str(slurm_job_id)],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Atualiza status no banco
            cursor.execute(
                "UPDATE uploads SET status = 'CANCELADO', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), job_id)
            )
            conn.commit()
            
            # Log
            log_action(user_id or 0, 'Job cancelado', f'{base_name} (Slurm: {slurm_job_id})')
            
            conn.close()
            return True, f"Job {slurm_job_id} cancelado com sucesso"
        else:
            conn.close()
            return False, f"Erro ao cancelar job: {result.stderr}"
            
    except Exception as e:
        return False, f"Erro: {str(e)}"

# ==============================================================
# SCHEDULER DO SLURM
# ==============================================================

# try:
#     from apscheduler.schedulers.background import BackgroundScheduler
    
#     scheduler = BackgroundScheduler()
    
#     @scheduler.scheduled_job('interval', seconds=30)
#     def scheduled_status_update():
#         """Atualiza status dos jobs periodicamente"""
#         with app.app_context():
#             try:
#                 update_job_status_from_slurm()
#             except Exception as e:
#                 print(f"[SCHEDULER] Erro: {e}")
    
#     def start_slurm_monitor():
#         """Inicia o monitor do Slurm"""
#         if not scheduler.running:
#             scheduler.start()
#             print("[SLURM MONITOR] Iniciado")
    
#     def stop_slurm_monitor():
#         """Para o monitor do Slurm"""
#         if scheduler.running:
#             scheduler.shutdown()
#             print("[SLURM MONITOR] Parado")
    
# except ImportError:
#     print("[AVISO] APScheduler não instalado. Monitor Slurm desabilitado.")
    
#     def start_slurm_monitor():
#         print("[SLURM MONITOR] APScheduler não instalado. Use: pip install apscheduler")
    
#     def stop_slurm_monitor():
#         pass

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    
    scheduler = BackgroundScheduler()
    
    @scheduler.scheduled_job('interval', seconds=30)
    def scheduled_status_update():
        """Atualiza status dos jobs periodicamente"""
        with app.app_context():  # ADICIONAR CONTEXTO AQUI
            try:
                update_job_status_from_slurm()
            except Exception as e:
                print(f"[SCHEDULER] Erro: {e}")
    
    def start_slurm_monitor():
        """Inicia o monitor do Slurm"""
        if not scheduler.running:
            scheduler.start()
            print("[SLURM MONITOR] Iniciado")
    
    def stop_slurm_monitor():
        """Para o monitor do Slurm"""
        if scheduler.running:
            scheduler.shutdown()
            print("[SLURM MONITOR] Parado")
    
    # Inicia automaticamente ao importar - COM CONTEXTO
    try:
        with app.app_context():
            start_slurm_monitor()
    except Exception as e:
        print(f"[ERRO] Falha ao iniciar monitor Slurm: {e}")
        
except ImportError:
    print("[AVISO] APScheduler não instalado. Monitor Slurm desabilitado.")
    
    def start_slurm_monitor():
        print("[SLURM MONITOR] APScheduler não instalado. Use: pip install apscheduler")
    
    def stop_slurm_monitor():
        pass

# ==============================================================
# INICIALIZAÇÃO
# ==============================================================

# Inicia automaticamente ao importar
try:
    start_slurm_monitor()
except Exception as e:
    print(f"[ERRO] Falha ao iniciar monitor Slurm: {e}")