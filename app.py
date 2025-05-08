from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, session, g
import os
import subprocess
import json
import re
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from smtplib import SMTP_SSL
from threading import Thread


app = Flask(__name__)
app.secret_key = '#!Alph@3!' 

# ==============================================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================================
DATABASE = 'database.db'

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
# FUNÇÕES DE BANCO DE DADOS
# ==============================================================
def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

def get_db_connection():
    """Retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

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
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
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

def send_processing_complete_email(user_name, user_email, base_name):
    """Envia e-mail ao usuário informando que o processamento foi concluído"""
    download_url = url_for('download_result', user_id=session['user_id'], project_name=base_name, _external=True)
    html = f"""
    <html>
        <body>
            <p>Olá {user_name},</p>
            <p>Seu processamento com o AlphaFold foi concluído com sucesso.</p>
            <p>Você pode baixar o resultado clicando no link abaixo:</p>
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

        if user and user['password'] == password:
            if user['is_active'] == 0:
                flash('Seu cadastro ainda não foi aprovado.', 'warning')
            elif user['is_active'] == 2:
                flash('Sua conta foi inativada. Contate o administrador.', 'danger')
            elif user['is_active'] == 1:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                session['is_admin'] = bool(user['is_admin'])
                flash('Login bem-sucedido!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Rota de logout"""
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Rota de registro de novos usuários"""
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password'] 

        if get_user_by_email(email):
            flash('E-mail já cadastrado.', 'danger')
            return redirect(url_for('login'))

        user_data = {'name': name, 'email': email, 'password': password}
        token = serializer.dumps(user_data, salt='email-verification')
        send_verification_email(name, email, token)

        flash('Verifique seu e-mail para confirmar o cadastro.', 'info')
        return redirect(url_for('aviso', aviso_id=1))

    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    """Rota para confirmar e-mail do usuário"""
    try:
        user_data = serializer.loads(token, salt='email-verification', max_age=3600)
        name, email, password = user_data['name'], user_data['email'], user_data['password']

        with get_db_connection() as conn:
            c = conn.cursor()
            if get_user_by_email(email):
                flash('Este e-mail já foi confirmado anteriormente.', 'info')
                return redirect(url_for('login'))

            c.execute('INSERT INTO users (name, email, password, is_active) VALUES (?, ?, ?, ?)',
                      (name, email, password, 0))
            conn.commit()

        send_admin_notification(name, email)
        flash('E-mail confirmado com sucesso! Aguardando aprovação do administrador.', 'success')
        return redirect(url_for('aviso', aviso_id=2))

    except Exception as e:
        flash('O link de confirmação é inválido ou expirou.', 'danger')
        print('Erro na confirmação:', e)
        return redirect(url_for('register'))

# ==============================================================
# ROTAS DE USUÁRIO
# ==============================================================
@app.route('/dashboard')
def dashboard():
    """Painel principal do usuário"""
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    uploads = conn.execute(
        "SELECT * FROM uploads WHERE user_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('dashboard.html', nome_usuario=session.get('user_name', 'Usuário'), uploads=uploads)

    

@app.route('/aviso/<int:aviso_id>')
def aviso(aviso_id):
    """Exibe mensagens de aviso"""
    avisos = {
        1: "Um email de confimação foi enviado para o endereço de email cadastrado. Por favor, verifique a sua caixa de entrada (ou spam) para confirmar o seu e-mail.", 
        2: "Seu e-mail foi confirmado! Agora é só aguardar a aprovação do administrador.",
        3: "A sua conta foi ativada com sucesso!",
    }
    return render_template('base_avisos.html', aviso_mensagem=avisos.get(aviso_id, "Aviso desconhecido."))

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
                         search_query=search_query)

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
                         search_query=search_query)

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
                         search_query=search_query)

@app.route('/admin/aprovar/<int:user_id>', methods=['POST'])
def aprovar_usuario(user_id):
    """Aprova um usuário pendente"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT name, email FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()

        if user:
            c.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
            conn.commit()
            send_activation_email(user['email'], user['name'])
            flash('Usuário ativado com sucesso!', 'success')
        else:
            flash('Usuário não encontrado!', 'error')

    return redirect(url_for('usuarios_ativos'))

@app.route('/admin/inativar/<int:user_id>', methods=['POST'])
def inativar_usuario(user_id):
    """Inativa um usuário"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_active = 2 WHERE id = ?', (user_id,))
        conn.commit()
    flash('Usuário desativado com sucesso!', 'warning')
    return redirect(url_for('usuarios_desativados'))

@app.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def excluir_usuario(user_id):
    """Exclui um usuário pendente"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            flash('Usuário excluído com sucesso!' if c.rowcount > 0 else 'Usuário não encontrado.', 
                  'success' if c.rowcount > 0 else 'warning')
    except sqlite3.IntegrityError:
        flash('Erro de integridade ao excluir usuário.', 'danger')

    return redirect(url_for('usuarios_pendentes'))

