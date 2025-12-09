/****************************
 * CONSTANTES E CONFIGURAÇÕES
 ****************************/
const sequenceHelp = document.getElementById('sequenceHelp');
const entityType = document.getElementById('entityType');
const sequenceField = document.getElementById('sequence');

// Variáveis globais para controlar o modal de filename
let filenameModal = null;
let pendingAction = null; // 'download', 'process', ou 'both'
let pendingJsonData = null;

const examples = {
    protein: {
        seq: "MVQDTGKDTNLKGTAEANESVVYCDVFMQAALKEATCALEEGEVPVGCVLVKADSSTAAQAQAGDDLALQKLIVARGRNATNRKGHGLAHAEFVAVEELLRQATAGTSENIGGGGNSGAVSQDLADYVLYVVVEPCIMCAAMLLYNRVRKVYFGCTNPRFGGNGTVLSVHNSYKGCSGEDAALIGYESCGGYRAEEAVVLLQQFYRRENTNAPLGKRKRKD",
        warn: "A sequência deve conter apenas letras. Caracteres inválidos: B, J, O, U, X, Z."
    },
    dna: {
        seq: "ATGCGTACGTAGCTAGCTAGCTAGCTAGCTAGCTA",
        warn: "A sequência deve conter apenas A, T, C e G."
    },
    rna: {
        seq: "AUGCGUACGUAGCUAGCUAGCUAGCUAGCUAGCUA",
        warn: "A sequência deve conter apenas A, U, C e G."
    },
    ligand: {
        seq: "CC(=O)OC1=CC=CC=C1C(=O)O", // ácido acetilsalicílico (aspirina)
        warn: "Insira o SMILES da molécula ligante (formato texto)."
    },
    ion: {
        seq: "Na+", 
        warn: "Insira o símbolo do íon, como Na+, K+, Mg2+, etc."
    }
};

let cardCounter = 1;

/******************************
 * FUNÇÕES DE MANIPULAÇÃO DE UI
 ******************************/
