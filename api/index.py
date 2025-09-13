from flask import Flask, request, render_template_string
import os
import re
import requests
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date
from pathlib import Path
import tempfile
import io

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

# INLABS credentials
INLABS_EMAIL = os.getenv('INLABS_EMAIL', 'educmaia@gmail.com')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD', 'maia2807')

# DOU sections
DEFAULT_SECTIONS = "DO1 DO1E"
URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

def clean_html(text):
    """Remove HTML tags from text for better readability."""
    if not text:
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def create_inlabs_session():
    """Create and login to INLABS session."""
    print(f"[DEBUG] Attempting login with email: {INLABS_EMAIL}")
    payload = {"email": INLABS_EMAIL, "password": INLABS_PASSWORD}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    session = requests.Session()
    try:
        print(f"[DEBUG] Making POST request to: {URL_LOGIN}")
        response = session.post(URL_LOGIN, data=payload, headers=headers, timeout=30)
        print(f"[DEBUG] Login response status: {response.status_code}")
        print(f"[DEBUG] Response cookies: {dict(session.cookies)}")

        if session.cookies.get('inlabs_session_cookie'):
            print("[DEBUG] INLABS login successful.")
            return session
        else:
            print(f"[DEBUG] Login failed. Response content: {response.text[:200]}...")
            raise ValueError("Login failed: No session cookie obtained.")
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        import traceback
        print(f"[ERROR] Login traceback: {traceback.format_exc()}")
        raise

def download_dou_xml_vercel(sections=None):
    """Download DOU XML ZIPs for today - Vercel version."""
    if sections is None:
        sections = DEFAULT_SECTIONS

    try:
        session = create_inlabs_session()
        cookie = session.cookies.get('inlabs_session_cookie')
        if not cookie:
            raise ValueError("No cookie after login.")

        today = date.today()
        ano = today.strftime("%Y")
        mes = today.strftime("%m")
        dia = today.strftime("%d")
        data_completa = f"{ano}-{mes}-{dia}"

        downloaded_data = {}

        for dou_secao in sections.split():
            print(f"Downloading {data_completa}-{dou_secao}.zip...")
            url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"
            cabecalho_arquivo = {
                'Cookie': f'inlabs_session_cookie={cookie}',
                'origem': '736372697074'
            }
            response = session.get(url_arquivo, headers=cabecalho_arquivo)

            if response.status_code == 200:
                print(f"[DEBUG] Response for {dou_secao}: {response.status_code}, Content-Length: {len(response.content)}")
                print(f"[DEBUG] Content-Type: {response.headers.get('content-type', 'unknown')}")
                print(f"[DEBUG] First 50 bytes: {response.content[:50]}")

                # Check if it's actually a ZIP file
                if len(response.content) > 4:
                    zip_signature = response.content[:4]
                    if zip_signature == b'PK\x03\x04' or zip_signature == b'PK\x05\x06' or zip_signature == b'PK\x07\x08':
                        downloaded_data[dou_secao] = response.content
                        print(f"[DEBUG] Downloaded valid ZIP: {data_completa}-{dou_secao}.zip")
                    else:
                        print(f"[ERROR] Downloaded content for {dou_secao} is not a valid ZIP file. Signature: {zip_signature}")
                        # Save first 500 chars to debug
                        try:
                            content_preview = response.content[:500].decode('utf-8', errors='ignore')
                            print(f"[DEBUG] Content preview: {content_preview}")
                        except:
                            print(f"[DEBUG] Cannot decode content as text")
                else:
                    print(f"[ERROR] Downloaded content for {dou_secao} is too small: {len(response.content)} bytes")
            elif response.status_code == 404:
                print(f"[DEBUG] Not found: {data_completa}-{dou_secao}.zip")
            else:
                print(f"[ERROR] Error downloading {dou_secao}: status {response.status_code}")
                print(f"[ERROR] Response content: {response.content[:200]}")

        session.close()
        return downloaded_data
    except Exception as e:
        print(f"Error in download_dou_xml_vercel: {e}")
        if 'session' in locals():
            session.close()
        raise

