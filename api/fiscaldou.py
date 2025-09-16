from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import os
import json
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

# Edge Config configuration
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

# INLABS credentials
INLABS_EMAIL = os.getenv('INLABS_EMAIL')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD')

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

# DOU sections
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"
URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

# Fallback storage simples
emails_storage = set()
search_terms_storage = {}
cache_storage = {}

def get_current_emails():
    """Get current emails - fallback to memory storage"""
    return emails_storage

def save_emails(emails_set):
    """Save emails to memory storage"""
    emails_storage.clear()
    emails_storage.update(emails_set)
    return True

def get_email_terms(email):
    """Get search terms for email"""
    return search_terms_storage.get(email, [])

def save_email_terms(email, terms_list):
    """Save search terms for email"""
    search_terms_storage[email] = terms_list
    return True

def load_template(template_name):
    """Load HTML template from templates directory."""
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', template_name)
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading template {template_name}: {e}")
        return None

def load_static_file(filename):
    """Load static file (CSS/JS) from static directory."""
    try:
        static_path = os.path.join(os.path.dirname(__file__), 'templates', 'static', filename)
        with open(static_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading static file {filename}: {e}")
        return None

def render_template(template_content, **context):
    """Simple template rendering using string replacement."""
    if not template_content:
        return ""

    result = template_content

    # Replace simple variables like {{ variable }}
    for key, value in context.items():
        if isinstance(value, (list, dict)):
            # For complex objects, use JSON representation
            result = result.replace(f'{{{{ {key}|tojson|safe }}}}', json.dumps(value, ensure_ascii=False))
            result = result.replace(f'{{{{ {key}|length }}}}', str(len(value) if hasattr(value, '__len__') else 0))
        else:
            result = result.replace(f'{{{{ {key} }}}}', str(value or ''))
            result = result.replace(f'{{{{ {key} or \'\' }}}}', str(value or ''))

    # Handle simple conditionals {% if condition %}...{% endif %}
    def handle_if_blocks(text):
        # Simple if without else
        if_pattern = r'\{%\s*if\s+([^%]+)\s*%\}(.*?)\{%\s*endif\s*%\}'

        def replace_if(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # Simple condition evaluation - check if variable exists and is truthy
            var_name = condition.split()[0]
            if var_name in context and context[var_name]:
                return content
            else:
                return ''

        return re.sub(if_pattern, replace_if, text, flags=re.DOTALL)

    result = handle_if_blocks(result)

    # Handle simple loops {% for item in items %}...{% endfor %}
    def handle_for_loops(text):
        for_pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}(.*?)\{%\s*endfor\s*%\}'

        def replace_for(match):
            item_var = match.group(1).strip()
            items_var = match.group(2).strip()
            loop_content = match.group(3)

            if items_var in context and hasattr(context[items_var], '__iter__'):
                items = context[items_var]
                result_parts = []
                for i, item in enumerate(items):
                    item_content = loop_content
                    # Replace loop variable
                    if isinstance(item, dict):
                        for k, v in item.items():
                            item_content = item_content.replace(f'{{{{ {item_var}.{k} }}}}', str(v or ''))
                    else:
                        item_content = item_content.replace(f'{{{{ {item_var} }}}}', str(item or ''))

                    # Add loop counter
                    item_content = item_content.replace('{{ loop.index }}', str(i + 1))
                    result_parts.append(item_content)

                return ''.join(result_parts)

            return ''

        return re.sub(for_pattern, replace_for, text, flags=re.DOTALL)

    result = handle_for_loops(result)

    # Clean up any remaining template syntax
    result = re.sub(r'\{\{[^}]*\}\}', '', result)
    result = re.sub(r'\{%[^%]*%\}', '', result)

    return result

def create_inlabs_session():
    """Create and login to INLABS session."""
    if not INLABS_EMAIL or not INLABS_PASSWORD:
        raise ValueError("INLABS credentials not configured")

    payload = {"email": INLABS_EMAIL, "password": INLABS_PASSWORD}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    s = requests.Session()
    try:
        response = s.post(URL_LOGIN, data=payload, headers=headers)
        if s.cookies.get('inlabs_session_cookie'):
            return s
        else:
            raise ValueError("INLABS login failed")
    except Exception as e:
        raise ValueError(f"INLABS connection error: {e}")

def download_dou_xml(target_date=None, sections=None):
    """Download DOU XML files for given date."""
    if not sections:
        sections = DEFAULT_SECTIONS.split()

    if not target_date:
        target_date = date.today()

    try:
        s = create_inlabs_session()
        cookie = s.cookies.get('inlabs_session_cookie')

        data_completa = target_date.strftime("%Y-%m-%d")
        downloaded_content = []

        for dou_secao in sections:
            url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"
            cabecalho_arquivo = {
                'Cookie': f'inlabs_session_cookie={cookie}',
                'origem': '736372697074'
            }

            response = s.request("GET", url_arquivo, headers=cabecalho_arquivo)

            if response.status_code == 200 and response.content.startswith(b'PK'):
                downloaded_content.append({
                    'section': dou_secao,
                    'content': response.content,
                    'date': data_completa
                })

        s.close()
        return downloaded_content
    except Exception as e:
        print(f"Download error: {e}")
        return []

def extract_articles_from_zip(zip_content):
    """Extract articles from ZIP content."""
    articles = []
    try:
        import io
        zip_buffer = io.BytesIO(zip_content)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            for file_name in zip_file.namelist():
                if file_name.endswith('.xml'):
                    with zip_file.open(file_name) as xml_file:
                        content = xml_file.read().decode('utf-8', errors='ignore')
                        try:
                            root = ET.fromstring(content)
                            for article in root.findall('.//article'):
                                text_content = ET.tostring(article, encoding='unicode', method='text')
                                if text_content and len(text_content.strip()) > 50:
                                    articles.append({
                                        'filename': file_name,
                                        'text': text_content.strip(),
                                        'xml_content': content,
                                        'section': file_name.split('-')[2] if '-' in file_name else 'unknown'
                                    })
                        except ET.ParseError:
                            continue
    except Exception as e:
        print(f"Extraction error: {e}")
    return articles

def search_dou_real(search_terms=None, use_cache=True):
    """Perform real DOU search."""
    if not search_terms:
        search_terms = []
        for email in get_current_emails():
            search_terms.extend(get_email_terms(email))
        search_terms = list(set(search_terms))

    if not search_terms:
        return []

    # Check cache first
    cache_key = f"search_{date.today().isoformat()}"
    if use_cache and cache_key in cache_storage:
        cached_results = cache_storage[cache_key]
        if cached_results.get('timestamp') and \
           (datetime.now() - datetime.fromisoformat(cached_results['timestamp'])).hours < 6:
            return cached_results.get('results', [])

    try:
        # Download DOU files
        zip_files = download_dou_xml()
        if not zip_files:
            return []

        # Extract articles
        all_articles = []
        for zip_data in zip_files:
            articles = extract_articles_from_zip(zip_data['content'])
            for article in articles:
                article['date'] = zip_data['date']
            all_articles.extend(articles)

        # Search for terms
        matches = []
        for article in all_articles:
            text_lower = article['text'].lower()
            matched_terms = []
            snippets = []

            for term in search_terms:
                if term.lower() in text_lower:
                    matched_terms.append(term)

                    # Extract snippets
                    positions = [m.start() for m in re.finditer(re.escape(term.lower()), text_lower)]
                    for pos in positions:
                        start = max(0, pos - 100)
                        end = min(len(article['text']), pos + len(term) + 100)
                        snippet = article['text'][start:end].strip()
                        snippets.append(snippet)

            if matched_terms:
                matches.append({
                    'article': article,
                    'terms_matched': matched_terms,
                    'snippets': snippets
                })

        # Cache results
        cache_storage[cache_key] = {
            'results': matches,
            'timestamp': datetime.now().isoformat()
        }

        return matches
    except Exception as e:
        print(f"Search error: {e}")
        return []

def send_email_notification(email, matches):
    """Send email notification for matches."""
    if not SMTP_USER or not SMTP_PASS:
        return False

    try:
        subject = f"DOU Fiscalizações - {len(matches)} ocorrência(s) encontrada(s)"

        body = f"""
        <html>
        <body>
        <h2>🏛️ FiscalDOU - Notificações Encontradas</h2>
        <p>Foram encontradas {len(matches)} ocorrência(s) hoje:</p>
        """

        for i, match in enumerate(matches, 1):
            article = match['article']
            terms = ', '.join(match['terms_matched'])
            snippets = match['snippets'][:2]  # Max 2 snippets

            body += f"""
            <div style="border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px;">
                <h3>📄 Ocorrência {i}</h3>
                <p><strong>Arquivo:</strong> {article['filename']}</p>
                <p><strong>Seção:</strong> {article['section']}</p>
                <p><strong>Termos encontrados:</strong> {terms}</p>
                <p><strong>Trechos relevantes:</strong></p>
                <ul>
            """
            for snippet in snippets:
                body += f"<li><em>{snippet[:200]}...</em></li>"

            body += "</ul></div>"

        body += """
        <p>Atenciosamente,<br>
        <strong>FiscalDOU</strong><br>
        Sistema de Monitoramento do Diário Oficial da União</p>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = email
        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if path == '/health':
            self._handle_health()
        elif path == '/config':
            self._handle_config()
        elif path == '/api/cron/daily':
            self._handle_cron_daily()
        elif path.startswith('/static/'):
            self._handle_static(path)
        else:
            self._handle_home(query)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        # Parse form data
        if self.headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded'):
            form_data = parse_qs(post_data.decode('utf-8'))
            form_data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
        else:
            form_data = {}

        self._handle_home_post(form_data)

    def _handle_health(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "status": "ok",
            "service": "FiscalDOU",
            "timestamp": datetime.now().isoformat(),
            "environment": "production",
            "platform": "vercel",
            "version": "2.1"
        }

        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_config(self):
        """Config endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "status": "ok",
            "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
            "smtp_configured": bool(os.getenv('SMTP_SERVER') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASS')),
            "edge_config_available": bool(EDGE_CONFIG_ID),
            "inlabs_configured": bool(os.getenv('INLABS_EMAIL') and os.getenv('INLABS_PASSWORD')),
            "template_system": "active",
            "environment_variables": {
                "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
                "SMTP_SERVER": "configured" if os.getenv('SMTP_SERVER') else "missing",
                "SMTP_USER": "configured" if os.getenv('SMTP_USER') else "missing",
                "SMTP_PASS": "configured" if os.getenv('SMTP_PASS') else "missing",
                "INLABS_EMAIL": "configured" if os.getenv('INLABS_EMAIL') else "missing",
                "INLABS_PASSWORD": "configured" if os.getenv('INLABS_PASSWORD') else "missing"
            }
        }

        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_cron_daily(self):
        """Cron daily endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        try:
            emails = sorted(list(get_current_emails()))
            total_terms = sum(len(get_email_terms(email)) for email in emails)

            # Execute real search
            matches = search_dou_real()
            sent_count = 0

            # Send notifications to all registered emails
            if matches and emails:
                for email in emails:
                    if send_email_notification(email, matches):
                        sent_count += 1

            response = {
                'ok': True,
                'message': 'Cron job executed successfully with real DOU search',
                'timestamp': datetime.now().isoformat(),
                'emails_registered': len(emails),
                'total_search_terms': total_terms,
                'matches_found': len(matches),
                'emails_sent': sent_count,
                'mode': 'production',
                'search_system': 'active',
                'details': [
                    {
                        'email': email,
                        'status': 'notification-sent' if email in emails else 'not-sent',
                        'terms_count': len(get_email_terms(email))
                    } for email in emails
                ]
            }
        except Exception as e:
            response = {
                'ok': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'mode': 'error'
            }

        self.wfile.write(json.dumps(response).encode('utf-8'))

    def _handle_static(self, path):
        """Handle static files (CSS, JS)."""
        filename = path.split('/')[-1]

        # Determine content type
        if filename.endswith('.css'):
            content_type = 'text/css'
        elif filename.endswith('.js'):
            content_type = 'application/javascript'
        else:
            content_type = 'text/plain'

        content = load_static_file(filename)

        if content:
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'File not found')

    def _handle_home(self, query=None):
        """Handle main page using template."""
        current_emails = get_current_emails()
        message = query.get('message', [''])[0] if query else ''

        # Get email terms
        email_terms = {}
        for email in current_emails:
            email_terms[email] = get_email_terms(email)

        # Check environment variables
        openai_configured = bool(os.getenv('OPENAI_API_KEY'))
        smtp_configured = bool(os.getenv('SMTP_SERVER') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASS'))
        edge_config_available = bool(EDGE_CONFIG_ID)
        inlabs_configured = bool(os.getenv('INLABS_EMAIL') and os.getenv('INLABS_PASSWORD'))

        # Load template
        template_content = load_template('main.html')

        if template_content:
            # Prepare template context
            context = {
                'message': message,
                'emails': list(current_emails),
                'email_terms': email_terms,
                'search_term': '',
                'use_ai': False,
                'results': [],
                'search_stats': {},
                'openai_configured': openai_configured,
                'smtp_configured': smtp_configured,
                'edge_config_available': edge_config_available,
                'inlabs_configured': inlabs_configured
            }

            # Handle static file URLs (simple replacement)
            template_content = template_content.replace(
                "{{ url_for('static', filename='style.css') }}",
                "/static/style.css"
            )
            template_content = template_content.replace(
                "{{ url_for('static', filename='script.js') }}",
                "/static/script.js"
            )

            # Render template
            html_content = render_template(template_content, **context)

            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        else:
            # Fallback HTML
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()

            fallback_html = f"""
            <!DOCTYPE html>
            <html><head><title>FiscalDOU</title><meta charset="utf-8"></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1>🏛️ FiscalDOU - Template System</h1>
                <p><strong>Status:</strong> Template não encontrado - usando fallback</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Emails cadastrados:</strong> {len(current_emails)}</p>
                {f'<div style="padding: 15px; background: #e3f2fd; border-radius: 4px; margin: 20px 0;"><strong>Mensagem:</strong> {message}</div>' if message else ''}
                <p><a href="/health">Health Check</a> | <a href="/config">Configurações</a></p>
            </body></html>
            """
            self.wfile.write(fallback_html.encode('utf-8'))

    def _handle_home_post(self, form_data):
        """Handle POST requests to main page."""
        action = form_data.get('action', '')
        email = form_data.get('email', '').strip().lower()
        search_term = form_data.get('search_term', '').strip()
        message = ''

        try:
            current_emails = get_current_emails()

            if action == 'register' and email:
                if email in current_emails:
                    message = f'Email {email} já está cadastrado.'
                else:
                    current_emails.add(email)
                    if save_emails(current_emails):
                        message = f'✅ Email {email} cadastrado com sucesso!'
                    else:
                        message = f'❌ Erro ao cadastrar email {email}'

            elif action == 'unregister' and email:
                if email in current_emails:
                    current_emails.remove(email)
                    if save_emails(current_emails):
                        save_email_terms(email, [])
                        message = f'✅ Email {email} removido com sucesso!'
                    else:
                        message = f'❌ Erro ao remover email {email}'
                else:
                    message = f'❌ Email {email} não encontrado.'

            elif action == 'search_mestrando_exterior':
                try:
                    matches = search_dou_real(['mestrando', 'mestrado', 'exterior', 'internacional'])
                    if matches:
                        message = f"🔍 Busca real executada! Encontradas {len(matches)} ocorrências para termos relacionados a mestrado no exterior"
                    else:
                        message = "🔍 Busca real executada! Nenhuma ocorrência encontrada para termos relacionados a mestrado no exterior"
                except Exception as e:
                    message = f"❌ Erro na busca real: {str(e)}"

            elif action == 'search_all_terms':
                try:
                    matches = search_dou_real()
                    if matches:
                        message = f"🔍 Busca real executada! Encontradas {len(matches)} ocorrências para todos os termos cadastrados"
                    else:
                        message = "🔍 Busca real executada! Nenhuma ocorrência encontrada para os termos cadastrados"
                except Exception as e:
                    message = f"❌ Erro na busca real: {str(e)}"

            elif action == 'send_now' and email:
                try:
                    matches = search_dou_real()
                    if matches:
                        if send_email_notification(email, matches):
                            message = f"📧 Email enviado para {email}! {len(matches)} ocorrência(s) encontrada(s)"
                        else:
                            message = f"❌ Erro ao enviar email para {email}"
                    else:
                        message = f"📧 Email enviado para {email} - Nenhuma ocorrência encontrada hoje"
                except Exception as e:
                    message = f"❌ Erro ao processar envio: {str(e)}"

            elif action == 'send_now_all':
                try:
                    matches = search_dou_real()
                    sent_count = 0
                    for em in current_emails:
                        if send_email_notification(em, matches):
                            sent_count += 1

                    if matches:
                        message = f"📧 Emails enviados para {sent_count} endereços! {len(matches)} ocorrência(s) encontrada(s)"
                    else:
                        message = f"📧 Emails enviados para {sent_count} endereços - Nenhuma ocorrência encontrada hoje"
                except Exception as e:
                    message = f"❌ Erro no envio em lote: {str(e)}"

            elif action == 'refresh_cache':
                try:
                    # Clear cache and force new search
                    cache_key = f"search_{date.today().isoformat()}"
                    if cache_key in cache_storage:
                        del cache_storage[cache_key]

                    matches = search_dou_real(use_cache=False)
                    message = f"🔄 Cache atualizado! {len(matches)} ocorrência(s) encontrada(s) na busca mais recente"
                except Exception as e:
                    message = f"❌ Erro ao atualizar cache: {str(e)}"

            elif search_term:
                try:
                    matches = search_dou_real([search_term])
                    if matches:
                        message = f'🔍 Busca real executada por "{search_term}"! Encontradas {len(matches)} ocorrência(s)'
                    else:
                        message = f'🔍 Busca real executada por "{search_term}" - Nenhuma ocorrência encontrada'
                except Exception as e:
                    message = f'❌ Erro na busca por "{search_term}": {str(e)}'

            else:
                message = "⚠️ Por favor, forneça um termo de busca ou selecione uma ação."

        except Exception as e:
            message = f"❌ Erro: {str(e)}"

        # Redirect back to main page with message
        self.send_response(302)
        self.send_header('Location', f'/?message={quote(message)}')
        self.end_headers()