// Adiciona um novo card de entidade
function addNewCard() {
  cardCounter++;
  const newCard = document.createElement('div');
  newCard.className = 'form-card';
  newCard.id = `card-${cardCounter}`;
  
  newCard.innerHTML = `
    <button class="btn btn-sm remove-card-btn" onclick="removeCard('card-${cardCounter}')">
      <i class="fas fa-times"></i>
    </button>
    
    <div class="card-header">
      <h5 class="mb-0 mt=1">Entidade ${cardCounter}</h5>
    </div>

    <form class="entity-form">
      <!-- Container principal com os campos básicos -->
      <div class="mb-4">
        <div class="row g-3 align-items-stretch">
          <!-- Coluna da esquerda -->
          <div class="col-md-3 d-flex flex-column justify-content-between">
            <!-- Entidade -->
            <div>
              <label for="entityType-${cardCounter}" class="form-label mb-0">Entidade</label>
              <select class="form-select entity-type" id="entityType-${cardCounter}" name="entity_type" required>
                <option value="" selected disabled>Selecione</option>
                <option value="protein">Proteína</option>
                <option value="dna">DNA</option>
                <option value="rna">RNA</option>
                <option value="ligand">Ligante</option>
                <option value="ion">Íon</option>
              </select>
            </div>
      
            <!-- Número de cópias -->
            <div>
              <label for="copies-${cardCounter}" class="form-label mt-2 mb-0">Cópias</label>
              <input type="number" class="form-control copies" id="copies-${cardCounter}" name="copies" min="1" max="10" value="1" required>
            </div>
      
            <!-- Model Seeds -->
            <div>
              <label for="seeds-${cardCounter}" class="form-label mt-2 mb-0">Model Seeds</label>
              <input type="number" class="form-control seeds" id="seeds-${cardCounter}" name="seeds" min="1" max="10" value="1" required>
            </div>
          </div>
      
          <!-- Coluna da direita -->
          <div class="col-md-9 d-flex flex-column">
            <label for="sequence-${cardCounter}" class="form-label mb-0">Sequência</label>
            <div class="flex-grow-1 d-flex flex-column">
              <textarea class="form-control sequence flex-grow-1" id="sequence-${cardCounter}" name="sequence" required></textarea>
              <div class="sequence-help form-text text-danger mt-1" style="display: none;"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Botão de opções -->
      <div class="dropdown mb-4">
        <button class="btn btn-outline-primary dropdown-toggle" type="button" data-bs-toggle="dropdown">
          <i class="fas fa-cog me-2"></i> Opções Avançadas
        </button>
        <ul class="dropdown-menu">
          <li><a class="dropdown-item" href="#" onclick="addMSABlock(this); return false;"><i class="fas fa-layer-group me-2"></i>Adicionar MSA</a></li>
          <li><hr class="dropdown-divider"></li>
          <li><a class="dropdown-item" href="#" onclick="toggleSection(this, 'templates'); return false;"><i class="fas fa-copy me-2"></i>Adicionar Templates</a></li>
          <li><a class="dropdown-item" href="#" onclick="toggleSection(this, 'pairing'); return false;"><i class="fas fa-link me-2"></i>Adicionar Pairing</a></li>
          <li><a class="dropdown-item" href="#" onclick="toggleSection(this, 'modifications'); return false;"><i class="fas fa-atom me-2"></i>Adicionar Modificações</a></li>
          <li><a class="dropdown-item" href="#" onclick="toggleSection(this, 'coordinates'); return false;"><i class="fas fa-map-marker-alt me-2"></i>Adicionar Coordenadas</a></li>
          <li><a class="dropdown-item" href="#" onclick="toggleSection(this, 'masked'); return false;"><i class="fas fa-mask me-2"></i>Adicionar Regiões Mascaradas</a></li>
        </ul>
      </div>

      <!-- Blocos de MSA -->
      <div class="msa-blocks mb-3"></div>

      <!-- Seções opcionais -->
      <div class="optional-sections">
        <!-- Templates -->
        <div class="optional-section templates-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Templates (1 por linha):</label>
          <textarea class="form-control mt-2" name="templates" rows="3" placeholder="Ex: 1abc_A"></textarea>
        </div>

        <!-- Pairing -->
        <div class="optional-section pairing-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Pairing:</label>
          <input type="text" class="form-control mt-2" name="pairing" placeholder="Ex: symmetric">
        </div>

        <!-- Modificações -->
        <div class="optional-section modifications-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Modificações (JSON):</label>
          <textarea class="form-control mt-2" name="modifications" rows="4" placeholder='Ex: [{"position": 3, "type": "phosphorylation"}]'></textarea>
        </div>

        <!-- Coordenadas -->
        <div class="optional-section coordinates-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Coordenadas (JSON):</label>
          <textarea class="form-control mt-2" name="coordinates" rows="4" placeholder='Ex: {"residue": 25, "x": 1.0, "y": 2.0, "z": 3.0}'></textarea>
        </div>

        <!-- Regiões Mascaradas -->
        <div class="optional-section masked-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Regiões Mascaradas (JSON):</label>
          <textarea class="form-control mt-2" name="masked_regions" rows="4" placeholder='Ex: [{"start": 10, "end": 20}]'></textarea>
        </div>
      </div>
    </form>
  `;
  
  document.getElementById('cards-container').appendChild(newCard);
  
  // Inicializa os event listeners para o novo card
  initEntityTypeListener(newCard);
}

// Remove um card específico
function removeCard(cardId) {
  if (document.querySelectorAll('.form-card').length > 1) {
    const cardNumber = parseInt(cardId.split('-')[1]);
    
    // Se estivermos removendo o último card, decrementamos o counter
    if (cardNumber === cardCounter) {
      cardCounter--;
    }
    
    document.getElementById(cardId).remove();
    
    // Atualiza os números dos cards restantes
    updateCardNumbers();
  } else {
    alert("Você precisa ter pelo menos uma entidade configurada.");
  }
}

