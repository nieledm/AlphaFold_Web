"""
Gerenciamento de eventos Socket.IO para atualização em tempo real
"""
from flask import current_app
from flask_socketio import emit, join_room, leave_room
from apps.monitor.utils import get_system_status, parse_system_status, get_job_counts, get_pending_jobs
from config import ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER
from flask import session
from threading import Thread
import time
from database import get_db_connection

# Placeholder para socketio - será atribuído em app.py
socketio = None

# Dicionários para rastrear threads de atualização por sessão
update_threads = {}
stop_updates = {}
job_update_threads = {}
stop_job_updates = {}
log_update_threads = {}
stop_log_updates = {}


# =========================================================
# FUNÇÕES DE HANDLERS (sem decoradores)
# =========================================================

def handle_connect():
    """Gerencia conexão do cliente"""
    print(f"[SocketIO] Cliente conectado: {session.get('user_name', 'Usuário desconhecido')}")
    emit('connect_response', {'data': 'Conectado ao servidor'})


def handle_disconnect():
    """Gerencia desconexão do cliente"""
    print(f"[SocketIO] Cliente desconectado: {session.get('user_name', 'Usuário desconhecido')}")


def handle_status_update_request():
    """
    Cliente requisita uma atualização de status.
    Enviamos CPU, Memória, GPU, etc
    """
    try:
        # Busca o status do servidor remoto
        raw_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
        status = parse_system_status(raw_status) if 'error' not in raw_status else None
        
        # Busca contagem de jobs
        running_count, pending_count = get_job_counts()
        
        # Busca jobs pendentes (se for admin)
        pending_jobs_list = get_pending_jobs() if session.get("is_admin") else []

        # Emite os dados para o cliente
        emit('status_update', {
            'status': status,
            'error': raw_status.get('error') if 'error' in raw_status else None,
            'running_count': running_count,
            'pending_count': pending_count,
            'pending_jobs_list': pending_jobs_list,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"[SocketIO] Erro ao atualizar status: {str(e)}")
        emit('status_error', {
            'error': f"Erro ao atualizar status: {str(e)}",
            'timestamp': time.time()
        })


def handle_start_live_updates():
    """
    Cliente pede para começar a receber atualizações periódicas.
    """
    session_id = session.get('session_id', 'unknown')
    is_admin = session.get('is_admin', False)
    print(f"[SocketIO] Cliente {session_id} solicitou atualizações ao vivo")
    
    # Marca que não deve parar
    stop_updates[session_id] = False
    
    def emit_updates(is_admin_flag):
        """Função que roda em background e emite atualizações"""
        
        # Envia atualizações a cada 5 segundos
        while not stop_updates.get(session_id, False):
            try:
                # Busca status
                raw_status = get_system_status(ALPHAFOLD_SSH_HOST, ALPHAFOLD_SSH_PORT, ALPHAFOLD_SSH_USER)
                status = parse_system_status(raw_status) if 'error' not in raw_status else None
                
                running_count, pending_count = get_job_counts()
                pending_jobs_list = get_pending_jobs() if session.get("is_admin") else []

                # Emite para o cliente específico
                with current_app.app_context():
                    socketio.emit('status_update', {
                        'status': status,
                        'error': raw_status.get('error') if 'error' in raw_status else None,
                        'running_count': running_count,
                        'pending_count': pending_count,
                        'pending_jobs_list': pending_jobs_list,
                        'timestamp': time.time()
                    }, to=session_id)
                
                time.sleep(5)  # Aguarda 5 segundos antes da próxima atualização
                
            except Exception as e:
                print(f"[SocketIO] Erro ao emitir atualizações: {str(e)}")
                break
    
    # Inicia thread para emitir atualizações (só se não tiver uma ativa)
    if session_id not in update_threads or not update_threads[session_id].is_alive():
        update_thread = Thread(target=emit_updates, args=(is_admin,), daemon=True)
        update_thread.start()
        update_threads[session_id] = update_thread
    
    emit('live_updates_started', {'message': 'Atualizações ao vivo iniciadas'})


def handle_stop_live_updates():
    """Cliente pede para parar de receber atualizações periódicas"""
    session_id = session.get('session_id', 'unknown')
    print(f"[SocketIO] Cliente {session_id} solicitou parada de atualizações ao vivo")
    
    # Marca para parar
    stop_updates[session_id] = True
    
    emit('live_updates_stopped', {'message': 'Atualizações ao vivo pararam'})


def handle_user_jobs_update():
    """
    Cliente (dashboard) requisita lista atualizada de seus jobs
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            emit('jobs_error', {'error': 'Usuário não autenticado'})
            return
        
        # Busca os jobs do usuário
        conn = get_db_connection()
        uploads = conn.execute(
            'SELECT base_name, file_name, status, created_at FROM uploads WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        ).fetchall()
        conn.close()
        
        # Converte para lista de dicts
        uploads_list = [
            {
                'base_name': u[0],
                'file_name': u[1],
                'status': u[2],
                'created_at': u[3]
            }
            for u in uploads
        ]
        
        emit('jobs_update', {
            'uploads': uploads_list,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"[SocketIO] Erro ao atualizar jobs: {str(e)}")
        emit('jobs_error', {'error': f"Erro ao atualizar jobs: {str(e)}"})


# Dicionário para rastrear threads de jobs por sessão
job_update_threads = {}
stop_job_updates = {}

def handle_start_jobs_live_updates():
    """
    Cliente (dashboard) pede atualizações periódicas de seus jobs
    """
    session_id = session.get('session_id', 'unknown')
    user_id = session.get('user_id')
    
    if not user_id:
        emit('jobs_error', {'error': 'Usuário não autenticado'})
        return
    
    print(f"[SocketIO] Usuário {user_id} solicitou atualizações de jobs ao vivo")
    
    # Marca que não deve parar
    stop_job_updates[session_id] = False
    
    def emit_job_updates():
        """Função que roda em background e emite atualizações de jobs"""
        
        # Envia atualizações a cada 3 segundos
        while not stop_job_updates.get(session_id, False):
            try:
                conn = get_db_connection()
                uploads = conn.execute(
                    'SELECT base_name, file_name, status, created_at FROM uploads WHERE user_id = ? ORDER BY created_at DESC',
                    (user_id,)
                ).fetchall()
                conn.close()
                
                # Converte para lista de dicts
                uploads_list = [
                    {
                        'base_name': u[0],
                        'file_name': u[1],
                        'status': u[2],
                        'created_at': u[3]
                    }
                    for u in uploads
                ]
                
                # Emite para o cliente específico
                with current_app.app_context():
                    socketio.emit('jobs_update', {
                        'uploads': uploads_list,
                        'timestamp': time.time()
                    }, to=session_id)
                
                time.sleep(3)  # Aguarda 3 segundos antes da próxima atualização
                
            except Exception as e:
                print(f"[SocketIO] Erro ao emitir atualizações de jobs: {str(e)}")
                break
    
    # Inicia thread para emitir atualizações (só se não tiver uma ativa)
    if session_id not in job_update_threads or not job_update_threads[session_id].is_alive():
        job_thread = Thread(target=emit_job_updates, daemon=True)
        job_thread.start()
        job_update_threads[session_id] = job_thread
    
    emit('jobs_live_updates_started', {'message': 'Atualizações de jobs iniciadas'})


def handle_stop_jobs_live_updates():
    """Cliente (dashboard) pede para parar atualizações de jobs"""
    session_id = session.get('session_id', 'unknown')
    print(f"[SocketIO] Usuário solicitou parada de atualizações de jobs ao vivo")
    
    # Marca para parar
    stop_job_updates[session_id] = True
    
    emit('jobs_live_updates_stopped', {'message': 'Atualizações de jobs pararam'})


def handle_logs_update_request():
    """
    Cliente (página de logs) requisita lista atualizada de logs
    """
    try:
        # Verifica se é admin
        if not session.get('is_admin'):
            emit('logs_error', {'error': 'Acesso negado: apenas admins podem ver logs'})
            return
        
        # Busca os logs com filtros da sessão
        search_query = session.get('logs_search_query', '')
        user_name_filter = session.get('logs_user_name_filter', '')
        user_id_filter = session.get('logs_user_id_filter', '')
        start_date = session.get('logs_start_date', '')
        end_date = session.get('logs_end_date', '')
        
        conn = get_db_connection()
        
        query = """
            SELECT 
                l.id, 
                l.user_id, 
                u.name AS user_name,
                l.action, 
                l.timestamp, 
                l.details 
            FROM logs l
            LEFT JOIN users u ON l.user_id = u.id
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
                query += " AND user_id = ?"
                params.append(int(user_id_filter))
            except ValueError:
                pass

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date + " 00:00:00")

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date + " 23:59:59")

        query += " ORDER BY timestamp DESC, l.id DESC LIMIT 100"
        logs_data = conn.execute(query, params).fetchall()
        conn.close()
        
        # Converte para lista de dicts
        logs_list = [
            {
                'id': log[0],
                'user_id': log[1],
                'user_name': log[2] or 'N/A',
                'action': log[3],
                'timestamp': log[4],
                'details': log[5] or 'N/A'
            }
            for log in logs_data
        ]
        
        emit('logs_update', {
            'logs': logs_list,
            'count': len(logs_list),
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"[SocketIO] Erro ao atualizar logs: {str(e)}")
        emit('logs_error', {'error': f"Erro ao atualizar logs: {str(e)}"})


# Dicionário para rastrear threads de logs por sessão
log_update_threads = {}
stop_log_updates = {}

def handle_start_logs_live_updates(data=None):
    """
    Cliente (página de logs) pede atualizações periódicas de logs
    """
    session_id = session.get('session_id', 'unknown')
    
    # Verifica se é admin
    if not session.get('is_admin'):
        emit('logs_error', {'error': 'Acesso negado: apenas admins podem ver logs'})
        return
    
    # Armazena filtros na sessão para usar nas atualizações
    if data:
        session['logs_search_query'] = data.get('search_query', '')
        session['logs_user_name_filter'] = data.get('user_name_filter', '')
        session['logs_user_id_filter'] = data.get('user_id_filter', '')
        session['logs_start_date'] = data.get('start_date', '')
        session['logs_end_date'] = data.get('end_date', '')
    
    print(f"[SocketIO] Admin solicitou atualizações de logs ao vivo")
    
    # Marca que não deve parar
    stop_log_updates[session_id] = False
    
    def emit_log_updates():
        """Função que roda em background e emite atualizações de logs"""
        
        # Envia atualizações a cada 4 segundos
        while not stop_log_updates.get(session_id, False):
            try:
                # Busca os logs
                search_query = session.get('logs_search_query', '')
                user_name_filter = session.get('logs_user_name_filter', '')
                user_id_filter = session.get('logs_user_id_filter', '')
                start_date = session.get('logs_start_date', '')
                end_date = session.get('logs_end_date', '')
                
                conn = get_db_connection()
                
                query = """
                    SELECT 
                        l.id, 
                        l.user_id, 
                        u.name AS user_name,
                        l.action, 
                        l.timestamp, 
                        l.details 
                    FROM logs l
                    LEFT JOIN users u ON l.user_id = u.id
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
                        query += " AND user_id = ?"
                        params.append(int(user_id_filter))
                    except ValueError:
                        pass

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date + " 00:00:00")

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date + " 23:59:59")

                query += " ORDER BY timestamp DESC, l.id DESC LIMIT 100"
                logs_data = conn.execute(query, params).fetchall()
                conn.close()
                
                # Converte para lista de dicts
                logs_list = [
                    {
                        'id': log[0],
                        'user_id': log[1],
                        'user_name': log[2] or 'N/A',
                        'action': log[3],
                        'timestamp': log[4],
                        'details': log[5] or 'N/A'
                    }
                    for log in logs_data
                ]
                
                # Emite para o cliente específico
                with current_app.app_context():
                    socketio.emit('logs_update', {
                        'logs': logs_list,
                        'count': len(logs_list),
                        'timestamp': time.time()
                    }, to=session_id)
                
                time.sleep(4)  # Aguarda 4 segundos antes da próxima atualização
                
            except Exception as e:
                print(f"[SocketIO] Erro ao emitir atualizações de logs: {str(e)}")
                break
    
    # Inicia thread para emitir atualizações (só se não tiver uma ativa)
    if session_id not in log_update_threads or not log_update_threads[session_id].is_alive():
        log_thread = Thread(target=emit_log_updates, daemon=True)
        log_thread.start()
        log_update_threads[session_id] = log_thread
    
    emit('logs_live_updates_started', {'message': 'Atualizações de logs iniciadas'})


def handle_stop_logs_live_updates():
    """Cliente (página de logs) pede para parar atualizações de logs"""
    session_id = session.get('session_id', 'unknown')
    print(f"[SocketIO] Admin solicitou parada de atualizações de logs ao vivo")
    
    # Marca para parar
    stop_log_updates[session_id] = True
    
    emit('logs_live_updates_stopped', {'message': 'Atualizações de logs pararam'})


# =========================================================
# FUNÇÃO PARA REGISTRAR HANDLERS (chamada de app.py)
# =========================================================

def register_socketio_handlers(socket_instance):
    """
    Registra todos os handlers de Socket.IO com a instância do socketio.
    Deve ser chamada após socketio ser criado em app.py
    """
    global socketio
    socketio = socket_instance
    
    # Registra os handlers
    socketio.on('connect')(handle_connect)
    socketio.on('disconnect')(handle_disconnect)
    socketio.on('request_status_update')(handle_status_update_request)
    socketio.on('start_live_updates')(handle_start_live_updates)
    socketio.on('stop_live_updates')(handle_stop_live_updates)
    socketio.on('request_user_jobs_update')(handle_user_jobs_update)
    socketio.on('start_jobs_live_updates')(handle_start_jobs_live_updates)
    socketio.on('stop_jobs_live_updates')(handle_stop_jobs_live_updates)
    socketio.on('request_logs_update')(handle_logs_update_request)
    socketio.on('start_logs_live_updates')(handle_start_logs_live_updates)
    socketio.on('stop_logs_live_updates')(handle_stop_logs_live_updates)
    
    print("[SocketIO] Todos os handlers foram registrados com sucesso!")
