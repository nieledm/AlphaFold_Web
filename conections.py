import paramiko
from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER

def get_ssh_connection():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        hostname=ALPHAFOLD_SSH_HOST,
        port=ALPHAFOLD_SSH_PORT,
        username=ALPHAFOLD_SSH_USER,
        allow_agent=True,
        look_for_keys=True
    )
    return ssh
