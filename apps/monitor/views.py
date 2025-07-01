from flask import render_template, current_app, session, redirect, url_for, flash
from database import get_db_connection
from apps.logs.utils import log_action
from .utils import get_system_status, get_job_counts, get_pending_jobs

from flask import Blueprint
monitor_bp = Blueprint('monitor', __name__, template_folder='../../templates')

@monitor_bp.route('/status')
def status_page():
    cfg = current_app.config
    try:
        system_status = get_system_status(
            cfg['ALPHAFOLD_SSH_HOST'],
            cfg['ALPHAFOLD_SSH_PORT'],
            cfg['ALPHAFOLD_SSH_USER']
        )
    except Exception as e:
        system_status = {"error": str(e)}

    running_jobs, pending_jobs = get_job_counts()
    queue_jobs = get_pending_jobs() if session.get("is_admin") else []

    return render_template('status_page.html',
                           status=system_status,
                           running_jobs=running_jobs,
                           pending_jobs=pending_jobs,
                           queue_jobs=queue_jobs,
                           is_admin=session.get("is_admin", False))

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