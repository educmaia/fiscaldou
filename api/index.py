from flask import Flask, request, render_template_string
import os
import re
import requests
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from pathlib import Path
import tempfile
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

def get_search_terms_from_edge_config(email):
    """Get search terms for a specific email from Edge Config"""
    terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
    terms = get_from_edge_config(terms_key)
    if terms and isinstance(terms, list):
        return terms
    return []

def save_search_terms_to_edge_config(email, terms_list):
    """Save search terms for a specific email to Edge Config"""
    terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
    return set_edge_config_item(terms_key, terms_list)

def add_search_term_to_edge_config(email, term):
    """Add a search term for an email in Edge Config"""
    current_terms = get_search_terms_from_edge_config(email)
    if term not in current_terms:
        current_terms.append(term)
        return save_search_terms_to_edge_config(email, current_terms)
    return False

def remove_search_term_from_edge_config(email, term):
    """Remove a search term for an email in Edge Config"""
    current_terms = get_search_terms_from_edge_config(email)
    if term in current_terms:
        current_terms.remove(term)
        return save_search_terms_to_edge_config(email, current_terms)
    return False

# Fallback storage (usado se Edge Config não estiver disponível)
emails_storage = set()
search_terms_storage = {}

# INLABS credentials
INLABS_EMAIL = os.getenv('INLABS_EMAIL', 'educmaia@gmail.com')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD', 'maia2807')

# DOU sections - Start with just DO1 to test
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"
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

def test_inlabs_connectivity():
    """Test basic connectivity to INLABS."""
    try:
        print("[DEBUG] Testing INLABS connectivity...")
        response = requests.get("https://inlabs.in.gov.br/", timeout=10)
        print(f"[DEBUG] INLABS homepage status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] INLABS connectivity test failed: {e}")
        return False

def create_inlabs_session():
    """Create and login to INLABS session."""
    # First test connectivity
    if not test_inlabs_connectivity():
        raise ValueError("Cannot connect to INLABS - network issue or site down")

    print(f"[DEBUG] Attempting login with email: {INLABS_EMAIL}")
    payload = {"email": INLABS_EMAIL, "password": INLABS_PASSWORD}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    session = requests.Session()
    try:
        print(f"[DEBUG] Making POST request to: {URL_LOGIN}")
        response = session.post(URL_LOGIN, data=payload, headers=headers, timeout=30)
        print(f"[DEBUG] Login response status: {response.status_code}")
        print(f"[DEBUG] Response headers: {dict(response.headers)}")
        print(f"[DEBUG] Response cookies: {dict(session.cookies)}")

        if session.cookies.get('inlabs_session_cookie'):
            print("[DEBUG] ✅ INLABS login successful.")

            # Test access to main interface after login
            print("[DEBUG] Testing access to main INLABS interface...")
            test_url = "https://inlabs.in.gov.br/index.php"
            test_response = session.get(test_url, timeout=30)
            print(f"[DEBUG] Main interface status: {test_response.status_code}")

            if "logout" in test_response.text.lower() or "sair" in test_response.text.lower():
                print("[DEBUG] ✅ Successfully logged into INLABS interface")
            else:
                print("[DEBUG] ⚠️ Warning: May not be properly logged in to INLABS interface")
                print(f"[DEBUG] Interface preview: {test_response.text[:300]}")

            return session
        else:
            print(f"[DEBUG] ❌ Login failed. Response content preview:")
            content_preview = response.text[:500]
            print(f"[DEBUG] {content_preview}")
            raise ValueError("Login failed: No session cookie obtained.")
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        import traceback
        print(f"[ERROR] Login traceback: {traceback.format_exc()}")
        raise

def is_valid_zip_content(content):
    """Check if content is a valid ZIP file by checking its signature."""
    try:
        if len(content) < 4:
            return False
        signature = content[:4]
        return signature.startswith(b'PK')
    except Exception:
        return False

