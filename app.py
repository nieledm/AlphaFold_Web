from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash, request, session, g, send_file, jsonify, current_app
from flask import session, redirect, url_for, render_template, request
import os
import io
import subprocess
import json
import re
import sqlite3
import shutil
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP_SSL
from threading import Thread
from datetime import datetime
import pytz
import tempfile
import zipfile
import paramiko
import select
import time
import stat
from database import get_db_connection, init_db, DATABASE


app = Flask(__name__)
app.secret_key = '#!Alph@3!' 

# ==============================================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================================

# Configuração conexão Horizon
ALPHAFOLD_SSH_HOST = '143.106.4.186'
ALPHAFOLD_SSH_PORT = 2323
ALPHAFOLD_SSH_USER = 'alphaFoldWeb'

# Configurações AlphaFold
ALPHAFOLD_INPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_input'
ALPHAFOLD_OUTPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_output'
ALPHAFOLD_PARAMS = '/str1/projects/AI-DD/alphafold3/alphafold3_params'
ALPHAFOLD_DB = '/str1/projects/AI-DD/alphafold3/alphafold3_DB'

# Configurações de e-mail
EMAIL_SENDER = 'nieledm@gmail.com'
EMAIL_PASSWORD = 'zlde qbxb zvif bfpg'
serializer = URLSafeTimedSerializer(app.secret_key)

# ==============================================================
# DECORADORES DE AUTENTICAÇÃO E AUTORIZAÇÃO
# ==============================================================

def login_required(f):
    """
    Decorador para rotas que exigem que o usuário esteja logado.
    Redireciona para a página de login se o usuário não estiver na sessão.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorador para rotas que exigem que o usuário seja um administrador.
    Redireciona para o dashboard ou página de login se não for admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Acesso não autorizado. Apenas administradores podem acessar esta página.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================
# FUNÇÕES DE BANCO DE DADOS
# ==============================================================
def get_user_by_email(email):
    """Busca um usuário pelo e-mail"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        return c.fetchone()

# ==============================================================
# FUNÇÕES DE E-MAIL
# ==============================================================
def send_email(to_email, subject, html_content):
    """Função genérica para enviar e-mails"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        with SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
            log_action('', 'Envio de email', 'Sucesso no envio')

        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        log_action('', 'Envio de email', 'Erro no envio')
        return False

def send_verification_email(name, email, token):
    """Envia e-mail de verificação para novo usuário"""
    verification_url = url_for('confirm_email', token=token, _external=True)
    html = f"""
    <html>
        <body>
            <p>Olá {name},</p>
            <p>Por favor, confirme seu e-mail clicando no link abaixo:</p>
            <p><a href="{verification_url}">Confirmar e-mail</a></p>
        </body>
    </html>
    """
    send_email(email, "Confirme seu e-mail", html)

def send_admin_notification(name, email):
    """Notifica administradores sobre novo usuário pendente"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT email FROM users WHERE is_admin = 1')
        admins = c.fetchall()
    
    html = f"""
    <html>
        <body>
            <p>Olá,</p>
            <p>O usuário {name} ({email}) confirmou o seu e-mail para usar o AlphaFold e aguarda aprovação.</p>
            <p>Por favor, acesse o painel de administração para aprovar ou rejeitar a solicitação.</p>
        </body>
    </html>
    """
    
    for admin in admins:
        send_email(admin[0], "Novo usuário aguardando aprovação no AlphaFold", html)

def send_activation_email(user_email, user_name):
    """Envia e-mail de confirmação de ativação da conta"""
    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Sua conta foi ativada com sucesso!</p>
            <p>Agora você pode acessar o sistema.</p>
        </body>
    </html>
    """
    send_email(user_email, "Sua conta no AlphaFold foi ativada", html)

def send_processing_complete_email(user_name, user_email, base_name, user_id):
    """Envia e-mail ao usuário informando que o processamento foi concluído"""
    try:
        download_url = url_for('download_result', base_name=base_name, _external=True)
    except Exception as e:
        print(f"[ERRO] Falha ao gerar link de download: {e}")
        download_url = "[Erro ao gerar link]"

    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Seu processamento com o AlphaFold foi concluído com sucesso.</p>
            <p>Você pode baixar o resultado indo ao seu dashboard ou clicando no link abaixo:</p>
            <p><a href="{download_url}">Download do resultado</a></p>
            <p>Obrigado por usar o sistema AlphaFold!</p>
        </body>
    </html>
    """
    send_email(user_email, "AlphaFold: Resultado disponível", html)

