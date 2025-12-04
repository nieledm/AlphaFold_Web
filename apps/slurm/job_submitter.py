import uuid
import shlex
from .utils import run_remote_cmd
import base64

SBATCH_DIR = "/tmp/slurm_scripts"

import base64

def submit_slurm_job(cmd, user, base_name, gpu=1, cpus=8, mem="32G", time="24:00:00"):
    job_uid = uuid.uuid4().hex[:8]
    job_name = f"af_{base_name}_{job_uid}"
    
    script_content = f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output={SBATCH_DIR}/{job_name}.out
#SBATCH --error={SBATCH_DIR}/{job_name}.err
#SBATCH --gres=gpu:{gpu}
#SBATCH -p all
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
#SBATCH -t {time}

echo "Job iniciado em $(date)"
echo "Node: $SLURMD_NODENAME"

{cmd}

echo "Job finalizado em $(date)"
"""
    
    # Codificar em base64 para evitar problemas de escape
    script_b64 = base64.b64encode(script_content.encode()).decode()
    
    # Comando seguro para criar script
    ssh_cmd = f"""mkdir -p {SBATCH_DIR} && echo '{script_b64}' | base64 -d > '{SBATCH_DIR}/{job_name}.sh' && chmod +x '{SBATCH_DIR}/{job_name}.sh'"""
    
    exit_code, out, err = run_remote_cmd(ssh_cmd)
    if exit_code != 0:
        raise RuntimeError(f"Erro salvando script: {err}")
    
    ssh_cmd = f"""mkdir -p {SBATCH_DIR} && cat > '{SBATCH_DIR}/{job_name}.sh' << 'EOF'
{script_content}
EOF
chmod +x '{SBATCH_DIR}/{job_name}.sh'"""
    
    exit_code, out, err = run_remote_cmd(ssh_cmd)
    if exit_code != 0:
        raise RuntimeError(f"Erro salvando script: {err}\nComando: {ssh_cmd}")
    
    # Submeter job
    exit_code, out, err = run_remote_cmd(f"sbatch '{SBATCH_DIR}/{job_name}.sh'")
    if exit_code != 0:
        raise RuntimeError(f"Erro submetendo job: {err}")
    
    # Extrair job ID
    try:
        job_id = out.strip().split()[-1]
        return job_id
    except:
        raise RuntimeError(f"Erro extraindo job_id. Resposta: {out}")