// Atualiza a numeração dos cards
function updateCardNumbers() {
  const cards = document.querySelectorAll('.form-card');
  let currentNumber = 1;
  
  cards.forEach(card => {
    const cardId = `card-${currentNumber}`;
    card.id = cardId;
    
    // Atualiza o título
    const title = card.querySelector('.card-header h5');
    title.textContent = `Entidade #${currentNumber}`;
    
    // Atualiza o botão de remoção
    const removeBtn = card.querySelector('.remove-card-btn');
    removeBtn.setAttribute('onclick', `removeCard('${cardId}')`);
    
    // Atualiza IDs dos inputs
    const inputs = card.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
      const oldId = input.id;
      if (oldId) {
        const parts = oldId.split('-');
        if (parts.length > 1) {
          input.id = `${parts[0]}-${currentNumber}`;
        }
      }
    });
    
    currentNumber++;
  });
  
  // Atualiza o contador global
  cardCounter = currentNumber - 1;
}

function addMSABlock(button) {
  const card = button.closest('.form-card');
  const msaBlocksContainer = card.querySelector('.msa-blocks');
  const index = card.querySelectorAll('.msa-block').length;
  
  const container = document.createElement('div');
  container.className = 'msa-block mb-3 p-3 border rounded bg-light position-relative';
  container.innerHTML = `
    <button class="btn-close position-absolute top-0 end-0 m-2" onclick="this.parentElement.remove()"></button>
    <label class="form-label">Formato do MSA:</label>
    <input type="text" class="form-control mb-2" name="msa_format" placeholder="Ex: a3m">

    <label class="form-label">Dados do MSA (1 sequência por linha):</label>
    <textarea name="msa_data" rows="4" class="form-control" placeholder=">seq1\nACGT..."></textarea>
  `;
  
  msaBlocksContainer.appendChild(container);
}

function removeMSABlock(closeButton) {
    const block = closeButton.closest('.msa-block');
    block.remove();
    updateBlockIndexes();
}

function updateBlockIndexes() {
    document.querySelectorAll('.msa-block').forEach((block, index) => {
        block.querySelectorAll('[name^="msa_format_"], [name^="msa_data_"]').forEach(input => {
            input.name = input.name.replace(/_(\d+)$/, `_${index}`);
        });
    });
}

function toggleSection(button, sectionType) {
  const card = button.closest('.form-card');
  const section = card.querySelector(`.${sectionType}-section`);
  section.style.display = section.style.display === 'none' ? 'block' : 'none';
}

function removeSection(button) {
  button.closest('.optional-section').style.display = 'none';
}

/**********************
 * FUNÇÕES DE VALIDAÇÃO
 **********************/
// Valida a sequência de acordo com o tipo de entidade
function validateSequence(entityType, sequence) {
  const invalidChars = {
      protein: /[BJOUXZ]/i,
      dna: /[^ATCG]/i,
      rna: /[^AUCG]/i
  };

  if (entityType in invalidChars && invalidChars[entityType].test(sequence)) {
      return {
          error: `Sequência inválida para ${entityType}. Caracteres permitidos: ${
              entityType === 'protein' ? 'Aminoácidos padrão' : 
              entityType === 'dna' ? 'A, T, C, G' : 'A, U, C, G'
          }`
      };
  }

  return { valid: true };
}

/************************************
 * FUNÇÕES DE CONSTRUÇÃO DE ENTIDADES
 ************************************/
// Gera IDs para as cópias da entidade (A, B, C...)
function generateEntityIDs(startIndex, copies) {
  const result = [];
  
  for (let i = 0; i < copies; i++) {
      const totalIndex = startIndex + i;
      
      // Calcula letra(s) (A-Z, AA-AZ, BA-BZ, etc.)
      let id = '';
      let num = totalIndex;
      
      // Gera IDs em base-26: A, B, C, ..., Z, AA, AB, ..., AZ, BA, ...
      do {
          id = String.fromCharCode(65 + (num % 26)) + id;
          num = Math.floor(num / 26) - 1;
      } while (num >= 0);
      
      result.push(id);
  }
  
  // Retorna como string se uma cópia, ou array se múltiplas
  return copies === 1 ? result[0] : result;
}

