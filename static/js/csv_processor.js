/****************************
 * FUNÇÕES PARA UPLOAD DE CSV
 ****************************/

// Variável global para armazenar dados do CSV
window.csvData = null;

// Inicializa o sistema de upload de CSV
function initCSVUpload() {
  const csvUploadInput = document.getElementById('csvUpload');
  if (csvUploadInput) {
    csvUploadInput.addEventListener('change', handleCSVUpload);
  }
}

// Processa o upload do arquivo CSV
function handleCSVUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  // Verifica se é um arquivo CSV
  if (!file.name.toLowerCase().endsWith('.csv')) {
    alert('Por favor, selecione um arquivo CSV.');
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const csvContent = e.target.result;
    processCSVContent(csvContent, file.name);
  };
  reader.readAsText(file);
}

// Processa o conteúdo do CSV e gera os JSONs
function processCSVContent(csvContent, filename) {
  try {
    const lines = csvContent.split('\n').filter(line => line.trim());
    
    if (lines.length < 3) {
      alert('O arquivo CSV deve conter pelo menos os headers e algumas linhas de dados.');
      return;
    }

    // Processa as listas separadas
    const proteins = [];
    const smilesList = [];
    let currentSection = null;
    let smilesSectionHeaders = null; // Para capturar 'smiles, nome'

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // 1. Detecta o INÍCIO da seção SMILES e captura os headers
      if (currentSection !== 'proteins' && (line.toLowerCase().startsWith('smiles') || line.toLowerCase().startsWith('smile'))) {
        currentSection = 'smiles';
        // Captura e normaliza os headers (ex: ['smiles', 'nome'])
        smilesSectionHeaders = line.toLowerCase().split(',').map(h => h.trim()); 
        continue;
      } else if (line.toLowerCase() === 'sequencia' || line.toLowerCase() === 'sequence' || 
      line.toLowerCase()=== `sequencias` || line.toLowerCase() === 'sequences' ||
      line.toLowerCase() === 'protein' || line.toLowerCase() === 'proteina' ||
      line.toLowerCase() === 'proteins' || line.toLowerCase() === 'proteinas') {
        currentSection = 'proteins';
        continue;
      }
      
      // 2. Processa as linhas de dados
      if (currentSection === 'smiles' && line) {
        // Assume que os dados estão separados por vírgula (CSV)
        const parts = line.split(',').map(p => p.trim());
        
        // Verifica se há pelo menos duas colunas e se os headers foram definidos
        if (smilesSectionHeaders && parts.length >= 2) {
            // Mapeia os índices baseados no header. Assumindo 'smiles' e 'nome'
            const smilesIndex = smilesSectionHeaders.findIndex(h => h === 'smiles' || h === 'smile');
            const nameIndex = smilesSectionHeaders.findIndex(h => h === 'nome' || h === 'name');
            
            // Cria o objeto padronizado
            const smile = parts[smilesIndex !== -1 ? smilesIndex : 0];
            const name = parts[nameIndex !== -1 ? nameIndex : 1];
            
            smilesList.push({ smiles: smile, name: name });
        } else if (parts.length === 1) {
            // Caso tenha apenas a coluna SMILES, usa um nome padrão
            smilesList.push({ smiles: parts[0], name: `S${smilesList.length + 1}` });
        }
      } else if (currentSection === 'proteins' && line) {
        proteins.push(line);
      }      
    }

    // Remove duplicatas
    const uniqueSmilesMap = new Map();
    smilesList.forEach(item => {
        // Usa o SMILES como chave. Se já existe, mantém o primeiro nome encontrado
        if (!uniqueSmilesMap.has(item.smiles)) {
            uniqueSmilesMap.set(item.smiles, item);
        }
    });
    
    const uniqueProteins = [...new Set(proteins)];
    const uniqueSmiles = [...uniqueSmilesMap.values()]; // Lista final de objetos padronizados

    if (uniqueSmiles.length === 0) {
      alert('Nenhum SMILES válido encontrado no CSV.');
      return;
    }

    // Gera todas as combinações
    const combinations = generateCombinations(uniqueProteins, uniqueSmiles);

    // Mostra preview e opções
    showCSVPreview(combinations, uniqueProteins, uniqueSmiles, filename);
    
  } catch (error) {
    console.error('Erro ao processar CSV:', error);
    alert('Erro ao processar o arquivo CSV. Verifique o formato.');
  }
}

// Verifica se uma linha é um header
function isHeaderLine(line) {
  const headers = ['nome', 'name', 'nomes', 'names', 
    'smiles', 'smile', 
    'sequencia', 'sequence', 'sequencias', 'sequences', 
    'protein', 'proteina', 'proteinas', 'proteins'];
  return headers.includes(line.toLowerCase());
}