def try_download_for_date_vercel(session, data_completa, sections):
    """
    Try to download DOU files for a specific date - Vercel version.

    Returns:
        dict: Successfully downloaded ZIP content by section, empty if none found.
    """
    downloaded_data = {}

    for dou_secao in sections.split():
        print(f"[DEBUG] Downloading {data_completa}-{dou_secao}.zip...")
        url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"

        # Use session directly for better cookie handling
        response = session.get(url_arquivo, timeout=60)

        if response.status_code == 200:
            # Check if content is actually a ZIP file
            if is_valid_zip_content(response.content):
                downloaded_data[dou_secao] = response.content
                print(f"[DEBUG] Downloaded valid ZIP: {data_completa}-{dou_secao}.zip ({len(response.content)} bytes)")
            else:
                print(f"[DEBUG] Downloaded content for {dou_secao} is NOT a valid ZIP (got HTML page)")
                # Don't save invalid files for this date
        elif response.status_code == 404:
            print(f"[DEBUG] Not found: {data_completa}-{dou_secao}.zip")
        else:
            print(f"[DEBUG] Error downloading {dou_secao}: status {response.status_code}")

    print(f"[DEBUG] Download attempt for {data_completa} completed. Valid files: {len(downloaded_data)}")
    return downloaded_data

def download_dou_xml_vercel(sections=None, max_fallback_days=2):
    """Download DOU XML ZIPs with fallback to previous days - Vercel version."""
    if sections is None:
        sections = DEFAULT_SECTIONS

    try:
        session = create_inlabs_session()
        cookie = session.cookies.get('inlabs_session_cookie')
        if not cookie:
            raise ValueError("No cookie after login.")

        # Determine starting date (today)
        target_date = date.today()

        # Try downloading for up to max_fallback_days
        for days_back in range(max_fallback_days + 1):
            current_date = target_date - timedelta(days=days_back)
            data_completa = current_date.strftime("%Y-%m-%d")
            data_formatada = current_date.strftime("%d/%m/%Y")

            if days_back == 0:
                print(f"[INFO] Verificando DOU de hoje ({data_formatada})...")
            else:
                print(f"[INFO] DOU de hoje não disponível. Verificando {days_back} dia(s) atrás ({data_formatada})...")

            downloaded_data = try_download_for_date_vercel(session, data_completa, sections)

            if downloaded_data:
                print(f"[SUCCESS] DOU encontrado para {data_formatada}! {len(downloaded_data)} arquivo(s) baixado(s).")
                session.close()
                return downloaded_data
            else:
                print(f"[WARNING] Nenhum DOU válido encontrado para {data_formatada}")

        print(f"[ERROR] Nenhum DOU válido encontrado após verificar {max_fallback_days + 1} dias.")
        session.close()
        return {}
    except Exception as e:
        print(f"[ERROR] Error in download_dou_xml_vercel: {e}")
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

# ----------------------
# Email helper (SMTP)
# ----------------------
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

def send_email_html(recipient, subject, html_body):
    if not (SMTP_SERVER and SMTP_PORT and SMTP_USER and SMTP_PASS):
        print("[ERROR] SMTP environment variables not fully configured.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = recipient
    msg.attach(MIMEText(html_body, 'html'))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.ehlo()
            try:
                server.starttls()
                server.ehlo()
            except Exception as e:
                print(f"[WARN] STARTTLS not available/failed: {e}")

        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipient, msg.as_string())
        server.quit()
        print(f"[INFO] Email sent to {recipient}")
        return True
    except Exception as e:
        print(f"[ERROR] Email send failed for {recipient}: {e}")
        try:
            server.quit()
        except Exception:
            pass
        return False

def format_email_body_html(email, date_str, matches):
    if not matches:
        return f"""
        <html><body>
        <h2>DOU Notificações - {date_str}</h2>
        <p>Olá {email},</p>
        <p>Nenhuma ocorrência encontrada hoje no DOU para os seus termos.</p>
        <p>Até breve,</p>
        </body></html>
        """

    parts = [
        f"<h2>DOU Notificações - {date_str}</h2>",
        f"<p>Olá {email},</p>",
        f"<p>Foram encontradas {len(matches)} ocorrência(s) hoje:</p>"
    ]
    for i, m in enumerate(matches, 1):
        art = m.get('article', {})
        terms = ', '.join(m.get('terms_matched', []))
        summary = m.get('summary') or ''
        parts.append(
            f"<div style='border:1px solid #ddd;border-radius:6px;padding:12px;margin:10px 0;'>"
            f"<h3>{i}. {art.get('filename','(sem nome)')} - {art.get('section','')}</h3>"
            f"<p><strong>Termos:</strong> {terms}</p>"
            f"<p><strong>Resumo:</strong><br>{summary}</p>"
            f"</div>"
        )
    parts.append("<p>Até breve,</p>")
    return f"<html><body>{''.join(parts)}</body></html>"

