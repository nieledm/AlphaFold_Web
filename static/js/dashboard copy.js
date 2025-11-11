document.addEventListener('DOMContentLoaded', function() {
    // Recupera os dados do sessionStorage
    const jsonData = sessionStorage.getItem('alphafoldJsonData');
    
    const fileInput = document.querySelector('input[type="file"]');

    if (!fileInput) {
        console.warn('Campo de arquivo não encontrado.');
        return;
    }
    
    if (jsonData) {
        const now = new Date();
        const timestamp = now.toISOString()
            .replace(/[:.]/g, '-') 
            .replace('T', '_')
            .slice(0, 19);
        
        const fileName = `alphafold_data_${timestamp}.json`;

        // Cria um Blob com os dados
        const blob = new Blob([jsonData], { type: 'application/json' });
        const file = new File([blob], fileName, { type: 'application/json' });
        
        // Cria um DataTransfer para simular o upload do arquivo
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        // Atribui os arquivos ao input
        const fileInput = document.querySelector('input[type="file"]');
        fileInput.files = dataTransfer.files;

        // Preenche também o campo de nome manualmente
        const filenameInput = document.getElementById('filename');
        if (filenameInput) {
            filenameInput.value = file.name;
        }
        
        // envia o formulário automaticamente
        // document.querySelector('form').submit();
        
        // Limpa o sessionStorage
        sessionStorage.removeItem('alphafoldJsonData');
    }

    // Atualiza o nome do arquivo ao selecionar manualmente
    fileInput.addEventListener('change', function () {
        const fileName = this.files[0]?.name || '';
        const filenameInput = document.getElementById('filename');
        if (filenameInput) {
            filenameInput.value = fileName;
        }
    });
});

// Preenche o campo Nome do Arquivo automaticamente
document.querySelector('input[type="file"]').addEventListener('change', function () {
    const fileName = this.files[0]?.name || '';
    document.getElementById('filename').value = fileName;
});