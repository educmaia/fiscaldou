from flask import Flask, request, render_template_string, send_from_directory
import sqlite3
from pathlib import Path
from search import find_matches
from summarize import summarize_matches
import re

app = Flask(__name__)
DB_PATH = Path('emails.db')


def init_db():
    """Initialize SQLite database tables if not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            term TEXT NOT NULL,
            FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE,
            UNIQUE(email_id, term)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database tables ensured.")


init_db()


def clean_html(text):
    """Remove HTML tags from text for better readability."""
    if not text:
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


@app.route('/', methods=['GET', 'POST'])
def home():
    message = None
    search_results = None
    selected_email = request.args.get('email', '')

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
                    matches = find_matches([search_term])
                    if matches:
                        # Summarize matches
                        summarized = summarize_matches(matches, use_ai=use_ai)
                        # Clean HTML from summaries and snippets for better display
                        for result in summarized:
                            if 'summary' in result and result['summary']:
                                result['summary'] = clean_html(
                                    result['summary'])
                            if 'snippets' in result and result['snippets']:
                                result['snippets'] = [clean_html(
                                    snippet) for snippet in result['snippets']]
                        search_results = summarized
                        message = f"Encontrados {len(matches)} artigos."
                    else:
                        message = "Nenhum artigo encontrado para o termo especificado."
                except Exception as e:
                    message = f"Erro na busca: {str(e)}"
        else:
            # Handle email actions
            action = request.form.get('action')
            email = request.form.get('email').strip().lower()

            if action in ['register', 'unregister']:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                if action == 'register':
                    try:
                        cursor.execute(
                            'INSERT INTO emails (email) VALUES (?)', (email,))
                        conn.commit()
                        message = f'Email {email} cadastrado com sucesso!'
                        selected_email = email
                    except sqlite3.IntegrityError:
                        message = f'Email {email} já cadastrado.'
                        selected_email = email
                elif action == 'unregister':
                    cursor.execute(
                        'DELETE FROM emails WHERE email = ?', (email,))
                    if cursor.rowcount > 0:
                        message = f'Email {email} removido com sucesso!'
                        conn.commit()
                        selected_email = ''
                    else:
                        message = f'Email {email} não encontrado.'
                        selected_email = email

                conn.close()
            elif action == 'add_term':
                term = request.form.get('term', '').strip()
                if term and selected_email:
                    if add_search_term(selected_email, term):
                        message = f'Termo "{term}" adicionado para {selected_email}!'
                    else:
                        message = f'Termo "{term}" já existe para {selected_email}.'
                else:
                    message = "Selecione um email e digite um termo."
            elif action == 'remove_term':
                term = request.form.get('remove_term')
                if term and selected_email:
                    if remove_search_term(selected_email, term):
                        message = f'Termo "{term}" removido de {selected_email}!'
                    else:
                        message = f'Termo "{term}" não encontrado para {selected_email}.'
            elif action == 'search_terms':
                if selected_email:
                    terms = get_search_terms(selected_email)
                    if terms:
                        all_matches = []
                        for term in terms:
                            try:
                                matches = find_matches([term])
                                all_matches.extend(matches)
                            except Exception as e:
                                message = f"Erro na busca do termo '{term}': {str(e)}"
                                break
                        if all_matches:
                            # Summarize and clean
                            summarized = summarize_matches(all_matches)
                            for result in summarized:
                                if 'summary' in result and result['summary']:
                                    result['summary'] = clean_html(
                                        result['summary'])
                                if 'snippets' in result and result['snippets']:
                                    result['snippets'] = [clean_html(
                                        snippet) for snippet in result['snippets']]
                            search_results = summarized
                            message = f"Encontrados {len(all_matches)} artigos para os termos de {selected_email}."
                        else:
                            message = f"Nenhum artigo encontrado para os termos de {selected_email}."
                    else:
                        message = f"Nenhum termo cadastrado para {selected_email}."

    terms = get_search_terms(selected_email) if selected_email else []
    import json
    results_json = json.dumps(search_results or [])
    return render_template_string(HTML_TEMPLATE, emails=get_emails(), message=message, results=search_results, selected_email=selected_email, terms=terms, results_json=results_json)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_term = request.form.get('search_term', '').strip()
        use_ai = request.form.get('use_ai') == 'on'
        if not search_term:
            return render_template_string(SEARCH_TEMPLATE, results=None, message="Por favor, digite um termo de busca.", search_term="")

        try:
            # Perform search with the provided term
            matches = find_matches([search_term])
            if matches:
                # Summarize matches
                summarized = summarize_matches(matches, use_ai=use_ai)
                # Clean HTML from summaries and snippets
                for result in summarized:
                    if 'summary' in result and result['summary']:
                        result['summary'] = clean_html(result['summary'])
                    if 'snippets' in result and result['snippets']:
                        result['snippets'] = [clean_html(
                            snippet) for snippet in result['snippets']]
                return render_template_string(SEARCH_TEMPLATE, results=summarized, message=f"Encontrados {len(matches)} artigos.", search_term=search_term)
            else:
                return render_template_string(SEARCH_TEMPLATE, results=None, message="Nenhum artigo encontrado para o termo especificado.", search_term=search_term)
        except Exception as e:
            return render_template_string(SEARCH_TEMPLATE, results=None, message=f"Erro na busca: {str(e)}", search_term=search_term)

    return render_template_string(SEARCH_TEMPLATE, results=None, message=None, search_term="")


def get_emails():
    """Get list of registered emails."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM emails ORDER BY email')
    emails = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emails


