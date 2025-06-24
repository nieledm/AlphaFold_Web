import paramiko
from database import get_db_connection

def get_system_status(ssh_host, ssh_port, ssh_user):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ssh_host, port=ssh_port, username=ssh_user)

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