// Constrói objeto para entidade de proteína
function buildProteinEntity(ids, sequence, card) {
  const entity = {
      protein: {
          id: ids,
          sequence: sequence
      }
  };

  // Adicionar modificações se existirem
  const modificationsSection = card.querySelector('.modifications-section');
  if (modificationsSection && modificationsSection.style.display !== 'none') {
      try {
          const mods = JSON.parse(modificationsSection.querySelector('textarea').value);
          if (Array.isArray(mods)) {
              entity.protein.modifications = mods.map(mod => ({
                  ptmType: mod.type,
                  ptmPosition: mod.position
              }));
          }
      } catch (e) {
          console.error("Erro ao parsear modificações:", e);
      }
  }

  // Adicionar MSA se existir
  const msaBlocks = card.querySelectorAll('.msa-block');
  if (msaBlocks.length > 0) {
      // Simplificação: pega o primeiro bloco MSA
      const msaData = msaBlocks[0].querySelector('[name="msa_data"]').value;
      entity.protein.unpairedMsa = msaData;
      entity.protein.pairedMsa = ""; // Como recomendado na documentação
  }

  // Adicionar templates se existirem
  const templatesSection = card.querySelector('.templates-section');
  if (templatesSection && templatesSection.style.display !== 'none') {
      const templatesText = templatesSection.querySelector('textarea').value;
      if (templatesText.trim()) {
          entity.protein.templates = templatesText.split('\n')
              .filter(t => t.trim())
              .map(template => ({
                  mmcifPath: template.trim(),
                  queryIndices: [], // Seria preenchido conforme alinhamento
                  templateIndices: [] // Seria preenchido conforme alinhamento
              }));
      }
  }

  return entity;
}

// Constrói objeto para entidade de DNA
function buildDNAEntity(ids, sequence, card) {
  const entity = {
      dna: {
          id: ids,
          sequence: sequence
      }
  };

  // Adicionar modificações se existirem
  const modificationsSection = card.querySelector('.modifications-section');
  if (modificationsSection && modificationsSection.style.display !== 'none') {
      try {
          const mods = JSON.parse(modificationsSection.querySelector('textarea').value);
          if (Array.isArray(mods)) {
              entity.dna.modifications = mods.map(mod => ({
                  modificationType: mod.type,
                  basePosition: mod.position
              }));
          }
      } catch (e) {
          console.error("Erro ao parsear modificações:", e);
      }
  }

  return entity;
}

// Constrói objeto para entidade de RNA
function buildRNAEntity(ids, sequence, card) {
  const entity = {
      rna: {
          id: ids,
          sequence: sequence
      }
  };

  // Adicionar modificações se existirem
  const modificationsSection = card.querySelector('.modifications-section');
  if (modificationsSection && modificationsSection.style.display !== 'none') {
      try {
          const mods = JSON.parse(modificationsSection.querySelector('textarea').value);
          if (Array.isArray(mods)) {
              entity.rna.modifications = mods.map(mod => ({
                  modificationType: mod.type,
                  basePosition: mod.position
              }));
          }
      } catch (e) {
          console.error("Erro ao parsear modificações:", e);
      }
  }

  // Adicionar MSA se existir
  const msaBlocks = card.querySelectorAll('.msa-block');
  if (msaBlocks.length > 0) {
      // Simplificação: pega o primeiro bloco MSA
      const msaData = msaBlocks[0].querySelector('[name="msa_data"]').value;
      entity.rna.unpairedMsa = msaData;
  }

  return entity;
}