// Gera combinações entre proteínas e SMILES (produto cartesiano)
function generateCombinations(proteins, smilesList) {
  const combinations = [];
  
  for (let i = 0; i < proteins.length; i++) {
    for (let j = 0; j < smilesList.length; j++) {
      combinations.push({
        protein: proteins[i],
        proteinIndex: i + 1,
        smiles: smilesList[j].smiles,
        ligandName: smilesList[j].name,
        combination: `P${i + 1}-S${j + 1}`
      });
    }
  }
  
  return combinations;
}

// Mostra preview dos dados e opções
function showCSVPreview(combinations, proteins, smilesList, filename) {
  const totalCombinations = combinations.length;
  
  const previewContent = `
    <div class="alert alert-info">
      <h5><i class="fas fa-table me-2"></i>Preview das Combinações</h5>
      <p>
        <strong>${proteins.length}</strong> proteínas × <strong>${smilesList.length}</strong> SMILES = 
        <strong>${totalCombinations}</strong> combinações totais
      </p>
      
      <div class="row">
        <div class="col-md-6">
          <h6>Lista de Proteínas (${proteins.length}):</h6>
          <div style="max-height: 150px; overflow-y: auto;" class="small">
            ${proteins.map((p, i) => `
              <div class="mb-1">
                <strong>P${i + 1}:</strong> 
                <span title="${p}">${p.substring(0, 40)}${p.length > 40 ? '...' : ''}</span>
              </div>
            `).join('')}
          </div>
        </div>
        <div class="col-md-6">
          <h6>Lista de SMILES (${smilesList.length}):</h6>
          <div style="max-height: 150px; overflow-y: auto;" class="small">
            ${smilesList.map((s, i) => `
              <div class="mb-1">
                <strong>S${i + 1}:</strong> 
                <span title="${s}">${s.substring(0, 40)}${s.length > 40 ? '...' : ''}</span>
              </div>
            `).join('')}
          </div>
        </div>
      </div>
      
      <div class="mt-3">
        <h6>Primeiras Combinações (${totalCombinations} no total):</h6>
        <div class="table-responsive" style="max-height: 200px; overflow-y: auto;">
          <table class="table table-sm table-striped">
            <thead>
              <tr>
                <th>#</th>
                <th>Combinação</th>
                <th>Proteína</th>
                <th>SMILES</th>
              </tr>
            </thead>
            <tbody>
              ${combinations.slice(0, 10).map((item, index) => `
                <tr>
                  <td>${index + 1}</td>
                  <td><small class="text-muted">${item.combination}</small></td>
                  <td title="${item.protein}">P${proteins.indexOf(item.protein) + 1}</td>
                  <td title="${item.smiles}">S${smilesList.indexOf(item.smiles) + 1}</td>
                </tr>
              `).join('')}
              ${combinations.length > 10 ? `
                <tr>
                  <td colspan="4" class="text-center text-muted">
                    ... e mais ${combinations.length - 10} combinações
                  </td>
                </tr>
              ` : ''}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <div class="mb-3">
      <label for="baseFilename" class="form-label">Nome base para os arquivos:</label>
      <input type="text" class="form-control" id="baseFilename" value="${filename.replace('.csv', '')}">
    </div>
    
    <div class="alert alert-warning">
      <small>
        <i class="fas fa-exclamation-triangle me-2"></i>
        <strong>Atenção:</strong> Serão gerados <strong>${totalCombinations}</strong> arquivos JSON, 
        um para cada combinação proteína-SMILES.
      </small>
    </div>
    
    <div class="d-grid gap-2">
      <button class="btn btn-success" onclick="processAllCSVData('download')">
        <i class="fas fa-download me-2"></i>Baixar todos os JSONs (${totalCombinations})
      </button>
      <button class="btn btn-primary" onclick="processAllCSVData('process')">
        <i class="fas fa-play me-2"></i>Processar todos no servidor (${totalCombinations})
      </button>
    </div>
  `;
  
  // Cria ou atualiza o modal de preview
  let previewModal = document.getElementById('csvPreviewModal');
  if (!previewModal) {
    previewModal = document.createElement('div');
    previewModal.className = 'modal fade';
    previewModal.id = 'csvPreviewModal';
    previewModal.innerHTML = `
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Combinações do CSV - Produto Cartesiano</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" id="csvPreviewContent">
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(previewModal);
  }
  
  document.getElementById('csvPreviewContent').innerHTML = previewContent;
  
  // Armazena os dados globalmente para uso posterior
  window.csvData = combinations;
  
  // Mostra o modal
  const modal = new bootstrap.Modal(previewModal);
  modal.show();
}


// Processa todos os dados do CSV
function processAllCSVData(action) {
  const combinations = window.csvData;
  if (!combinations || combinations.length === 0) return;
  
  const baseFilename = document.getElementById('baseFilename').value.trim() || 'batch';
  
  // Limita o número de processamentos para evitar sobrecarga
  if (combinations.length > 50) {
    if (!confirm(`Você está prestes a processar ${combinations.length} arquivos. Isso pode levar algum tempo. Continuar?`)) {
      return;
    }
  }
  
  let processed = 0;
  let errors = 0;
  
  // Processa cada combinação
  combinations.forEach((item, index) => {
    try {
      const jsonData = createJSONFromCSVItem(item, index + 1);
      const proteinPrefix = `${baseFilename}_protein${item.proteinIndex}`;
      const itemFilename = `${item.ligandName}_${item.proteinIndex}`;
      
      switch (action) {
        case 'download':
          downloadJSON(jsonData, itemFilename);
          processed++;
          break;
        case 'process':
          // Para processamento, envia um por um com delay
          setTimeout(() => {
            sendToServer(jsonData, itemFilename)
              .then(() => {
                processed++;
                updateProgress(processed, combinations.length);
                
                // Quando todos forem processados, redireciona
                if (processed + errors === combinations.length) {
                  setTimeout(() => {
                    if (errors === 0) {
                      window.location.href = '/dashboard';
                    } else {
                      alert(`Processamento concluído com ${errors} erro(s).`);
                    }
                  }, 1000);
                }
              })
              .catch(() => {
                errors++;
                updateProgress(processed, combinations.length);
              });
          }, index * 500); // Delay de 0.5 segundo entre requisições
          break;
      }
    } catch (error) {
      console.error(`Erro na combinação ${item.combination}:`, error);
      errors++;
    }
  });
  
  if (action === 'download') {
    alert(`Download de ${processed} arquivos JSON concluído!`);
  } else {
    showProgressModal(combinations.length);
  }
}

// Cria JSON para uma combinação do CSV
function createJSONFromCSVItem(item, index) {
  // Valida a sequência da proteína
  const proteinValidation = validateSequence('protein', item.protein);
  if (proteinValidation.error) {
    throw new Error(`Proteína inválida na combinação ${item.combination}: ${proteinValidation.error}`);
  }
  
  // Gera IDs únicos - usa funções do builder_json_form.js
  const proteinId = generateEntityIDs(0, 1); // Proteína como A
  const ligandId = generateEntityIDs(1, 1); // Ligante como B
  
  // Cria a estrutura JSON
  const jsonData = {
    name: `AlphaFold Prediction ${item.combination}`,
    modelSeeds: [42],
    sequences: [
      // Proteína
      {
        protein: {
          id: proteinId,
          sequence: item.protein
        }
      },
      // Ligante
      {
        ligand: {
          id: ligandId,
          smiles: item.smiles
        }
      }
    ],
    dialect: "alphafold3",
    version: 2
  };
  
  return jsonData;
}

// Envia JSON para o servidor
function sendToServer(jsonData, filename) {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('json_data', JSON.stringify(jsonData, null, 2));
    formData.append('filename', filename);
    formData.append('batch_upload', 'true');
    
    fetch('/upload', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (response.ok) {
        resolve();
      } else {
        reject(new Error('Erro no servidor'));
      }
    })
    .catch(error => {
      reject(error);
    });
  });
}

// Mostra modal de progresso
function showProgressModal(total) {
  let progressModal = document.getElementById('progressModal');
  if (!progressModal) {
    progressModal = document.createElement('div');
    progressModal.className = 'modal fade';
    progressModal.id = 'progressModal';
    progressModal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Processando Combinações...</h5>
          </div>
          <div class="modal-body">
            <div class="progress mb-3">
              <div class="progress-bar progress-bar-striped progress-bar-animated" 
                   id="progressBar" style="width: 0%"></div>
            </div>
            <p class="text-center" id="progressText">0/${total} combinações processadas</p>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(progressModal);
  }
  
  const modal = new bootstrap.Modal(progressModal, { keyboard: false });
  modal.show();
}

// Atualiza a barra de progresso
function updateProgress(current, total) {
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  
  if (progressBar && progressText) {
    const percent = (current / total) * 100;
    progressBar.style.width = `${percent}%`;
    progressText.textContent = `${current}/${total} combinações processadas`;
  }
}

// Mostra modal com instruções do CSV
function showCSVInstructions() {
  const instructionsContent = `
    <div class="alert alert-info">
      <h5><i class="fas fa-info-circle me-2"></i>Instruções do Formato CSV</h5>
      <p>Seu arquivo CSV deve conter **LISTAS SEPARADAS** de proteínas e ligantes.</p>
      
      <div class="mb-3">
        <strong>Formato esperado:</strong>
        <pre class="bg-dark text-light p-3 rounded small">nome, smiles
Aspirina, CC(=O)OC1=CC=CC=C1C(=O)O
Ligante_Teste, CC(C)(C)OC(=O)N1CCC(Nc2nc3c(cc2C(F)(F)F)ccn3C(=O)c2cccc(F)c2)CC1
sequencia
MVQDTGKDTNLKGTAEANESVVYCDVFMQAALKEATCALEEGEVPVGCVLVKADSSTA
MKTAYIAKQRQISFVKSHFSRQDILDLKEQKMSMADKQSDTEEIIFDSGVDKTRSIAKELRKVLD</pre>
      </div>
      
      <div class="mb-3">
        <strong>Como funciona:</strong>
        <ul class="small">
          <li>**Cada proteína é combinada com cada SMILES** (Produto Cartesiano).</li>
          <li>**O campo 'nome' será usado na nomenclatura dos arquivos JSON** (ex: Aspirina_protein1.json).</li>
          <li>**Exemplo:** 2 proteínas × 2 ligantes = 4 combinações totais.</li>
          <li>Valores duplicados são automaticamente removidos.</li>
        </ul>
      </div>
      
      <div class="mb-2">
        <strong>Headers aceitos:</strong>
        <ul class="small">
          <li>Para proteínas: <code>sequencia</code>, <code>sequence</code>, <code>protein</code>, <code>proteina</code></li>
          <li>Para ligantes: **<code>nome</code>**, **<code>name</code>**, <code>smiles</code>, <code>smile</code> (em qualquer ordem, separados por vírgula).</li>
        </ul>
      </div>
    </div>
    
    <div class="text-center">
      <button class="btn btn-primary" onclick="startCSVUpload()">
        <i class="fas fa-upload me-2"></i>Fazer Upload do CSV
      </button>
    </div>
  `;
  
  // Cria ou atualiza o modal de instruções
  let instructionsModal = document.getElementById('csvInstructionsModal');
  if (!instructionsModal) {
    instructionsModal = document.createElement('div');
    instructionsModal.className = 'modal fade';
    instructionsModal.id = 'csvInstructionsModal';
    instructionsModal.innerHTML = `
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="fas fa-file-csv me-2"></i>Upload em Lote via CSV</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body" id="csvInstructionsContent">
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(instructionsModal);
  }
  
  modal.show();
}

