from flask import render_template, session, redirect, url_for, flash
from database import get_db_connection
from apps.logs.utils import log_action
from .utils import get_system_status, get_job_counts, get_pending_jobs, parse_system_status

from flask import Blueprint
monitor_bp = Blueprint('monitor', __name__, template_folder='../../templates')

from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER

@monitor_bp.route('/status')
def status_page():
    try:
        raw_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
    except Exception as e:
        raw_status = {"error": str(e)}

    status = parse_system_status(raw_status) if 'error' not in raw_status else None

    # running_jobs, pending_jobs = get_job_counts()
    # queue_jobs = get_pending_jobs() if session.get("is_admin") else []
    running_count, pending_count = get_job_counts()
    pending_jobs_list = get_pending_jobs() if session.get("is_admin") else []
    queue_jobs = []

    return render_template('status_page.html',
                         status=status,
                         error=raw_status.get('error'),
                        #  running_jobs=running_jobs,
                        #  pending_jobs=pending_jobs,
                        running_count=running_count,
                         pending_count=pending_count,
                         pending_jobs_list=pending_jobs_list,
                         queue_jobs=queue_jobs, 
                         is_admin=session.get("is_admin", False),
                         nome_usuario=session.get('user_name', 'Usuário'),
                         active_page='status') 

@monitor_bp.route('/cancel/<base_name>', methods=['POST']) 
def cancel_job(base_name):
    """Cancela jobs como usuário padrão"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status_page'))

    conn = get_db_connection()
    conn.execute("UPDATE uploads SET status = 'CANCELADO' WHERE base_name = ? AND status = 'PENDENTE'", (base_name,))
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Job cancelado", base_name)
    flash(f"Job {base_name} cancelado.", "info")
    return redirect(url_for('monitor.status_page'))

@monitor_bp.route('/force_cancel/<base_name>', methods=['POST'])
def force_cancel_job(base_name):
    """Cancela jobs como admin"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status_page'))

    conn = get_db_connection()
    job = conn.execute("SELECT * FROM uploads WHERE base_name = ? AND status = 'PROCESSANDO'", (base_name,)).fetchone()
    
    if not job:
        flash("Job não encontrado ou não está em processamento.", "warning")
        return redirect(url_for('monitor.status_page'))

    # Marcar como CANCELADO à força
    conn.execute("UPDATE uploads SET status = 'CANCELADO' WHERE base_name = ?", (base_name,))
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Cancelamento forçado", base_name)
    flash(f"Job {base_name} cancelado à força.", "info")
    return redirect(url_for('monitor.status_page'))


@monitor_bp.route('/increase_priority/<base_name>', methods=['POST'])
def increase_priority(base_name):
    """Dá prioridade para algum job em espera"""
    if not session.get('is_admin'):
        flash("Acesso negado", "danger")
        return redirect(url_for('monitor.status_page'))

    conn = get_db_connection()
    conn.execute(
        "UPDATE uploads SET priority = priority + 1 WHERE base_name = ? AND status = 'PENDENTE'",
        (base_name,)
    )
    conn.commit()
    conn.close()

    log_action(session.get("user_id"), "Prioridade aumentada", base_name)
    flash(f"Prioridade do job {base_name} aumentada.", "info")
    return redirect(url_for('monitor.status_page'))