from flask import render_template, redirect, url_for, flash, request, session
import os
import shutil
from database import get_db_connection

from apps.logs.utils import log_action
from apps.autentication.utils import admin_required, login_required
from config import ALPHAFOLD_INPUT_BASE, ALPHAFOLD_OUTPUT_BASE
from apps.emails.utils import send_activation_email

from flask import Blueprint
admins_bp = Blueprint('admins', __name__, template_folder='templates')

# ==============================================================
# ROTAS DE ADMINISTRAÇÃO
# ==============================================================
@admins_bp.route('/admin/usuarios_ativos')
def usuarios_ativos():
    """Lista usuários ativos"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))

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

@admins_bp.route('/admin/usuarios_pendentes')
def usuarios_pendentes():
    """Lista usuários pendentes de aprovação"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))

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

@admins_bp.route('/admin/usuarios_desativados')
def usuarios_desativados():
    """Lista usuários desativados"""
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('users.dashboard'))

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

@admins_bp.route('/admin/aprovar/<int:user_id>', methods=['POST'])
def aprovar_usuario(user_id):
    """Aprova um usuário pendente"""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: aprovar_usuario para ID {user_id}')
        return redirect(url_for('users.dashboard'))

    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT name, email, is_active FROM users WHERE id = ?', (user_id,)) # Incluindo is_active para verificação
            user_to_approve = c.fetchone() # Renomeado para clareza

            if user_to_approve:
                if user_to_approve['is_active'] == 1:
                    flash(f"Usuário {user_to_approve['name']} já está ativo.", 'info')
                    log_action(admin_user_id, 'Tentativa de aprovação de usuário já ativo', f'ID: {user_id}, Nome: {user_to_approve["name"]}, Email: {user_to_approve["email"]}')
                    return redirect(url_for('admins.usuarios_ativos'))

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

    return redirect(url_for('admins.usuarios_ativos'))

@admins_bp.route('/admin/inativar/<int:user_id>', methods=['POST'])
def inativar_usuario(user_id):
    """Inativa um usuário"""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: inativar_usuario para ID {user_id}')
        return redirect(url_for('users.dashboard'))

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
                    return redirect(url_for('admins.usuarios_desativados'))
                
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

    return redirect(url_for('admins.usuarios_desativados'))


@admins_bp.route('/usuarios/<int:user_id>/excluir', methods=['POST'])
def excluir_usuario(user_id):
    """Exclui um usuário (pendente, ativo, ou desativado) e seus dados associados."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: excluir_usuario para ID {user_id}')
        return redirect(url_for('user.dashboard'))

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
                    return redirect(url_for('admins.usuarios_ativos')) # ou onde for mais apropriado

                c.execute('DELETE FROM uploads WHERE user_id = ?', (user_id,))
                c.execute('DELETE FROM logs WHERE user_id = ?', (user_id,))
                
                c.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()

                if c.rowcount > 0:
                    flash('Usuário excluído com sucesso!', 'success')
                    log_action(admin_user_id, 'Usuário Excluído', f'ID: {user_id}, Nome: {user_to_delete["name"]}, Email: {user_to_delete["email"]}')

                    user_folder_name = user_to_delete['name']
                    input_user_dir = os.path.join(ALPHAFOLD_INPUT_BASE, user_folder_name).replace("\\", "/")
                    output_user_dir = os.path.join(ALPHAFOLD_OUTPUT_BASE, user_folder_name).replace("\\", "/")
                    
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

    return redirect(url_for('admins.usuarios_pendentes'))

@admins_bp.route('/usuarios/<int:user_id>/admin', methods=['POST'])
def toggle_admin(user_id):
    """Alterna status de administrador de um usuário."""
    admin_user_id = session.get('user_id')

    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', f'Rota: toggle_admin para ID {user_id}')
        return redirect(url_for('users.dashboard'))

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

    return redirect(url_for('admins.usuarios_ativos'))