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
    console.log('=== INICIANDO PROCESSAMENTO DO CSV ===');
    
    // Divide as linhas mantendo possíveis linhas vazias para referência
    const lines = csvContent.split('\n').map(line => line.trim());
    console.log('Total de linhas:', lines.length);
    
    if (lines.length < 4) {
      alert('O arquivo CSV está muito curto. Formato esperado:\n\n' +
            'Name;SMILES\n' +
            'Nome1;SMILES1\n' +
            'Nome2;SMILES2\n' +
            ';\n' +
            'protein;\n' +
            'SEQUENCIADAPROTEINA');
      return;
    }

    // Detecta o separador baseado na primeira linha
    const firstLine = lines[0];
    const separator = firstLine.includes(';') ? ';' : ',';
    console.log(`Separador detectado: "${separator}"`);

    // Define todas as variações de headers possíveis
    const smilesHeaders = ['smiles', 'smile', 'smi'];
    const nameHeaders = ['name', 'nome', 'names', 'nomes', 'title', 'titles', 'id', 'identifier'];
    const proteinHeaders = ['protein', 'proteina', 'proteins', 'proteinas', 
                           'sequence', 'sequencia', 'sequences', 'sequencias'];
    
    // Processa as listas separadas
    const proteins = [];
    const smilesList = [];
    let currentSection = 'smiles'; // Começa com SMILES
    let foundTransition = false;
    let smilesNameIndex = -1;
    let smilesSmilesIndex = -1;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lowerLine = line.toLowerCase();
      
      console.log(`Linha ${i}: "${line.substring(0, 50)}${line.length > 50 ? '...' : ''}"`);

      // Pula linhas completamente vazias
      if (line === '') {
        continue;
      }

      // Detecta transição para proteínas (linha com apenas separador ou header de proteína)
      if (!foundTransition && currentSection === 'smiles') {
        // Verifica se é uma linha de transição
        const isTransitionLine = line === ';' || 
                                line === separator || 
                                proteinHeaders.some(header => 
                                  lowerLine === header || 
                                  lowerLine === header + separator);
        
        if (isTransitionLine) {
          foundTransition = true;
          currentSection = 'proteins';
          console.log(`Transição detectada na linha ${i}: "${line}"`);
          continue;
        }
      }
      
      // Processa SMILES (antes da transição)
      if (currentSection === 'smiles') {
        // Primeira linha - detecta headers
        if (i === 0) {
          const headers = line.split(separator).map(h => h.trim().toLowerCase());
          console.log('Headers encontrados:', headers);
          
          // Procura índices para Name e SMILES
          headers.forEach((header, index) => {
            if (nameHeaders.includes(header)) {
              smilesNameIndex = index;
              console.log(`Header "Name" encontrado na coluna ${index + 1}`);
            }
            if (smilesHeaders.includes(header)) {
              smilesSmilesIndex = index;
              console.log(`Header "SMILES" encontrado na coluna ${index + 1}`);
            }
          });
          
          // Se não encontrou, assume posições padrão
          if (smilesNameIndex === -1 && smilesSmilesIndex === -1) {
            smilesNameIndex = 0;
            smilesSmilesIndex = Math.min(1, headers.length - 1);
            console.log(`Usando posições padrão: Name=${smilesNameIndex}, SMILES=${smilesSmilesIndex}`);
          }
          
          continue;
        }
        
        // Processa dados SMILES (linha não vazia e com separador)
        if (line.includes(separator)) {
          const parts = line.split(separator).map(p => p.trim());
          
          // Remove partes vazias no final
          while (parts.length > 0 && parts[parts.length - 1] === '') {
            parts.pop();
          }
          
          if (parts.length >= 2) {
            // Usa índices detectados ou padrão
            const nameIndex = smilesNameIndex !== -1 ? 
                            Math.min(smilesNameIndex, parts.length - 1) : 0;
            const smilesIndex = smilesSmilesIndex !== -1 ? 
                              Math.min(smilesSmilesIndex, parts.length - 1) : 1;
            
            const name = parts[nameIndex] || `Ligante_${smilesList.length + 1}`;
            const smile = parts[smilesIndex];
            
            // Valida e adiciona
            if (smile && isValidSmiles(smile)) {
              smilesList.push({ 
                smiles: smile, 
                name: name,
                originalIndex: smilesList.length + 1
              });
              console.log(`✅ SMILES ${smilesList.length}: "${name}" = ${smile.substring(0, 30)}...`);
            } else if (smile) {
              console.warn(`❌ SMILES inválido ignorado na linha ${i}: ${smile.substring(0, 50)}`);
            }
          }
        } else if (line && line.length > 10) {
          // Possível SMILES sem separador (apenas uma coluna)
          const smile = line;
          if (isValidSmiles(smile)) {
            smilesList.push({ 
              smiles: smile, 
              name: `Ligante_${smilesList.length + 1}`,
              originalIndex: smilesList.length + 1
            });
            console.log(`✅ SMILES ${smilesList.length} (sem nome): ${smile.substring(0, 30)}...`);
          }
        }
      }
      
      // Processa proteínas (após a transição)
      if (currentSection === 'proteins') {
        // Ignora linhas que são headers de proteína
        const isProteinHeader = proteinHeaders.some(header => 
          lowerLine === header || 
          lowerLine === header + separator ||
          lowerLine.startsWith(header + separator));
        
        if (isProteinHeader) {
          console.log(`Header de proteína ignorado: "${line}"`);
          continue;
        }
        
        // Ignora linhas de transição
        if (line === ';' || line === separator) {
          continue;
        }
        
        // Remove o separador do final se existir
        let proteinSeq = line;
        if (proteinSeq.endsWith(separator)) {
          proteinSeq = proteinSeq.slice(0, -1);
        }
        
        // Remove qualquer caractere não-alfabético do início/fim (mantendo apenas AA)
        proteinSeq = proteinSeq.replace(/^[^A-Za-z]+|[^A-Za-z]+$/g, '');
        
        if (proteinSeq.length > 0 && isValidProteinSequence(proteinSeq)) {
          proteins.push(proteinSeq);
          console.log(`✅ Proteína ${proteins.length} (${proteinSeq.length} aa): ${proteinSeq.substring(0, 30)}...`);
        } else if (proteinSeq.length > 0) {
          console.warn(`❌ Sequência de proteína inválida ignorada: ${proteinSeq.substring(0, 50)}`);
        }
      }
    }

    console.log('=== RESUMO FINAL ===');
    console.log(`SMILES encontrados: ${smilesList.length}`);
    console.log(`Proteínas encontradas: ${proteins.length}`);
    
    // Mostra todos os SMILES encontrados
    smilesList.forEach((item, index) => {
      console.log(`  S${index + 1}: ${item.name} -> ${item.smiles.substring(0, 40)}...`);
    });
    
    // Mostra todas as proteínas encontradas
    proteins.forEach((protein, index) => {
      console.log(`  P${index + 1}: ${protein.substring(0, 40)}...`);
    });

    if (smilesList.length === 0) {
      const errorMsg = 'Nenhum SMILES válido encontrado no CSV.\n\n' +
                      'FORMATO CORRETO NO EXCEL:\n\n' +
                      'Coluna A        Coluna B\n' +
                      'Name            SMILES\n' +
                      'PS-5485_01      O=C(N[C@H](CCOCc1...\n' +
                      'PS-5485_02      CCOC(=O)c1cc(COC...\n' +
                      '(linha em branco)\n' +
                      'protein;\n' +
                      'MKSSTQTILEHTAIPRHIAVIMDGNGRWAKKR...\n\n' +
                      'HEADERS ACEITOS para SMILES:\n' +
                      '• Name/Nome/Title/ID (qualquer um)\n' +
                      '• SMILES/Smile/SMI (qualquer um)\n\n' +
                      'HEADERS ACEITOS para Proteínas:\n' +
                      '• Protein/Proteina/Sequence/Sequencia';
      alert(errorMsg);
      return;
    }

    if (proteins.length === 0) {
      const errorMsg = 'Nenhuma proteína válida encontrada no CSV.\n\n' +
                      'VERIFIQUE:\n' +
                      '1. Após os SMILES, DEVE haver uma LINHA EM BRANCO\n' +
                      '2. Em seguida, uma linha com "protein;" ou similar\n' +
                      '3. Na próxima linha: a sequência da proteína\n\n' +
                      'Exemplo correto:\n' +
                      '... última linha de SMILES ...\n' +
                      '(linha em branco)\n' +
                      'protein; (ou sequence; ou sequencia;)\n' +
                      'MKSSTQTILEHTAIPRHIAVIMDGNGRWAKKR...';
      alert(errorMsg);
      return;
    }

    // Remove duplicatas
    const uniqueSmilesMap = new Map();
    smilesList.forEach(item => {
        if (!uniqueSmilesMap.has(item.smiles)) {
            uniqueSmilesMap.set(item.smiles, item);
        }
    });
    
    const uniqueProteins = [...new Set(proteins)];
    const uniqueSmiles = [...uniqueSmilesMap.values()];

    // Gera todas as combinações
    const combinations = generateCombinations(uniqueProteins, uniqueSmiles);
    console.log(`Total combinações geradas: ${combinations.length} (${uniqueProteins.length} proteínas × ${uniqueSmiles.length} SMILES)`);

    // Mostra preview e opções
    showCSVPreview(combinations, uniqueProteins, uniqueSmiles, filename);
    
  } catch (error) {
    console.error('Erro detalhado:', error);
    console.error('Stack trace:', error.stack);
    
    const errorMsg = 'Erro ao processar o CSV. Siga este formato EXATO no Excel:\n\n' +
                    'COLUNA A (qualquer header: Name/Nome/Title) | COLUNA B (qualquer header: SMILES/Smile)\n' +
                    '--------------------------------------------|--------------------------------------------\n' +
                    'PS-5485_01                                  | O=C(N[C@H](CCOCc1...\n' +
                    'PS-5485_02                                  | CCOC(=O)c1cc(COC...\n' +
                    '(DEIXE UMA LINHA EM BRANCO)\n' +
                    'protein; (ou sequence; ou sequencia;)       | (deixe vazio)\n' +
                    'MKSSTQTILEHTAIPRHIAVIMDGNGRWAKKR...         | (deixe vazio)\n\n' +
                    'IMPORTANTE: Salve como "CSV (delimitado por ponto e vírgula)"';
    
    alert(errorMsg);
  }
}

