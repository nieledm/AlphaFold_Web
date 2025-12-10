import paramiko
from conections import get_ssh_connection

def run_remote_cmd(cmd):
    """
    Executa um comando remoto via SSH e retorna (exit_code, stdout, stderr)
    """
    ssh = None
    try:
        ssh = get_ssh_connection()
        stdin, stdout, stderr = ssh.exec_command(cmd)

        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()

        return exit_code, out, err

    finally:
        if ssh:
            ssh.close()

def debug_run_remote_cmd(cmd):
    """Função de debug para verificar comandos SSH"""
    try:
        from conections import get_ssh_connection
        import paramiko
        
        ssh = get_ssh_connection()
        print(f"[SSH DEBUG] Executando: {cmd}")
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        ssh.close()
        
        print(f"[SSH DEBUG] Exit: {exit_status}")
        print(f"[SSH DEBUG] Output: '{output}'")
        print(f"[SSH DEBUG] Error: '{error}'")
        
        return exit_status, output, error
        
    except Exception as e:
        print(f"[SSH DEBUG ERROR] {e}")
        return 1, "", str(e)

# Adicione esta função para testar a conexão SSH
def test_ssh_connection():
    """Testa a conexão SSH básica"""
    try:
        from conections import get_ssh_connection
        ssh = get_ssh_connection()
        
        # Testa um comando simples
        stdin, stdout, stderr = ssh.exec_command("echo 'test'")
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        ssh.close()
        
        if output.strip() == 'test':
            print("[SSH TEST] Conexão SSH OK")
            return True
        else:
            print(f"[SSH TEST] Erro: output={output}, error={error}")
            return False
            
    except Exception as e:
        print(f"[SSH TEST] Falha na conexão SSH: {e}")
        return False

def slurm_sacct(job_id):
    """
    Retorna status do job via sacct
    """
    cmd = f"sacct -j {job_id} --format=JobID,State,Elapsed,ExitCode -P"
    return run_remote_cmd(cmd)


def slurm_scancel(job_id):
    """
    Cancela o job
    """
    cmd = f"scancel {job_id}"
    return run_remote_cmd(cmd)


def slurm_squeue(user=None):
    """
    Lista jobs na fila
    """
    if user:
        cmd = f"squeue -u {user}"
    else:
        cmd = "squeue"

    return run_remote_cmd(cmd)
