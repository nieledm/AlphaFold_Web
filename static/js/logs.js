function confirmClearLogs(form) {
    const daysOld = form.days_old.value;
    let message = 'Tem certeza que deseja limpar os logs?';
    
    if (daysOld === 'dates') {
        const startDate = form.clear_start_date.value;
        const endDate = form.clear_end_date.value;
        if (!startDate || !endDate) {
            alert('Por favor, selecione o intervalo de datas para limpeza.');
            return false;
        }
        message += `\n\nPeríodo selecionado: ${startDate} até ${endDate}`;
    } else if (daysOld === 'all') {
        message += '\n\nTodos os logs serão removidos.';
    } else if (daysOld) {
        message += `\n\nLogs com mais de ${daysOld} dias serão removidos.`;
    } else {
        alert('Por favor, selecione uma opção de limpeza.');
        return false;
    }
    
    message += '\n\nEsta ação é irreversível.';
    return confirm(message);
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.toggle-details').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const detailsContent = this.closest('.log-details').querySelector('.details-content');
            const isExpanded = detailsContent.classList.toggle('expanded');
            
            // Atualizar ícone
            this.querySelector('i').className = isExpanded ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
            
            // Atualizar tooltip
            if (this._tooltip) {
                this._tooltip._config.title = isExpanded ? 'Mostrar menos' : 'Mostrar mais';
                this._tooltip.update();
            }
        });
    });
    
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', function() {
            e.preventDefault();
            e.stopPropagation();
            
            const sortField = this.dataset.sort;
            const currentUrl = new URL(window.location.href);
            
            if (currentUrl.searchParams.get('sort') === sortField) {
                currentUrl.searchParams.set('order', 
                    currentUrl.searchParams.get('order') === 'asc' ? 'desc' : 'asc');
            } else {
                currentUrl.searchParams.set('sort', sortField);
                currentUrl.searchParams.set('order', 'asc');
            }
            
            window.location.href = currentUrl.toString();
        });
    });
});document.querySelectorAll('.sortable').length