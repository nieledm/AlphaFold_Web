from flask import request, g, jsonify
from database import get_db_connection, init_db
from threading import Thread
from apps.monitor.utils import job_manager_loop
from config import app
from datetime import datetime

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
# BLUE PRINTS
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
# GERENCIADOR DE JOBS (fila AlphaFold)
# ==============================================================

def start_job_manager():
    """Inicia o loop do gerenciador de jobs em thread separada"""
    t = Thread(target=job_manager_loop, daemon=True)
    t.start()
    print("[JobManager] Loop de gerenciamento iniciado em background.")

# Inicia o gerenciador de jobs antes do app
start_job_manager()
# ==============================================================

if __name__ == '__main__':
    init_db()
    start_job_manager()  # inicia o loop antes do servidor Flask
    app.run(debug=True, host='0.0.0.0', port=5055)
