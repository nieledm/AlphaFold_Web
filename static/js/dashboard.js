document.addEventListener('DOMContentLoaded', function() {
    // Recupera os dados do sessionStorage
    const jsonData = sessionStorage.getItem('alphafoldJsonData');
    
    if (jsonData) {
        // Cria um Blob com os dados
        const blob = new Blob([jsonData], { type: 'application/json' });
        const file = new File([blob], 'alphafold_data.json', { type: 'application/json' });
        
        // Cria um DataTransfer para simular o upload do arquivo
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        
        // Atribui os arquivos ao input
        const fileInput = document.querySelector('input[type="file"]');
        fileInput.files = dataTransfer.files;
        
        // Opcional: envia o formulário automaticamente
        document.querySelector('form').submit();
        
        // Limpa o sessionStorage
        sessionStorage.removeItem('alphafoldJsonData');
    }
});