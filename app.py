from flask import request, g, jsonify
from database import get_db_connection, init_db
from threading import Thread
from config import app
from datetime import datetime
from flask_socketio import SocketIO
from apps.monitor.utils import start_slurm_monitor

# ==============================================================
# DATA E HORÁRIO
# ==============================================================

def format_datetime(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return value.strftime(format)

app.jinja_env.filters['format_datetime'] = format_datetime

# ==============================================================
# 📦 BLUE PRINTS
# ==============================================================

from apps.autentication.views import aut_bp
app.register_blueprint(aut_bp)

from apps.monitor.views import monitor_bp
app.register_blueprint(monitor_bp)

from apps.emails.utils import emails_bp
app.register_blueprint(emails_bp)

from apps.logs.views import logs_bp
app.register_blueprint(logs_bp)

from apps.alphafold.views import apf_bp
app.register_blueprint(apf_bp)

from apps.admin_rotas.views import admins_bp
app.register_blueprint(admins_bp)

from apps.users_rotas.views import users_bp
app.register_blueprint(users_bp)

from apps.configuration.views import config_bp
app.register_blueprint(config_bp)

from apps.slurm import slurm_bp
app.register_blueprint(slurm_bp, url_prefix="/slurm")

# ==============================================================
# FUNÇÕES DE CONTEXTO E INICIALIZAÇÃO
# ==============================================================
@app.context_processor
def inject_user():
    """Injeta variáveis em todos os templates"""
    return dict(nome_usuario=getattr(g, 'nome_usuario', 'Usuário'))

@app.route('/check_status')
def check_status():
    job_id = request.args.get('job_id')
    conn = get_db_connection()
    status = conn.execute('SELECT status FROM uploads WHERE base_name = ?', (job_id,)).fetchone()
    conn.close()
    return jsonify({'status': status[0] if status else 'DESCONHECIDO'})

# ==============================================================
# SOCKET.IO (para atualização em tempo real)
# ==============================================================

socketio = SocketIO(app, cors_allowed_origins="*")

# Importa e registra os eventos do Socket.IO
from apps.monitor.socket_events import register_socketio_handlers
register_socketio_handlers(socketio)

# # ==============================================================
# # GERENCIADOR DE JOBS (fila AlphaFold)
# # ==============================================================

# def start_job_manager():
#     """Inicia o loop do gerenciador de jobs em thread separada"""
#     t = Thread(target=job_manager_loop, daemon=True)
#     t.start()
#     print("[JobManager] Loop de gerenciamento iniciado em background.")

# @app.route('/debug_queue')
# def debug_queue():
#     """Endpoint para debug da fila de jobs"""
#     conn = get_db_connection()
    
#     # Status dos jobs
#     status_counts = conn.execute("""
#         SELECT status, COUNT(*) as count 
#         FROM uploads 
#         GROUP BY status
#     """).fetchall()
    
#     # Últimos 10 jobs
#     recent_jobs = conn.execute("""
#         SELECT base_name, status, created_at, user_id 
#         FROM uploads 
#         ORDER BY created_at DESC 
#         LIMIT 10
#     """).fetchall()
    
#     # Containers em execução
#     from apps.monitor.utils import get_running_container_count, get_max_containers
#     running_containers = get_running_container_count()
#     max_containers = get_max_containers()
    
#     conn.close()
    
#     return jsonify({
#         'status_counts': dict(status_counts),
#         'recent_jobs': [dict(job) for job in recent_jobs],
#         'containers': {
#             'running': running_containers,
#             'max': max_containers
#         }
#     })
# ==============================================================

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5055)