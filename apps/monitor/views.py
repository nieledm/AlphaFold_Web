from flask import render_template, session, redirect, url_for, flash, request, jsonify, current_app
from database import get_db_connection
from apps.logs.utils import log_action
from .utils import get_system_status, get_job_counts, get_pending_jobs, parse_system_status
from datetime import datetime, timedelta

from flask import Blueprint
monitor_bp = Blueprint('monitor', __name__, template_folder='../../templates')

from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER

@monitor_bp.route('/status')
def status():
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))
    
    try:
        # Status do sistema
        raw_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
        status = parse_system_status(raw_status)
        
        # Contagens do banco
        conn = get_db_connection()
        
        # Jobs em processamento
        running_jobs = conn.execute("""
            SELECT uploads.base_name, uploads.job_id, uploads.created_at, users.name as user_name
            FROM uploads 
            JOIN users ON uploads.user_id = users.id 
            WHERE uploads.status = 'PROCESSANDO'
            ORDER BY uploads.created_at DESC
        """).fetchall()
        
        # Jobs pendentes
        pending_jobs = conn.execute("""
            SELECT uploads.id, uploads.base_name, uploads.job_id, uploads.created_at, users.name as user_name
            FROM uploads 
            JOIN users ON uploads.user_id = users.id 
            WHERE uploads.status = 'PENDENTE'
            ORDER BY uploads.created_at ASC
        """).fetchall()
        
        # Contagens totais
        total_jobs = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        completed_count = conn.execute("SELECT COUNT(*) FROM uploads WHERE status = 'COMPLETO'").fetchone()[0]
        error_count = conn.execute("SELECT COUNT(*) FROM uploads WHERE status = 'ERRO'").fetchone()[0]
        
        conn.close()
        
        # Contar jobs Slurm por status
        slurm_running_count = len([j for j in status.get('slurm_queue', []) if j.get('state') in ['RUNNING', 'R']])
        slurm_pending_count = len([j for j in status.get('slurm_queue', []) if j.get('state') in ['PENDING', 'PD']])
        
        return render_template('status_page.html',
                               titulo='Status do Servidor',
                               active_page='status',
                               nome_usuario=session.get('user_name', 'Admin'),
                               status=status,
                               running_jobs_list=[dict(job) for job in running_jobs],
                               pending_jobs_list=[dict(job) for job in pending_jobs],
                               running_count=len(running_jobs),
                               total_jobs=total_jobs,
                               completed_count=completed_count,
                               error_count=error_count,
                               slurm_running_count=slurm_running_count,
                               slurm_pending_count=slurm_pending_count)
        
    except Exception as e:
        current_app.logger.error(f"Erro ao obter status: {e}")
        return render_template('status_page.html',
                               titulo='Status do Servidor',
                               active_page='status',
                               nome_usuario=session.get('user_name', 'Admin'),
                               status={},
                               error=str(e))

@monitor_bp.route('/cancel/<base_name>', methods=['POST']) 
def cancel_job(base_name):
    """Cancela jobs como usuário padrão"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status'))

    conn = get_db_connection()
    conn.execute("UPDATE uploads SET status = 'CANCELADO' WHERE base_name = ? AND status = 'PENDENTE'", (base_name,))
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Job cancelado", base_name)
    flash(f"Job {base_name} cancelado.", "info")
    return redirect(url_for('monitor.status'))

@monitor_bp.route('/force_cancel/<base_name>', methods=['POST'])
def force_cancel_job(base_name):
    """Cancela jobs como admin"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status'))

    conn = get_db_connection()
    job = conn.execute("SELECT * FROM uploads WHERE base_name = ? AND status = 'PROCESSANDO'", (base_name,)).fetchone()
    
    if not job:
        flash("Job não encontrado ou não está em processamento.", "warning")
        return redirect(url_for('monitor.status'))

    # Marcar como CANCELADO à força
    conn.execute("UPDATE uploads SET status = 'CANCELADO' WHERE base_name = ?", (base_name,))
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Cancelamento forçado", base_name)
    flash(f"Job {base_name} cancelado à força.", "info")
    return redirect(url_for('monitor.status'))


