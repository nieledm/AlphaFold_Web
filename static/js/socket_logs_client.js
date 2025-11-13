/**
 * Cliente Socket.IO para atualização em tempo real da Página de Logs
 * Monitora novos logs em tempo real
 */

// Conecta ao servidor Socket.IO
const socket = io();

let isReceivingLogUpdates = false;

// =========================================================
// EVENTOS DE CONEXÃO
// =========================================================

socket.on('connect', function() {
    console.log('[Socket.IO Logs] Conectado ao servidor');
    // Solicita uma atualização inicial de logs
    requestLogsUpdate();
});

socket.on('disconnect', function() {
    console.log('[Socket.IO Logs] Desconectado do servidor');
});

// =========================================================
// RECEBER ATUALIZAÇÕES DE LOGS
// =========================================================

socket.on('logs_update', function(data) {
    console.log('[Socket.IO] Logs atualizados:', data.logs.length, 'registros');
    updateLogsUI(data.logs);
});

socket.on('logs_error', function(data) {
    console.error('[Socket.IO] Erro:', data.error);
    showLogsError(data.error);
});

socket.on('logs_live_updates_started', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingLogUpdates = true;
});

socket.on('logs_live_updates_stopped', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingLogUpdates = false;
});

// =========================================================
// FUNÇÕES DE REQUISIÇÃO
// =========================================================

/**
 * Requisita uma atualização de logs imediata
 */
function requestLogsUpdate() {
    socket.emit('request_logs_update');
}

/**
 * Inicia atualizações periódicas de logs em tempo real
 */
function startLogsLiveUpdates() {
    const filters = {
        search_query: document.getElementById('search')?.value || '',
        user_name_filter: document.getElementById('user_name_filter')?.value || '',
        user_id_filter: document.getElementById('user_id_filter')?.value || '',
        start_date: document.getElementById('start_date')?.value || '',
        end_date: document.getElementById('end_date')?.value || ''
    };
    
    socket.emit('start_logs_live_updates', filters);
}

/**
 * Para atualizações periódicas de logs
 */
function stopLogsLiveUpdates() {
    socket.emit('stop_logs_live_updates');
}

// =========================================================
// ATUALIZAR UI DA PÁGINA DE LOGS
// =========================================================

/**
 * Atualiza a tabela de logs com novos dados
 */
function updateLogsUI(logs) {
    const tbody = document.querySelector('.table tbody');
    if (!tbody) return;

    // Se não houver logs, mostra mensagem
    if (!logs || logs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted py-4">
                    Nenhum log encontrado
                </td>
            </tr>
        `;
        return;
    }

    // Reconstrói a tabela com os novos dados
    tbody.innerHTML = logs.map((log, index) => {
        const actionBadgeClass = getActionBadgeClass(log.action);
        const [dateStr, timeStr] = log.timestamp.split(' ');
        
        // Trunca detalhes se for muito longo
        const detailsShort = log.details.length > 50 
            ? log.details.substring(0, 50) + '...' 
            : log.details;
        const hasMoreDetails = log.details.length > 50;

        return `
            <tr class="log-row" data-log-id="${log.id}">
                <td>${log.id}</td>
                <td>
                    <span class="fw-semibold">${escapeHtml(log.user_name)}</span>
                    <small class="text-muted d-block">ID: ${log.user_id || 'N/A'}</small>
                </td>
                <td>
                    <span class="badge ${actionBadgeClass}">
                        ${escapeHtml(log.action)}
                    </span>
                </td>
                <td>
                    <span class="d-block">${dateStr}</span>
                    <small class="text-muted">${timeStr}</small>
                </td>
                <td class="log-details">
                    <div class="details-content">
                        ${escapeHtml(log.details)}
                    </div>
                    ${hasMoreDetails ? '<button class="btn btn-sm btn-link p-0 toggle-details" data-bs-toggle="tooltip" title="Mostrar mais"><i class="bi bi-chevron-down"></i></button>' : ''}
                </td>
            </tr>
        `;
    }).join('');

    // Anima as novas linhas
    animateNewLogRows();
    
    // Atualiza o contador de logs
    updateLogsCounter(logs.length);
}

/**
 * Retorna a classe CSS para o badge de ação
 */
function getActionBadgeClass(action) {
    const classes = {
        'login': 'bg-success',
        'delete': 'bg-danger',
        'update': 'bg-warning text-dark',
        'upload': 'bg-primary',
        'download': 'bg-info'
    };
    return classes[action] || 'bg-secondary';
}

/**
 * Anima as linhas adicionadas
 */
function animateNewLogRows() {
    const rows = document.querySelectorAll('.log-row');
    rows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.animation = `fadeIn 0.3s ease-in forwards`;
        row.style.animationDelay = `${index * 0.05}s`;
    });
}

/**
 * Atualiza o contador de logs
 */
function updateLogsCounter(count) {
    const counter = document.querySelector('.logs-counter');
    if (counter) {
        counter.innerHTML = `
            <i class="bi bi-info-circle"></i>
            Mostrando ${count} registros (atualizado em tempo real)
        `;
    }
}

/**
 * Atualiza o timestamp da última atualização
 */

/**
 * Mostra mensagem de erro
 */
function showLogsError(error) {
    console.error('Erro de logs:', error);
    const errorContainer = document.getElementById('logs-error-container');
    if (errorContainer) {
        errorContainer.innerHTML = `<div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(error)}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
    } else {
        // Se não existir container, cria um no topo da tabela
        const table = document.querySelector('.table-responsive');
        if (table) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show mb-3';
            alert.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${escapeHtml(error)}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
            table.parentElement.insertBefore(alert, table);
        }
    }
}

/**
 * Escapa caracteres HTML para segurança
 */
function escapeHtml(text) {
    if (!text) return '';
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
        startLogsLiveUpdates();
    }, 1000);
});

// Para atualizações quando sair da página
window.addEventListener('beforeunload', function() {
    stopLogsLiveUpdates();
});

// Reinicia atualizações quando filtros são aplicados
const filterForm = document.querySelector('form[action*="view_logs"]');
if (filterForm) {
    filterForm.addEventListener('submit', function(e) {
        // Deixa o formulário fazer o submit, mas quando voltar, reinicia Socket.IO
        setTimeout(() => {
            stopLogsLiveUpdates();
            setTimeout(() => {
                startLogsLiveUpdates();
            }, 500);
        }, 100);
    });
}

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
    
    #last-update-logs.updated {
    }
    
`;
document.head.appendChild(style);