// Constrói objeto para entidade de ligante
function buildLigandEntity(ids, sequence, card) {
  // Verifica se a sequência parece ser um SMILES (contém caracteres especiais de química)
  const isSmiles = /[\[\]\(\)=#@]/.test(sequence);
  
  const entity = {
      ligand: {
          id: ids
      }
  };

  if (isSmiles) {
      entity.ligand.smiles = sequence;
  } else {
      entity.ligand.ccdCodes = [sequence];
  }

  return entity;
}

// Constrói objeto para entidade de íon
function buildIonEntity(ids, sequence) {
  // Remove números de carga (como o '+' em 'Na+') para obter o código CCD
  const ccdCode = sequence.replace(/[0-9+-]/g, '');
  
  return {
      ligand: {  // Íons são tratados como ligantes no AlphaFold 3
          id: ids,
          ccdCodes: [ccdCode]
      }
  };
}

/*************************************
 * FUNÇÕES PRINCIPAIS DE PROCESSAMENTO
 *************************************/

// Processa um card individual para extrair os dados da entidade
function processEntityCard(card, index, totalCopiesBefore = 0) {
  const entityType = card.querySelector('.entity-type').value;
  const copies = parseInt(card.querySelector('.copies').value) || 1;
  const sequence = card.querySelector('.sequence').value.trim();
  const seeds = parseInt(card.querySelector('.seeds').value) || 1;
  
  // Validação básica
  if (!entityType || !sequence) {
      return { error: "Tipo de entidade e sequência são obrigatórios" };
  }

  // Validar sequência de acordo com o tipo
  const validation = validateSequence(entityType, sequence);
  if (validation.error) {
      return { error: validation.error };
  }

  // Gerar IDs para as cópias (A, B, C... ou AA, AB, etc. se muitas cópias)
  // Passando o total de cópias que vieram antes deste card
  const ids = generateEntityIDs(totalCopiesBefore, copies);

  // Construir o objeto da entidade baseado no tipo
  let entity = {};
  switch (entityType) {
      case 'protein':
          entity = buildProteinEntity(ids, sequence, card);
          break;
      case 'dna':
          entity = buildDNAEntity(ids, sequence, card);
          break;
      case 'rna':
          entity = buildRNAEntity(ids, sequence, card);
          break;
      case 'ligand':
          entity = buildLigandEntity(ids, sequence, card);
          break;
      case 'ion':
          entity = buildIonEntity(ids, sequence);
          break;
      default:
          return { error: "Tipo de entidade desconhecido" };
  }

  return entity;
}

// Função principal para gerar o JSON de todas as entidades
function generateAllJSON() {
  const cards = document.querySelectorAll('.form-card');
  const entities = [];
  let hasErrors = false;
  const allSeeds = new Set();
  let totalCopiesBefore = 0; // Rastreia o total de cópias antes do card atual

  // Processar cada card/entidade
  cards.forEach((card, index) => {
      const entity = processEntityCard(card, index, totalCopiesBefore);
      if (entity.error) {
          hasErrors = true;
          alert(`Erro na Entidade #${index + 1}: ${entity.error}`);
      } else {
          entities.push(entity);
          
          // Atualiza o total de cópias para o próximo card
          const copies = parseInt(card.querySelector('.copies').value) || 1;
          totalCopiesBefore += copies;

          const seedInput = card.querySelector('.seeds');
            if (seedInput) {
                const seedValue = parseInt(seedInput.value);
                if (!isNaN(seedValue)) {
                    allSeeds.add(seedValue);
                }
            }
      }
  });

  if (hasErrors || entities.length === 0) {
      return null;
  }

  // Converter o Set de seeds para array
  const seedsArray = Array.from(allSeeds);
  if (seedsArray.length === 0) {
      seedsArray.push(42); // Valor padrão se nenhum seed for especificado
  }

  // Criar o objeto JSON final conforme especificação AlphaFold 3
  const jsonData = {
      name: "AlphaFold Prediction",
      modelSeeds: seedsArray,
      sequences: entities,
      dialect: "alphafold3",
      version: 2
  };

  return jsonData;
}

/*****************************
 * FUNÇÕES DE DOWNLOAD E ENVIO
 *****************************/

// Mostra o modal para o usuário digitar o nome do arquivo
function showFilenameModal(action) {
  pendingAction = action;
  const jsonData = generateAndValidateJSON();
  
  if (!jsonData) return;
  
  pendingJsonData = jsonData;
  
  // Inicializa o modal se não tiver sido feito ainda
  if (!filenameModal) {
    const modalElement = document.getElementById('filenameModal');
    filenameModal = new bootstrap.Modal(modalElement);
  }
  
  // Limpa o input e adiciona um placeholder com sugestão
  const filenameInput = document.getElementById('filenameInput');
  const now = new Date();
  const pad = (n) => n.toString().padStart(2, '0');
  const defaultName = `alphafold_input_${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  
  filenameInput.value = '';
  filenameInput.placeholder = defaultName;
  
  // Abre o modal
  filenameModal.show();
  
  // Coloca o foco no input
  filenameInput.focus();
}

// Confirma o nome do arquivo e executa a ação pendente
function confirmFilename() {
  const filenameInput = document.getElementById('filenameInput');
  let filename = filenameInput.value.trim();
  
  // Se o usuário não digitou nada, usa o placeholder
  if (!filename) {
    filename = filenameInput.placeholder;
  }
  
  // Remove caracteres inválidos do nome do arquivo
  filename = filename.replace(/[<>:"|?*\/\\]/g, '_').replace(/\s+/g, '_');
  
  // Fecha o modal
  if (filenameModal) {
    filenameModal.hide();
  }
  
  // Executa a ação pendente
  switch (pendingAction) {
    case 'download':
      downloadJSON(pendingJsonData, filename);
      break;
    case 'process':
      ProcessJSONWithName(filename);
      break;
    case 'both':
      downloadAndProcessJSONWithName(filename);
      break;
  }
  
  // Limpa as variáveis
  pendingAction = null;
  pendingJsonData = null;
}

// Permite confirmar ao pressionar Enter no input
document.addEventListener('DOMContentLoaded', function() {
  const filenameInput = document.getElementById('filenameInput');
  if (filenameInput) {
    filenameInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        confirmFilename();
      }
    });
  }
});

// Função para download do JSON
function generateAndValidateJSON() {
  const jsonData = generateAllJSON();
  if (!jsonData) {
    alert("Corrija os erros antes de gerar o JSON.");
    return null;
  }

  // Adicionar bondedAtomPairs se houver múltiplas entidades com pairing
  const pairingSections = document.querySelectorAll('.pairing-section');
  if (pairingSections.length > 0) {
    jsonData.bondedAtomPairs = [];

    pairingSections.forEach(section => {
      if (section.style.display !== 'none') {
        const pairingData = section.querySelector('input').value;
        if (pairingData) {
          // Processamento real dos dados pode ser inserido aqui
          jsonData.bondedAtomPairs.push(/* dados de ligação */);
        }
      }
    });
  }

  return jsonData;
}

function downloadJSON(jsonData, baseFilename = 'alphafold_input') {
  //Data e Hora local do Brasil
  const now = new Date();

  const pad = (n) => n.toString().padStart(2, '0');

  const year = now.getFullYear();
  const month = pad(now.getMonth() + 1);
  const day = pad(now.getDate());
  const hours = pad(now.getHours());
  const minutes = pad(now.getMinutes());
  const timestamp = `${year}-${month}-${day}_${hours}-${minutes}`;
  
  // Cria o nome do arquivo com timestamp (se não tiver underscore no nome, adiciona um antes do timestamp)
  let filename;
  if (baseFilename === 'alphafold_input') {
    // Nome padrão
    filename = `${baseFilename}_${timestamp}.json`;
  } else {
    // Nome customizado pelo usuário - adiciona timestamp antes da extensão
    filename = `${baseFilename}_${timestamp}.json`;
  }

  //criar o blob para download
  const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function downloadAllJSON() {
  showFilenameModal('download');
}

function ProcessJSON() {
  showFilenameModal('process');
}

function ProcessJSONWithName(filename) {
  const jsonData = pendingJsonData;
  if (!jsonData) return;

  // Enviar via FormData
  const formData = new FormData();
  formData.append('json_data', JSON.stringify(jsonData, null, 2));
  formData.append('filename', filename);
  
  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (response.ok) {
      window.location.href = '/dashboard';
    } else {
      alert('Erro no upload do arquivo JSON');
    }
  })
  .catch(error => {
    console.error('Erro:', error);
    alert('Erro no upload do arquivo JSON');
  });
}

function downloadAndProcessJSON() {
  showFilenameModal('both');
}

function downloadAndProcessJSONWithName(filename) {
  const jsonData = pendingJsonData;
  if (!jsonData) return;

  // Primeiro faz o download
  downloadJSON(jsonData, filename);
  
  // Depois envia para o servidor
  const formData = new FormData();
  formData.append('json_data', JSON.stringify(jsonData, null, 2));
  formData.append('filename', filename);
  
  fetch('/upload', {
    method: 'POST',
    body: formData
  })
  .then(response => {
    if (response.ok) {
      window.location.href = '/dashboard';
    } else {
      alert('Erro no upload do arquivo JSON');
    }
  })
  .catch(error => {
    console.error('Erro:', error);
    alert('Erro no upload do arquivo JSON');
  });
}

/***************
 * INICIALIZAÇÃO
 ***************/
// Inicializa os listeners para o primeiro card
document.addEventListener('DOMContentLoaded', function() {
  initEntityTypeListener(document.getElementById('card-1'));
});

// Configura o listener para mudança de tipo de entidade em um card específico
function initEntityTypeListener(card) {
  const entityType = card.querySelector('.entity-type');
  const sequenceField = card.querySelector('.sequence');
  const sequenceHelp = card.querySelector('.sequence-help');

  const examples = {
    protein: {
      seq: "MVQDTGKDTNLKGTAEANESVVYCDVFMQAALKEATCALEEGEVPVGCVLVKADSSTAAQAQAGDDLALQKLIVARGRNATNRKGHGLAHAEFVAVEELLRQATAGTSENIGGGGNSGAVSQDLADYVLYVVVEPCIMCAAMLLYNRVRKVYFGCTNPRFGGNGTVLSVHNSYKGCSGEDAALIGYESCGGYRAEEAVVLLQQFYRRENTNAPLGKRKRKD",
      warn: "A sequência deve conter apenas letras. Caracteres inválidos: B, J, O, U, X, Z."
    },
    dna: {
      seq: "ATGCGTACGTAGCTAGCTAGCTAGCTAGCTAGCTA",
      warn: "A sequência deve conter apenas A, T, C e G."
    },
    rna: {
      seq: "AUGCGUACGUAGCUAGCUAGCUAGCUAGCUAGCUA",
      warn: "A sequência deve conter apenas A, U, C e G."
    },
    ligand: {
      seq: "CC(=O)OC1=CC=CC=C1C(=O)O",
      warn: "Insira o SMILES da molécula ligante (formato texto)."
    },
    ion: {
      seq: "Na+", 
      warn: "Insira o símbolo do íon, como Na+, K+, Mg2+, etc."
    }
  };

  // Flag para saber se o campo contém atualmente um exemplo
  let hasExample = false;

  entityType.addEventListener('change', function() {
    const selected = this.value;
    if (examples[selected]) {
      sequenceField.value = examples[selected].seq;
      hasExample = true;
      sequenceHelp.textContent = examples[selected].warn;
      sequenceHelp.style.display = 'block';
    } else {
      sequenceHelp.style.display = 'none';
      hasExample = false;
    }
  });

  // Listener para digitar - limpa o exemplo na primeira alteração
  sequenceField.addEventListener('input', function() {
    if (hasExample) {
      // Limpa o campo na primeira alteração
      this.value = '';
      hasExample = false;
    }
  });

  // Listener para cole (paste) - limpa o exemplo e substitui pelo conteúdo colado
  sequenceField.addEventListener('paste', function(e) {
    if (hasExample) {
      hasExample = false;
      // setTimeout garante que o paste foi processado
      setTimeout(() => {
        // A textarea já terá o conteúdo colado
        if (this.value.trim()) {
          hasExample = false;
        }
      }, 0);
    }
  });
}

document.getElementById('jsonForm').addEventListener('submit', function (e) {
    const selected = entityType.value;
    const seq = sequenceField.value.toUpperCase();

    let invalid = false;
    if (selected === 'protein' && /[BJOUXZ]/.test(seq)) invalid = true;
    if (selected === 'dna' && /[^ATCG]/i.test(seq)) invalid = true;
    if (selected === 'rna' && /[^AUCG]/i.test(seq)) invalid = true;

    if (invalid) {
        e.preventDefault();
        alert("A sequência contém caracteres inválidos. Corrija antes de continuar.");
    }
    
});