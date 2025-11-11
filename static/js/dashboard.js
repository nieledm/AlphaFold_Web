document.addEventListener('DOMContentLoaded', function() {
    // Feedback visual para os botões
    const buttons = document.querySelectorAll('.btn-action');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-1px)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Auto-dismiss alerts após 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Melhorar a experiência do upload
    const fileInput = document.getElementById('file-input');
    const fileDisplay = document.getElementById('file-display');

    if (fileInput && fileDisplay) {
        fileInput.addEventListener('dragenter', function(e) {
            e.preventDefault();
            fileDisplay.style.borderColor = '#07b4b1';
            fileDisplay.style.background = '#f0fffd';
        });

        fileInput.addEventListener('dragleave', function(e) {
            e.preventDefault();
            if (!fileDisplay.classList.contains('has-file')) {
                fileDisplay.style.borderColor = '#dee2e6';
                fileDisplay.style.background = '#f8f9fa';
            }
        });

        fileInput.addEventListener('drop', function(e) {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });

        fileInput.addEventListener('dragover', function(e) {
            e.preventDefault();
        });
    }
});