// Função para verificar se uma linha é um header
function isHeaderLine(line) {
  if (!line || typeof line !== 'string') return false;
  
  const headers = ['nome', 'name', 'nomes', 'names', 
    'smiles', 'smile', 'smi',
    'title', 'titles', 'id', 'identifier',
    'sequencia', 'sequence', 'sequencias', 'sequences', 
    'protein', 'proteina', 'proteinas', 'proteins'];
  
  const lowerLine = line.toLowerCase().trim();
  
  // Verifica se a linha é exatamente um header
  if (headers.includes(lowerLine)) {
    return true;
  }
  
  // Verifica se a linha contém headers com separador
  const parts = lowerLine.split(/[;,]/).map(p => p.trim());
  return parts.some(part => headers.includes(part));
}

// Função auxiliar para validar SMILES
function isValidSmiles(smiles) {
  if (!smiles || typeof smiles !== 'string') return false;
  
  const cleanSmiles = smiles.trim();
  
  // Verifica comprimento mínimo
  if (cleanSmiles.length < 5) {
    console.log(`SMILES muito curto (${cleanSmiles.length} chars): ${cleanSmiles}`);
    return false;
  }
  
  // Remove caracteres de nova linha ou retorno de carro
  const cleanSmilesNoCRLF = cleanSmiles.replace(/[\r\n]+/g, '');
  
  // Verifica caracteres válidos em SMILES
  const validSmilesChars = /^[A-Za-z0-9@+\-\\/()\[\]=#$.*%{}~]+$/;
  
  if (!validSmilesChars.test(cleanSmilesNoCRLF)) {
    const invalidChar = cleanSmilesNoCRLF.match(/[^A-Za-z0-9@+\-\\/()\[\]=#$.*%{}~]/);
    console.log(`SMILES com caractere inválido "${invalidChar?.[0]}": ${cleanSmilesNoCRLF.substring(0, 50)}`);
    return false;
  }
  
  // Verifica características de SMILES
  const hasOrganicAtoms = /[CHONPSFBrClI]/i.test(cleanSmilesNoCRLF);
  const hasStructureChars = /\[|\]|\(|\)|@|=|#/.test(cleanSmilesNoCRLF);
  
  return hasOrganicAtoms && hasStructureChars;
}

// Função auxiliar para validar sequência de proteína
function isValidProteinSequence(seq) {
  if (!seq || typeof seq !== 'string') return false;
  
  const cleanSeq = seq.trim().toUpperCase();
  
  // Remove caracteres de nova linha
  const cleanSeqNoCRLF = cleanSeq.replace(/[\r\n]+/g, '');
  
  // Verifica comprimento
  if (cleanSeqNoCRLF.length < 20) {
    console.log(`Sequência muito curta para ser proteína (${cleanSeqNoCRLF.length} aa): ${cleanSeqNoCRLF}`);
    return false;
  }
  
  // Verifica se contém apenas aminoácidos padrão
  const aminoAcidRegex = /^[ACDEFGHIKLMNPQRSTVWY]+$/;
  
  if (!aminoAcidRegex.test(cleanSeqNoCRLF)) {
    // Encontra caracteres inválidos
    const invalidMatch = cleanSeqNoCRLF.match(/[^ACDEFGHIKLMNPQRSTVWY]/g);
    if (invalidMatch) {
      console.log(`Sequência com caracteres inválidos (${invalidMatch.join(',')}): ${cleanSeqNoCRLF.substring(0, 50)}...`);
    }
    return false;
  }
  
  // Verifica diversidade de aminoácidos
  const uniqueAAs = new Set(cleanSeqNoCRLF.split(''));
  if (uniqueAAs.size < 5) {
    console.log(`Baixa diversidade de AA (apenas ${uniqueAAs.size} tipos diferentes)`);
    return false;
  }
  
  return true;
}

// Função auxiliar para validar SMILES
function isValidSmiles(smiles) {
  if (!smiles || typeof smiles !== 'string') return false;
  
  // Remove espaços
  const cleanSmiles = smiles.trim();
  if (cleanSmiles.length < 2) return false;
  
  // Verifica caracteres comuns em SMILES
  const commonSmilesChars = /^[A-Za-z0-9@+\-\\/()\[\]=#$.%{}~ ]+$/;
  
  // Verifica se tem pelo menos alguns átomos comuns
  const hasAtoms = /[CHONPSFBrClI]/i.test(cleanSmiles);
  
  return commonSmilesChars.test(cleanSmiles) && hasAtoms;
}

// Função auxiliar para validar sequência de proteína
function isValidProteinSequence(seq) {
  if (!seq || typeof seq !== 'string') return false;
  
  const cleanSeq = seq.trim();
  if (cleanSeq.length < 10) return false; // Sequências muito curtas provavelmente não são proteínas
  
  // Verifica se contém principalmente aminoácidos
  const aminoAcidRegex = /^[ACDEFGHIKLMNPQRSTVWY]+$/i;
  return aminoAcidRegex.test(cleanSeq);
}

// Verifica se uma linha é um header
function isHeaderLine(line) {
  const headers = ['nome', 'name', 'nomes', 'names', 
    'smiles', 'smile',
    'title', 'titles', 
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

  document.getElementById('csvInstructionsContent').innerHTML = instructionsContent;
  
  const modal = new bootstrap.Modal(instructionsModal);
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