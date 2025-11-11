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

    // Controle do file input
    const fileInput = document.getElementById('file-input');
    const fileDisplay = document.getElementById('filename-display'); // Agora é o input
    const uploadBtn = document.getElementById('upload-btn');

    if (fileInput && fileDisplay) {
        // Event listener para change (seleção normal)
        fileInput.addEventListener('change', function(e) {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                fileDisplay.value = fileName;
                fileDisplay.classList.add('has-file');
                uploadBtn.disabled = false;
            } else {
                fileDisplay.value = '';
                fileDisplay.placeholder = 'Nenhum arquivo selecionado';
                fileDisplay.classList.remove('has-file');
                uploadBtn.disabled = true;
            }
        });

        // Drag & drop functionality
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

    // Feedback visual durante o upload
    document.querySelector('form').addEventListener('submit', function(e) {
        if (uploadBtn && !uploadBtn.disabled) {
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Enviando...';
            uploadBtn.disabled = true;
        }
    });
});