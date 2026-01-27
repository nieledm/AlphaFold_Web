
import json
import re
import paramiko
import select
import time
import shlex
from database import get_db_connection
from conections import get_ssh_connection

from apps.logs.utils import log_action
from config import ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, ALPHAFOLD_PREDICTION, app
                 
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
    """
    Apenas agenda na fila, não executa diretamente
    """
    with app.app_context():
        log_action(user_id, 'Job agendado na fila', base_name)
        
        # Apenas marca como PENDENTE - o Job Manager fará o resto
        conn = get_db_connection()
        conn.execute(
            "UPDATE uploads SET status = ? WHERE base_name = ? AND user_id = ?",
            ("PENDENTE", base_name, user_id)
        )
        conn.commit()
        conn.close()
        
        log_action(user_id, 'Status Atualizado', f'{base_name} -> PENDENTE (aguardando na fila)')
        
        # Envia email informando que o job foi agendado
        try:
            send_email(user_email, "Job AlphaFold Agendado", 
                      f"<p>Olá {user_name},</p>"
                      f"<p>Seu job <strong>{base_name}</strong> foi agendado na fila de processamento.</p>"
                      f"<p>Você será notificado quando o processamento iniciar e quando terminar.</p>")
        except Exception as mail_err:
            log_action(user_id, 'Erro ao enviar e-mail de agendamento', str(mail_err))