# ==============================================================
# FUNÇÕES DE VALIDAÇÃO
# ==============================================================
def validar_json_input(json_path):
    """Valida o arquivo JSON de entrada para o AlphaFold"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return False, "O arquivo JSON deve conter um dicionário de cadeias."

        for chain_id, sequence in data.items():
            if not isinstance(sequence, str):
                return False, f"A cadeia '{chain_id}' deve conter apenas uma sequência como string."

            if "\n" in sequence or ">" in sequence:
                return False, f"A cadeia '{chain_id}' contém quebras de linha ou formatação FASTA."

            if not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", sequence, re.IGNORECASE):
                return False, f"A cadeia '{chain_id}' contém caracteres inválidos. Apenas aminoácidos padrão são permitidos."

        return True, "OK"

    except Exception as e:
        return False, f"Erro ao validar JSON: {str(e)}"

# ==============================================================
# ROTAS DE AUTENTICAÇÃO
# ==============================================================
@app.route('/')
def index():
    """Rota principal que redireciona para login ou dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas.', 'danger')
            log_action(user_id_for_log, 'Tentativa de Login Falha', f'Credenciais inválidas para o email: {email}')

    return render_template('login.html')

@app.route('/ver_sessao')
def ver_sessao():
    return dict(session)

@app.route('/logout')
def logout():
    """Rota de logout"""
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/termos', methods=['GET', 'POST'])
def termos_de_uso():
    # Se já aceitou os termos, redireciona para registro
    if session.get('terms_accepted'):
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        # Verifica se TODOS os checkboxes foram marcados
        accept_terms = request.form.get('accept_terms') == 'on'
        accept_alphafold = request.form.get('accept_alphafold') == 'on'
        accept_detic = request.form.get('accept_detic') == 'on'
        
        if accept_terms and accept_alphafold and accept_detic:
            session['terms_accepted'] = True
            session.modified = True
            return redirect(url_for('register'))
        else:
            flash('Você deve aceitar todos os termos para continuar.', 'error')
            return redirect(url_for('termos_de_uso')) 
    
    return render_template('termo_de_uso.html')


def validar_nome(nome):
    return len(nome.strip().split()) >= 2

def validar_email(email):
    dominios = ['unicamp', 'unesp', 'usp', 'fatec', 'unifesp', 'unb', 'ufrj', 'ufmg', 'ufrgs']
    return any(d in email.lower() for d in dominios)

def validar_senha(senha):
    regex = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$')
    return regex.match(senha)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de registro de novos usuários"""
    # Verifica se os termos foram aceitos
    if not session.get('terms_accepted'):
        flash('Você precisa aceitar os termos de uso antes de se registrar', 'warning')
        return redirect(url_for('termos_de_uso'))
    
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
            return redirect(url_for('login'))

        user_data = {'name': name, 'email': email, 'password': generate_password_hash(password)}
        token = serializer.dumps(user_data, salt='email-verification')
        send_verification_email(name, email, token)
        flash('Verifique seu e-mail para confirmar o cadastro.', 'info')
        log_action(None, 'Novo usuário registrado', f"Email: {email}")        
        return redirect(url_for('aviso', aviso_id=1))

    return render_template('register.html')

@app.route('/confirm/<token>')
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
                return redirect(url_for('login'))

            c.execute('INSERT INTO users (name, email, password, is_active) VALUES (?, ?, ?, ?)',
                      (name, email, password, 0))
            conn.commit()
        log_action(None, f'Email {email} verificado com sucesso')
        send_admin_notification(name, email)
        flash('E-mail confirmado com sucesso! Aguardando aprovação do administrador.', 'success')
        return redirect(url_for('aviso', aviso_id=2))

    except Exception as e:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
        print('Erro na confirmação:', e)
        log_action(None, f'Falha na confirmação do eail {email_for_log}')
        return redirect(url_for('register'))

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form['email']
        user = get_user_by_email(email)
        if user and user['is_active'] == 1:
            token = serializer.dumps(email, salt='reset-password')
            reset_url = url_for('resetar_senha', token=token, _external=True)
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

@app.route('/resetar_senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=3600)
    except:
        flash("O link expirou ou é inválido.", "danger")
        return redirect(url_for('login'))

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
        return redirect(url_for('login'))

    return render_template('resetar_senha.html')
    
# ==============================================================
# ROTAS DE USUÁRIO
# ==============================================================
@app.route('/dashboard')
def dashboard():
    """Painel principal do usuário"""
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('login'))

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

@app.route('/aviso/<int:aviso_id>')
def aviso(aviso_id):
    """Exibe mensagens de aviso"""
    avisos = {
        1: "Um email de confimação foi enviado para o endereço de email cadastrado. Por favor, verifique a sua caixa de entrada (ou spam) para confirmar o seu e-mail.", 
        2: "Seu e-mail foi confirmado! Agora é só aguardar a aprovação do administrador.",
        3: "A sua conta foi ativada com sucesso!",
    }
    return render_template('base_avisos.html', aviso_mensagem=avisos.get(aviso_id, "Aviso desconhecido."))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html',
                           active_page='sobre',
                           nome_usuario=session.get('user_name', 'Usuário'))

# ==============================================================
# ROTAS DE ADMINISTRAÇÃO
# ==============================================================
@app.route('/admin/usuarios_ativos')
def usuarios_ativos():
    """Lista usuários ativos"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '')
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, name, email, is_admin 
            FROM users 
            WHERE is_active = 1 AND (name LIKE ? OR email LIKE ?) 
            ORDER BY name ASC
        ''', ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_ativos = c.fetchall()
        
    return render_template('usuarios_ativos.html',
                         titulo='Usuários Ativos',
                         active_page='ativos', 
                         usuarios_ativos=usuarios_ativos,                            
                         search_query=search_query,
                         nome_usuario=session.get('user_name', 'Usuário'))

@app.route('/admin/usuarios_pendentes')
def usuarios_pendentes():
    """Lista usuários pendentes de aprovação"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '')
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, name, email 
            FROM users 
            WHERE is_active = 0 AND (name LIKE ? OR email LIKE ?) 
            ORDER BY name ASC
        ''', ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_pendentes = c.fetchall()

    return render_template('usuarios_pendentes.html',
                         titulo='Usuários Pendentes de Ativação',
                         active_page='pendentes', 
                         usuarios_pendentes=usuarios_pendentes, 
                         search_query=search_query,
                         nome_usuario=session.get('user_name', 'Usuário'))

