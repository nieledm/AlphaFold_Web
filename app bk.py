from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, session, g
import os
import subprocess
import json
import re
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '#!Alph@3!' 
DATABASE = 'database.db'

#########################################################################
################## BANCO DE DADOS (sqlite3 puro) ########################
#########################################################################

def init_db():
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

def get_user_by_email(email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        return c.fetchone()

#########################################################################
####################### ROTAS DE TELAS## ################################
#########################################################################

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/aviso/<int:aviso_id>')
def aviso(aviso_id):
    avisos = {
        1: "Um email de confimação foi enviado para o endereço de email cadastrado. Por favor, verifique a sua caixa de entrada (ou spam) para confirmar o seu e-mail.", 
        2: "Seu e-mail foi confirmado! Agora é só aguardar a aprovação do administrador.",
        3: "A sua conta foi ativada com sucesso!",
    }

    aviso_mensagem = avisos.get(aviso_id, "Aviso desconhecido.")

    return render_template('base_avisos.html', aviso_mensagem=aviso_mensagem)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'] 

        # Verifica se o e-mail já existe
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            if c.fetchone():
                flash('E-mail já cadastrado.', 'danger')
                return redirect(url_for('login'))

        # Gera token com os dados do usuário
        user_data = {'name': name, 'email': email, 'password': password}
        token = serializer.dumps(user_data, salt='email-verification')

        # Envia o e-mail com o link de confirmação
        send_verification_email(name, email, token)

        flash('Verifique seu e-mail para confirmar o cadastro.', 'info')
        return redirect(url_for('aviso', id=1))

    return render_template('register.html')

#confirmar email e cadastrar no banco
@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        user_data = serializer.loads(token, salt='email-verification', max_age=3600)

        name = user_data['name']
        email = user_data['email']
        password = user_data['password'] 

        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()

            # Evita duplicações por segurança
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            if c.fetchone():
                flash('Este e-mail já foi confirmado anteriormente.', 'info')
                return redirect(url_for('login'))

            # Insere o usuário aguardando aprovação
            c.execute('INSERT INTO users (name, email, password, is_active) VALUES (?, ?, ?, ?)',
                      (name, email, password, 0))
            conn.commit()

        # Envia notificação para todos os administradores
        send_admin_notification(name, email)

        flash('E-mail confirmado com sucesso! Aguardando aprovação do administrador.', 'success')
        return redirect(url_for('aviso', id=2))

    except Exception as e:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
        print('Erro na confirmação:', e)
        return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('SELECT id, name, email, password, is_admin, is_active FROM users WHERE email = ?', (email,))
            user = c.fetchone()

            if user and user[3] == password:
                is_active = user[5]
                if is_active == 0:
                    flash('Seu cadastro ainda não foi aprovado.', 'warning')
                elif is_active == 2:
                    flash('Sua conta foi inativada. Contate o administrador.', 'danger')
                elif is_active == 1:
                    session['user_id'] = user[0]
                    session['user_name'] = user[1]
                    session['is_admin'] = bool(user[4])
                    flash('Login bem-sucedido!', 'success')
                    return redirect(url_for('dashboard'))
            else:
                flash('Credenciais inválidas.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('login'))

    nome = session.get('user_name', 'Usuário')
    return render_template('dashboard.html', nome_usuario=nome)

# Rota para ver usuários ativos
@app.route('/admin/usuarios_ativos', methods=['GET'])
def usuarios_ativos():
    search_query = request.args.get('search', '')  # Pega a query de pesquisa, se existir

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar usuários ativos com filtro e ordenação
        c.execute('SELECT id, name, email, is_admin FROM users WHERE is_active = 1 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_ativos = c.fetchall()
        
    return render_template('usuarios_ativos.html',
                           titulo='Usuários Ativos', 
                           usuarios_ativos=usuarios_ativos,                            
                           search_query=search_query)

# Rota para ver usuários  pendentes
@app.route('/admin/usuarios_pendentes', methods=['GET'])
def usuarios_pendentes():
    search_query = request.args.get('search', '')  # Pega a query de pesquisa, se existir

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar usuários pendentes com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 0 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_pendentes = c.fetchall()

    return render_template('usuarios_pendentes.html',
                           titulo='Usuários Pendentes de Ativação', 
                           usuarios_pendentes=usuarios_pendentes, 
                           search_query=search_query)

# Rota para ver usuários desativos
@app.route('/admin/usuarios_desativados', methods=['GET'])
def usuarios_desativados():
    search_query = request.args.get('search', '')  # Pega a query de pesquisa, se existir

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar usuários desativados com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 2 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_desativados = c.fetchall()

    return render_template('usuarios_desativados.html',
                           titulo='Usuários Desativados', 
                           usuarios_desativados=usuarios_desativados, 
                           search_query=search_query)

# Rota para aprovar usuário
@app.route('/admin/aprovar/<int:user_id>', methods=['POST'])
def aprovar_usuario(user_id):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar os dados do usuário para obter o nome e o e-mail
        c.execute('SELECT name, email FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()

        if user:
            user_name, user_email = user  # Desempacotar o nome e e-mail do usuário

            # Atualizar o status do usuário para 'ativo'
            c.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
            conn.commit()

            flash('Usuário ativado com sucesso!', 'success')

            # Enviar o e-mail de ativação para o usuário
            send_activation_email(user_email, user_name)
        else:
            flash('Usuário não encontrado!', 'error')

    return redirect(url_for('usuarios_ativos'))

#Rota para inativar usuários
@app.route('/admin/inativar/<int:user_id>', methods=['POST'])
def inativar_usuario(user_id):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_active = 2 WHERE id = ?', (user_id,))
        conn.commit()
    flash('Usuário desativado com sucesso!', 'warning')
    return redirect(url_for('usuarios_desativados'))

#Rota para excluir usuários pendenttes
@app.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def excluir_usuario(user_id):
    try:
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM Users WHERE id = ?', (user_id,))
            conn.commit()

            # Verifica se realmente excluiu alguma linha
            if c.rowcount > 0:
                flash('Usuário excluído com sucesso!', 'success')
            else:
                flash('Usuário não encontrado.', 'warning')

    except sqlite3.IntegrityError:
        flash('Erro de integridade ao excluir usuário.', 'danger')

    return redirect(url_for('usuarios_pendentes'))

#Rota para dar toggle admin
@app.route('/usuarios/<int:user_id>/admin', methods=['POST'])
def toggle_admin(user_id):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()

        if result:
            current_status = result[0]
            new_status = 0 if current_status == 1 else 1
            c.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_status, user_id))
            conn.commit()

            if new_status:
                flash('Usuário agora é um administrador.', 'success')
            else:
                flash('Privilégios de administrador removidos.', 'info')
        else:
            flash('Usuário não encontrado.', 'danger')

    return redirect(url_for('usuarios_ativos')) 

#########################################################################
################## PASSANDO O NOME DO USUÁRIO LOGADO ####################
#########################################################################
@app.before_request
def before_request():
    # Define o nome do usuário globalmente
    g.nome_usuario = session.get('user_name', 'Usuário')

@app.context_processor
def inject_user():
    return dict(nome_usuario=g.nome_usuario)

#########################################################################
################## DOCKER + UPLOAD + VALIDAÇÃO JSON #####################
#########################################################################

# Diretórios base do AlphaFold3
ALPHAFOLD_INPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_input'
ALPHAFOLD_OUTPUT_BASE = '/str1/projects/AI-DD/alphafold3/alphafold3_output'
ALPHAFOLD_PARAMS = '/str1/projects/AI-DD/alphafold3/alphafold3_params'
ALPHAFOLD_DB = '/str1/projects/AI-DD/alphafold3/alphafold3_DB'

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    if file and file.filename.endswith('.json'):
        filename = file.filename
        base_name = filename.rsplit('.', 1)[0]

        input_subdir = os.path.join(ALPHAFOLD_INPUT_BASE, base_name)
        output_subdir = os.path.join(ALPHAFOLD_OUTPUT_BASE, base_name)

        os.makedirs(input_subdir, exist_ok=True)
        os.makedirs(output_subdir, exist_ok=True)

        input_file_path = os.path.join(input_subdir, filename)
        file.save(input_file_path)

        # Validação JSON 
        # validado, mensagem = validar_json_input(input_file_path)
        # if not validado:
        #     flash(mensagem)
        #     return redirect(url_for('dashboard'))

        # Comando Docker
        command = (
            f"docker run -it "
            f"--volume {ALPHAFOLD_INPUT_BASE}:/root/af_input "
            f"--volume {ALPHAFOLD_OUTPUT_BASE}:/root/af_output "
            f"--volume {ALPHAFOLD_PARAMS}:/root/models "
            f"--volume {ALPHAFOLD_DB}:/root/public_databases "
            f"--gpus all alphafold3 "
            f"python run_alphafold.py "
            f"--json_path=/root/af_input/{base_name}/{filename} "
            f"--output_dir=/root/af_output/{base_name}"
        )

        subprocess.run(command, shell=True)

        result_file = os.path.join(output_subdir, 'predicted.pdb')
        if os.path.exists(result_file):
            return send_from_directory(output_subdir, 'predicted.pdb')
        else:
            return 'Prediction failed or output not generated.'

    return 'Invalid file format'

def validar_json_input(json_path):
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

#########################################################################
############################ ENVIO DE EMAIL #############################
#########################################################################

from flask import url_for
from itsdangerous import URLSafeTimedSerializer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Configurações de e-mail
EMAIL_SENDER = 'nieledm@gmail.com'
EMAIL_PASSWORD = 'zlde qbxb zvif bfpg' # Use uma app password se for Gmail
# O EMAIL_PASSWORD deve ser uma app password (não a senha da conta Gmail normal). 
# Você gera isso em https://myaccount.google.com/apppasswords.

# Serializer para gerar tokens seguros
serializer = URLSafeTimedSerializer(app.secret_key)

def send_verification_email(name, email, token):
    verification_url = url_for('confirm_email', token=token, _external=True)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Confirme seu e-mail"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email

    html = f"""
    <html>
        <body>
            <p>Olá {name},</p>
            <p>Por favor, confirme seu e-mail clicando no link abaixo:</p>
            <p><a href="{verification_url}">Confirmar e-mail</a></p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, email, msg.as_string())

# Enviar e-mail para todos os administradores
def send_admin_notification(name, email):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        # Busca todos os administradores
        c.execute('SELECT email FROM users WHERE is_admin = 1')
        admins = c.fetchall()  # Lista de e-mails dos admins

    # Envia o e-mail para cada administrador
    for admin in admins:
        admin_email = admin[0]
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Novo usuário aguardando aprovação no AlphaFold"
        msg["From"] = EMAIL_SENDER
        msg["To"] = admin_email

        html = f"""
        <html>
            <body>
                <p>Olá,</p>
                <p>O usuário {name} ({email}) confirmou o seu e-mail para usar o AlphaFold e aguarda aprovação.</p>
                <p>Por favor, acesse o painel de administração para aprovar ou rejeitar a solicitação.</p>
            </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, admin_email, msg.as_string())

def send_activation_email(user_email, user_name):
    # Definir o conteúdo do e-mail
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Sua conta no AlphaFold foi ativada"
    msg["From"] = EMAIL_SENDER
    msg["To"] = user_email

    # Corpo do e-mail em HTML
    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Sua conta foi ativada com sucesso!</p>
            <p>Agora você pode acessar o sistema.</p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    # Enviar o e-mail via SMTP com conexão segura
    try:
        with SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, user_email, msg.as_string())
        print(f"E-mail de ativação enviado para {user_email}")
    except Exception as e:
        print(f"Erro ao enviar o e-mail de ativação: {e}")

#########################################################################
################################# MAIN ##################################
#########################################################################

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)