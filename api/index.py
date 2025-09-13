from flask import Flask, request, render_template_string
import os
import re
import requests
import json
from datetime import datetime

app = Flask(__name__)

# Edge Config configuration
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

def get_edge_config_url():
    """Get Edge Config API URL"""
    if EDGE_CONFIG_ID:
        return f"https://api.vercel.com/v1/edge-config/{EDGE_CONFIG_ID}/items"
    return None

def get_from_edge_config(key):
    """Get value from Edge Config"""
    try:
        if not EDGE_CONFIG_ID:
            return None
            
        # Para leitura, usamos a URL de leitura direta
        url = f"https://edge-config.vercel.com/{EDGE_CONFIG_ID}"
        headers = {
            'Authorization': f'Bearer {VERCEL_TOKEN}' if VERCEL_TOKEN else ''
        }
        
        response = requests.get(f"{url}/{key}", headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error reading from Edge Config: {e}")
        return None

def set_edge_config_item(key, value):
    """Set value in Edge Config"""
    try:
        if not EDGE_CONFIG_ID or not VERCEL_TOKEN:
            return False
            
        url = get_edge_config_url()
        headers = {
            'Authorization': f'Bearer {VERCEL_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'items': [
                {
                    'operation': 'upsert',
                    'key': key,
                    'value': value
                }
            ]
        }
        
        response = requests.patch(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error writing to Edge Config: {e}")
        return False

def get_emails_from_edge_config():
    """Get emails list from Edge Config"""
    emails = get_from_edge_config('emails')
    if emails and isinstance(emails, list):
        return set(emails)
    return set()

def save_emails_to_edge_config(emails_set):
    """Save emails list to Edge Config"""
    emails_list = list(emails_set)
    return set_edge_config_item('emails', emails_list)

# Fallback storage (usado se Edge Config não estiver disponível)
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

# Template HTML com design original do DOU Notifier
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DOU Notifier - Serverless</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --text-primary: #1f2937;
            --text-secondary: #6b7280;
            --background: #f8fafc;
            --card-bg: #ffffff;
            --border: #e5e7eb;
            --radius: 12px;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            --shadow-hover: 0 10px 25px rgba(0, 0, 0, 0.1);
            --transition: all 0.2s ease-in-out;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: var(--text-primary);
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            color: white;
        }

        .header p {
            color: rgba(255, 255, 255, 0.9);
            font-size: 1.1rem;
        }

        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            max-width: 1200px;
            margin: 0 auto;
        }

        .card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 30px;
            transition: var(--transition);
            border: 1px solid var(--border);
        }

        .card:hover {
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }

        .card h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--text-primary);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: var(--text-primary);
        }

        input[type="email"], input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--border);
            border-radius: var(--radius);
            font-size: 1rem;
            transition: var(--transition);
            background: var(--background);
        }

        input[type="email"]:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        .suggestion-chip {
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: var(--transition);
            border: 2px solid var(--primary-color);
            margin: 4px;
        }

        .suggestion-chip:hover {
            background: var(--primary-hover);
            border-color: var(--primary-hover);
            transform: translateY(-1px);
        }

        button {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: var(--radius);
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            width: 100%;
            margin-top: 10px;
        }

        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }

        button:active {
            transform: translateY(0);
        }

        .message {
            padding: 12px 16px;
            border-radius: var(--radius);
            margin-bottom: 20px;
            font-weight: 500;
        }

        .message.success {
            background: rgba(16, 185, 129, 0.1);
            color: var(--success-color);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .message.error {
            background: rgba(239, 68, 68, 0.1);
            color: var(--error-color);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .email-list {
            margin-top: 20px;
        }

        .email-list ul {
            list-style: none;
        }

        .email-list li {
            background: var(--background);
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: var(--transition);
        }

        .email-list li:hover {
            background: #e2e8f0;
        }

        .email-list li .email {
            font-weight: 500;
        }

        .email-list li .remove-btn {
            background: var(--error-color);
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: var(--transition);
            width: auto;
            margin: 0;
        }

        .email-list li .remove-btn:hover {
            background: #dc2626;
        }

        .results {
            margin-top: 30px;
        }

        .result-item {
            background: var(--background);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 20px;
            transition: var(--transition);
            cursor: pointer;
        }

        .result-item:hover {
            box-shadow: var(--shadow);
            transform: translateY(-1px);
        }

        .result-item h4 {
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 1.1rem;
        }

        .result-item p {
            margin-bottom: 8px;
            color: var(--text-secondary);
        }

        .snippet {
            background: white;
            padding: 10px;
            border-left: 4px solid var(--primary-color);
            margin: 8px 0;
            font-style: italic;
            border-radius: 0 var(--radius) var(--radius) 0;
        }

        .suggestions-panel {
            margin-top: 15px;
            padding: 15px;
            background: var(--background);
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }

        @media (max-width: 768px) {
            .container {
                grid-template-columns: 1fr;
                gap: 20px;
            }

            .header h1 {
                font-size: 2rem;
            }

            .card {
                padding: 20px;
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .card, .result-item {
            animation: fadeIn 0.3s ease-out;
        }

        /* Configurações específicas para a versão serverless */
        .serverless-info {
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.3);
            border-radius: var(--radius);
            padding: 15px;
            margin-bottom: 20px;
            color: #92400e;
            font-weight: 500;
        }
    </style>
    <script>
        function setTerm(term) {
            document.getElementById('search_term').value = term;
        }

        function openModal(index) {
            // Para versão serverless, apenas mostra um alert
            alert('Funcionalidade de modal disponível na versão completa. Confira o código no GitHub!');
        }
    </script>
</head>
<body>
    <div class="header">
        <h1>DOU Notifier</h1>
        <p>Gerencie notificações e busque no Diário Oficial da União</p>
    </div>

    {% if message %}
        <div class="message {% if 'Erro' in message or 'não encontrado' in message %}error{% else %}success{% endif %}">
            {{ message }}
        </div>
    {% endif %}

    <div class="container">
        <div class="card">
            <h2>🔍 Buscar no DOU</h2>
            <form method="post">
                <div class="form-group">
                    <label for="search_term">Termo de busca</label>
                    <input type="text" id="search_term" name="search_term" 
                           placeholder="Digite o termo de busca" 
                           value="{{ search_term or '' }}" required>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" name="use_ai" {{ 'checked' if use_ai else '' }}> 
                        Usar IA para resumos (OpenAI)
                    </label>
                </div>
                <button type="submit">Buscar</button>

                <div class="suggestions-panel">
                    <strong>Sugestões de busca:</strong>
                    <div style="margin-top: 10px;">
                        <span class="suggestion-chip" onclick="setTerm('23001.000069/2025-95')">23001.000069/2025-95</span>
                        <span class="suggestion-chip" onclick="setTerm('Associação Brasileira das Faculdades (Abrafi)')">Associação Brasileira das Faculdades (Abrafi)</span>
                        <span class="suggestion-chip" onclick="setTerm('Resolução CNE/CES nº 2/2024')">Resolução CNE/CES nº 2/2024</span>
                        <span class="suggestion-chip" onclick="setTerm('reconhecimento de diplomas de pós-graduação stricto sensu obtidos no exterior')">reconhecimento de diplomas...</span>
                        <span class="suggestion-chip" onclick="setTerm('589/2025')">589/2025</span>
                        <span class="suggestion-chip" onclick="setTerm('relatado em 4 de setembro de 2025')">relatado em 4 de setembro de 2025</span>
                    </div>
                </div>
            </form>

            {% if results %}
                <div class="results">
                    <h3>📋 Resultados da Busca ({{ results|length }})</h3>
                    {% for result in results %}
                        <div class="result-item" onclick="openModal({{ loop.index }})">
                            <h4>{{ result.article.title or result.article.filename }} ({{ result.article.section }})</h4>
                            <p><strong style="color: var(--success-color);">🔍 Termos que geraram este resultado:</strong> 
                               <span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;">{{ result.terms_matched|join('</span> <span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;">') }}</span>
                            </p>
                            {% if result.summary %}
                                <p><strong>Resumo:</strong> {{ result.summary }}</p>
                            {% endif %}
                            {% if result.snippets %}
                                <div style="margin-top: 10px;">
                                    <strong>Trechos relevantes:</strong>
                                    {% for snippet in result.snippets[:2] %}
                                        <div class="snippet">{{ snippet }}</div>
                                    {% endfor %}
                                </div>
                            {% endif %}
                            <p style="color: var(--primary-color); font-size: 0.9rem; cursor: pointer; margin-top: 10px;">Clique para ver detalhes</p>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>

        <div class="card">
            <h2>📧 Gerenciar Emails</h2>

            <form method="post">
                <div class="form-group">
                    <label for="email_register">Cadastrar novo email</label>
                    <input type="email" id="email_register" name="email" placeholder="Digite o email" required>
                </div>
                <button type="submit" name="action" value="register">Cadastrar</button>
            </form>

            <form method="post" style="margin-top: 20px;">
                <div class="form-group">
                    <label for="email_remove">Remover email</label>
                    <input type="email" id="email_remove" name="email" placeholder="Digite o email para remover" required>
                </div>
                <button type="submit" name="action" value="unregister" style="background: var(--error-color);">Remover</button>
            </form>

            <div class="email-list">
                <h3>Emails Cadastrados</h3>
                {% if emails %}
                    <ul>
                        {% for email in emails %}
                            <li>
                                <span class="email">{{ email }}</span>
                                <form method="post" style="display: inline; margin: 0;">
                                    <input type="hidden" name="email" value="{{ email }}">
                                    <button type="submit" name="action" value="unregister" class="remove-btn">❌</button>
                                </form>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p style="color: var(--text-secondary); font-style: italic;">Nenhum email cadastrado.</p>
                {% endif %}
            </div>

            <div style="margin-top: 30px; padding: 15px; background: var(--background); border-radius: var(--radius); border: 1px solid var(--border);">
                <h4>ℹ️ Informações do Sistema</h4>
                <ul style="margin: 10px 0; padding-left: 20px; color: var(--text-secondary);">
                    <li>Status: {{ '🟢 Online' }}</li>
                    <li>Funcionalidade: Sistema de monitoramento DOU</li>
                </ul>
                <p style="text-align: center; margin-top: 15px;">
                    <a href="https://github.com/educmaia/fiscaldou" target="_blank"
                       style="color: var(--primary-color); text-decoration: none; font-weight: 500;">
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
    try:
        message = None
        search_results = None
        search_term = ''
        use_ai = False
        
        # Verificar variáveis de ambiente
        openai_key = bool(os.getenv('OPENAI_API_KEY'))
        smtp_server = os.getenv('SMTP_SERVER', '')
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_pass = bool(os.getenv('SMTP_PASS'))
        edge_config_available = bool(EDGE_CONFIG_ID)
        
        # Carregar emails do Edge Config ou usar fallback
        if edge_config_available:
            current_emails = get_emails_from_edge_config()
            if current_emails is None:
                current_emails = emails_storage  # Fallback
        else:
            current_emails = emails_storage
        
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
                        if email in current_emails:
                            message = f'Email {email} já está cadastrado.'
                        else:
                            current_emails.add(email)
                            # Salvar no Edge Config ou fallback
                            if edge_config_available:
                                if save_emails_to_edge_config(current_emails):
                                    message = f'Email {email} cadastrado com sucesso! (Edge Config)'
                                else:
                                    emails_storage.add(email)  # Fallback
                                    message = f'Email {email} cadastrado com sucesso! (Fallback)'
                            else:
                                emails_storage.add(email)
                                message = f'Email {email} cadastrado com sucesso! (Memória)'
                    
                    elif action == 'unregister':
                        if email in current_emails:
                            current_emails.remove(email)
                            # Salvar no Edge Config ou fallback
                            if edge_config_available:
                                if save_emails_to_edge_config(current_emails):
                                    message = f'Email {email} removido com sucesso! (Edge Config)'
                                else:
                                    emails_storage.discard(email)  # Fallback
                                    message = f'Email {email} removido com sucesso! (Fallback)'
                            else:
                                emails_storage.discard(email)
                                message = f'Email {email} removido com sucesso! (Memória)'
                        else:
                            message = f'Email {email} não encontrado.'
                else:
                    message = "Por favor, forneça um email válido."
        
        return render_template_string(HTML_TEMPLATE,
                                    message=message,
                                    results=search_results,
                                    search_term=search_term,
                                    use_ai=use_ai,
                                    emails=list(current_emails))
    
    except Exception as e:
        # Em caso de erro, retornar uma página simples
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Erro - FiscalDOU</title></head>
        <body>
            <h1>Erro no FiscalDOU</h1>
            <p>Ocorreu um erro: {str(e)}</p>
            <p><a href="/">Tentar novamente</a></p>
        </body>
        </html>
        """
        return error_html, 500

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
    try:
        return {
            "status": "ok",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "smtp_configured": bool(os.getenv('SMTP_SERVER') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASS')),
            "environment_variables": {
                "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
                "SMTP_SERVER": "configured" if os.getenv('SMTP_SERVER') else "missing",
                "SMTP_USER": "configured" if os.getenv('SMTP_USER') else "missing", 
                "SMTP_PASS": "configured" if os.getenv('SMTP_PASS') else "missing"
            }
        }
    except Exception as e:
        return {"error": str(e)}, 500

@app.route('/favicon.ico')
def favicon():
    """Handle favicon requests."""
    return '', 204

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return f"Internal Server Error: {str(error)}", 500

@app.errorhandler(404)  
def not_found(error):
    """Handle 404 errors."""
    return "Page not found", 404

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)