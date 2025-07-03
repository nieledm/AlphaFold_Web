// Função principal que será executada quando o DOM estiver carregado
function initStatusPage() {
    // Atualizar barra de progresso da memória
    updateProgressBar(
        'mem-progress', 
        window.memUsage || 0, 
        'bg-warning'
    );
    
    // Atualizar barra de progresso da CPU
    updateProgressBar(
        'cpu-progress', 
        window.cpuUsage || 0, 
        'bg-success'
    );
    
    // Atualizar GPUs dinamicamente
    if (window.gpuData) {
        window.gpuData.forEach((gpu, index) => {
            updateProgressBar(
                `gpu-progress-${index + 1}`, 
                parseFloat(gpu.utilization || 0), 
                gpu.utilization > 80 ? 'bg-danger' : 'bg-primary'
            );
        });
    }
}

// Função auxiliar para atualizar barras de progresso
function updateProgressBar(elementId, value, colorClass) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Atualizar estilo e atributos
    element.style.width = `${value}%`;
    element.setAttribute('aria-valuenow', value);
    element.textContent = `${value}%`;
    
    // Remover classes de cor existentes e adicionar a nova
    element.classList.remove('bg-danger', 'bg-warning', 'bg-success', 'bg-primary');
    element.classList.add(colorClass);
}

// Esperar o DOM carregar
document.addEventListener('DOMContentLoaded', initStatusPage);