def extract_articles_vercel(zip_data):
    """Extract articles from ZIP data - Vercel version."""
    articles = []

    try:
        print(f"[DEBUG] Starting extraction from {len(zip_data)} zip files")
        for section, zip_bytes in zip_data.items():
            print(f"[DEBUG] Processing section: {section}, ZIP size: {len(zip_bytes)} bytes")

            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
                    all_files = zip_ref.namelist()
                    print(f"[DEBUG] All files in {section}: {all_files}")

                    xml_files = [f for f in all_files if f.endswith('.xml')]
                    print(f"[DEBUG] Found {len(xml_files)} XML files in {section}: {xml_files}")

                    if not xml_files:
                        # Check if ZIP is valid and what it contains
                        print(f"[DEBUG] No XML files found. All files: {all_files}")
                        # Try to read first few bytes to check content
                        if all_files:
                            first_file = all_files[0]
                            try:
                                content = zip_ref.read(first_file)[:200]
                                print(f"[DEBUG] First file {first_file} content preview: {content}")
                            except Exception as e:
                                print(f"[DEBUG] Error reading first file: {e}")

                    for xml_filename in xml_files:
                        try:
                            print(f"[DEBUG] Processing XML file: {xml_filename}")
                            xml_content = zip_ref.read(xml_filename)
                            print(f"[DEBUG] XML content size: {len(xml_content)} bytes")

                            root = ET.fromstring(xml_content)
                            print(f"[DEBUG] XML root tag: {root.tag}")

                            # Extract artCategory
                            art_category_elem = root.find('.//*[@artCategory]')
                            art_category_text = art_category_elem.get('artCategory', 'N/A') if art_category_elem is not None else "N/A"

                            # Extract text from article tags
                            text_parts = []
                            for article in root.findall('.//article'):
                                article_text = ET.tostring(article, encoding='unicode', method='text').strip()
                                if article_text:
                                    text_parts.append(article_text)

                            print(f"[DEBUG] Found {len(text_parts)} articles in {xml_filename}")

                            full_text = ' '.join(text_parts).strip()
                            if full_text:
                                articles.append({
                                    'section': section,
                                    'filename': xml_filename,
                                    'text': full_text,
                                    'xml_path': f"#xml-{section}-{xml_filename}",
                                    'artCategory': art_category_text
                                })
                                print(f"[DEBUG] Successfully extracted text from {xml_filename} ({len(text_parts)} articles, {len(full_text)} chars)")
                            else:
                                print(f"[DEBUG] No text extracted from {xml_filename}")

                        except ET.ParseError as e:
                            print(f"[ERROR] XML parsing error in {xml_filename}: {e}")
                        except Exception as e:
                            print(f"[ERROR] Error processing {xml_filename}: {e}")
                            import traceback
                            print(f"[ERROR] Traceback: {traceback.format_exc()}")

            except zipfile.BadZipFile as e:
                print(f"[ERROR] Bad ZIP file for section {section}: {e}")
            except Exception as e:
                print(f"[ERROR] Error opening ZIP for section {section}: {e}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")

    except Exception as e:
        print(f"[ERROR] Error in extract_articles_vercel: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise

    print(f"[DEBUG] Extraction completed. Total articles: {len(articles)}")
    return articles

def find_matches_vercel(search_terms):
    """Find matches in DOU - Vercel version with statistics."""
    if not search_terms:
        return [], {}

    stats = {
        'sections_downloaded': 0,
        'zip_files_downloaded': 0,
        'xml_files_processed': 0,
        'total_articles_extracted': 0,
        'articles_searched': 0,
        'matches_found': 0,
        'download_time': 0,
        'extraction_time': 0,
        'search_time': 0
    }

    try:
        import time

        # Download today's XML ZIPs
        start_time = time.time()
        print("Starting download for today's DOU XMLs.")
        zip_data = download_dou_xml_vercel()
        stats['download_time'] = round(time.time() - start_time, 2)

        if not zip_data:
            print("No files downloaded today.")
            return [], stats

        stats['sections_downloaded'] = len(zip_data)
        stats['zip_files_downloaded'] = len(zip_data)

        # Extract articles
        start_time = time.time()
        print("Starting extraction of articles.")
        articles = extract_articles_vercel(zip_data)
        stats['extraction_time'] = round(time.time() - start_time, 2)

        if not articles:
            print("No articles extracted.")
            return [], stats

        stats['total_articles_extracted'] = len(articles)
        stats['articles_searched'] = len(articles)

        # Count XML files processed
        for section, zip_bytes in zip_data.items():
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
                    xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
                    stats['xml_files_processed'] += len(xml_files)
            except:
                pass

        # Search
        start_time = time.time()
        print(f"Searching {len(articles)} articles for terms.")
        matches = []

        for article in articles:
            text_lower = article['text'].lower()
            matched_terms = []
            snippets = []

            for term in search_terms:
                if term.lower() in text_lower:
                    matched_terms.append(term)

                    # Find match positions and extract snippets (100 chars context)
                    positions = [m.start() for m in re.finditer(re.escape(term.lower()), text_lower)]
                    for pos in positions:
                        start = max(0, pos - 100)
                        end = min(len(article['text']), pos + len(term) + 100)
                        snippet = article['text'][start:end].strip()
                        if snippet not in snippets:  # Avoid duplicates
                            snippets.append(snippet)
                        if len(snippets) >= 3:  # Limit snippets
                            break

            if matched_terms:
                matches.append({
                    'article': article,
                    'terms_matched': matched_terms,
                    'snippets': snippets
                })
                print(f"Match found in {article['filename']} ({article['section']}): {matched_terms}")

        stats['search_time'] = round(time.time() - start_time, 2)
        stats['matches_found'] = len(matches)

        print(f"Search completed. Found {len(matches)} matching articles.")
        return matches, stats

    except Exception as e:
        print(f"Error in find_matches_vercel: {e}")
        return [], stats

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #fafafa;
            min-height: 100vh;
            padding: 20px;
            color: var(--text-primary);
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
            gap: 30px;
            max-width: 1400px;
            margin: 0 auto;
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

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 15px 0;
        }

        .stat-item {
            background: var(--background);
            padding: 12px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            text-align: center;
        }

        .stat-number {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            display: block;
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr 1fr;
                gap: 25px;
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

            .stats-grid {
                grid-template-columns: 1fr;
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
        <!-- PRIMEIRA COLUNA: ESTATÍSTICAS -->
        <div class="card">
            <h2>📊 Estatísticas da Busca</h2>

            <!-- Botão de Atualização -->
            <form method="post" style="margin-bottom: 20px;">
                <input type="hidden" name="action" value="refresh_cache">
                <button type="submit" style="background: var(--warning-color); width: 100%;">
                    🔄 Atualizar Cache DOU
                </button>
            </form>

            {% if search_stats %}
                {% if search_stats.get('error') %}
                    <div style="padding: 15px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: var(--radius); color: var(--error-color); margin-bottom: 20px;">
                        <h4>🚨 Erro no Processamento</h4>
                        <p><strong>Erro:</strong> {{ search_stats.get('error', 'Unknown error') }}</p>
                        <details style="margin-top: 10px;">
                            <summary style="cursor: pointer; color: var(--primary-color);">Ver detalhes técnicos</summary>
                            <pre style="white-space: pre-wrap; font-size: 0.8rem; margin-top: 10px;">{{ search_stats.get('traceback', 'No traceback available') }}</pre>
                        </details>
                        <p style="margin-top: 10px;"><a href="/debug" target="_blank" style="color: var(--primary-color);">🔧 Ir para página de debug</a></p>
                    </div>
                {% else %}
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-number">{{ search_stats.get('xml_files_processed', 0) }}</span>
                            <div class="stat-label">Arquivos XML<br>Processados</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">{{ search_stats.get('total_articles_extracted', 0) }}</span>
                            <div class="stat-label">Artigos<br>Extraídos</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">{{ search_stats.get('sections_downloaded', 0) }}</span>
                            <div class="stat-label">Seções DOU<br>Baixadas</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">{{ search_stats.get('matches_found', 0) }}</span>
                            <div class="stat-label">Matches<br>Encontrados</div>
                        </div>
                    </div>

                    <div style="margin-top: 20px; padding: 15px; background: var(--background); border-radius: var(--radius); border: 1px solid var(--border);">
                        <h4>⏱️ Tempo de Processamento</h4>
                        <ul style="margin: 10px 0; padding-left: 20px; color: var(--text-secondary); font-size: 0.9rem;">
                            <li>Download: {{ search_stats.get('download_time', 0) }}s</li>
                            <li>Extração: {{ search_stats.get('extraction_time', 0) }}s</li>
                            <li>Busca: {{ search_stats.get('search_time', 0) }}s</li>
                            <li><strong>Total: {{ (search_stats.get('download_time', 0) + search_stats.get('extraction_time', 0) + search_stats.get('search_time', 0))|round(2) }}s</strong></li>
                        </ul>
                    </div>
                {% endif %}
            {% else %}
                <div style="text-align: center; color: var(--text-secondary); font-style: italic; padding: 40px;">
                    📊 Faça uma busca para ver as estatísticas de processamento
                </div>
            {% endif %}
        </div>

        <!-- SEGUNDA COLUNA: BUSCAR NO DOU -->
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

        <!-- TERCEIRA COLUNA: EMAILS -->

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
                        # Perform real search with the provided term
                        print(f"[DEBUG] Starting search for term: {search_term}")
                        matches, search_stats = find_matches_vercel([search_term])
                        print(f"[DEBUG] Search completed. Matches: {len(matches) if matches else 0}, Stats: {search_stats}")

                        if matches:
                            # Clean HTML from summaries and snippets
                            for result in matches:
                                if 'snippets' in result and result['snippets']:
                                    result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]
                                # Add summary
                                result['summary'] = f'Documento oficial que trata sobre {search_term}, estabelecendo diretrizes e procedimentos relacionados ao tema.'

                            search_results = matches
                            message = f"Encontrados {len(matches)} artigos reais para '{search_term}' em {search_stats.get('xml_files_processed', 0)} arquivos XML processados."
                        else:
                            if search_stats.get('xml_files_processed', 0) > 0:
                                message = f"Nenhum artigo encontrado para o termo '{search_term}' (Processados {search_stats.get('xml_files_processed', 0)} arquivos XML)."
                            else:
                                message = f"Nenhum artigo encontrado para o termo '{search_term}'. Debug: {search_stats}"
                    except Exception as e:
                        print(f"[ERROR] Search failed: {str(e)}")
                        import traceback
                        print(f"[ERROR] Traceback: {traceback.format_exc()}")
                        message = f"Erro na busca: {str(e)}"
                        search_stats = {'error': str(e), 'traceback': traceback.format_exc()}
                        # Fallback to demo if real search fails
                        try:
                            matches = search_dou_demo(search_term)
                            if matches:
                                search_results = matches
                                message += f" (Mostrando dados de demonstração - {len(matches)} artigos)"
                        except:
                            pass
            
            elif 'action' in request.form and request.form.get('action') == 'refresh_cache':
                # Handle cache refresh
                try:
                    print("[DEBUG] Refreshing cache - downloading fresh DOU data")
                    matches, search_stats = find_matches_vercel(['teste'])  # Use a dummy term to trigger download
                    message = f"Cache atualizado! Processados {search_stats.get('xml_files_processed', 0)} arquivos XML em {search_stats.get('download_time', 0):.2f}s"
                except Exception as e:
                    print(f"[ERROR] Cache refresh failed: {e}")
                    message = f"Erro ao atualizar cache: {str(e)}"
                    search_stats = {'error': str(e)}

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
                                    emails=list(current_emails),
                                    search_stats=search_stats if 'search_stats' in locals() else {})
    
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

@app.route('/debug')
def debug():
    """Debug endpoint to test individual functions."""
    try:
        debug_info = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "environment_vars": {
                "INLABS_EMAIL": INLABS_EMAIL,
                "INLABS_PASSWORD": "***" if INLABS_PASSWORD else "NOT SET",
                "URL_LOGIN": URL_LOGIN,
                "URL_DOWNLOAD": URL_DOWNLOAD,
                "DEFAULT_SECTIONS": DEFAULT_SECTIONS
            }
        }

        # Test search function with a simple term
        try:
            print("[DEBUG] Testing search function...")
            matches, stats = find_matches_vercel(['teste'])
            debug_info['test_search'] = {
                "matches": len(matches) if matches else 0,
                "stats": stats,
                "success": True
            }
        except Exception as e:
            debug_info['test_search'] = {
                "error": str(e),
                "success": False
            }

        return debug_info
    except Exception as e:
        return {"error": str(e), "success": False}, 500

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