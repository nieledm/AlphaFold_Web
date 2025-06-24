import threading
import time
import paramiko
import select
from database import get_db_connection
from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER, \
                 ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, ALPHAFOLD_PARAMS, ALPHAFOLD_DB, \
                EMAIL_SENDER, EMAIL_PASSWORD, serializer
from apps.logs import log_action
from apps.emails import send_processing_complete_email

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # para acessar app.py e database.py diretamente

from database import get_db_connection
from flask import Flask
import smtplib
from email.mime.text import MIMEText

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

    # Pegamos dados do usuário
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
