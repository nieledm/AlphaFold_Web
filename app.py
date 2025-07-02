from flask import request, g, jsonify
from database import get_db_connection, init_db

from config import app

from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER
import paramiko


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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5055)
