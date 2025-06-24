import subprocess
import sqlite3
from datetime import datetime
import pytz
import time
from database import get_db_connection, init_db, DATABASE

def log_action(user_id, action, details=None):
    """Registra uma ação no banco de dados de logs com retry."""
    attempts = 3
    delay = 0.1  # segundos

    tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(tz)
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    for i in range(attempts):
        try:
            conn = get_db_connection()
            try:
                conn.execute(
                    'INSERT INTO logs (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)',
                    (user_id, action, timestamp, details)
                )
                conn.commit()
                break  # sucesso, sai do loop
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and i < attempts - 1:
                    time.sleep(delay)
                    delay *= 2  # exponencial
                    continue  # tenta de novo
                else:
                    print(f"[log_action] Falha ao registrar (tentativa {i+1}): {e}")
            finally:
                conn.close()
        except Exception as e:
            print(f"[log_action] Erro inesperado ao abrir conexão (tentativa {i+1}): {e}")
