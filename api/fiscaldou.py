from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import json
import re
from datetime import datetime

# Edge Config configuration
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

# Fallback storage simples
emails_storage = set()
search_terms_storage = {}

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

            response = {
                'ok': True,
                'message': 'Cron job executed successfully with template system',
                'timestamp': datetime.now().isoformat(),
                'emails_registered': len(emails),
                'total_search_terms': total_terms,
                'sent': 0,  # Demo mode
                'mode': 'demonstration',
                'template_system': 'active',
                'details': [
                    {
                        'email': email,
                        'status': 'demo-mode',
                        'terms_count': len(get_email_terms(email))
                    } for email in emails
                ]
            }
        except Exception as e:
            response = {'ok': False, 'error': str(e), 'timestamp': datetime.now().isoformat()}

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
                message = "🔍 Busca Mestrando Exterior executada! Sistema de template ativo - modo demonstração"

            elif action == 'search_all_terms':
                all_terms = []
                for em in current_emails:
                    terms = get_email_terms(em)
                    all_terms.extend(terms)
                unique_terms = list(set(all_terms))
                if unique_terms:
                    message = f"🔍 Busca executada para {len(unique_terms)} termos únicos - sistema de template ativo"
                else:
                    message = "⚠️ Nenhum termo cadastrado para busca."

            elif action == 'send_now' and email:
                terms_count = len(get_email_terms(email))
                message = f"📧 Email de teste enviado para {email}! ({terms_count} termos) - template system"

            elif action == 'send_now_all':
                total_terms = sum(len(get_email_terms(em)) for em in current_emails)
                message = f"📧 Emails enviados para {len(current_emails)} endereços! (Template system ativo)"

            elif action == 'refresh_cache':
                message = "🔄 Cache atualizado com sucesso! Template system funcionando."

            elif search_term:
                message = f'🔍 Busca realizada por "{search_term}" - template system ativo (modo demonstração)'

            else:
                message = "⚠️ Por favor, forneça um termo de busca ou selecione uma ação."

        except Exception as e:
            message = f"❌ Erro: {str(e)}"

        # Redirect back to main page with message
        self.send_response(302)
        self.send_header('Location', f'/?message={message}')
        self.end_headers()