@app.route('/admin/usuarios_desativados')
def usuarios_desativados():
    """Lista usuários desativados"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '')
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT id, name, email 
            FROM users 
            WHERE is_active = 2 AND (name LIKE ? OR email LIKE ?) 
            ORDER BY name ASC
        ''', ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_desativados = c.fetchall()

    return render_template('usuarios_desativados.html',
                         titulo='Usuários Desativados',
                         active_page='desativados', 
                         usuarios_desativados=usuarios_desativados, 
                         search_query=search_query,
                         nome_usuario=session.get('user_name', 'Usuário'))

@app.route('/admin/aprovar/<int:user_id>', methods=['POST'])
def aprovar_usuario(user_id):
    """Aprova um usuário pendente"""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: aprovar_usuario para ID {user_id}')
        return redirect(url_for('dashboard'))

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT name, email, is_active FROM users WHERE id = ?', (user_id,)) # Incluindo is_active para verificação
            user_to_approve = c.fetchone() # Renomeado para clareza

            if user_to_approve:
                if user_to_approve['is_active'] == 1:
                    flash(f"Usuário {user_to_approve['name']} já está ativo.", 'info')
                    log_action(admin_user_id, 'Tentativa de aprovação de usuário já ativo', f'ID: {user_id}, Nome: {user_to_approve["name"]}, Email: {user_to_approve["email"]}')
                    return redirect(url_for('usuarios_ativos'))

                c.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
                conn.commit()
                send_activation_email(user_to_approve['email'], user_to_approve['name'])
                flash(f'Usuário {user_to_approve["name"]} ativado com sucesso!', 'success')
                log_action(admin_user_id, 'Usuário Aprovado', f'ID: {user_id}, Nome: {user_to_approve["name"]}, Email: {user_to_approve["email"]}')
            else:
                flash('Usuário não encontrado!', 'error')
                log_action(admin_user_id, 'Tentativa de aprovação de usuário inexistente', f'ID do usuário tentado: {user_id}')

    except Exception as e:
        flash(f'Ocorreu um erro ao aprovar o usuário: {e}', 'danger')
        log_action(admin_user_id, 'Erro ao aprovar usuário', f'ID do usuário: {user_id}. Erro: {e}')

    return redirect(url_for('usuarios_ativos'))

@app.route('/admin/inativar/<int:user_id>', methods=['POST'])
def inativar_usuario(user_id):
    """Inativa um usuário"""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: inativar_usuario para ID {user_id}')
        return redirect(url_for('dashboard'))

    user_to_inactivate = None
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT name, email, is_active FROM users WHERE id = ?', (user_id,))
            user_to_inactivate = c.fetchone()

            if user_to_inactivate:
                if user_to_inactivate['is_active'] == 2:
                    flash(f"Usuário {user_to_inactivate['name']} já está inativado.", 'info')
                    log_action(admin_user_id, 'Tentativa de inativar usuário já inativado', f'ID: {user_id}, Nome: {user_to_inactivate["name"]}, Email: {user_to_inactivate["email"]}')
                    return redirect(url_for('usuarios_desativados'))
                
                c.execute('UPDATE users SET is_active = 2 WHERE id = ?', (user_id,))
                conn.commit()
                flash(f'Usuário {user_to_inactivate["name"]} desativado com sucesso!', 'warning')
                
                log_action(admin_user_id, 'Usuário Desativado', f'ID: {user_id}, Nome: {user_to_inactivate["name"]}, Email: {user_to_inactivate["email"]}')
            else:
                flash('Usuário não encontrado!', 'error')
                log_action(admin_user_id, 'Tentativa de inativação de usuário inexistente', f'ID do usuário tentado: {user_id}')

    except Exception as e:
        flash(f'Ocorreu um erro ao inativar o usuário: {e}', 'danger')
        log_action(admin_user_id, 'Erro ao inativar usuário', f'ID do usuário: {user_id}. Erro: {e}')

    return redirect(url_for('usuarios_desativados'))


@app.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def excluir_usuario(user_id):
    """Exclui um usuário (pendente, ativo, ou desativado) e seus dados associados."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: excluir_usuario para ID {user_id}')
        return redirect(url_for('dashboard'))

    user_to_delete = None
    try:
        with get_db_connection() as conn:
            c = conn.cursor()

            c.execute('SELECT name, email, is_active FROM users WHERE id = ?', (user_id,))
            user_to_delete = c.fetchone()

            if user_to_delete:
                if admin_user_id == user_id:
                    flash('Você não pode excluir sua própria conta.', 'danger')
                    log_action(admin_user_id, 'Tentativa de auto-exclusão negada', f'ID: {user_id}, Nome: {user_to_delete["name"]}')
                    return redirect(url_for('usuarios_ativos')) # ou onde for mais apropriado

                c.execute('DELETE FROM uploads WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM logs WHERE user_id = ?', (user_id,))
                
                c.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()

                if c.rowcount > 0:
                    flash('Usuário excluído com sucesso!', 'success')
                    log_action(admin_user_id, 'Usuário Excluído', f'ID: {user_id}, Nome: {user_to_delete["name"]}, Email: {user_to_delete["email"]}')

                    user_folder_name = user_to_delete['name']
                    input_user_dir = os.path.join(ALPHAFOLD_INPUT_BASE, user_folder_name)
                    output_user_dir = os.path.join(ALPHAFOLD_OUTPUT_BASE, user_folder_name)
                    
                    if os.path.exists(input_user_dir):
                        shutil.rmtree(input_user_dir)
                        log_action(admin_user_id, 'Arquivos de Input do Usuário Excluídos', f'Caminho: {input_user_dir}')
                    if os.path.exists(output_user_dir):
                        shutil.rmtree(output_user_dir)
                        log_action(admin_user_id, 'Arquivos de Output do Usuário Excluídos', f'Caminho: {output_user_dir}')

                else:
                    flash('Usuário não encontrado para exclusão.', 'warning')
                    log_action(admin_user_id, 'Tentativa de exclusão de usuário inexistente', f'ID do usuário tentado: {user_id}')
            else:
                flash('Usuário não encontrado para exclusão.', 'warning')
                log_action(admin_user_id, 'Tentativa de exclusão de usuário inexistente (pré-verificação)', f'ID do usuário tentado: {user_id}')

    except Exception as e: # Captura sqlite3.IntegrityError e outros erros
        flash(f'Ocorreu um erro ao excluir o usuário: {e}', 'danger')
        log_action(admin_user_id, 'Erro ao excluir usuário', f'ID do usuário: {user_id}. Erro: {e}')

    return redirect(url_for('usuarios_pendentes'))

