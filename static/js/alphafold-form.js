const sequenceHelp = document.getElementById('sequenceHelp');
const entityType = document.getElementById('entityType');
const sequenceField = document.getElementById('sequence');

  // Funções para processamento global
function downloadAllJSON() {
    // Implementar lógica para gerar JSON de todas as entidades
    alert("Implementar lógica para download de todos os JSONs");
}
  
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

function downloadJSON() {
    const form = document.querySelector('form');
    const formData = new FormData(form);
    fetch("/generate_json", {
        method: "POST",
        body: formData
    }).then(res => res.blob())
        .then(blob => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "input_alphafold.json";
        a.click();
    }).catch(err => alert("Erro ao gerar JSON: " + err));
}

let cardCounter = 1;

// Adiciona um novo card de entidade
function addNewCard() {
  cardCounter++;
  const newCard = document.createElement('div');
  newCard.className = 'form-card';
  newCard.id = `card-${cardCounter}`;
  
  newCard.innerHTML = `
    <button class="btn btn-danger btn-sm remove-card-btn" onclick="removeCard('card-${cardCounter}')">
      <i class="fas fa-times"></i>
    </button>
    
    <div class="card-header">
      <h5 class="mb-0">Entidade #${cardCounter}</h5>
    </div>

    <form class="entity-form">
      <div class="mb-4">
        <div class="row g-3">
          <div class="col-md-3">
            <label for="entityType-${cardCounter}" class="form-label">Entidade</label>
            <select class="form-select entity-type" id="entityType-${cardCounter}" name="entity_type" required>
              <option value="" selected disabled>Selecione</option>
              <option value="protein">Proteína</option>
              <option value="dna">DNA</option>
              <option value="rna">RNA</option>
              <option value="ligand">Ligante</option>
              <option value="ion">Íon</option>
            </select>
          </div>
          
          <div class="col-md-2">
            <label for="copies-${cardCounter}" class="form-label">Cópias</label>
            <input type="number" class="form-control copies" id="copies-${cardCounter}" name="copies" min="1" max="10" value="1" required>
          </div>
          
          <div class="col-md-7">
            <label for="sequence-${cardCounter}" class="form-label">Sequência</label>
            <textarea class="form-control sequence" id="sequence-${cardCounter}" name="sequence" rows="3" required></textarea>
            <div class="sequence-help form-text text-danger mt-1" style="display: none;"></div>
          </div>
        </div>
      </div>

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

      <div class="msa-blocks mb-3"></div>

      <div class="optional-sections">
        <div class="optional-section templates-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Templates (1 por linha):</label>
          <textarea class="form-control mt-2" name="templates" rows="3" placeholder="Ex: 1abc_A"></textarea>
        </div>

        <div class="optional-section pairing-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Pairing:</label>
          <input type="text" class="form-control mt-2" name="pairing" placeholder="Ex: symmetric">
        </div>

        <div class="optional-section modifications-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Modificações (JSON):</label>
          <textarea class="form-control mt-2" name="modifications" rows="4" placeholder='Ex: [{"position": 3, "type": "phosphorylation"}]'></textarea>
        </div>

        <div class="optional-section coordinates-section mb-3 p-4 border rounded position-relative" style="display: none;">
          <button class="btn-close position-absolute top-0 end-0 m-2" onclick="removeSection(this)"></button>
          <label class="form-label fw-bold">Coordenadas (JSON):</label>
          <textarea class="form-control mt-2" name="coordinates" rows="4" placeholder='Ex: {"residue": 25, "x": 1.0, "y": 2.0, "z": 3.0}'></textarea>
        </div>

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

// Funções para manipulação das seções dentro de cada card
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

function toggleSection(button, sectionType) {
  const card = button.closest('.form-card');
  const section = card.querySelector(`.${sectionType}-section`);
  section.style.display = section.style.display === 'none' ? 'block' : 'none';
}

function removeSection(button) {
  button.closest('.optional-section').style.display = 'none';
}

function processAllEntities() {
  // Implementar lógica para processar todas as entidades
  alert("Implementar lógica para processar todas as entidades");
}

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

  entityType.addEventListener('change', function() {
    const selected = this.value;
    if (examples[selected]) {
      sequenceField.value = examples[selected].seq;
      sequenceHelp.textContent = examples[selected].warn;
      sequenceHelp.style.display = 'block';
    } else {
      sequenceHelp.style.display = 'none';
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