def get_search_terms(email):
    """Get search terms for a specific email."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT term FROM search_terms st
        JOIN emails e ON st.email_id = e.id
        WHERE e.email = ?
        ORDER BY term
    ''', (email,))
    terms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return terms


def add_search_term(email, term):
    """Add a search term for an email."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM emails WHERE email = ?', (email,))
        email_id = cursor.fetchone()
        if email_id:
            cursor.execute(
                'INSERT INTO search_terms (email_id, term) VALUES (?, ?)', (email_id[0], term.strip()))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        pass  # Term already exists
    finally:
        conn.close()
    return False


def remove_search_term(email, term):
    """Remove a search term for an email."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM search_terms WHERE email_id = (
            SELECT id FROM emails WHERE email = ?
        ) AND term = ?
    ''', (email, term.strip()))
    removed = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return removed


# Modern HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DOU Notifier - Cadastro e Busca</title>
    <style>
        :root {
            --primary-color: #2563eb;
            --primary-hover: #1d4ed8;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --error-color: #ef4444;
            --warning-color: #f59e0b;
            --background: #f8fafc;
            --card-bg: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --radius: 8px;
            --transition: all 0.2s ease-in-out;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, var(--background) 0%, #e2e8f0 100%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }

        .header p {
            color: var(--text-secondary);
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

        .suggestions-panel {
            /* Always visible */
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
        }

        .result-item:hover {
            box-shadow: var(--shadow);
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

        .no-results {
            text-align: center;
            color: var(--text-secondary);
            font-style: italic;
            padding: 40px;
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.3s ease-out;
        }

        .modal-content {
            background-color: var(--card-bg);
            margin: 5% auto;
            padding: 30px;
            border-radius: var(--radius);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            width: 90%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }

        .close {
            color: var(--text-secondary);
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            transition: var(--transition);
        }

        .close:hover {
            color: var(--text-primary);
        }

        .modal-snippet {
            background: var(--background);
            padding: 15px;
            border-left: 4px solid var(--primary-color);
            margin: 10px 0;
            border-radius: 0 var(--radius) var(--radius) 0;
            font-style: italic;
            line-height: 1.6;
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

            .modal-content {
                margin: 10% auto;
                padding: 20px;
                width: 95%;
            }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .card, .result-item {
            animation: fadeIn 0.3s ease-out;
        }
    </style>
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
                    <input type="text" id="search_term" name="search_term" placeholder="Digite o termo de busca" required>
                </div>
                <button type="submit">Buscar</button>

                <div class="suggestions-panel" style="margin-top: 15px; padding: 15px; background: var(--background); border-radius: var(--radius); border: 1px solid var(--border);">
                    <strong>Sugestões de busca:</strong>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;">
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
                            <h4>{{ result.article.filename }} ({{ result.article.section }})</h4>
                            <p><strong style="color: var(--success-color);">🔍 Termos que geraram este resultado:</strong> <span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;">{{ result.terms_matched|join('</span> <span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;">') }}</span></p>
                            <p><strong style="color: var(--warning-color);">🏛️ Orgão de Origem:</strong> {{ result.article.artCategory }}</p>
                            {% if result.summary %}
                                <p><strong>Resumo:</strong> {{ result.summary }}</p>
                            {% endif %}
                            <p style="color: var(--primary-color); font-size: 0.9rem; cursor: pointer;">Clique para ver detalhes</p>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>

        <div class="card">
            <h2>📧 Gerenciar Emails e Termos</h2>

            <form method="post">
                <div class="form-group">
                    <label for="email_register">Cadastrar novo email</label>
                    <input type="email" id="email_register" name="email" placeholder="Digite o email" required>
                </div>
                <button type="submit" name="action" value="register">Cadastrar</button>
            </form>

            <form method="post">
                <div class="form-group">
                    <label for="email_remove">Remover email</label>
                    <input type="email" id="email_remove" name="email" placeholder="Digite o email para remover" required>
                </div>
                <button type="submit" name="action" value="unregister">Remover</button>
            </form>

            <div class="email-list">
                <h3>Emails Cadastrados</h3>
                {% if emails %}
                    <ul>
                        {% for email in emails %}
                            <li>
                                <a href="?email={{ email }}" class="email-link">{{ email }}</a>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p style="color: var(--text-secondary); font-style: italic;">Nenhum email cadastrado.</p>
                {% endif %}
            </div>

            {% if selected_email %}
                <div class="term-management" style="margin-top: 30px; border-top: 1px solid var(--border); padding-top: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3>🎯 Termos de Busca para {{ selected_email }}</h3>
                        <form method="post" style="margin: 0;">
                            <input type="hidden" name="email" value="{{ selected_email }}">
                            <button type="submit" name="action" value="search_terms" style="background: var(--success-color); padding: 8px 16px;">Buscar Agora</button>
                        </form>
                    </div>

                    <form method="post">
                        <input type="hidden" name="email" value="{{ selected_email }}">
                        <div class="form-group">
                            <label for="term_add">Adicionar termo</label>
                            <input type="text" id="term_add" name="term" placeholder="Digite o termo de busca" required>
                        </div>
                        <button type="submit" name="action" value="add_term">Adicionar</button>
                    </form>

                    {% if terms %}
                        <div class="term-list" style="margin-top: 20px;">
                            <h4>Termos Atuais</h4>
                            <ul>
                                {% for term in terms %}
                                    <li style="display: flex; justify-content: space-between; align-items: center; background: var(--background); padding: 8px 12px; margin-bottom: 5px; border-radius: var(--radius);">
                                        <span>{{ term }}</span>
                                        <form method="post" style="margin: 0;">
                                            <input type="hidden" name="email" value="{{ selected_email }}">
                                            <input type="hidden" name="remove_term" value="{{ term }}">
                                            <button type="submit" name="action" value="remove_term" style="background: var(--error-color); color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">Remover</button>
                                        </form>
                                    </li>
                                {% endfor %}
                            </ul>
                        </div>
                    {% else %}
                        <p style="color: var(--text-secondary); font-style: italic; margin-top: 10px;">Nenhum termo cadastrado.</p>
                    {% endif %}
                </div>
            {% endif %}
        </div>
    </div>

    <!-- Modal -->
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal()">&times;</span>
            <div id="modal-body">
                <!-- Content will be inserted here -->
            </div>
        </div>
    </div>

    <script>
        const results = {{ results_json|safe }};

        function openModal(index) {
            const result = results[index - 1]; // 1-based to 0-based
            if (!result) return;

            const modalBody = document.getElementById('modal-body');
            modalBody.innerHTML = `
                <h2>${result.article.filename} (${result.article.section})</h2>
                <p><strong style="color: var(--success-color);">🔍 Termos que geraram este resultado:</strong> ${result.terms_matched.map(term => `<span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold; margin-right: 4px;">${term}</span>`).join('')}</p>
                <p><strong style="color: var(--warning-color);">🏛️ Orgão de Origem:</strong> ${result.article.artCategory}</p>
                ${result.summary ? `<p><strong>Resumo:</strong></p><p>${result.summary}</p>` : ''}
                ${result.snippets && result.snippets.length ? `
                    <p><strong>Trechos relevantes:</strong></p>
                    ${result.snippets.map(snippet => `<div class="modal-snippet">${snippet}</div>`).join('')}
                ` : ''}
                <p><strong>Link XML:</strong> <a href="${result.article.xml_path}" target="_blank">${result.article.xml_path}</a></p>
            `;

            document.getElementById('resultModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('resultModal').style.display = 'none';
        }

        function setTerm(term) {
            document.getElementById('search_term').value = term;
            document.getElementById('suggestions-tooltip').style.display = 'none';
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('resultModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

# Search HTML template
SEARCH_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Busca no DOU - DOU Notifier</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }
        form { margin: 20px 0; }
        input[type="text"] { width: 400px; padding: 5px; }
        button { padding: 5px 10px; margin: 5px; }
        .message { color: blue; font-weight: bold; }
        .error { color: red; font-weight: bold; }
        .result { border: 1px solid #ccc; padding: 10px; margin: 10px 0; background: #f9f9f9; }
        .summary { font-style: italic; }
        .snippets { margin-top: 10px; }
        .snippet { background: #fff; padding: 5px; margin: 5px 0; border-left: 3px solid #007bff; }
    </style>
</head>
<body>
    <h1>Busca no Diário Oficial da União</h1>
    {% if message %}
        <p class="{% if 'Erro' in message %}error{% else %}message{% endif %}">{{ message }}</p>
    {% endif %}

    <form method="post">
        <div class="form-group">
            <input type="text" name="search_term" placeholder="Digite o termo de busca" value="{{ search_term }}" required>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" name="use_ai" checked> Usar IA para resumos
            </label>
        </div>
        <button type="submit">Buscar</button>
    </form>

    {% if results %}
        <h2>Resultados da Busca</h2>
        {% for result in results %}
            <div class="result">
                <h3>{{ result.article.filename }} ({{ result.article.section }})</h3>
                <p><strong>Termos encontrados:</strong> {{ result.terms_matched|join(', ') }}</p>
                {% if result.summary %}
                    <p class="summary"><strong>Resumo:</strong> {{ result.summary }}</p>
                {% endif %}
                {% if result.snippets %}
                    <div class="snippets">
                        <strong>Trechos relevantes:</strong>
                        {% for snippet in result.snippets[:3] %}
                            <div class="snippet">{{ snippet }}</div>
                        {% endfor %}
                    </div>
                {% endif %}
            </div>
        {% endfor %}
    {% endif %}

    <p><a href="/">Voltar ao Cadastro</a> | <a href="/search">Nova Busca</a></p>
</body>
</html>
'''


@app.route('/xml/<path:filename>')
def serve_xml(filename):
    """Serve XML files from the extracted directory."""
    try:
        return send_from_directory('extracted', filename, as_attachment=True)
    except FileNotFoundError:
        return "Arquivo não encontrado", 404


if __name__ == '__main__':
    print("Flask app rodando em http://localhost:5000")
    app.run(debug=True, port=5000)
