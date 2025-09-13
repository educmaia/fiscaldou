from flask import Flask, request, render_template_string, jsonify
import os
import re
import requests
from datetime import datetime
import xml.etree.ElementTree as ET
from io import StringIO

app = Flask(__name__)

# Armazenamento temporário em memória (substitui SQLite)
emails_storage = set()
search_terms_storage = {}

def clean_html(text):
    """Remove HTML tags from text for better readability."""
    if not text:
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def search_dou_demo(search_term):
    """
    Simulação de busca no DOU para demonstração.
    Em produção, conectaria com a API do INLABS.
    """
    # Dados de exemplo para demonstração
    demo_results = [
        {
            'filename': 'DO1_515_20250913_23099001.xml',
            'section': 'Seção 1',
            'content': f'Portaria nº 123 - Considerando a necessidade de regulamentar os procedimentos relacionados ao {search_term}, resolve: Art. 1º Ficam estabelecidas as diretrizes para implementação das medidas previstas no {search_term}...',
            'title': f'PORTARIA RELACIONADA A {search_term.upper()}'
        },
        {
            'filename': 'DO1_515_20250913_23099002.xml', 
            'section': 'Seção 2',
            'content': f'Resolução CNE/CES - O Conselho Nacional de Educação, no uso de suas atribuições, resolve estabelecer normas sobre {search_term}. Considerando os estudos realizados, determina-se que...',
            'title': f'RESOLUÇÃO SOBRE {search_term.upper()}'
        }
    ]
    
    # Filtrar apenas resultados que realmente contêm o termo
    filtered_results = []
    for result in demo_results:
        if search_term.lower() in result['content'].lower() or search_term.lower() in result['title'].lower():
            # Criar snippets destacando o termo encontrado
            snippets = []
            content_lower = result['content'].lower()
            term_lower = search_term.lower()
            
            # Encontrar posições do termo
            start = 0
            while True:
                pos = content_lower.find(term_lower, start)
                if pos == -1:
                    break
                # Extrair contexto ao redor do termo (50 chars antes e depois)
                snippet_start = max(0, pos - 50)
                snippet_end = min(len(result['content']), pos + len(search_term) + 50)
                snippet = result['content'][snippet_start:snippet_end]
                if snippet_start > 0:
                    snippet = "..." + snippet
                if snippet_end < len(result['content']):
                    snippet = snippet + "..."
                snippets.append(snippet)
                start = pos + 1
                if len(snippets) >= 3:  # Máximo 3 snippets
                    break
            
            filtered_results.append({
                'article': {
                    'filename': result['filename'],
                    'section': result['section'],
                    'title': result['title']
                },
                'terms_matched': [search_term],
                'snippets': snippets,
                'summary': f'Documento oficial que trata sobre {search_term}, estabelecendo diretrizes e procedimentos relacionados ao tema.'
            })
    
    return filtered_results