# ----------------------
# Cron route
# ----------------------
@app.route('/api/cron/daily', methods=['GET'])
def cron_daily():
    """
    Vercel Cron target. Fetch emails and terms from Edge Config,
    run search and summaries per email, and send notifications.
    """
    try:
        # Optional basic guard for non-cron calls
        # Vercel adds header 'x-vercel-cron' on cron invocations
        is_cron = request.headers.get('x-vercel-cron') is not None or request.args.get('force') == '1'

        emails = sorted(list(get_emails_from_edge_config()))
        if not emails:
            return ({
                'ok': True,
                'message': 'No emails registered in Edge Config',
                'sent': 0,
                'isCron': is_cron
            }, 200)

        # Aggregate stats
        date_str = date.today().strftime('%d/%m/%Y')
        total_sent = 0
        per_email = []

        # If any email has terms, run search once per unique term set? We run per email to respect per-user terms
        for email in emails:
            terms = get_search_terms_from_edge_config(email)
            if not terms:
                per_email.append({'email': email, 'status': 'no-terms', 'matches': 0})
                continue

            matches, stats = find_matches_vercel(terms)

            # Summaries (use AI if key configured; summarize.py falls back gracefully)
            try:
                from summarize import summarize_matches
                summarized = summarize_matches(matches)
            except Exception as e:
                print(f"[WARN] Summarization failed, sending without summaries: {e}")
                summarized = matches

            # Prepare and possibly send
            html = format_email_body_html(email, date_str, summarized)
            dry_run = request.args.get('dry') == '1'

            sent_ok = True if dry_run else send_email_html(email, f"DOU Notificações - {date_str}", html)
            if sent_ok:
                total_sent += 1 if not dry_run else 0
                per_email.append({'email': email, 'status': 'sent' if not dry_run else 'dry', 'matches': len(summarized), 'stats': stats})
            else:
                per_email.append({'email': email, 'status': 'send-failed', 'matches': len(summarized)})

        return ({
            'ok': True,
            'isCron': is_cron,
            'sent': total_sent,
            'details': per_email
        }, 200)
    except Exception as e:
        print(f"[ERROR] Cron execution failed: {e}")
        return ({'ok': False, 'error': str(e)}, 500)

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

        /* NOVA ESTRUTURA: 3 COLUNAS NO TOPO + RESULTADOS EMBAIXO */
        .top-section {
            display: flex !important;
            width: 100% !important;
            max-width: 1400px;
            margin: 0 auto 30px auto;
            padding: 0 20px;
            gap: 20px;
            align-items: flex-start;
        }

        .top-column {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 320px;
        }

        .top-column-1 {
            flex: 1 1 33.33%;
        }

        .top-column-2 {
            flex: 1 1 33.33%;
        }

        .top-column-3 {
            flex: 1 1 33.33%;
        }

        .divider {
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, transparent 0%, var(--primary-color) 50%, transparent 100%);
            margin: 40px 0;
            opacity: 0.3;
        }

        .bottom-section {
            width: 100%;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
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

        .message.info {
            background: rgba(14, 165, 233, 0.1);
            color: var(--primary-color);
            border: 1px solid rgba(14, 165, 233, 0.2);
        }

        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(14,165,233,0.3);
            border-top-color: var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
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
            position: relative;
        }

        .result-item:hover {
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
            border-color: var(--primary-color);
            background: linear-gradient(135deg, var(--background) 0%, rgba(59, 130, 246, 0.02) 100%);
        }

        .result-item:active {
            transform: translateY(0);
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

        /* Media queries para nova estrutura */
        @media (max-width: 1024px) {
            .top-section {
                gap: 15px;
                padding: 0 15px;
            }

            .bottom-section {
                padding: 0 15px;
            }

            .card {
                padding: 20px;
            }
        }

        /* Responsivo: empilhar colunas em telas pequenas */
        @media (max-width: 900px) {
            .top-section {
                flex-direction: column !important;
                gap: 20px;
            }

            .top-column {
                min-width: auto !important;
            }

            .top-column-1, .top-column-2, .top-column-3 {
                flex: 1 1 100% !important;
                width: 100% !important;
            }

            .header h1 {
                font-size: 1.8rem;
            }

            .card {
                padding: 20px;
            }

            .stats-grid {
                grid-template-columns: 1fr 1fr;
            }

            .divider {
                margin: 30px 0;
            }
        }

        /* Para telas muito pequenas */
        @media (max-width: 600px) {
            .top-section, .bottom-section {
                padding: 0 10px;
            }

            .card {
                padding: 15px;
            }

            .stats-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 1.6rem;
            }

            .divider {
                margin: 20px 0;
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
            backdrop-filter: blur(2px);
            animation: fadeIn 0.3s ease-out;
        }

        .modal-content {
            background-color: var(--card-bg);
            margin: 2% auto;
            padding: 0;
            border-radius: var(--radius);
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            animation: slideIn 0.3s ease-out;
        }

        .modal-header {
            background: var(--primary-color);
            color: white;
            padding: 20px;
            border-radius: var(--radius) var(--radius) 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h2 {
            margin: 0;
            font-size: 1.4rem;
        }

        .close {
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            line-height: 1;
            opacity: 0.7;
            transition: var(--transition);
        }

        .close:hover,
        .close:focus {
            opacity: 1;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }

        .modal-body {
            padding: 25px;
            line-height: 1.6;
            color: var(--text-primary);
        }

        .modal-footer {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }

        .btn-primary, .btn-secondary {
            padding: 10px 20px;
            border: none;
            border-radius: var(--radius);
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            font-size: 0.9rem;
        }

        .btn-primary {
            background: var(--primary-color);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: var(--background);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--card-bg);
            transform: translateY(-1px);
        }

        .result-detail {
            margin-bottom: 20px;
        }

        .result-detail h3 {
            color: var(--primary-color);
            margin-bottom: 10px;
            font-size: 1.1rem;
        }

        .result-detail .meta-info {
            background: var(--background);
            padding: 15px;
            border-radius: var(--radius);
            margin-bottom: 15px;
            font-size: 0.9rem;
        }

        .result-detail .content {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            font-family: 'Segoe UI', system-ui, sans-serif;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }

        .highlight {
            background: rgba(59, 130, 246, 0.2);
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: 600;
        }

        @keyframes slideIn {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        @media (max-width: 768px) {
            .modal-content {
                width: 95%;
                margin: 5% auto;
            }

            .modal-header {
                padding: 15px;
            }

            .modal-body {
                padding: 20px;
            }

            .modal-footer {
                padding: 15px;
                flex-direction: column;
            }

            .btn-primary, .btn-secondary {
                width: 100%;
                margin-bottom: 10px;
            }
        }
    </style>
    <script>
        // Dados dos resultados (será preenchido pelo template)
        let searchResults = {{ results|tojson|safe if results else '[]' }};
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

    <!-- SEÇÃO SUPERIOR: 3 COLUNAS LADO A LADO -->
    <div class="top-section">
        <!-- COLUNA 1: ESTATÍSTICAS DA BUSCA -->
        <div class="top-column top-column-1">
            <div class="card">
                <h2>📊 Estatísticas da Busca</h2>

                <!-- Botão de Atualização -->
                <form method="post" style="margin-bottom: 20px;" id="refreshCacheForm">
                    <input type="hidden" name="action" value="refresh_cache">
                    <button type="submit" style="background: var(--warning-color); width: 100%;" id="refreshCacheBtn">
                        🔄 Atualizar Cache DOU
                    </button>
                </form>
                <div id="refreshProcessing" class="message info" style="display:none; margin-top: 10px;"></div>

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
        </div>

        <!-- COLUNA 2: BUSCAR NO DOU -->
        <div class="top-column top-column-2">
            <div class="card">
                <h2>🔍 Buscar no DOU</h2>
                <form method="post" id="searchForm">
                    <div class="form-group">
                        <label for="search_term">Termo de busca</label>
                        <input type="text" id="search_term" name="search_term"
                               placeholder="Digite o termo de busca"
                               value="{{ search_term or '' }}" required>
                    </div>
                    <button type="submit" id="searchBtn">Buscar</button>
                </form>
                <div id="searchProcessing" class="message info" style="display:none; margin-top: 10px;"></div>

                <!-- Botão para buscar todas as sugestões -->
                <form method="post" style="margin-top: 15px;" id="searchSuggestionsForm">
                    <button type="submit" name="action" value="search_all_suggestions" style="background: var(--success-color); width: 100%;" id="searchSuggestionsBtn">
                        🔍 Buscar Todas as Sugestões
                    </button>
                </form>
                <div id="suggestionsProcessing" class="message info" style="display:none; margin-top: 10px;"></div>

                <div style="margin-top: 20px;">
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
                </div>
            </div>
        </div>

        <!-- COLUNA 3: GERENCIAR EMAILS -->
        <div class="top-column top-column-3">
            <div class="card">
                <h2>📧 Gerenciar Emails</h2>
                <!-- Enviar para todos agora -->
                <form method="post" style="margin-bottom: 15px;" id="sendAllNowForm">
                    <button type="submit" id="sendAllNowBtn" name="action" value="send_now_all" style="background: var(--success-color); width: 100%;">
                        ▶️ Enviar teste para todos agora
                    </button>
                </form>
                <div id="sendAllProcessing" class="message info" style="display:none; margin-top: 10px;"></div>

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
                    <h3>Emails e Termos de Busca</h3>
                    {% if emails %}
                        {% for email in emails %}
                            <div class="email-card" style="margin-bottom: 20px; padding: 15px; background: var(--background); border-radius: var(--radius); border: 1px solid var(--border);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <span class="email" style="font-weight: 600;">{{ email }}</span>
                                    <form method="post" style="display: inline; margin: 0;">
                                        <input type="hidden" name="email" value="{{ email }}">
                                        <button type="submit" name="action" value="unregister" class="remove-btn" style="background: var(--error-color); color: white; border: none; padding: 5px 10px; border-radius: var(--radius-sm); font-size: 0.8rem;">Remover Email</button>
                                    </form>
                                </div>
                                <!-- Botão enviar agora para este email -->
                                <form method="post" style="margin: 8px 0;">
                                    <input type="hidden" name="email" value="{{ email }}">
                                    <button type="submit" name="action" value="send_now" style="background: var(--primary-color); color: white; border: none; padding: 8px 12px; border-radius: var(--radius-sm); font-size: 0.85rem;">▶️ Enviar teste agora</button>
                                </form>

                                <!-- Termos de busca para este email -->
                                <div class="email-terms">
                                    <h4 style="margin: 10px 0 5px 0; font-size: 0.9rem; color: var(--text-secondary);">Termos de Busca:</h4>
                                    {% if email_terms[email] %}
                                        <div class="terms-list" style="margin-bottom: 10px;">
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
                                        <p style="font-size: 0.8rem; color: var(--text-secondary); font-style: italic; margin: 5px 0;">Nenhum termo cadastrado.</p>
                                    {% endif %}

                                    <!-- Formulário para adicionar novo termo -->
                                    <form method="post" style="display: flex; gap: 6px; margin-top: 10px; align-items: stretch;">
                                        <input type="hidden" name="email" value="{{ email }}">
                                        <input type="text" name="term" placeholder="Novo termo de busca" style="flex: 1; padding: 6px 10px; font-size: 0.8rem; border: 1px solid var(--border); border-radius: var(--radius-sm); min-width: 0;" required>
                                        <button type="submit" name="action" value="add_term" style="background: var(--success-color); color: white; border: none; padding: 6px 10px; border-radius: var(--radius-sm); font-size: 0.8rem; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">+</button>
                                    </form>
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p style="color: var(--text-secondary); font-style: italic;">Nenhum email cadastrado.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <!-- LINHA DIVISÓRIA -->
    <div class="divider"></div>

    <!-- SEÇÃO INFERIOR: RESULTADOS ENCONTRADOS (FULL WIDTH) -->
    <div class="bottom-section">
        <div class="card">
            <h2>📋 Resultados Encontrados</h2>
            {% if results %}
                <div class="results">
                    <h3>Resultados da Busca ({{ results|length }})</h3>
                    {% for result in results %}
                        <div class="result-item" onclick="openModal({{ loop.index }})">
                            <h4>{{ result.article.title or result.article.filename }} ({{ result.article.section }})</h4>
                            {% if result.article.artCategory %}
                            <p><strong>Órgão:</strong> {{ result.article.artCategory }}</p>
                            {% endif %}
                            <p><strong style="color: var(--success-color);">🔍 Termos que geraram este resultado:</strong>
                               <span style="background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;">{{ result.terms_matched|join('</span> <span style=\"background: var(--success-color); color: white; padding: 2px 6px; border-radius: 12px; font-weight: bold;\">') }}</span>
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
                            <p style="color: var(--primary-color); font-size: 0.9rem; cursor: pointer; margin-top: 10px; font-weight: 500;">
                                🔍 Clique para ver detalhes completos
                            </p>
                        </div>
                    {% endfor %}
                </div>
            {% else %}
                <div style="text-align: center; color: var(--text-secondary); font-style: italic; padding: 40px;">
                    Nenhum resultado para exibir.
                </div>
            {% endif %}
        </div>
    </div>

    <!-- Modal para visualização detalhada dos resultados -->
    <div id="resultModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Detalhes do Resultado</h2>
                <span class="close">&times;</span>
            </div>
            <div class="modal-body">
                <div id="modalContent">
                    <!-- Conteúdo será preenchido via JavaScript -->
                </div>
            </div>
            <div class="modal-footer">
                <button onclick="closeModal()" class="btn-secondary">Fechar</button>
                <button onclick="copyToClipboard()" class="btn-primary">Copiar Texto</button>
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

            elif 'action' in request.form and request.form.get('action') == 'search_all_terms':
                # Search for all terms from all registered emails
                try:
                    all_terms = []
                    for email in current_emails:
                        if edge_config_available:
                            email_terms = get_search_terms_from_edge_config(email)
                        else:
                            email_terms = search_terms_storage.get(email, [])
                        all_terms.extend(email_terms)

                    # Remove duplicates
                    unique_terms = list(set(all_terms))

                    if unique_terms:
                        print(f"[DEBUG] Searching for all registered terms: {unique_terms}")
                        matches, search_stats = find_matches_vercel(unique_terms)

                        if matches:
                            # Clean HTML from summaries and snippets
                            for result in matches:
                                if 'snippets' in result and result['snippets']:
                                    result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]
                                # Add summary
                                result['summary'] = f'Documento oficial relacionado aos termos: {", ".join(result["terms_matched"])}'

                            search_results = matches
                            search_term = ", ".join(unique_terms[:3]) + ("..." if len(unique_terms) > 3 else "")
                            message = f"Busca por todos os termos cadastrados: {len(matches)} artigos encontrados para {len(unique_terms)} termos únicos."
                        else:
                            message = f"Nenhum artigo encontrado para os {len(unique_terms)} termos cadastrados. Processados {search_stats.get('xml_files_processed', 0)} arquivos XML."
                    else:
                        message = "Nenhum termo de busca cadastrado nos emails."
                        search_stats = {}
                except Exception as e:
                    print(f"[ERROR] Search all terms failed: {str(e)}")
                    message = f"Erro na busca por todos os termos: {str(e)}"
                    search_stats = {'error': str(e)}

            elif 'action' in request.form and request.form.get('action') == 'search_all_suggestions':
                # Search for all predefined suggestions
                try:
                    # Lista das sugestões predefinidas
                    suggestion_terms = [
                        "23001.000069/2025-95",
                        "Associação Brasileira das Faculdades (Abrafi)",
                        "Resolução CNE/CES nº 2/2024",
                        "reconhecimento de diplomas de pós-graduação stricto sensu obtidos no exterior",
                        "589/2025",
                        "relatado em 4 de setembro de 2025"
                    ]

                    print(f"[DEBUG] Searching for all suggestions: {suggestion_terms}")
                    matches, search_stats = find_matches_vercel(suggestion_terms)

                    if matches:
                        # Clean HTML from summaries and snippets
                        for result in matches:
                            if 'snippets' in result and result['snippets']:
                                result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]
                            # Add summary
                            result['summary'] = f'Documento oficial relacionado aos termos: {", ".join(result["terms_matched"])}'

                        search_results = matches
                        search_term = ", ".join(suggestion_terms[:3]) + ("..." if len(suggestion_terms) > 3 else "")
                        message = f"Busca por todas as sugestões: {len(matches)} artigos encontrados para {len(suggestion_terms)} termos sugeridos."
                    else:
                        message = f"Nenhum artigo encontrado para as sugestões. Processados {search_stats.get('xml_files_processed', 0)} arquivos XML."
                except Exception as e:
                    print(f"[ERROR] Search all suggestions failed: {str(e)}")
                    message = f"Erro na busca por todas as sugestões: {str(e)}"
                    search_stats = {'error': str(e)}

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

                if action == 'add_term':
                    # Add search term to email
                    term = request.form.get('term', '').strip()
                    if email and term:
                        if edge_config_available:
                            if add_search_term_to_edge_config(email, term):
                                message = f'Termo "{term}" adicionado para {email}!'
                            else:
                                message = f'Termo "{term}" já existe para {email}.'
                        else:
                            # Fallback
                            if email not in search_terms_storage:
                                search_terms_storage[email] = []
                            if term not in search_terms_storage[email]:
                                search_terms_storage[email].append(term)
                                message = f'Termo "{term}" adicionado para {email}! (Memória)'
                            else:
                                message = f'Termo "{term}" já existe para {email}.'
                    else:
                        message = "Por favor, forneça um email e termo válidos."

                elif action == 'remove_term':
                    # Remove search term from email
                    term = request.form.get('term', '').strip()
                    if email and term:
                        if edge_config_available:
                            if remove_search_term_from_edge_config(email, term):
                                message = f'Termo "{term}" removido de {email}!'
                            else:
                                message = f'Termo "{term}" não encontrado para {email}.'
                        else:
                            # Fallback
                            if email in search_terms_storage and term in search_terms_storage[email]:
                                search_terms_storage[email].remove(term)
                                message = f'Termo "{term}" removido de {email}! (Memória)'
                            else:
                                message = f'Termo "{term}" não encontrado para {email}.'
                    else:
                        message = "Por favor, forneça um email e termo válidos."

                elif action == 'send_now_all':
                    # Send test email now for all registered emails
                    try:
                        processed = 0
                        sent = 0
                        skipped = 0
                        for em in current_emails:
                            terms = get_search_terms_from_edge_config(em) if edge_config_available else search_terms_storage.get(em, [])
                            if not terms:
                                skipped += 1
                                continue
                            matches, _stats = find_matches_vercel(terms)
                            try:
                                from summarize import summarize_matches
                                summarized = summarize_matches(matches)
                            except Exception:
                                summarized = matches
                            html = format_email_body_html(em, date.today().strftime('%d/%m/%Y'), summarized)
                            ok = send_email_html(em, f"DOU Notificações - {date.today().strftime('%d/%m/%Y')}", html)
                            sent += 1 if ok else 0
                            processed += 1
                        message = f"Envio concluído: {sent}/{processed} emails enviados. {skipped} sem termos."
                    except Exception as e:
                        message = f"Erro ao enviar para todos: {str(e)}"

                elif action == 'send_now' and email:
                    # Send test email now for a specific email
                    try:
                        terms = get_search_terms_from_edge_config(email) if edge_config_available else search_terms_storage.get(email, [])
                        if not terms:
                            message = f"{email} não possui termos cadastrados."
                        else:
                            matches, _stats = find_matches_vercel(terms)
                            try:
                                from summarize import summarize_matches
                                summarized = summarize_matches(matches)
                            except Exception:
                                summarized = matches
                            html = format_email_body_html(email, date.today().strftime('%d/%m/%Y'), summarized)
                            ok = send_email_html(email, f"DOU Notificações - {date.today().strftime('%d/%m/%Y')}", html)
                            if ok:
                                message = f"Email de teste enviado para {email} com {len(summarized)} ocorrência(s)."
                            else:
                                message = f"Falha no envio para {email}. Verifique as credenciais SMTP."
                    except Exception as e:
                        message = f"Erro ao enviar para {email}: {str(e)}"

                elif action in ['register', 'unregister'] and email:
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
                                    # Also remove all terms for this email
                                    terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
                                    set_edge_config_item(terms_key, [])
                                    message = f'Email {email} removido com sucesso! (Edge Config)'
                                else:
                                    emails_storage.discard(email)  # Fallback
                                    search_terms_storage.pop(email, None)
                                    message = f'Email {email} removido com sucesso! (Fallback)'
                            else:
                                emails_storage.discard(email)
                                search_terms_storage.pop(email, None)
                                message = f'Email {email} removido com sucesso! (Memória)'
                        else:
                            message = f'Email {email} não encontrado.'
                else:
                    message = "Por favor, forneça um email válido."
        
        # Carregar termos de busca para cada email
        email_terms = {}
        for email in current_emails:
            if edge_config_available:
                email_terms[email] = get_search_terms_from_edge_config(email)
            else:
                email_terms[email] = search_terms_storage.get(email, [])

        return render_template_string(HTML_TEMPLATE,
                                    message=message,
                                    results=search_results,
                                    search_term=search_term,
                                    use_ai=use_ai,
                                    emails=list(current_emails),
                                    email_terms=email_terms,
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
