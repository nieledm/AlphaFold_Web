from flask import Blueprint, jsonify, request, session
from apps.monitor.utils import (
    get_pending_jobs, get_next_job, update_job_priority, 
    cancel_job, get_slurm_queue, get_job_counts
)

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/api/jobs/queue', methods=['GET'])
def get_queue():
    """Obtém fila de jobs"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    pending = get_pending_jobs()
    next_job = get_next_job()
    slurm_queue = get_slurm_queue()
    counts = get_job_counts()
    
    return jsonify({
        'pending_jobs': pending,
        'next_job': next_job,
        'slurm_queue': slurm_queue,
        'counts': counts
    })

@jobs_bp.route('/api/jobs/<int:job_id>/priority', methods=['POST'])
def change_priority(job_id):
    """Altera prioridade de um job"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    direction = request.json.get('direction', 'up')
    
    if direction not in ['up', 'down']:
        return jsonify({'error': 'Direção inválida'}), 400
    
    success = update_job_priority(job_id, direction)
    
    if success:
        return jsonify({'success': True, 'message': f'Prioridade {direction} atualizada'})
    else:
        return jsonify({'error': 'Falha ao atualizar prioridade'}), 500

@jobs_bp.route('/api/jobs/<int:job_id>/cancel', methods=['POST'])
def cancel_user_job(job_id):
    """Cancela um job"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Não autorizado'}), 401
    
    success, message = cancel_job(job_id, user_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400

@jobs_bp.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def admin_cancel_job(job_id):
    """Admin cancela qualquer job"""
    if not session.get('is_admin'):
        return jsonify({'error': 'Não autorizado'}), 403
    
    success, message = cancel_job(job_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400

# Registra o blueprint no app
def init_app(app):
    app.register_blueprint(jobs_bp)