@app.route('/usuarios/<int:user_id>/admin', methods=['POST'])
def toggle_admin(user_id):
    """Alterna status de administrador de um usuário."""
    admin_user_id = session.get('user_id')

    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: toggle_admin para ID {user_id}')
        return redirect(url_for('dashboard'))

    user_to_toggle = None
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute('SELECT id, name, email, is_admin FROM users WHERE id = ?', (user_id,))
            user_to_toggle = c.fetchone()

            if user_to_toggle:
                current_status = user_to_toggle['is_admin']
                new_status = 0 if current_status == 1 else 1
                
                c.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_status, user_id))
                conn.commit()

                if new_status == 1:
                    flash(f'Usuário {user_to_toggle["name"]} agora é um administrador.', 'success')
                    log_action(admin_user_id, 'Privilégios de Administrador Concedidos', f'ID: {user_id}, Nome: {user_to_toggle["name"]}, Email: {user_to_toggle["email"]}')
                else:
                    flash(f'Privilégios de administrador de {user_to_toggle["name"]} removidos.', 'info')
                    log_action(admin_user_id, 'Privilégios de Administrador Removidos', f'ID: {user_id}, Nome: {user_to_toggle["name"]}, Email: {user_to_toggle["email"]}')
            else:
                flash('Usuário não encontrado.', 'danger')
                log_action(admin_user_id, 'Tentativa de toggle admin em usuário inexistente', f'ID do usuário tentado: {user_id}')

    except Exception as e:
        flash(f'Ocorreu um erro ao alternar o status de administrador: {e}', 'danger')
        log_action(admin_user_id, 'Erro ao alternar status de administrador', f'ID do usuário: {user_id}. Erro: {e}')

    return redirect(url_for('usuarios_ativos'))

# ==============================================================
# ROTAS DO ALPHAFOLD (UPLOAD, PROCESSAMENTO E DOWNLOAD)
# ==============================================================
@app.route('/builder_json_form', methods=['GET'])
def builder_json_form():
    print("Usuário na sessão:", dict(session))
    return render_template('builder_json_form.html',
                            nome_usuario=session.get('user_name', 'Usuário'))