@app.route('/usuarios/<int:user_id>/admin', methods=['POST'])
def toggle_admin(user_id):
    """Alterna status de administrador"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('dashboard'))

    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()

        if result:
            new_status = 0 if result['is_admin'] == 1 else 1
            c.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_status, user_id))
            conn.commit()
            flash('Usuário agora é um administrador.' if new_status else 'Privilégios de administrador removidos.', 
                  'success' if new_status else 'info')
        else:
            flash('Usuário não encontrado.', 'danger')

    return redirect(url_for('usuarios_ativos')) 

# ==============================================================
# ROTAS DO ALPHAFOLD (UPLOAD, PROCESSAMENTO E DOWNLOAD)
# ==============================================================
@app.route('/builder_json_form', methods=['GET'])
def builder_json_form():
    return render_template('builder_json_form.html')

@app.route('/generate_json', methods=['POST'])
def generate_json():
    if 'user_id' not in session:
        flash('Por favor, faça login primeiro.', 'warning')
        return redirect(url_for('login'))

    data = request.form
    json_data = {"inputs": []}

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

    # === Upload automático para /upload ===
    with open(tmpfile_path, 'rb') as f:
        upload_response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': (tmpfile_name, f, 'application/json')},
            cookies=request.cookies  # passa os cookies para manter a sessão
        )

    if upload_response.status_code == 302:  # redirecionamento com sucesso
        flash("Arquivo gerado e enviado com sucesso!", "success")
    else:
        flash("Erro ao enviar o arquivo gerado para processamento.", "danger")

    # === Retorna para download (caso deseje salvar também) ===
    return send_file(tmpfile_path, mimetype='application/json', as_attachment=True, download_name='input_alphafold.json')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Processa upload de arquivos para o AlphaFold"""
    if not all(key in session for key in ['user_id', 'user_name', 'user_email']):
        flash('Por favor, faça login novamente.', 'warning')
        return redirect(url_for('login'))

    if 'file' not in request.files:
        return 'No file part'

    file = request.files['file']
    if file.filename == '':
        return 'No selected file'

    if file and file.filename.endswith('.json'):
        filename = file.filename
        base_name = filename.rsplit('.', 1)[0]

        # Cria diretórios
        input_subdir = os.path.join(ALPHAFOLD_INPUT_BASE, base_name)
        output_subdir = os.path.join(ALPHAFOLD_OUTPUT_BASE, base_name)
        os.makedirs(input_subdir, exist_ok=True)
        os.makedirs(output_subdir, exist_ok=True)

        # Salva arquivo
        input_file_path = os.path.join(input_subdir, filename)
        file.save(input_file_path)

        # Salva no banco
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO uploads (user_id, file_name, base_name, status) VALUES (?, ?, ?, ?)',
            (session['user_id'], filename, base_name, 'PROCESSANDO')
        )
        conn.commit()
        conn.close()

        # Monta comando e roda em background
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

        Thread(target=run_alphafold_in_background, args=(
            command, output_subdir, session['user_name'], session['user_email'], base_name
        )).start()

        flash("Arquivo enviado. Você será notificado quando o processamento terminar.", 'info')
        return redirect(url_for('dashboard'))

    return 'Invalid file format'

def run_alphafold_in_background(command, output_subdir, user_name, user_email, base_name):
    subprocess.run(command, shell=True)
    result_file = os.path.join(output_subdir, 'predicted.pdb')

    conn = get_db_connection()
    if os.path.exists(result_file):
        # Atualiza status para COMPLETO
        conn.execute("UPDATE uploads SET status = ? WHERE base_name = ?", ('COMPLETO', base_name))
        send_processing_complete_email(user_name, user_email, base_name)
    else:
        conn.execute("UPDATE uploads SET status = ? WHERE base_name = ?", ('ERRO', base_name))
        send_email(user_email, "Erro no processamento do AlphaFold", f"<p>Olá {user_name},</p><p>Ocorreu um erro e o arquivo de resultado não foi gerado.</p>")
    conn.commit()
    conn.close()

@app.route('/download/<base_name>')
def download_result(base_name):
    """Permite download do arquivo processado se pronto"""
    output_dir = os.path.join(ALPHAFOLD_OUTPUT_BASE, base_name)
    file_path = os.path.join(output_dir, 'predicted.pdb')
    if os.path.exists(file_path):
        return send_from_directory(output_dir, 'predicted.pdb', as_attachment=True)
    else:
        flash('Arquivo não encontrado ou ainda não gerado.', 'danger')
        return redirect(url_for('dashboard'))


# ==============================================================
# FUNÇÕES DE CONTEXTO E INICIALIZAÇÃO
# ==============================================================
@app.before_request
def before_request():
    """Define variáveis globais antes de cada requisição"""
    g.nome_usuario = session.get('user_name', 'Usuário')

@app.context_processor
def inject_user():
    """Injeta variáveis em todos os templates"""
    return dict(nome_usuario=g.nome_usuario)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)