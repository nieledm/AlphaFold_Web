from flask import render_template, session, request, redirect, url_for, flash, send_file, session 
from database import get_db_connection
import os
import json
import tempfile
import zipfile
from apps.autentication.utils import admin_required
               
from .utils import log_action

from flask import Blueprint
logs_bp = Blueprint('logs', __name__, template_folder='../../templates')

@logs_bp.route('/admin/view_logs', methods=['GET'])
def view_logs():
    """Exibe os logs do sistema com opções de filtro."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', 'Rota: view_logs')
        return redirect(url_for('users.dashboard'))

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

@logs_bp.route('/admin/clear_logs', methods=['POST'])
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
                return redirect(url_for('logs.view_logs'))
            
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
            return redirect(url_for('logs.view_logs'))

        cursor.execute(delete_query, delete_params)
        conn.commit()
        
        rows_deleted = cursor.rowcount
        flash(f'Foram removidos {rows_deleted} logs com sucesso!', 'success')
        
        log_action(admin_user_id, 'Logs Limpos', f'Removidos {rows_deleted} logs. Critérios: {"; ".join(details_for_log) if details_for_log else "Nenhum específico"}')

    except Exception as e:
        flash(f'Ocorreu um erro ao limpar os logs: {e}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('logs.view_logs'))

@logs_bp.route('/admin/export_logs', methods=['POST'])
def export_logs():
    """Exporta os logs do sistema no formato JSON compactado em ZIP."""
    admin_user_id = session.get('user_id')
    if not session.get('is_admin'):
        flash('Acesso não autorizado.', 'danger')
        log_action(admin_user_id, 'Tentativa de acesso não autorizado', 'Rota: export_logs')
        return redirect(url_for('users.dashboard'))

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
        return redirect(url_for('logs.view_logs'))
    finally:
        conn.close()