@app.route('/generate_json', methods=['POST'])
def generate_json():

    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Usuário Desconhecido')

    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        log_action(None, 'Tentativa de Gerar JSON (Não Autenticado)')
        return redirect(url_for('login'))

    data = request.form
    json_data = {"inputs": []}

    log_action(user_id, 'Início da Geração de JSON', f'Usuário: {user_name}')

    # === Dados principais ===
    entity = data.get("entity", "").strip()
    sequence = data.get("sequence", "").strip().replace("\r\n", "\n")
    copies = int(data.get("copies", 1))

    input_entry = {
        "entity_type": entity,
        "sequence": sequence,
        "copies": copies
    }

    # === MSA ===
    msa_blocks = []
    index = 0
    while True:
        msa_format = data.get(f"msa_format_{index}")
        msa_data = data.get(f"msa_data_{index}")
        if not msa_format or not msa_data:
            break
        msa_blocks.append({
            "msa_format": msa_format.strip(),
            "msa_data": [s.strip() for s in msa_data.strip().split("\n") if s.strip()]
        })
        index += 1
    if msa_blocks:
        input_entry["msa"] = msa_blocks

    # === Campos opcionais ===
    templates = data.get("templates", "").strip()
    if templates:
        input_entry["templates"] = [t.strip() for t in templates.splitlines() if t.strip()]

    pairing = data.get("pairing", "").strip()
    if pairing:
        input_entry["pairing"] = pairing

    modifications = data.get("modifications", "").strip()
    if modifications:
        try:
            input_entry["modifications"] = json.loads(modifications)
        except json.JSONDecodeError:
            return "JSON inválido em modificações", 400

    coordinates = data.get("coordinates", "").strip()
    if coordinates:
        try:
            input_entry["coordinates"] = json.loads(coordinates)
        except json.JSONDecodeError:
            return "JSON inválido em coordinates", 400

    masked_regions = data.get("masked_regions", "").strip()
    if masked_regions:
        try:
            input_entry["masked_regions"] = json.loads(masked_regions)
        except json.JSONDecodeError:
            return "JSON inválido em masked_regions", 400

    json_data["inputs"].append(input_entry)

    # === Salvar arquivo temporário ===
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmpfile:
        json.dump(json_data, tmpfile, indent=2)
        tmpfile_path = tmpfile.name
        tmpfile_name = os.path.basename(tmpfile_path)

        log_action(user_id, 'JSON Gerado Com Sucesso', f'Nome temporário: {tmpfile_name}')

    # === Upload automático para /upload ===
    with open(tmpfile_path, 'rb') as f:
        upload_response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': (tmpfile_name, f, 'application/json')},
            cookies=request.cookies  # passa os cookies para manter a sessão
        )

    if upload_response.status_code == 302:  # redirecionamento com sucesso
        flash("Arquivo gerado e enviado com sucesso!", "success")
        log_action(user_id, 'JSON Gerado e Enviado', f'Nome do arquivo: {tmpfile_name}')
    else:
        flash("Erro ao enviar o arquivo gerado para processamento.", "danger")
        log_action(user_id, 'Erro ao Enviar JSON Gerado', f'Nome do arquivo: {tmpfile_name}, Status: {upload_response.status_code}, Resposta: {upload_response.text}')

    # === Retorna para download (caso deseje salvar também) ===
    return send_file(tmpfile_path, mimetype='application/json', as_attachment=True, download_name='input_alphafold.json')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Processa upload de arquivos para o AlphaFold"""
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Usuário Desconhecido')
    user_email = session.get('user_email', 'Email Desconhecido')

    dict(session)
    #Time Zone e data
    tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(tz)
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    if not all(key in session for key in ['user_id', 'user_name', 'user_email']):
        flash('Por favor, faça login novamente.', 'warning')
        log_action(None, 'Tentativa de Upload (Sessão Inválida)', 'Usuário desconhecido ou sessão expirada')
        return redirect(url_for('login'))
    
    log_action(user_id, 'Início de Upload de Arquivo', f'Usuário: {user_name}')

    if 'file' not in request.files:
        flash('Nenhum arquivo enviado.', 'danger')
        log_action(user_id, 'Erro de Upload', 'Nenhum arquivo na requisição')
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        log_action(user_id, 'Erro de Upload', 'Nome de arquivo vazio')
        return 'No selected file'

    if file and file.filename.endswith('.json'):
        filename = file.filename
        base_name = filename.rsplit('.', 1)[0]

        # Conexão SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ALPHAFOLD_SSH_HOST, port=ALPHAFOLD_SSH_PORT, username=ALPHAFOLD_SSH_USER)

        sftp = ssh.open_sftp()

        user_name = session['user_name']
        user_email = session['user_email']
        user_id = session['user_id']

        input_subdir = os.path.join(ALPHAFOLD_INPUT_BASE, user_name)
        output_user_dir = os.path.join(ALPHAFOLD_OUTPUT_BASE, user_name)
        output_subdir = os.path.join(output_user_dir, base_name)

        # Cria diretórios para input e output caso não existam
        mkdir_command = f"mkdir -p '{input_subdir}' '{output_user_dir}' '{output_subdir}'"
        ssh.exec_command(mkdir_command)

        # Salva arquivo
        input_file_path = os.path.join(input_subdir, filename)
        # file.save(input_file_path)
        sftp.putfo(file.stream, input_file_path)

        sftp.close()
        ssh.close()

        # Salva no banco
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO uploads (user_id, file_name, base_name, status, created_at) VALUES (?, ?, ?, ?, ?)',
            (session['user_id'], filename, base_name, 'PROCESSANDO', now_str)
        )
        conn.commit()
        conn.close()

        log_action(user_id, 'Arquivo JSON Uploaded', f'Nome: {filename}, BaseName: {base_name}')

        # Monta comando e roda em background
        command = (
            f"docker run "
            f"--volume {input_subdir}:/root/af_input "
            f"--volume {output_user_dir}:/root/af_output "
            f"--volume {ALPHAFOLD_PARAMS}:/root/models "
            f"--volume {ALPHAFOLD_DB}:/root/public_databases "
            f"--gpus all alphafold3 "
            f"python run_alphafold.py "
            f"--json_path=/root/af_input/{filename} "
            f"--output_dir=/root/af_output/{base_name} "
        )

        Thread(target=run_alphafold_in_background, args=(
            command, user_name, user_email, base_name, user_id
        )).start()
                
        flash("Arquivo enviado. Você será notificado quando o processamento terminar.", 'info')
        log_action(user_id, 'Processamento AlphaFold Iniciado', f'BaseName: {base_name}')
        return redirect(url_for('dashboard'))

    return 'Invalid file format'

def run_alphafold_in_background(cmd, user_name, user_email, base_name, user_id):
    with app.app_context():
        log_action(user_id, 'Executando AlphaFold', base_name)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(ALPHAFOLD_SSH_HOST, port=ALPHAFOLD_SSH_PORT, username=ALPHAFOLD_SSH_USER)

            mkdir = f"mkdir -p '{ALPHAFOLD_INPUT_BASE}/{user_name}' " \
                    f"'{ALPHAFOLD_OUTPUT_BASE}/{user_name}/{base_name}'"
            ssh.exec_command(mkdir)

            stdin, stdout, stderr = ssh.exec_command(cmd)

            # -------------- LOG EM TEMPO REAL --------------
            stdout_lines = []
            stderr_lines = []

            while not stdout.channel.exit_status_ready():
                rl, wl, xl = select.select([stdout.channel], [], [], 1.0)
                if rl:
                    line = stdout.readline()
                    if line:
                        stdout_lines.append(line.strip())

                rl_err, _, _ = select.select([stderr.channel], [], [], 1.0)
                if rl_err:
                    err_line = stderr.readline()
                    if err_line:
                        stderr_lines.append(err_line.strip())

            # Após o término, registra os logs em lote:
            for line in stdout_lines:
                log_action(user_id, 'AlphaFold output', line)
            for line in stderr_lines:
                log_action(user_id, 'AlphaFold error', line)
            # -------------- FIM DO LOOP ---------------------

            exit_status = stdout.channel.recv_exit_status()
            log_action(user_id, 'Exit status', str(exit_status))

            remote_cif = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name}/{base_name}/" \
                        f"alphafold_prediction/alphafold_prediction_model.cif"
            
            check_cmd = f'test -f "{remote_cif}" && echo OK || echo NO'

            # Verificar se arquivo de resultado foi gerado (espera até 60s)
            result_exists = False
            wait_time = 0

            while wait_time < 60:
                stdin, stdout, _ = ssh.exec_command(check_cmd)
                result = stdout.read().decode().strip()
                if result == "OK":
                    result_exists = True
                    break
                time.sleep(5)
                wait_time += 5

            with get_db_connection() as conn:
                if result_exists and exit_status == 0:
                    conn.execute("UPDATE uploads SET status='COMPLETO' WHERE base_name=?", (base_name,))
                    conn.commit()
                    log_action(user_id, 'Processamento CONCLUÍDO', remote_cif)
                    send_processing_complete_email(user_name, user_email, base_name, user_id)
                else:
                    conn.execute("UPDATE uploads SET status='ERRO' WHERE base_name=?", (base_name,))
                    conn.commit()
                    log_action(user_id, 'Processamento ERRO',
                            f'Exit={exit_status}, arquivo existe? {result_exists}')
                    send_email(user_email, "Erro no processamento do AlphaFold",
                            f"<p>Olá {user_name},</p><p>Ocorreu um erro e o arquivo de resultado não foi gerado.</p>")
        except Exception as e:
            log_action(user_id, 'Falha run_alphafold', str(e))
            try:
                send_email(user_email, "Erro na execução AlphaFold",
                        f"<p>Olá {user_name},</p><p>Ocorreu um erro inesperado: {e}</p>")
            except Exception as mail_err:
                log_action(user_id, 'Erro ao enviar e-mail', str(mail_err))
        finally:
            ssh.close()

@app.route('/download/<base_name>')
def download_result(base_name):
    """Permite download do arquivo processado se pronto"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_name:
        flash('Usuário não encontrado. Faça login novamente.', 'warning')
        log_action(None, 'Tentativa de Download (Não Autenticado)', f'BaseName: {base_name}')
        return redirect(url_for('login'))
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=ALPHAFOLD_SSH_HOST,
            port=ALPHAFOLD_SSH_PORT,
            username=ALPHAFOLD_SSH_USER
        )

        sftp = ssh.open_sftp()
        remote_folder = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name}/{base_name}/alphafold_prediction"

        try:
            remote_files = sftp.listdir(remote_folder)
        except IOError as e:
            flash('Resultados não encontrados no servidor.', 'danger')
            print(f"[ERRO] Falha ao acessar: {remote_folder} - Erro: {e}")
            log_action(user_id, 'Download Negado', f'Diretório remoto não encontrado: {remote_folder}')
            return redirect(url_for('dashboard'))

        # Cria um ZIP em memória
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            def add_folder_to_zip(sftp, zipf, remote_path, relative_path=''):
                for item in sftp.listdir(remote_path):
                    item_full_path = f"{remote_path}/{item}"
                    item_relative_path = f"{relative_path}/{item}" if relative_path else item
                    try:
                        if stat.S_ISDIR(sftp.stat(item_full_path).st_mode):
                            # É uma pasta, chama recursivamente
                            add_folder_to_zip(sftp, zipf, item_full_path, item_relative_path)
                        else:
                            # É um arquivo, adiciona
                            with sftp.open(item_full_path, 'rb') as f:
                                file_data = f.read()
                                zipf.writestr(item_relative_path, file_data)
                    except Exception as e:
                        print(f"[ERRO] Erro ao processar {item_full_path}: {e}")

            add_folder_to_zip(sftp, zipf, remote_folder)


        sftp.close()
        ssh.close()


        # Retorna o ZIP para o navegador
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{base_name}.zip"
        )

    except Exception as ex:
        flash('Erro ao tentar realizar o download.', 'danger')
        print(f"[ERRO] Exceção geral no download_result: {ex}")
        log_action(user_id, 'Erro no Download', str(ex))
        return redirect(url_for('dashboard'))


    except Exception as e:
        log_action(user_id, 'Erro no Download', str(e))
        flash('Erro ao processar o download.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/delete_result/<base_name>', methods=['POST'])
