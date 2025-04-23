from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, session
import os
import subprocess
import json
import re
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '123' 
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        try:
            with sqlite3.connect(DATABASE) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO users (name, email, password, is_active) VALUES (?, ?, ?, ?)',
                          (name, email, password, 0))
                conn.commit()
                flash('Cadastro enviado para aprovação do administrador.', 'info')
                return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('E-mail já cadastrado.', 'danger')

    return render_template('register.html')

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

# Rota para ver usuários ativos ou pendentes
@app.route('/admin/usuarios', methods=['GET'])
def admin_usuarios():
    search_query = request.args.get('search', '')  # Pega a query de pesquisa, se existir

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar usuários ativos com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 1 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_ativos = c.fetchall()

        # Buscar usuários pendentes com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 0 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_pendentes = c.fetchall()

        # Buscar usuários desativados com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 2 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_desativados = c.fetchall()

    return render_template('admin_usuarios.html', 
                           usuarios_ativos=usuarios_ativos, 
                           usuarios_pendentes=usuarios_pendentes, 
                           usuarios_desativados=usuarios_desativados, 
                           search_query=search_query)

# Rota para ver usuários ativos
@app.route('/admin/usuarios_ativos', methods=['GET'])
def usuarios_ativos():
    search_query = request.args.get('search', '')  # Pega a query de pesquisa, se existir

    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()

        # Buscar usuários ativos com filtro e ordenação
        c.execute('SELECT id, name, email FROM users WHERE is_active = 1 AND (name LIKE ? OR email LIKE ?) ORDER BY name ASC',
                  ('%' + search_query + '%', '%' + search_query + '%'))
        usuarios_ativos = c.fetchall()
        
    return render_template('usuarios_ativos.html', 
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
                           usuarios_desativados=usuarios_desativados, 
                           search_query=search_query)

# Rota para aprovar usuário
@app.route('/admin/aprovar/<int:user_id>', methods=['POST'])
def aprovar_usuario(user_id):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_active = 1 WHERE id = ?', (user_id,))
        conn.commit()
    flash('Usuário ativado com sucesso!', 'success')
    return redirect(url_for('admin_usuarios'))



#Rota para inativar usuários
@app.route('/admin/inativar/<int:user_id>', methods=['POST'])
def inativar_usuario(user_id):
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET is_active = 2 WHERE id = ?', (user_id,))
        conn.commit()
    flash('Usuário desativado com sucesso!', 'warning')
    return redirect(url_for('admin_usuarios'))

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
################################# MAIN ##################################
#########################################################################

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)