@monitor_bp.route('/increase_priority/<base_name>', methods=['POST'])
def increase_priority(base_name):
    """Dá prioridade para algum job em espera"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status'))

    conn = get_db_connection()
    conn.execute(
        "UPDATE uploads SET priority = priority + 1 WHERE base_name = ? AND status = 'PENDENTE'",
        (base_name,)
    )
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Prioridade aumentada", base_name)
    flash(f"Prioridade do job {base_name} aumentada.", "info")
    return redirect(url_for('monitor.status'))

@monitor_bp.route('/update_max_containers', methods=['POST'])
def update_max_containers():
    if not session.get("is_admin"):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status'))

    try:
        new_value = int(request.form.get("max_containers"))
        if new_value < 1:
            raise ValueError
        # set_max_containers(new_value)
        flash("Valor atualizado com sucesso.", "success")
    except:
        flash("Valor inválido.", "danger")

    return redirect(url_for('monitor.status'))

@monitor_bp.route('/admin/cleanup_stuck_jobs', methods=['POST'])
def cleanup_stuck_jobs():
    """Limpa jobs presos manualmente"""
    if not session.get('is_admin'):
        flash('Acesso negado', 'danger')
        return redirect(url_for('monitor.status'))
    
    try:
        conn = get_db_connection()
        
        # Conta jobs PROCESSANDO
        stuck_count = conn.execute("SELECT COUNT(*) FROM uploads WHERE status = 'PROCESSANDO'").fetchone()[0]
        
        # Reseta para PENDENTE
        conn.execute("UPDATE uploads SET status = 'PENDENTE' WHERE status = 'PROCESSANDO'")
        conn.commit()
        conn.close()
        
        flash(f'{stuck_count} jobs presos foram resetados para PENDENTE', 'success')
        log_action(session.get('user_id'), 'Cleanup manual', f'Resetados {stuck_count} jobs')
        
    except Exception as e:
        flash(f'Erro ao limpar jobs: {e}', 'danger')
    
    return redirect(url_for('monitor.status'))

@monitor_bp.route('/debug_queue')
def debug_queue():
    """Endpoint para debug da fila de jobs"""
    conn = get_db_connection()
    
    # Status dos jobs
    status_counts = conn.execute("""
        SELECT status, COUNT(*) as count 
        FROM uploads 
        GROUP BY status
    """).fetchall()
    
    # Últimos 10 jobs
    recent_jobs = conn.execute("""
        SELECT base_name, status, job_id, created_at, user_id 
        FROM uploads 
        ORDER BY created_at DESC 
        LIMIT 10
    """).fetchall()
    
    # Obter status atual do Slurm
    from apps.monitor.utils import get_slurm_queue
    slurm_queue = get_slurm_queue()
    
    conn.close()
    
    return jsonify({
        'status_counts': dict(status_counts),
        'recent_jobs': [dict(job) for job in recent_jobs],
        'slurm_queue': slurm_queue,
        'total_jobs': len(slurm_queue)
    })

# Adicione estas rotas ao seu blueprint de monitor

@monitor_bp.route('/cancel-slurm-job/<job_id>', methods=['POST'])
def cancel_slurm_job(job_id):
    """Cancela um job no Slurm"""
    if not session.get('is_admin'):
        flash('Não autorizado', 'danger')
        return redirect(url_for('monitor.status'))
    
    try:
        # Cancela no Slurm
        import subprocess
        result = subprocess.run(['scancel', job_id], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Atualiza status no banco
            conn = get_db_connection()
            conn.execute(
                "UPDATE uploads SET status = 'CANCELADO', updated_at = ? WHERE job_id = ?",
                (datetime.now().isoformat(), job_id)
            )
            conn.commit()
            conn.close()
            
            flash(f'Job {job_id} cancelado com sucesso', 'success')
        else:
            flash(f'Erro ao cancelar job: {result.stderr}', 'danger')
            
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    
    return redirect(url_for('monitor.status'))

@monitor_bp.route('/prioritize-slurm-job/<job_id>', methods=['POST'])
def prioritize_slurm_job(job_id):
    """Prioriza um job no Slurm (admin only)"""
    if not session.get('is_admin'):
        flash('Não autorizado', 'danger')
        return redirect(url_for('monitor.status'))
    
    try:
        # No Slurm, pode-se usar 'scontrol hold' e 'release' para gerenciar prioridade
        # Ou ajustar a data no banco para prioridade no sistema
        conn = get_db_connection()
        conn.execute(
            "UPDATE uploads SET created_at = ? WHERE job_id = ?",
            ((datetime.now() - timedelta(days=365)).isoformat(), job_id)
        )
        conn.commit()
        conn.close()
        
        flash(f'Job {job_id} priorizado', 'success')
        
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    
    return redirect(url_for('monitor.status'))

@monitor_bp.route('/api/slurm/queue')
def api_slurm_queue():
    """API para obter fila Slurm"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    from apps.monitor.utils import get_slurm_queue
    queue = get_slurm_queue()
    
    return jsonify({
        'slurm_queue': queue
    })