@login_required
def delete_result(base_name):
    user_id = session['user_id']
    user_name = session['user_name']
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ALPHAFOLD_SSH_HOST, port=ALPHAFOLD_SSH_PORT, username=ALPHAFOLD_SSH_USER)
        sftp = ssh.open_sftp()
        
        target_dir = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name}/{base_name}"
        ssh.exec_command(f"rm -rf '{target_dir}'")

        conn = get_db_connection()
        conn.execute("UPDATE uploads SET status='EXCLUIDO' WHERE base_name = ?", (base_name,))
        conn.commit()
        conn.close()

        sftp.close()
        ssh.close()

        flash("Resultado excluído com sucesso.", "success")
        log_action(user_id, 'Resultado Excluído', f'BaseName: {base_name}')
    except Exception as e:
        flash("Erro ao excluir resultado.", "danger")
        log_action(user_id, 'Erro ao excluir resultado', str(e))

    return redirect(url_for('dashboard'))

# ==============================================================
# BACKUP ALPHAFOLD3
# ==============================================================

@app.route('/admin/export_data')
def export_data():
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        conn = get_db_connection()
        data_to_export = {}

        # Exportar users
        users = conn.execute('SELECT id, name, email, is_admin, is_active FROM users').fetchall()
        data_to_export['users'] = [dict(row) for row in users]

        # Exportar uploads
        uploads = conn.execute('SELECT id, user_id, file_name, base_name, status, created_at FROM uploads').fetchall()
        data_to_export['uploads'] = [dict(row) for row in uploads]

        # Exportar logs
        logs = conn.execute('SELECT id, user_id, action, timestamp, details FROM logs').fetchall()
        data_to_export['logs'] = [dict(row) for row in logs]

        conn.close()

        # Salva o JSON em um arquivo temporário
        json_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.json').name
        with open(json_file_path, 'w') as f:
            json.dump(data_to_export, f, indent=4)

        # Compacta o arquivo JSON em um ZIP
        zip_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip').name
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_file_path, os.path.basename(json_file_path))

        os.remove(json_file_path) # Remove o arquivo JSON temporário

        return send_file(zip_file_path,
                         mimetype='application/zip',
                         as_attachment=True,
                         download_name='all_application_data.zip')

    except Exception as e:
        flash(f'Erro ao exportar dados: {e}', 'danger')
        return redirect(url_for('dashboard'))

