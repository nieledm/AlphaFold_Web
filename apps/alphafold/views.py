from flask import render_template, redirect, url_for, flash, request, session, g, send_file
from threading import Thread
from datetime import datetime
import os, io, json, pytz, tempfile, zipfile, paramiko, stat, shlex, pwd, grp
from database import get_db_connection
from conections import get_ssh_connection

from apps.logs.utils import log_action
from apps.autentication.utils import admin_required, login_required
from config import ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE, ALPHAFOLD_PARAMS, ALPHAFOLD_DB, ALPHAFOLD_PREDICTION

from .utils import run_alphafold_in_background

from flask import Blueprint
apf_bp = Blueprint('apf', __name__, template_folder='../../templates')

# ==============================================================
# ROTAS DO ALPHAFOLD (UPLOAD, PROCESSAMENTO E DOWNLOAD)
# ==============================================================
@apf_bp.route('/builder_json_form', methods=['GET'])
def builder_json_form():
    print("Usuário na sessão:", dict(session))
    return render_template('builder_json_form.html',
                            nome_usuario=session.get('user_name', 'Usuário'),
                            active_page='json_builder')

@apf_bp.route('/upload', methods=['POST'])
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
        return redirect(url_for('aut.login'))
    
    log_action(user_id, 'Início de Upload de Arquivo', f'Usuário: {user_name}')

    # VERIFICA SE É UM ARQUIVO OU DADOS JSON DIRETOS
    file = None
    json_data = None
    filename = None
    
    # Caso 1: Arquivo enviado via formulário (upload normal)
    if 'file' in request.files:
        file = request.files['file']
        if file and file.filename != '' and file.filename.endswith('.json'):
            filename = file.filename
    
    # Caso 2: Dados JSON enviados via JavaScript (do JSON Builder)
    elif request.form.get('json_data'):
        try:
            json_data = request.form.get('json_data')
            # Criar um nome de arquivo com timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            filename = f"alphafold_data_{timestamp}.json"
        except Exception as e:
            flash('Erro ao processar dados JSON.', 'danger')
            log_action(user_id, 'Erro de Upload', f'Erro no JSON: {str(e)}')
            return redirect(url_for('users.dashboard'))

    # Se nenhum dos casos foi atendido
    if not filename:
        flash('Nenhum arquivo JSON válido enviado.', 'danger')
        log_action(user_id, 'Erro de Upload', 'Nenhum arquivo JSON válido na requisição')
        return redirect(url_for('users.dashboard'))

    # Processamento comum para ambos os casos
    base_name = filename.rsplit('.', 1)[0]

    # Conexão SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh = get_ssh_connection()
    sftp = ssh.open_sftp()

    user_name_clean = session['user_name'].replace(' ', '')
    user_email = session['user_email']
    user_id = session['user_id']

    input_subdir = os.path.join(ALPHAFOLD_INPUT_BASE, user_name_clean)
    output_user_dir = os.path.join(ALPHAFOLD_OUTPUT_BASE, user_name_clean)
    output_subdir = os.path.join(output_user_dir, base_name)

    # Cria diretórios para input e output caso não existam
    input_path_ssh = shlex.quote(input_subdir)
    output_path_ssh = shlex.quote(output_user_dir)
    output_subdir_ssh = shlex.quote(output_subdir)

    mkdir_command = f"mkdir -p {input_path_ssh} {output_path_ssh} {output_subdir_ssh}"
    stdin, stdout, stderr = ssh.exec_command(mkdir_command)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        error = stderr.read().decode()
        raise RuntimeError(f"Erro criando diretórios: {error}")

    # Salva arquivo no servidor - DIFERENÇA AQUI
    input_file_path = os.path.join(input_subdir, filename)
    
    if file:  # Caso 1: Arquivo enviado pelo formulário
        sftp.putfo(file.stream, input_file_path)
    else:     # Caso 2: Dados JSON diretos
        # Criar um arquivo temporário com os dados JSON
        json_content = json_data if isinstance(json_data, str) else json.dumps(json_data, indent=2)
        with sftp.file(input_file_path, 'w') as remote_file:
            remote_file.write(json_content)

    sftp.close()
    ssh.close()

    # Salva no banco
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO uploads (user_id, file_name, base_name, status, created_at) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], filename, base_name, 'PENDENTE', now_str)
    )
    conn.commit()
    conn.close()

    log_action(user_id, 'Arquivo JSON Uploaded', f'Nome: {filename}, BaseName: {base_name}')

    uid = 0  # root
    gid = grp.getgrnam("alphaFoldWeb").gr_gid

    # Monta comando e roda em background
    command = (
        f"docker run "
        f"--user {uid}:{gid} "
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
        command, user_name_clean, user_email, base_name, user_id
    )).start()
            
    flash("Arquivo enviado. Você será notificado quando o processamento terminar.", 'info')
    log_action(user_id, 'Processamento AlphaFold Iniciado', f'BaseName: {base_name}')
    return redirect(url_for('users.dashboard'))

@apf_bp.route('/download/<base_name>')
def download_result(base_name):
    """Permite download do arquivo processado se pronto"""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    
    if not user_name:
        flash('Usuário não encontrado. Faça login novamente.', 'warning')
        log_action(None, 'Tentativa de Download (Não Autenticado)', f'BaseName: {base_name}')
        return redirect(url_for('aut.login'))
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh = get_ssh_connection()

        sftp = ssh.open_sftp()
        remote_folder = f"{ALPHAFOLD_OUTPUT_BASE}/{user_name.replace(' ', '')}/{base_name}/{ALPHAFOLD_PREDICTION}"

        try:
            remote_files = sftp.listdir(remote_folder)
        except IOError as e:
            flash('Resultados não encontrados no servidor.', 'danger')
            print(f"[ERRO] Falha ao acessar: {remote_folder} - Erro: {e}")
            log_action(user_id, 'Download Negado', f'Diretório remoto não encontrado: {remote_folder}')
            return redirect(url_for('users.dashboard'))

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
        return redirect(url_for('users.dashboard'))


    except Exception as e:
        log_action(user_id, 'Erro no Download', str(e))
        flash('Erro ao processar o download.', 'danger')
        return redirect(url_for('users.dashboard'))

@apf_bp.route('/delete_result/<base_name>', methods=['POST'])
@login_required
def delete_result(base_name):
    user_id = session['user_id']
    user_name = session['user_name']
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh = get_ssh_connection()
        sftp = ssh.open_sftp()
        
        user_dir = user_name.replace(' ', '')
        target_dir = f"{ALPHAFOLD_OUTPUT_BASE}/{user_dir}/{base_name}"

        target_dir_ssh = shlex.quote(target_dir)
        ssh.exec_command(f"rm -rf {target_dir_ssh}")

        # ssh.exec_command(f"rm -rf '{target_dir}'")

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

    return redirect(url_for('users.dashboard'))

# ==============================================================
# BACKUP ALPHAFOLD3
# ==============================================================

@apf_bp.route('/admin/export_data')
def export_data():
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))

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
        return redirect(url_for('users.dashboard'))