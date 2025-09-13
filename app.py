from flask import Flask, request, render_template_string, jsonify
import sqlite3
from pathlib import Path
import re
from datetime import datetime

app = Flask(__name__)

# Database initialization
def init_db():
    """Initialize the database with required tables."""
    DB_PATH = Path('emails.db')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create emails table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            term TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email, term),
            FOREIGN KEY (email) REFERENCES emails (email) ON DELETE CASCADE
        )''')

    conn.commit()
    conn.close()

# Initialize database on startup
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
    """Main page with complete FiscalDOU functionality."""
    message = None
    search_results = None
    search_term = ''
    use_ai = False

    if request.method == 'POST':
        if 'search_term' in request.form:
            # Handle search
            search_term = request.form.get('search_term', '').strip()
            use_ai = request.form.get('use_ai') == 'on'

            if not search_term:
                message = "Por favor, digite um termo de busca."
            else:
                try:
                    # Import search functions
                    from search import find_matches
                    matches = find_matches([search_term])

                    if matches:
                        # Clean HTML from summaries and snippets
                        for result in matches:
                            if 'snippets' in result and result['snippets']:
                                result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]

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
            term = request.form.get('term', '').strip()

            if action == 'add_email' and email:
                try:
                    conn = sqlite3.connect('emails.db')
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO emails (email) VALUES (?)', (email,))
                    conn.commit()
                    conn.close()
                    message = f'Email {email} cadastrado com sucesso!'
                except sqlite3.IntegrityError:
                    message = f'Email {email} já está cadastrado.'
                except Exception as e:
                    message = f'Erro ao cadastrar email: {str(e)}'

            elif action == 'remove_email' and email:
                try:
                    conn = sqlite3.connect('emails.db')
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM emails WHERE email = ?', (email,))
                    if cursor.rowcount > 0:
                        message = f'Email {email} removido com sucesso!'
                    else:
                        message = f'Email {email} não encontrado.'
                    conn.commit()
                    conn.close()
                except Exception as e:
                    message = f'Erro ao remover email: {str(e)}'

            elif action == 'add_term' and email and term:
                if add_search_term(email, term):
                    message = f'Termo "{term}" adicionado para {email}!'
                else:
                    message = f'Erro ao adicionar termo ou termo já existe.'

            elif action == 'remove_term' and email and term:
                if remove_search_term(email, term):
                    message = f'Termo "{term}" removido de {email}!'
                else:
                    message = f'Termo "{term}" não encontrado para {email}.'

    # Get current emails and their terms
    emails = get_emails()
    email_terms = {}
    for email in emails:
        email_terms[email] = get_search_terms(email)

    return render_template_string(HTML_TEMPLATE,
                                  message=message,
                                  results=search_results,
                                  search_term=search_term,
                                  use_ai=use_ai,
                                  emails=emails,
                                  email_terms=email_terms)

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search endpoint for API calls."""
    if request.method == 'POST':
        data = request.get_json()
        search_term = data.get('term', '').strip()

        if not search_term:
            return jsonify({'error': 'Search term is required'}), 400

        try:
            from search import find_matches
            matches = find_matches([search_term])

            # Clean and format results
            results = []
            for match in matches:
                results.append({
                    'filename': match['article']['filename'],
                    'section': match['article']['section'],
                    'terms_matched': match['terms_matched'],
                    'snippets': [clean_html(snippet) for snippet in match['snippets'][:3]]
                })

            return jsonify({
                'results': results,
                'count': len(results),
                'search_term': search_term
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'Method not allowed'}), 405

def get_emails():
    """Get all registered emails."""
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM emails ORDER BY email')
    emails = [row[0] for row in cursor.fetchall()]
    conn.close()
    return emails

def get_search_terms(email):
    """Get search terms for a specific email."""
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT term FROM search_terms
        WHERE email = ?
        ORDER BY term
    ''', (email.lower(),))
    terms = [row[0] for row in cursor.fetchall()]
    conn.close()
    return terms