# ==============================================================
# LOGS
# ==============================================================
def log_action(user_id, action, details=None):
    """Registra uma ação no banco de dados de logs com retry."""
    attempts = 3
    delay = 0.1  # segundos

    tz = pytz.timezone('America/Sao_Paulo')
    now = datetime.now(tz)
    timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

    for i in range(attempts):
        try:
            conn = get_db_connection()
            try:
                conn.execute(
                    'INSERT INTO logs (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)',
                    (user_id, action, timestamp, details)
                )
                conn.commit()
                break  # sucesso, sai do loop
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and i < attempts - 1:
                    time.sleep(delay)
                    delay *= 2  # exponencial
                    continue  # tenta de novo
                else:
                    print(f"[log_action] Falha ao registrar (tentativa {i+1}): {e}")
            finally:
                conn.close()
        except Exception as e:
            print(f"[log_action] Erro inesperado ao abrir conexão (tentativa {i+1}): {e}")

@app.route('/admin/view_logs', methods=['GET'])
def view_logs():
    """Exibe os logs do sistema com opções de filtro."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', 'Rota: view_logs')
        return redirect(url_for('dashboard'))

    search_query = request.args.get('search', '').strip()
    user_id_filter = request.args.get('user_id_filter', '').strip()
    # action_filter = request.args.get('action_filter', '').strip()
    user_name_filter = request.args.get('user_name_filter', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    conn = get_db_connection()
    logs = []
    try:
        query = """
            SELECT 
                l.id, 
                l.user_id, 
                u.name AS user_name, -- Alias para o nome do usuário da tabela users
                l.action, 
                l.timestamp, 
                l.details 
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.id -- JOIN para buscar o nome do usuário
            WHERE 1=1
        """
        params = []

        if search_query:
            query += " AND (action LIKE ? OR details LIKE ?)"
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        if user_name_filter:
            query += " AND u.name LIKE ?"
            params.append(f'%{user_name_filter}%')
        
        if user_id_filter:
            try:
                user_id_filter_int = int(user_id_filter)
                query += " AND user_id = ?"
                params.append(user_id_filter_int)
            except ValueError:
                flash('ID do usuário para filtro inválido.', 'danger')
                user_id_filter = ''

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date + " 00:00:00")

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date + " 23:59:59")

        query += " ORDER BY timestamp DESC, l.id DESC"
        logs = conn.execute(query, params).fetchall()
        
    except Exception as e:
        flash(f'Ocorreu um erro ao buscar os logs: {e}', 'danger')
    finally:
        conn.close()

    return render_template('logs.html', 
                           titulo='Logs do Sistema',
                           logs=logs,
                           search_query=search_query,
                           user_name_filter=user_name_filter,
                           user_id_filter=user_id_filter,
                           start_date=start_date,
                           end_date=end_date,
                           active_page='logs',
                           nome_usuario=session.get('user_name', 'Usuário'))

@app.route('/admin/clear_logs', methods=['POST'])
@admin_required
def clear_logs():
    """Limpa logs do sistema com base em filtros."""
    admin_user_id = session.get('user_id')
    
    days_old = request.form.get('days_old')
    action_type = request.form.get('action_type', '').strip()
    clear_start_date = request.form.get('clear_start_date', '').strip()
    clear_end_date = request.form.get('clear_end_date', '').strip()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        delete_query = "DELETE FROM logs WHERE 1=1"
        delete_params = []
        details_for_log = []

        if days_old == 'all':
            delete_query = "DELETE FROM logs"
            details_for_log.append('Todos os logs')
        elif days_old == 'dates':
            if not clear_start_date or not clear_end_date:
                flash('Por favor, forneça as datas de início e fim para a limpeza por intervalo.', 'warning')
                return redirect(url_for('view_logs'))
            
            delete_query += " AND timestamp >= ?"
            delete_params.append(clear_start_date + " 00:00:00")
            details_for_log.append(f'De: {clear_start_date}')

            delete_query += " AND timestamp <= ?"
            delete_params.append(clear_end_date + " 23:59:59")
            details_for_log.append(f'Até: {clear_end_date}')
        elif days_old and days_old.isdigit() and int(days_old) > 0:
            days_old_int = int(days_old)
            delete_query += " AND timestamp < datetime('now', ?)"
            delete_params.append(f'-{days_old_int} days')
            details_for_log.append(f'Mais antigos que {days_old_int} dias')
        
        if action_type:
            delete_query += " AND action LIKE ?"
            delete_params.append(f'%{action_type}%')
            details_for_log.append(f'Ação: {action_type}')

        if not days_old and not action_type:
            flash('Por favor, selecione uma opção de limpeza por data ou insira um tipo de ação.', 'warning')
            return redirect(url_for('view_logs'))

        cursor.execute(delete_query, delete_params)
        conn.commit()
        
        rows_deleted = cursor.rowcount
        flash(f'Foram removidos {rows_deleted} logs com sucesso!', 'success')
        
        log_action(admin_user_id, 'Logs Limpos', f'Removidos {rows_deleted} logs. Critérios: {"; ".join(details_for_log) if details_for_log else "Nenhum específico"}')

    except Exception as e:
        flash(f'Ocorreu um erro ao limpar os logs: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('view_logs'))

@app.route('/admin/export_logs', methods=['POST'])
def export_logs():
    """Exporta os logs do sistema no formato JSON compactado em ZIP."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', 'Rota: export_logs')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    logs_data = []
    try:
        logs = conn.execute('SELECT id, user_id, action, timestamp, details FROM logs ORDER BY timestamp DESC').fetchall()
        for log in logs:
            logs_data.append(dict(log))

        json_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8').name
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, indent=4, ensure_ascii=False)

        zip_file_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip').name
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_file_path, os.path.basename(json_file_path))

        os.remove(json_file_path)

        return send_file(zip_file_path, mimetype='application/zip',
                         as_attachment=True, download_name='system_logs.zip')

    except Exception as e:
        flash(f'Ocorreu um erro ao exportar os logs: {e}', 'danger')
        return redirect(url_for('view_logs'))
    finally:
        conn.close()

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

