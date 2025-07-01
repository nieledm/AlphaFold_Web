from flask import render_template, redirect, url_for, flash,session
from database import get_db_connection

from flask import Blueprint
users_bp = Blueprint('users', __name__, template_folder='templates')

# ==============================================================
# ROTAS DE USUÁRIO
# ==============================================================
@users_bp.route('/dashboard')
def dashboard():
    """Painel principal do usuário"""
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('aut.login'))

    print("Sessão após login:", dict(session))
    
    conn = get_db_connection()
    uploads = conn.execute(
        "SELECT * FROM uploads WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    dict(session)

    return render_template('dashboard.html', 
                           nome_usuario=session.get('user_name', 'Usuário'), 
                           uploads=uploads,
                           active_page='dashboard')    

@users_bp.route('/aviso/<int:aviso_id>')
def aviso(aviso_id):
    """Exibe mensagens de aviso"""
    avisos = {
        1: "Um email de confimação foi enviado para o endereço de email cadastrado. Por favor, verifique a sua caixa de entrada (ou spam) para confirmar o seu e-mail.", 
        2: "Seu e-mail foi confirmado! Agora é só aguardar a aprovação do administrador.",
        3: "A sua conta foi ativada com sucesso!",
    }
    return render_template('base_avisos.html', aviso_mensagem=avisos.get(aviso_id, "Aviso desconhecido."))

@users_bp.route('/sobre')
def sobre():
    return render_template('sobre.html',
                           active_page='sobre',
                           nome_usuario=session.get('user_name', 'Usuário'))