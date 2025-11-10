
import json
import re
import paramiko
import select
import time
import shlex
from database import get_db_connection
from conections import get_ssh_connection

from apps.logs.utils import log_action
from config import ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, app
                 
from apps.emails.utils import send_email, send_processing_complete_email

# ==============================================================
# FUNÇÕES DE VALIDAÇÃO
# ==============================================================
def validar_json_input(json_path):
    """Valida o arquivo JSON de entrada para o AlphaFold"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return False, "O arquivo JSON deve conter um dicionário de cadeias."

        for chain_id, sequence in data.items():
            if not isinstance(sequence, str):
                return False, f"A cadeia '{chain_id}' deve conter apenas uma sequência como string."

            if "\n" in sequence or ">" in sequence:
                return False, f"A cadeia '{chain_id}' contém quebras de linha ou formatação FASTA."

            if not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", sequence, re.IGNORECASE):
                return False, f"A cadeia '{chain_id}' contém caracteres inválidos. Apenas aminoácidos padrão são permitidos."

        return True, "OK"

    except Exception as e:
        return False, f"Erro ao validar JSON: {str(e)}"

def run_alphafold_in_background(cmd, user_name, user_email, base_name, user_id):
    with app.app_context():
        log_action(user_id, 'Executando AlphaFold', base_name)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh = get_ssh_connection()

            user_dir = user_name.replace(' ', '')

            input_path = shlex.quote(f"{ALPHAFOLD_INPUT_BASE}/{user_dir}")
            output_path = shlex.quote(f"{ALPHAFOLD_OUTPUT_BASE}/{user_dir}/{base_name}")
            
            mkdir = f"mkdir -p {input_path} {output_path}"
            ssh.exec_command(mkdir)

            stdin, stdout, stderr = ssh.exec_command(cmd)

            # -------------- LOG EM TEMPO REAL --------------
            stdout_lines = []
            stderr_lines = []

            while not stdout.channel.exit_status_ready():
                rl, wl, xl = select.select([stdout.channel], [], [], 1.0)
                if rl:
                    line = stdout.readline()
                    if line:
                        stdout_lines.append(line.strip())

                rl_err, _, _ = select.select([stderr.channel], [], [], 1.0)
                if rl_err:
                    err_line = stderr.readline()
                    if err_line:
                        stderr_lines.append(err_line.strip())

            # Após o término, registra os logs em lote:
            for line in stdout_lines:
                log_action(user_id, 'AlphaFold output', line)
            for line in stderr_lines:
                log_action(user_id, 'AlphaFold error', line)
            # -------------- FIM DO LOOP ---------------------

            exit_status = stdout.channel.recv_exit_status()
            log_action(user_id, 'Exit status', str(exit_status))

            remote_cif = f"output_path/" \
                        f"alphafold_prediction/alphafold_prediction_model.cif"
            
            check_cmd = f'test -f "{remote_cif}" && echo OK || echo NO'

            # Verificar se arquivo de resultado foi gerado (espera até 60s)
            result_exists = False
            wait_time = 0

            while wait_time < 60:
                stdin, stdout, _ = ssh.exec_command(check_cmd)
                result = stdout.read().decode().strip()
                if result == "OK":
                    result_exists = True
                    break
                time.sleep(5)
                wait_time += 5

            with get_db_connection() as conn:
                if result_exists and exit_status == 0:
                    conn.execute("UPDATE uploads SET status='COMPLETO' WHERE base_name=?", (base_name,))
                    conn.commit()
                    log_action(user_id, 'Processamento CONCLUÍDO', remote_cif)
                    send_processing_complete_email(user_name, user_email, base_name, user_id)
                else:
                    conn.execute("UPDATE uploads SET status='ERRO' WHERE base_name=?", (base_name,))
                    conn.commit()
                    log_action(user_id, 'Processamento ERRO',
                            f'Exit={exit_status}, arquivo existe? {result_exists}')
                    send_email(user_email, "Erro no processamento do AlphaFold",
                            f"<p>Olá {user_name},</p><p>Ocorreu um erro e o arquivo de resultado não foi gerado.</p>")
        except Exception as e:
            log_action(user_id, 'Falha run_alphafold', str(e))
            try:
                send_email(user_email, "Erro na execução AlphaFold",
                        f"<p>Olá {user_name},</p><p>Ocorreu um erro inesperado: {e}</p>")
            except Exception as mail_err:
                log_action(user_id, 'Erro ao enviar e-mail', str(mail_err))
        finally:
            ssh.close()