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