def add_search_term(email, term):
    """Add a search term for an email."""
    try:
        conn = sqlite3.connect('emails.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO search_terms (email, term)
            VALUES (?, ?)
        ''', (email.lower(), term.strip()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return False

def remove_search_term(email, term):
    """Remove a search term for an email."""
    conn = sqlite3.connect('emails.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM search_terms
        WHERE email = ? AND term = ?
    ''', (email.lower(), term.strip()))
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
            --primary-color: #0ea5e9;
            --primary-hover: #0284c7;
            --secondary-color: #6b7280;
            --success-color: #059669;
            --error-color: #dc2626;
            --warning-color: #d97706;
            --background: #ffffff;
            --card-bg: #ffffff;
            --text-primary: #111827;
            --text-secondary: #6b7280;
            --border: #f3f4f6;
            --border-light: #f9fafb;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --shadow-hover: 0 10px 20px -5px rgba(0, 0, 0, 0.12), 0 4px 8px -2px rgba(0, 0, 0, 0.08);
            --radius: 12px;
            --radius-sm: 6px;
            --transition: all 0.2s ease-in-out;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #fafafa;
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
            grid-template-columns: 1fr 1fr 1fr;
            gap: 25px;
            max-width: 1400px;
            margin: 0 auto;
            align-items: start;
        }

        .card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            padding: 32px;
            transition: var(--transition);
            border: 1px solid var(--border);
        }

        .card:hover {
            box-shadow: var(--shadow-lg);
            transform: translateY(-3px);
        }

        .card h2 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--text-primary);
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
            padding: 14px 18px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 1rem;
            transition: var(--transition);
            background: var(--background);
            box-shadow: var(--shadow-sm);
        }

        input[type="email"]:focus, input[type="text"]:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1), var(--shadow);
        }

        button {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 14px 24px;
            border-radius: var(--radius);
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            width: 100%;
            margin-top: 10px;
            box-shadow: var(--shadow-sm);
        }

        button:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        button:active {
            transform: translateY(0);
            box-shadow: var(--shadow-sm);
        }

        .message {
            padding: 15px;
            border-radius: var(--radius);
            margin-bottom: 20px;
            font-weight: 500;
        }

        .message.success {
            background: rgba(5, 150, 105, 0.1);
            color: var(--success-color);
            border: 1px solid rgba(5, 150, 105, 0.2);
        }

        .message.error {
            background: rgba(220, 38, 38, 0.1);
            color: var(--error-color);
            border: 1px solid rgba(220, 38, 38, 0.2);
        }

        .email-list ul {
            list-style: none;
            padding: 0;
        }

        .email-list li {
            background: var(--background);
            padding: 14px 18px;
            margin-bottom: 8px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: var(--transition);
            box-shadow: var(--shadow-sm);
        }

        .email-list li:hover {
            background: var(--border-light);
            box-shadow: var(--shadow);
        }

        .result-item {
            background: var(--background);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            margin-bottom: 20px;
            transition: var(--transition);
            box-shadow: var(--shadow-sm);
        }

        .result-item:hover {
            box-shadow: var(--shadow-md);
            transform: translateY(-1px);
        }

        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
                gap: 25px;
            }

            .card {
                margin-bottom: 20px;
            }
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
    </style>
