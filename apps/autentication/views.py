from flask import render_template, session, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection, get_user_by_email
from apps.emails.utils import send_verification_email, send_admin_notification, send_email
from apps.logs.utils import log_action
from config import serializer, app
from .utils import validar_email, validar_nome, validar_senha

from flask import Blueprint
aut_bp = Blueprint('aut', __name__, template_folder='../../templates')


# ==============================================================
# ROTAS DE AUTENTICAÇÃO
# ==============================================================
@aut_bp.route('/')
def index():
    """Rota principal que redireciona para login ou dashboard"""
    if 'user_id' in session:
        return redirect(url_for('users.dashboard'))
    return redirect(url_for('aut.login'))


@aut_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Rota de login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = get_user_by_email(email)

        user_id_for_log = None
        if user:
            user_id_for_log = user['id']

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            if user['is_active'] == 0:
                flash('Seu cadastro ainda não foi aprovado.', 'warning')
                log_action(session['user_id'], 'Usuário ainda não aprovado')
            elif user['is_active'] == 2:
                flash('Sua conta foi inativada. Contate o administrador.', 'danger')
                log_action(session['user_id'], 'Usuário com conta inativada')
            elif user['is_active'] == 1:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['is_admin'] = bool(user['is_admin'])
                flash('Login bem-sucedido!', 'success')
                log_action(session['user_id'], 'Login bem-sucedido')
                return redirect(url_for('users.dashboard'))
        else:
            flash('Credenciais inválidas.', 'danger')
            log_action(user_id_for_log, 'Tentativa de Login Falha', f'Credenciais inválidas para o email: {email}')

    return render_template('login.html')

@aut_bp.route('/ver_sessao')
def ver_sessao():
    return dict(session)

@aut_bp.route('/logout')
def logout():
    """Rota de logout"""
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('aut.login'))

@aut_bp.route('/termos', methods=['GET', 'POST'])
def termos_de_uso():
    # Se já aceitou os termos, redireciona para registro
    if session.get('terms_accepted'):
        return redirect(url_for('aut.register'))
    
    if request.method == 'POST':
        # Verifica se TODOS os checkboxes foram marcados
        accept_terms = request.form.get('accept_terms') == 'on'
        accept_alphafold = request.form.get('accept_alphafold') == 'on'
        accept_detic = request.form.get('accept_detic') == 'on'
        
        if accept_terms and accept_alphafold and accept_detic:
            session['terms_accepted'] = True
            session.modified = True
            return redirect(url_for('aut.register'))
        else:
            flash('Você deve aceitar todos os termos para continuar.', 'error')
            return redirect(url_for('aut.termos_de_uso')) 
    
    return render_template('termo_de_uso.html')

@aut_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de registro de novos usuários"""
    # Verifica se os termos foram aceitos
    if not session.get('terms_accepted'):
        flash('Você precisa aceitar os termos de uso antes de se registrar', 'warning')
        return redirect(url_for('aut.termos_de_uso'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']

        if not validar_nome(name):
            flash("Nome precisa conter nome e sobrenome.")
            return render_template('register.html', name=name, email=email)

        if not validar_email(email):
            flash("E-mail deve ser institucional válido.", name=name, email=email)
            return render_template('register.html', name=name, email=email)

        if password != password_confirm:
            flash("Senhas não conferem.")
            return render_template('register.html', name=name, email=email)

        if not validar_senha(password):
            flash("Senha deve conter mínimo 8 caracteres, letras maiúsculas, minúsculas, números e caracteres especiais.")
            return render_template('register.html', name=name, email=email)

        if get_user_by_email(email):
            flash('E-mail já cadastrado.', 'danger')
            return redirect(url_for('aut.login'))

        user_data = {'name': name, 'email': email, 'password': generate_password_hash(password)}
        token = serializer.dumps(user_data, salt='email-verification')
        send_verification_email(name, email, token)
        flash('Verifique seu e-mail para confirmar o cadastro.', 'info')
        log_action(None, 'Novo usuário registrado', f"Email: {email}")        
        return redirect(url_for('users.aviso', aviso_id=1))

    return render_template('register.html')

@aut_bp.route('/confirm/<token>')
def confirm_email(token):
    """Rota para confirmar e-mail do usuário"""
    email_for_log = "Desconhecido"
    try:
        user_data = serializer.loads(token, salt='email-verification', max_age=3600)
        name, email, password = user_data['name'], user_data['email'], user_data['password']
        email_for_log = email

        with get_db_connection() as conn:
            c = conn.cursor()
            if get_user_by_email(email):
                flash('Este e-mail já foi confirmado anteriormente.', 'info')
                return redirect(url_for('aut.login'))

            c.execute('INSERT INTO users (name, email, password, is_active) VALUES (?, ?, ?, ?)',
                      (name, email, password, 0))
            conn.commit()
        log_action(None, f'Email {email} verificado com sucesso')
        send_admin_notification(name, email)
        flash('E-mail confirmado com sucesso! Aguardando aprovação do administrador.', 'success')
        return redirect(url_for('users.aviso', aviso_id=2))

    except Exception as e:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
        print('Erro na confirmação:', e)
        log_action(None, f'Falha na confirmação do eail {email_for_log}')
        return redirect(url_for('aut.register'))

@aut_bp.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_by_email(email)
        if user and user['is_active'] == 1:
            token = serializer.dumps(email, salt='reset-password')
            reset_url = url_for('aut.resetar_senha', token=token, _external=True)
            html = f"""
            <p>Olá,</p>
            <p>Para redefinir sua senha para o AlphaFold Web, clique no link abaixo:</p>
            <p><a href="{reset_url}">Redefinir senha</a></p>
            """
            send_email(email, "Redefinição de senha - AlphaFold", html)
            flash("Um link de redefinição foi enviado para seu e-mail.", "info")
        else:
            flash("E-mail não encontrado ou inativo.", "danger")
    return render_template('esqueci_senha.html')

@aut_bp.route('/resetar_senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=3600)
    except:
        flash("O link expirou ou é inválido.", "danger")
        return redirect(url_for('aut.login'))

    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']

        if nova_senha != confirmar_senha:
            flash("As senhas não coincidem. Tente novamente.", "danger")
            return render_template('resetar_senha.html')

        senha_hash = generate_password_hash(nova_senha)
        conn = get_db_connection()
        conn.execute('UPDATE users SET password = ? WHERE email = ?', (senha_hash, email))
        conn.commit()
        conn.close()
        flash("Senha redefinida com sucesso.", "success")
        return redirect(url_for('aut.login'))

    return render_template('resetar_senha.html')