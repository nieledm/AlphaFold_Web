from flask import render_template, current_app, session, redirect, url_for, flash
from database import get_db_connection
from apps.logs.utils import log_action
from .utils import get_system_status, get_job_counts, get_pending_jobs, parse_system_status

from flask import Blueprint
monitor_bp = Blueprint('monitor', __name__, template_folder='../../templates')

from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER
import paramiko

# @monitor_bp.route('/status')
# def status_page():   
#     try:
#         system_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
#     except Exception as e:
#         system_status = {"error": str(e)}

#     running_jobs, pending_jobs = get_job_counts()
#     queue_jobs = get_pending_jobs() if session.get("is_admin") else []

#     return render_template('status_page.html',
#                            status=system_status,
#                            running_jobs=running_jobs,
#                            pending_jobs=pending_jobs,
#                            queue_jobs=queue_jobs,
#                            is_admin=session.get("is_admin", False))

@monitor_bp.route('/status')
def status_page():
    try:
        raw_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
    except Exception as e:
        raw_status = {"error": str(e)}

    status = parse_system_status(raw_status) if 'error' not in raw_status else None

    running_jobs, pending_jobs = get_job_counts()
    queue_jobs = get_pending_jobs() if session.get("is_admin") else []

    return render_template('status_page.html',
                           status=status,
                           error=raw_status.get('error'),
                           running_jobs=running_jobs,
                           pending_jobs=pending_jobs,
                           queue_jobs=queue_jobs,
                           is_admin=session.get("is_admin", False),
                           nome_usuario=session.get('user_name', 'Usuário'),
                           active_page='status')  


@monitor_bp.route('/cancel/<base_name>', methods=['POST'])
def cancel_job(base_name):
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