// Inicia o upload após ver as instruções
function startCSVUpload() {
  // Fecha o modal de instruções
  const instructionsModal = document.getElementById('csvInstructionsModal');
  if (instructionsModal) {
    const modal = bootstrap.Modal.getInstance(instructionsModal);
    modal.hide();
  }
  
  // Cria input de arquivo dinamicamente e clica nele
  let fileInput = document.getElementById('csvUpload');
  if (!fileInput) {
    fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.id = 'csvUpload';
    fileInput.accept = '.csv';
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);
    fileInput.addEventListener('change', handleCSVUpload);
  }
  
  fileInput.click();
}

// Adiciona o botão de upload CSV na interface
function addCSVUploadButton() {
  const cardsContainer = document.getElementById('cards-container');
  if (!cardsContainer) return;
  
  // Adiciona um botão simples antes do container de cards
  const uploadSection = document.createElement('div');
  uploadSection.className = 'mb-4 text-center';
  uploadSection.innerHTML = `
    <button type="button" class="btn btn-outline-primary" onclick="showCSVInstructions()">
      <i class="fas fa-file-csv me-2"></i>Upload em Lote via CSV
      <i class="fas fa-info-circle ms-2 small" 
         data-bs-toggle="tooltip" 
         data-bs-placement="top" 
         title="Clique para ver instruções do formato CSV"></i>
    </button>
    <p class="text-muted mt-2 small">Processe múltiplas combinações proteína-SMILES (produto cartesiano)</p>
  `;
  
  cardsContainer.parentNode.insertBefore(uploadSection, cardsContainer);
  
  // Inicializa tooltips do Bootstrap
  const tooltipTriggerList = [].slice.call(uploadSection.querySelectorAll('[data-bs-toggle="tooltip"]'));
  const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
  addCSVUploadButton();
});