# Template HTML inline com funcionalidades completas
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiscalDOU - Monitoramento DOU</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { 
            color: #333; 
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .section {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #2196f3;
        }
        .form-group {
            margin: 15px 0;
        }
        .form-group label {
            display: block;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .form-group input[type="text"], .form-group input[type="email"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background: #2196f3;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
        }
        button:hover {
            background: #1976d2;
        }
        .danger { background: #f44336; }
        .danger:hover { background: #d32f2f; }
        
        .message {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            font-weight: bold;
        }
        .success { background: #e8f5e8; color: #2e7d32; border: 1px solid #4caf50; }
        .error { background: #ffebee; color: #c62828; border: 1px solid #f44336; }
        
        .result {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .result h3 {
            color: #1976d2;
            margin: 0 0 10px 0;
        }
        .snippets {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .snippet {
            background: #fff;
            padding: 8px;
            margin: 5px 0;
            border-left: 3px solid #2196f3;
            border-radius: 3px;
        }
        .summary {
            font-style: italic;
            color: #666;
            background: #f0f8ff;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .nav-tabs {
            display: flex;
            border-bottom: 1px solid #ddd;
            margin-bottom: 20px;
        }
        .nav-tab {
            background: #f5f5f5;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            margin-right: 5px;
        }
        .nav-tab.active {
            background: #2196f3;
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .email-list {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
        }
        .email-item {
            background: #f9f9f9;
            padding: 8px;
            margin: 5px 0;
            border-radius: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
    <script>
        function showTab(tabName) {
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            const buttons = document.querySelectorAll('.nav-tab');
            buttons.forEach(btn => btn.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            document.querySelector(`button[onclick="showTab('${tabName}')"]`).classList.add('active');
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>🏛️ FiscalDOU</h1>
        <h2 style="text-align: center; color: #666;">Sistema de Monitoramento do Diário Oficial da União</h2>
        
        {% if message %}
            <div class="message {{ 'error' if 'Erro' in message or 'erro' in message else 'success' }}">
                {{ message }}
            </div>
        {% endif %}

        <div class="nav-tabs">
            <button class="nav-tab active" onclick="showTab('search')">🔍 Buscar no DOU</button>
            <button class="nav-tab" onclick="showTab('emails')">📧 Gerenciar Emails</button>
            <button class="nav-tab" onclick="showTab('config')">⚙️ Configurações</button>
        </div>

        <!-- Tab: Busca no DOU -->
        <div id="search" class="tab-content active">
            <div class="section">
                <h3>🔍 Busca no Diário Oficial da União</h3>
                <form method="post">
                    <div class="form-group">
                        <label for="search_term">Termo de Busca:</label>
                        <input type="text" id="search_term" name="search_term" 
                               placeholder="Ex: 23001.000069/2025-95, Resolução CNE/CES, etc." 
                               value="{{ search_term or '' }}" required>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="use_ai" {{ 'checked' if use_ai else '' }}> 
                            Usar IA para gerar resumos (OpenAI)
                        </label>
                    </div>
                    <button type="submit">🔍 Buscar</button>
                </form>
            </div>

            {% if results %}
                <div class="section">
                    <h3>📄 Resultados da Busca ({{ results|length }} encontrados)</h3>
                    {% for result in results %}
                        <div class="result">
                            <h3>{{ result.article.title or result.article.filename }}</h3>
                            <p><strong>Arquivo:</strong> {{ result.article.filename }}</p>
                            <p><strong>Seção:</strong> {{ result.article.section }}</p>
                            <p><strong>Termos encontrados:</strong> {{ result.terms_matched|join(', ') }}</p>
                            
                            {% if result.summary %}
                                <div class="summary">
                                    <strong>📝 Resumo:</strong> {{ result.summary }}
                                </div>
                            {% endif %}
                            
                            {% if result.snippets %}
                                <div class="snippets">
                                    <strong>📑 Trechos relevantes:</strong>
                                    {% for snippet in result.snippets[:3] %}
                                        <div class="snippet">{{ snippet }}</div>
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>

        <!-- Tab: Gerenciar Emails -->
        <div id="emails" class="tab-content">
            <div class="section">
                <h3>📧 Cadastro de Emails</h3>
                <form method="post">
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" 
                               placeholder="exemplo@email.com" required>
                    </div>
                    <button type="submit" name="action" value="register">✅ Cadastrar Email</button>
                    <button type="submit" name="action" value="unregister" class="danger">❌ Remover Email</button>
                </form>
            </div>

            <div class="section">
                <h3>📋 Emails Cadastrados ({{ emails|length }})</h3>
                <div class="email-list">
                    {% for email in emails %}
                        <div class="email-item">
                            <span>{{ email }}</span>
                            <form method="post" style="display: inline;">
                                <input type="hidden" name="email" value="{{ email }}">
                                <button type="submit" name="action" value="unregister" class="danger" style="padding: 5px 10px; font-size: 12px;">❌</button>
                            </form>
                        </div>
                    {% else %}
                        <p style="color: #666;">Nenhum email cadastrado ainda.</p>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Tab: Configurações -->
        <div id="config" class="tab-content">
            <div class="section">
                <h3>⚙️ Status das Configurações</h3>
                <ul>
                    <li>OpenAI API Key: {{ '✅ Configurada' if openai_key else '❌ Não configurada' }}</li>
                    <li>SMTP Server: {{ smtp_server or '❌ Não configurado' }}</li>
                    <li>SMTP User: {{ smtp_user or '❌ Não configurado' }}</li>
                    <li>SMTP Pass: {{ '✅ Configurada' if smtp_pass else '❌ Não configurada' }}</li>
                </ul>
            </div>

            <div class="section">
                <h3>ℹ️ Informações</h3>
                <p><strong>Versão:</strong> Serverless (Vercel)</p>
                <p><strong>Deploy:</strong> {{ deploy_time }}</p>
                <p><strong>Armazenamento:</strong> Memória temporária (reinicia a cada deploy)</p>
                <p><strong>Funcionalidades:</strong> Busca demonstrativa, cadastro temporário de emails</p>
            </div>

            <div class="section">
                <p style="text-align: center;">
                    <a href="https://github.com/educmaia/fiscaldou" target="_blank" style="color: #2196f3; text-decoration: none;">
                        📂 Ver código fonte completo no GitHub
                    </a>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    """Página principal com funcionalidades completas do FiscalDOU."""
    message = None
    search_results = None
    search_term = ''
    use_ai = False
    
    # Verificar variáveis de ambiente
    openai_key = bool(os.getenv('OPENAI_API_KEY'))
    smtp_server = os.getenv('SMTP_SERVER', '')
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = bool(os.getenv('SMTP_PASS'))
    
    if request.method == 'POST':
        if 'search_term' in request.form:
            # Handle search
            search_term = request.form.get('search_term', '').strip()
            use_ai = request.form.get('use_ai') == 'on'
            
            if not search_term:
                message = "Por favor, digite um termo de busca."
            else:
                try:
                    # Perform search with the provided term
                    matches = search_dou_demo(search_term)
                    if matches:
                        search_results = matches
                        message = f"Encontrados {len(matches)} artigos para '{search_term}'."
                    else:
                        message = f"Nenhum artigo encontrado para o termo '{search_term}'."
                except Exception as e:
                    message = f"Erro na busca: {str(e)}"
        
        else:
            # Handle email actions
            action = request.form.get('action')
            email = request.form.get('email', '').strip().lower()
            
            if action in ['register', 'unregister'] and email:
                if action == 'register':
                    if email in emails_storage:
                        message = f'Email {email} já está cadastrado.'
                    else:
                        emails_storage.add(email)
                        message = f'Email {email} cadastrado com sucesso!'
                
                elif action == 'unregister':
                    if email in emails_storage:
                        emails_storage.remove(email)
                        message = f'Email {email} removido com sucesso!'
                    else:
                        message = f'Email {email} não encontrado.'
            else:
                message = "Por favor, forneça um email válido."
    
    deploy_time = datetime.now().strftime('%d/%m/%Y às %H:%M:%S UTC')
    
    return render_template_string(HTML_TEMPLATE, 
                                openai_key=openai_key,
                                smtp_server=smtp_server,
                                smtp_user=smtp_user,
                                smtp_pass=smtp_pass,
                                deploy_time=deploy_time,
                                message=message,
                                results=search_results,
                                search_term=search_term,
                                use_ai=use_ai,
                                emails=list(emails_storage))

@app.route('/health')
def health():
    """Endpoint de health check."""
    return {
        "status": "ok",
        "service": "FiscalDOU",
        "timestamp": datetime.now().isoformat(),
        "environment": "production",
        "platform": "vercel"
    }

@app.route('/config')
def config():
    """Endpoint para verificar configurações (sem expor valores sensíveis)."""
    return {
        "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
        "smtp_configured": bool(os.getenv('SMTP_SERVER') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASS')),
        "environment_variables": {
            "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
            "SMTP_SERVER": "configured" if os.getenv('SMTP_SERVER') else "missing",
            "SMTP_USER": "configured" if os.getenv('SMTP_USER') else "missing", 
            "SMTP_PASS": "configured" if os.getenv('SMTP_PASS') else "missing"
        }
    }

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)