/**
 * Cliente Socket.IO para atualização em tempo real do Dashboard
 * Monitora jobs do usuário em tempo real
 */

// Conecta ao servidor Socket.IO
const socket = io();

let isReceivingJobUpdates = false;

// =========================================================
// EVENTOS DE CONEXÃO
// =========================================================

socket.on('connect', function() {
    console.log('[Socket.IO Dashboard] Conectado ao servidor');
    // Solicita uma atualização inicial de jobs
    requestJobsUpdate();
});

socket.on('disconnect', function() {
    console.log('[Socket.IO Dashboard] Desconectado do servidor');
});

// =========================================================
// RECEBER ATUALIZAÇÕES DE JOBS
// =========================================================

socket.on('jobs_update', function(data) {
    console.log('[Socket.IO] Jobs atualizados:', data.uploads);
    updateJobsUI(data.uploads);
});

socket.on('jobs_error', function(data) {
    console.error('[Socket.IO] Erro:', data.error);
    showJobsError(data.error);
});

socket.on('jobs_live_updates_started', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingJobUpdates = true;
});

socket.on('jobs_live_updates_stopped', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingJobUpdates = false;
});

// =========================================================
// FUNÇÕES DE REQUISIÇÃO
// =========================================================

/**
 * Requisita uma atualização de jobs imediata
 */
function requestJobsUpdate() {
    socket.emit('request_user_jobs_update');
}

/**
 * Inicia atualizações periódicas de jobs em tempo real
 */
function startJobsLiveUpdates() {
    socket.emit('start_jobs_live_updates');
}

/**
 * Para atualizações periódicas de jobs
 */
function stopJobsLiveUpdates() {
    socket.emit('stop_jobs_live_updates');
}

// =========================================================
// ATUALIZAR UI DO DASHBOARD
// =========================================================

/**
 * Atualiza a tabela de jobs com novos dados
 */
function updateJobsUI(uploads) {
    const tbody = document.querySelector('.uploads-table tbody');
    if (!tbody) return;

    // Se não houver uploads, mostra mensagem
    if (!uploads || uploads.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-muted py-4">
                    Nenhum upload ainda
                </td>
            </tr>
        `;
        return;
    }

    // Reconstrói a tabela com os novos dados
    tbody.innerHTML = uploads.map((upload, index) => {
        const statusClass = getStatusClass(upload.status);
        const statusIcon = getStatusIcon(upload.status);
        const statusText = upload.status;

        let actionHTML = '';
        if (upload.status === 'COMPLETO') {
            actionHTML = `
                <div class="action-buttons">
                    <a href="/download/${upload.base_name}" class="btn-action btn-download">
                        <i class="fas fa-download me-1"></i>Download
                    </a>
                    <form method="POST" 
                          action="/delete/${upload.base_name}" 
                          style="display:inline;" 
                          onsubmit="return confirm('Deseja excluir este resultado?');">
                        <button type="submit" class="btn-action btn-delete">
                            <i class="fas fa-trash me-1"></i>Excluir
                        </button>
                    </form>
                </div>
            `;
        } else if (upload.status === 'PROCESSANDO' || upload.status === 'PENDENTE') {
            actionHTML = `
                <span class="text-muted small">
                    <i class="fas fa-clock me-1"></i>Aguarde...
                </span>
            `;
        } else {
            actionHTML = '<span class="text-muted small">-</span>';
        }

        return `
            <tr class="job-row" data-base-name="${upload.base_name}">
                <td class="fw-medium">${escapeHtml(upload.file_name)}</td>
                <td>
                    <span class="status-badge ${statusClass}">
                        <i class="fas ${statusIcon} me-1"></i>${statusText}
                    </span>
                </td>
                <td class="text-muted">${upload.created_at}</td>
                <td>${actionHTML}</td>
            </tr>
        `;
    }).join('');

    // Anima as novas linhas
    animateNewRows();
}

/**
 * Retorna a classe CSS para o status
 */
function getStatusClass(status) {
    const classes = {
        'COMPLETO': 'status-complete',
        'ERRO': 'status-error',
        'CANCELADO': 'status-cancelled',
        'PENDENTE': 'status-pending',
        'EXCLUIDO': 'status-deleted',
        'PROCESSANDO': 'status-processing'
    };
    return classes[status] || 'status-unknown';
}

/**
 * Retorna o ícone FontAwesome para o status
 */
function getStatusIcon(status) {
    const icons = {
        'COMPLETO': 'fa-check-circle',
        'ERRO': 'fa-exclamation-circle',
        'CANCELADO': 'fa-ban',
        'PENDENTE': 'fa-hourglass-half',
        'EXCLUIDO': 'fa-trash',
        'PROCESSANDO': 'fa-sync-alt fa-spin'
    };
    return icons[status] || 'fa-question-circle';
}

/**
 * Anima as linhas adicionadas
 */
function animateNewRows() {
    const rows = document.querySelectorAll('.job-row');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.animation = `fadeIn 0.3s ease-in forwards`;
        row.style.animationDelay = `${index * 0.1}s`;
    });
}

/**
 * Atualiza o timestamp da última atualização
 */

/**
 * Mostra mensagem de erro
 */
function showJobsError(error) {
    console.error('Erro de jobs:', error);
    const errorContainer = document.getElementById('jobs-error-container');
    if (errorContainer) {
        errorContainer.innerHTML = `<div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(error)}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
    }
}

/**
 * Escapa caracteres HTML para segurança
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// =========================================================
// INICIALIZAÇÃO
// =========================================================

// Inicia atualizações ao vivo quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    // Aguarda um pouco para garantir que está conectado
    setTimeout(() => {
        startJobsLiveUpdates();
    }, 1000);
});

// Para atualizações quando sair da página
window.addEventListener('beforeunload', function() {
    stopJobsLiveUpdates();
});

// =========================================================
// ADICIONAR ANIMAÇÃO CSS
// =========================================================

// Injeta CSS para animação
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-5px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    #last-update-jobs.updated {
    }
    
`;
document.head.appendChild(style);
