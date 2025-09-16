// Dados dos resultados (será preenchido pelo template)
let searchResults = [];
let currentModalContent = '';

function setTerm(term) {
    document.getElementById('search_term').value = term;
}

function openModal(index) {
    const result = searchResults[index - 1]; // index-1 pois o template usa loop.index que começa em 1
    if (!result) return;

    const article = result.article;
    const title = article.title || article.filename || 'Documento DOU';
    const section = article.section || 'N/A';
    const terms = result.terms_matched || [];
    const summary = result.summary || '';
    const snippets = result.snippets || [];
    const fullText = article.text || 'Conteúdo não disponível';

    // Highlight dos termos encontrados no texto
    let highlightedText = fullText;
    terms.forEach(term => {
        const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<span class="highlight">$1</span>');
    });

    // Construir conteúdo do modal
    let modalHtml = `
        <div class="result-detail">
            <div class="meta-info">
                <strong>📄 Documento:</strong> ${title}<br>
                <strong>📋 Seção:</strong> ${section}<br>
                <strong>📁 Arquivo:</strong> ${article.filename || 'N/A'}<br>
                <strong>🔍 Termos encontrados:</strong> ${terms.join(', ')}<br>
                <strong>📝 Tamanho:</strong> ${fullText.length.toLocaleString()} caracteres
            </div>
    `;

    if (summary) {
        modalHtml += `
            <div class="result-detail">
                <h3>🤖 Resumo (IA)</h3>
                <div style="background: rgba(59, 130, 246, 0.1); padding: 15px; border-radius: var(--radius); border-left: 4px solid var(--primary-color);">
                    ${summary}
                </div>
            </div>
        `;
    }

    if (snippets && snippets.length > 0) {
        modalHtml += `
            <div class="result-detail">
                <h3>📝 Trechos Relevantes</h3>
        `;
        snippets.forEach(snippet => {
            modalHtml += `<div class="snippet" style="background: var(--background); padding: 12px; margin: 8px 0; border-radius: var(--radius); border-left: 3px solid var(--success-color);">${snippet}</div>`;
        });
        modalHtml += `</div>`;
    }

    modalHtml += `
        <div class="result-detail">
            <h3>📄 Conteúdo Completo</h3>
            <div class="content">${highlightedText}</div>
        </div>
    `;

    // Definir conteúdo do modal
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalContent').innerHTML = modalHtml;
    currentModalContent = fullText;

    // Mostrar modal
    const modal = document.getElementById('resultModal');
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevenir scroll do fundo

    // Scroll para o topo do modal
    const modalContent = modal.querySelector('.modal-content');
    modalContent.scrollTop = 0;
}

function closeModal() {
    const modal = document.getElementById('resultModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Restaurar scroll
}

function copyToClipboard() {
    if (currentModalContent) {
        navigator.clipboard.writeText(currentModalContent).then(() => {
            alert('Conteúdo copiado para a área de transferência!');
        }).catch(err => {
            // Fallback para navegadores mais antigos
            const textArea = document.createElement('textarea');
            textArea.value = currentModalContent;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            alert('Conteúdo copiado para a área de transferência!');
        });
    }
}

function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Fechar modal clicando no X
    const closeBtn = document.querySelector('.close');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Fechar modal clicando fora do conteúdo
    const modal = document.getElementById('resultModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    // Fechar modal com tecla ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });

    // Mostrar mensagem de processamento ao atualizar cache do DOU
    try {
        const refreshInput = document.querySelector('form input[name="action"][value="refresh_cache"]');
        if (refreshInput) {
            const refreshForm = refreshInput.closest('form');
            const refreshButton = refreshForm.querySelector('button[type="submit"]');
            let msg = document.getElementById('refreshProcessing');
            if (!msg) {
                msg = document.createElement('div');
                msg.id = 'refreshProcessing';
                msg.className = 'message info';
                msg.style.display = 'none';
                msg.style.marginTop = '10px';
                refreshForm.parentElement.insertBefore(msg, refreshForm.nextSibling);
            }
            refreshForm.addEventListener('submit', function() {
                if (refreshButton) {
                    refreshButton.disabled = true;
                    refreshButton.textContent = '🔄 Atualizando cache...';
                }
                msg.innerHTML = '<span class="spinner"></span>Download em andamento. Essa operação dura em torno de 20 segundos.';
                msg.style.display = 'block';
            });
        }
    } catch (err) {
        // Silenciar erros não críticos
    }

    // Mostrar mensagem de processamento ao submeter a busca
    try {
        const searchForm = document.getElementById('searchForm');
        const searchBtn = document.getElementById('searchBtn');
        const searchMsg = document.getElementById('searchProcessing');
        if (searchForm && searchBtn && searchMsg) {
            searchForm.addEventListener('submit', function() {
                searchBtn.disabled = true;
                searchBtn.textContent = '🔎 Buscando...';
                // Exibe a mesma mensagem solicitada
                searchMsg.innerHTML = '<span class="spinner"></span>Download em andamento. Essa operação dura em torno de 20 segundos.';
                searchMsg.style.display = 'block';
            });
        }

        // Mostrar mensagem de processamento para busca Mestrando Exterior
        const mestrandoForm = document.getElementById('searchMestrandoForm');
        const mestrandoBtn = document.getElementById('searchMestrandoBtn');
        const mestrandoMsg = document.getElementById('mestrandoProcessing');
        if (mestrandoForm && mestrandoBtn && mestrandoMsg) {
            mestrandoForm.addEventListener('submit', function() {
                mestrandoBtn.disabled = true;
                mestrandoBtn.textContent = '🔍 Buscando Mestrando...';
                mestrandoMsg.innerHTML = '<span class="spinner"></span>Busca sequencial em andamento. A busca completa pode demorar até 1 minuto.';
                mestrandoMsg.style.display = 'block';
            });
        }
    } catch (err) {
        // Silenciar erros não críticos
    }

    // Mostrar mensagem de processamento ao submeter busca de todas as sugestões
    try {
        const suggestionsForm = document.getElementById('searchSuggestionsForm');
        const suggestionsBtn = document.getElementById('searchSuggestionsBtn');
        const suggestionsMsg = document.getElementById('suggestionsProcessing');
        if (suggestionsForm && suggestionsBtn && suggestionsMsg) {
            suggestionsForm.addEventListener('submit', function() {
                suggestionsBtn.disabled = true;
                suggestionsBtn.textContent = '🔎 Buscando todas as sugestões...';
                suggestionsMsg.innerHTML = '<span class="spinner"></span>Download em andamento. Essa operação dura em torno de 20 segundos.';
                suggestionsMsg.style.display = 'block';
            });
        }
    } catch (err) {
        // Silenciar erros não críticos
    }

    // Mostrar mensagem ao enviar teste para todos agora
    try {
        const sendAllForm = document.getElementById('sendAllNowForm');
        const sendAllBtn = document.getElementById('sendAllNowBtn');
        const sendAllMsg = document.getElementById('sendAllProcessing');
        if (sendAllForm && sendAllBtn && sendAllMsg) {
            sendAllForm.addEventListener('submit', function() {
                sendAllBtn.disabled = true;
                sendAllBtn.textContent = '▶️ Enviando testes...';
                sendAllMsg.innerHTML = '<span class="spinner"></span>Download em andamento. Essa operação dura em torno de 20 segundos.';
                sendAllMsg.style.display = 'block';
            });
        }
    } catch (err) {
        // Silenciar erros não críticos
    }
});