</head>
<body>
    <div class="header">
        <h1>DOU Notifier</h1>
        <p>Sistema completo para monitoramento do Diário Oficial da União</p>
    </div>

    {% if message %}
        <div class="message {{ 'success' if 'sucesso' in message else 'error' }}">
            {{ message }}
        </div>
    {% endif %}

    <div class="container">
        <!-- Primeira coluna: Buscar no DOU -->
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
            </form>

            {% if results %}
                <div class="results" style="margin-top: 30px;">
                    <h3>📋 Resultados da Busca ({{ results|length }})</h3>
                    {% for result in results %}
                        <div class="result-item">
                            <h4>{{ result.article.filename }} ({{ result.article.section }})</h4>
                            <p><strong>Termos encontrados:</strong> {{ result.terms_matched|join(', ') }}</p>
                            {% if result.snippets %}
                                <div style="margin-top: 10px;">
                                    <strong>Trechos relevantes:</strong>
                                    {% for snippet in result.snippets[:2] %}
                                        <div style="margin: 5px 0; padding: 10px; background: var(--border-light); border-radius: var(--radius-sm);">{{ snippet }}</div>
                                    {% endfor %}
                                </div>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>

        <!-- Segunda coluna: Gerenciar Emails -->
        <div class="card">
            <h2>📧 Gerenciar Emails</h2>
            <form method="post">
                <div class="form-group">
                    <label for="email_add">Cadastrar novo email</label>
                    <input type="email" id="email_add" name="email" placeholder="Digite o email" required>
                </div>
                <button type="submit" name="action" value="add_email">Cadastrar</button>
            </form>

            <form method="post" style="margin-top: 20px;">
                <div class="form-group">
                    <label for="email_remove">Remover email</label>
                    <input type="email" id="email_remove" name="email" placeholder="Digite o email para remover" required>
                </div>
                <button type="submit" name="action" value="remove_email" style="background: var(--error-color);">Remover</button>
            </form>

            <div class="email-list" style="margin-top: 30px;">
                <h3>Emails Cadastrados</h3>
                {% if emails %}
                    <ul>
                        {% for email in emails %}
                            <li>
                                <span>{{ email }}</span>
                                <form method="post" style="display: inline; margin: 0;">
                                    <input type="hidden" name="email" value="{{ email }}">
                                    <button type="submit" name="action" value="remove_email" style="background: var(--error-color); width: auto; margin: 0; padding: 5px 10px; font-size: 0.8rem;">❌</button>
                                </form>
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <p style="color: var(--text-secondary); font-style: italic;">Nenhum email cadastrado.</p>
                {% endif %}
            </div>
        </div>

        <!-- Terceira coluna: Gerenciar Termos de Busca -->
        <div class="card">
            <h2>🔍 Termos de Busca</h2>

            {% if emails %}
                {% for email in emails %}
                    <div style="margin-bottom: 30px; padding: 15px; background: var(--border-light); border-radius: var(--radius); border: 1px solid var(--border);">
                        <h4 style="color: var(--primary-color); margin-bottom: 10px;">{{ email }}</h4>

                        <!-- Lista de termos -->
                        {% if email_terms[email] %}
                            <div style="margin-bottom: 15px;">
                                {% for term in email_terms[email] %}
                                    <span style="display: inline-block; background: var(--primary-color); color: white; padding: 4px 8px; border-radius: var(--radius-sm); font-size: 0.8rem; margin: 2px 4px 2px 0;">
                                        {{ term }}
                                        <form method="post" style="display: inline; margin: 0;">
                                            <input type="hidden" name="email" value="{{ email }}">
                                            <input type="hidden" name="term" value="{{ term }}">
                                            <button type="submit" name="action" value="remove_term" style="background: none; border: none; color: white; margin-left: 5px; font-size: 0.8rem; cursor: pointer;">×</button>
                                        </form>
                                    </span>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 15px;">Nenhum termo cadastrado.</p>
                        {% endif %}

                        <!-- Formulário para adicionar termo -->
                        <form method="post" style="display: flex; gap: 5px;">
                            <input type="hidden" name="email" value="{{ email }}">
                            <input type="text" name="term" placeholder="Novo termo" style="flex: 1; padding: 8px; font-size: 0.9rem;" required>
                            <button type="submit" name="action" value="add_term" style="background: var(--success-color); width: auto; padding: 8px 12px; font-size: 0.9rem; margin: 0;">+</button>
                        </form>
                    </div>
                {% endfor %}
            {% else %}
                <p style="color: var(--text-secondary); font-style: italic;">Cadastre emails para gerenciar termos de busca.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)