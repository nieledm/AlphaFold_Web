import os
import paramiko
from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER

# def get_ssh_connection():
#     ssh = paramiko.SSHClient()
#     ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

#     ssh.connect(
#         hostname=ALPHAFOLD_SSH_HOST,
#         port=ALPHAFOLD_SSH_PORT,
#         username=ALPHAFOLD_SSH_USER,
#         allow_agent=True,
#         look_for_keys=True
#     )
#     return ssh

def get_ssh_connection():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key_path = '/home/alphaFoldWeb/.ssh/id_ed25519'
    
    if os.path.exists(key_path):
        k = paramiko.Ed25519Key.from_private_key_file(key_path)
        
        ssh.connect(
            hostname=ALPHAFOLD_SSH_HOST,
            port=ALPHAFOLD_SSH_PORT,
            username=ALPHAFOLD_SSH_USER,
            pkey=k,                 # <--- Passa a chave Ed25519 carregada
            allow_agent=False,
            look_for_keys=False
        )
    else:
        raise FileNotFoundError(f"Chave Ed25519 nao encontrada dentro do container em: {key_path}")
        
    return ssh