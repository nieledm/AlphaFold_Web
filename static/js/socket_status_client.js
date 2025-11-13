/**
 * Cliente Socket.IO para atualização em tempo real do status
 * Inclua este arquivo na página que precisa de atualizações ao vivo
 */

// Conecta ao servidor Socket.IO
const socket = io();

// Flag para controlar se estamos recebendo atualizações
let isReceivingUpdates = false;

// =========================================================
// EVENTOS DE CONEXÃO
// =========================================================

socket.on('connect', function() {
    console.log('[Socket.IO] Conectado ao servidor');
    // Solicita uma atualização inicial
    requestStatusUpdate();
});

socket.on('connect_response', function(data) {
    console.log('[Socket.IO]', data.data);
});

socket.on('disconnect', function() {
    console.log('[Socket.IO] Desconectado do servidor');
});

// =========================================================
// RECEBER ATUALIZAÇÕES DE STATUS
// =========================================================

socket.on('status_update', function(data) {
    console.log('[Socket.IO] Status atualizado:', data);
    updateStatusUI(data);
});

socket.on('status_error', function(data) {
    console.error('[Socket.IO] Erro:', data.error);
    showError(data.error);
});

socket.on('live_updates_started', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingUpdates = true;
});

socket.on('live_updates_stopped', function(data) {
    console.log('[Socket.IO]', data.message);
    isReceivingUpdates = false;
});

// =========================================================
// FUNÇÕES DE REQUISIÇÃO
// =========================================================

/**
 * Requisita uma atualização de status imediata
 */
function requestStatusUpdate() {
    socket.emit('request_status_update');
}

/**
 * Inicia atualizações periódicas em tempo real
 */
function startLiveUpdates() {
    socket.emit('start_live_updates');
}

/**
 * Para atualizações periódicas
 */
function stopLiveUpdates() {
    socket.emit('stop_live_updates');
}

// =========================================================
// ATUALIZAR UI
// =========================================================

/**
 * Atualiza os elementos da página com os novos dados
 */
function updateStatusUI(data) {
    if (data.error) {
        showError(data.error);
        return;
    }

    const status = data.status;
    if (!status) return;

    // Atualizar CPU
    if (status.cpu) {
        updateCPUUI(status.cpu);
    }

    // Atualizar Memória
    if (status.mem) {
        updateMemoryUI(status.mem);
    }

    // Atualizar GPU
    if (status.gpu && status.gpu.length > 0) {
        updateGPUUI(status.gpu);
    }

    // Atualizar Armazenamento
    if (status.disk) {
        updateDiskUI(status.disk);
    }

    // Atualizar contagem de jobs
    if (data.running_count !== undefined || data.pending_count !== undefined) {
        updateJobCountsUI(data.running_count, data.pending_count);
    }

}

/**
 * Atualiza a seção de CPU
 */
function updateCPUUI(cpu) {
    const cpuProgress = document.getElementById('cpu-progress');
    if (cpuProgress) {
        cpuProgress.style.width = cpu.usage + '%';
        cpuProgress.getAttribute('aria-valuenow') && cpuProgress.setAttribute('aria-valuenow', cpu.usage);
        cpuProgress.textContent = cpu.usage + '%';
    }
}

/**
 * Atualiza a seção de Memória
 */
function updateMemoryUI(mem) {
    const memProgress = document.getElementById('mem-progress');
    if (memProgress) {
        memProgress.style.width = mem.percent_used + '%';
        memProgress.getAttribute('aria-valuenow') && memProgress.setAttribute('aria-valuenow', mem.percent_used);
        memProgress.textContent = mem.percent_used + '%';
    }

    // Atualiza badges
    const memBadges = document.querySelectorAll('#mem-progress').parentElement?.querySelectorAll('.badge');
    if (memBadges && memBadges.length >= 3) {
        memBadges[0].textContent = mem.total;
        memBadges[1].textContent = mem.used;
        memBadges[2].textContent = mem.free;
    }
}

/**
 * Atualiza a seção de GPU
 */
function updateGPUUI(gpus) {
    gpus.forEach((gpu, index) => {
        const gpuProgress = document.getElementById(`gpu-progress-${index + 1}`);
        if (gpuProgress) {
            gpuProgress.style.width = gpu.utilization_memory + '%';
            gpuProgress.setAttribute('aria-valuenow', gpu.utilization_memory);
            gpuProgress.textContent = gpu.utilization_memory + '%';
        }
    });
}

/**
 * Atualiza a seção de Armazenamento
 */
function updateDiskUI(disk) {
    // Atualize conforme a estrutura do seu HTML
    console.log('Atualizar disco:', disk);
}

/**
 * Atualiza contagem de jobs
 */
function updateJobCountsUI(running, pending) {
    const runningElement = document.getElementById('running-count');
    const pendingElement = document.getElementById('pending-count');

    if (runningElement) runningElement.textContent = running || 0;
    if (pendingElement) pendingElement.textContent = pending || 0;
}

/**
 * Atualiza o timestamp da última atualização
 */

/**
 * Mostra mensagem de erro
 */
function showError(error) {
    console.error('Erro de status:', error);
    // Você pode adicionar uma notificação visual aqui
    const errorContainer = document.getElementById('status-error-container');
    if (errorContainer) {
        errorContainer.innerHTML = `<div class="alert alert-danger alert-dismissible fade show" role="alert">
            ${error}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>`;
    }
}

// =========================================================
// INICIALIZAÇÃO
// =========================================================

// Inicia atualizações ao vivo quando a página carrega
document.addEventListener('DOMContentLoaded', function() {
    // Aguarda um pouco para garantir que está conectado
    setTimeout(() => {
        startLiveUpdates();
    }, 1000);
});

// Para atualizações quando sair da página
window.addEventListener('beforeunload', function() {
    stopLiveUpdates();
});
