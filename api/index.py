from flask import Flask, request, render_template_string, jsonify
import os
import re
import requests
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
import tempfile
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuração simples para Vercel - storage inline temporário
import os

# Edge Config configuration
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

# Fallback storage simples
emails_storage = set()
search_terms_storage = {}

def get_redis_client():
    """Redis desabilitado temporariamente"""
    return None

def get_from_edge_config(key):
    """Get value from Edge Config"""
    try:
        if not EDGE_CONFIG_ID:
            return None
        url = f"https://edge-config.vercel.com/{EDGE_CONFIG_ID}"
        headers = {'Authorization': f'Bearer {VERCEL_TOKEN}' if VERCEL_TOKEN else ''}
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
        url = f"https://api.vercel.com/v1/edge-config/{EDGE_CONFIG_ID}/items"
        headers = {'Authorization': f'Bearer {VERCEL_TOKEN}', 'Content-Type': 'application/json'}
        data = {'items': [{'operation': 'upsert', 'key': key, 'value': value}]}
        response = requests.patch(url, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error writing to Edge Config: {e}")
        return False

def get_current_emails():
    """Get current emails - Edge Config > Memory fallback"""
    try:
        emails = get_from_edge_config('emails')
        if emails and isinstance(emails, list):
            return set(emails)
        return emails_storage
    except:
        return emails_storage

def save_emails(emails_set):
    """Save emails - Edge Config > Memory fallback"""
    try:
        emails_list = list(emails_set)
        success = set_edge_config_item('emails', emails_list)
        emails_storage.clear()
        emails_storage.update(emails_set)
        return True
    except:
        emails_storage.clear()
        emails_storage.update(emails_set)
        return True

def get_email_terms(email):
    """Get search terms for email"""
    try:
        terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
        terms = get_from_edge_config(terms_key)
        if terms and isinstance(terms, list):
            return terms
        return search_terms_storage.get(email, [])
    except:
        return search_terms_storage.get(email, [])

def save_email_terms(email, terms_list):
    """Save search terms for email"""
    try:
        terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
        success = set_edge_config_item(terms_key, terms_list)
        search_terms_storage[email] = terms_list
        return True
    except:
        search_terms_storage[email] = terms_list
        return True

def add_email_term(email, term):
    """Add search term for email"""
    current_terms = get_email_terms(email)
    if term not in current_terms:
        current_terms.append(term)
        return save_email_terms(email, current_terms)
    return True

def remove_email_term(email, term):
    """Remove search term for email"""
    current_terms = get_email_terms(email)
    if term in current_terms:
        current_terms.remove(term)
        return save_email_terms(email, current_terms)
    return True

def get_all_email_terms():
    """Get terms for all registered emails"""
    current_emails = get_current_emails()
    email_terms = {}
    for email in current_emails:
        email_terms[email] = get_email_terms(email)
    return email_terms

# Carregar variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se python-dotenv não estiver disponível, continua sem
    pass

app = Flask(__name__)


# INLABS credentials
INLABS_EMAIL = os.getenv('INLABS_EMAIL', 'educmaia@gmail.com')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD', 'maia2807')

# DOU sections - Start with just DO1 to test
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"
URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

# Sugestões fixas utilizadas pelo botão "Buscar Todas as Sugestões"
SUGGESTION_TERMS = [
    "23001.000069/2025-95",
    "Associação Brasileira das Faculdades (Abrafi)",
    "Resolução CNE/CES nº 2/2024",
    "reconhecimento de diplomas de pós-graduação stricto sensu obtidos no exterior",
    "589/2025",
    "relatado em 4 de setembro de 2025",
]

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
        <html>
        <head>
            <meta charset="UTF-8">
            <title>DOU Notificações - {date_str}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; border-top: 1px solid #eee; }}
                .no-results {{ text-align: center; padding: 40px; color: #666; }}
                .icon {{ font-size: 48px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">📋 DOU Notificações</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{date_str}</p>
                </div>
                <div class="content">
                    <p style="font-size: 18px; margin-bottom: 20px;">Olá <strong>{email}</strong>,</p>
                    <div class="no-results">
                        <div class="icon">🔍</div>
                        <p style="font-size: 16px; margin: 0;">Nenhuma ocorrência encontrada hoje no DOU para os seus termos de monitoramento.</p>
                        <p style="font-size: 14px; color: #888; margin-top: 10px;">Continue monitorando - notificaremos você assim que houver novidades!</p>
                    </div>
                </div>
                <div class="footer">
                    <p style="margin: 0;">🤖 Sistema Automático de Monitoramento DOU</p>
                </div>
            </div>
        </body>
        </html>
        """

    # Calcular estatísticas
    total_terms_found = sum(len(m.get('terms_matched', [])) for m in matches)
    sections = set(m.get('article', {}).get('section', 'N/A') for m in matches)
    sections_list = ', '.join(sorted(sections))

    # Cabeçalho com estilo completo
    html_parts = [f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <title>DOU Notificações - {date_str}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 900px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 30px; }}
                .stats {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0; display: flex; justify-content: space-around; text-align: center; }}
                .stat-item {{ flex: 1; }}
                .stat-number {{ font-size: 24px; font-weight: bold; color: #667eea; display: block; }}
                .stat-label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
                .match-item {{ border: 1px solid #e1e8ed; border-radius: 8px; padding: 20px; margin: 20px 0; background: #fafbfc; }}
                .match-header {{ background: #667eea; color: white; padding: 15px; margin: -20px -20px 15px -20px; border-radius: 8px 8px 0 0; }}
                .match-title {{ font-size: 18px; font-weight: bold; margin: 0; }}
                .match-subtitle {{ font-size: 14px; opacity: 0.9; margin: 5px 0 0 0; }}
                .terms-badge {{ display: inline-block; background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin: 2px; }}
                .snippet {{ background: #fff; border-left: 4px solid #667eea; padding: 15px; margin: 10px 0; border-radius: 0 4px 4px 0; font-style: italic; color: #555; }}
                .metadata {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0; }}
                .metadata-item {{ background: white; padding: 10px; border-radius: 4px; border: 1px solid #eee; }}
                .metadata-label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
                .metadata-value {{ font-weight: 600; color: #333; }}
                .summary-section {{ background: white; border-radius: 6px; padding: 15px; margin: 15px 0; border: 1px solid #e1e8ed; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; border-top: 1px solid #eee; }}
                .highlight {{ background-color: #fff3cd; padding: 2px 4px; border-radius: 2px; }}
                @media (max-width: 600px) {{
                    .stats {{ flex-direction: column; }}
                    .metadata {{ grid-template-columns: 1fr; }}
                    .container {{ margin: 10px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">📋 DOU Notificações</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{date_str}</p>
                </div>
                <div class="content">
                    <p style="font-size: 18px; margin-bottom: 20px;">Olá <strong>{email}</strong>,</p>

                    <div class="stats">
                        <div class="stat-item">
                            <span class="stat-number">{len(matches)}</span>
                            <span class="stat-label">Ocorrências</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">{total_terms_found}</span>
                            <span class="stat-label">Termos Encontrados</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-number">{len(sections)}</span>
                            <span class="stat-label">Seções DOU</span>
                        </div>
                    </div>

                    <p style="color: #28a745; font-weight: 600; text-align: center; margin: 20px 0;">
                        ✅ Foram encontradas <strong>{len(matches)} ocorrência(s)</strong> hoje nas seções: <em>{sections_list}</em>
                    </p>
    """]

    # Iterar através das ocorrências
    for i, m in enumerate(matches, 1):
        art = m.get('article', {})
        terms = m.get('terms_matched', [])
        summary = m.get('summary', 'Resumo não disponível')
        snippets = m.get('snippets', [])

        # Informações do artigo
        filename = art.get('filename', 'Arquivo não identificado')
        section = art.get('section', 'Seção não especificada')
        xml_path = art.get('xml_path', '')

        # Badges dos termos
        terms_badges = ''.join([f'<span class="terms-badge">{term}</span>' for term in terms])

        # Metadados estruturados
        metadata_html = f"""
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Arquivo XML</div>
                <div class="metadata-value">{filename}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Seção DOU</div>
                <div class="metadata-value">{section}</div>
            </div>
        </div>
        """

        # Snippets destacados
        snippets_html = ""
        if snippets:
            snippets_html = "<div style='margin: 15px 0;'><strong>📄 Trechos relevantes:</strong></div>"
            for idx, snippet in enumerate(snippets[:3], 1):  # Máximo 3 snippets
                # Destacar termos encontrados no snippet
                highlighted_snippet = snippet
                for term in terms:
                    highlighted_snippet = highlighted_snippet.replace(
                        term, f'<span class="highlight"><strong>{term}</strong></span>'
                    )
                snippets_html += f'<div class="snippet"><strong>Trecho {idx}:</strong> {highlighted_snippet}</div>'

        # Seção da ocorrência
        html_parts.append(f"""
        <div class="match-item">
            <div class="match-header">
                <div class="match-title">📄 {i}. {filename}</div>
                <div class="match-subtitle">{section}</div>
            </div>

            <div style="margin: 15px 0;">
                <strong>🔍 Termos encontrados:</strong><br>
                {terms_badges}
            </div>

            {metadata_html}

            <div class="summary-section">
                <strong>📝 Resumo:</strong><br>
                <div style="margin-top: 10px; color: #555;">{summary}</div>
            </div>

            {snippets_html}

            {f'<div style="margin-top: 15px; font-size: 12px; color: #666;"><strong>🔗 Arquivo:</strong> {xml_path}</div>' if xml_path else ''}
        </div>
        """)

    # Rodapé
    html_parts.extend([
        """
                </div>
                <div class="footer">
                    <p style="margin: 0; font-size: 14px;">🤖 <strong>Sistema Automático de Monitoramento DOU</strong></p>
                    <p style="margin: 5px 0 0 0; font-size: 12px;">Monitoramento ativo • Notificações em tempo real • Powered by FiscalDOU</p>
                </div>
            </div>
        </body>
        </html>
        """
    ])

    return ''.join(html_parts)

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

        emails = sorted(list(get_current_emails()))
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
            terms = get_email_terms(email)
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

# HTML_TEMPLATE removido - agora usando arquivos externos em templates/
# Arquivos: templates/main.html, templates/static/style.css, templates/static/script.js

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
        
        # Carregar emails usando função unificada
        current_emails = get_current_emails()
        
        if request.method == 'POST':
            # Prioritizar ações específicas antes de verificar search_term
            action = request.form.get('action')

            if action == 'search_mestrando_exterior':
                # Busca sequencial para termos relacionados a Mestrando Exterior
                try:
                    mestrando_terms = [
                        '23001.000069/2025-95',
                        'Associação Brasileira das Faculdades (Abrafi)',
                        'Resolução CNE/CES',
                        'Resolução CNE/CES nº 2/2024',
                        'reconhecimento de diplomas',
                        '589/2025',
                        'relatado em 4 de setembro de 2025'
                    ]

                    print(f"[DEBUG] Searching for Mestrando Exterior terms: {mestrando_terms}")
                    all_matches = []
                    # Inicializar search_stats com todas as chaves necessárias
                    search_stats = {
                        'sections_downloaded': 0,
                        'zip_files_downloaded': 0,
                        'xml_files_processed': 0,
                        'total_articles_extracted': 0,
                        'articles_searched': 0,
                        'matches_found': 0,
                        'download_time': 0,
                        'extraction_time': 0,
                        'search_time': 0,
                        'total_matches': 0
                    }

                    # Busca sequencial por cada termo
                    for term in mestrando_terms:
                        print(f"[DEBUG] Searching for term: {term}")
                        matches, term_stats = find_matches_vercel([term])

                        if matches:
                            # Clean HTML from summaries and snippets
                            for result in matches:
                                if 'snippets' in result and result['snippets']:
                                    result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]
                                # Add summary with specific term
                                result['summary'] = f'Documento sobre Mestrando Exterior - termo: {term}'
                                result['search_term_used'] = term

                            all_matches.extend(matches)
                            search_stats['total_matches'] += len(matches)
                            search_stats['matches_found'] += len(matches)

                        # Acumular todas as estatísticas do term_stats
                        if term_stats:
                            for key in ['sections_downloaded', 'zip_files_downloaded', 'xml_files_processed',
                                       'total_articles_extracted', 'articles_searched', 'download_time',
                                       'extraction_time', 'search_time']:
                                if key in term_stats:
                                    search_stats[key] += term_stats[key]

                    if all_matches:
                        # Remove duplicates based on URL
                        seen_urls = set()
                        unique_matches = []
                        for match in all_matches:
                            if match.get('url') not in seen_urls:
                                unique_matches.append(match)
                                seen_urls.add(match.get('url'))

                        search_results = unique_matches
                        search_term = "Busca Mestrando Exterior"
                        message = f"Busca Mestrando Exterior: {len(unique_matches)} documentos únicos encontrados para {len(mestrando_terms)} termos pesquisados em {search_stats.get('xml_files_processed', 0)} arquivos XML processados."
                    else:
                        message = f"Nenhum documento encontrado para os termos de Mestrando Exterior. Processados {search_stats.get('xml_files_processed', 0)} arquivos XML."

                except Exception as e:
                    print(f"[ERROR] Search Mestrando Exterior failed: {str(e)}")
                    message = f"Erro na busca Mestrando Exterior: {str(e)}"
                    search_stats = {'error': str(e)}

                # Retornar imediatamente após processar a busca Mestrando Exterior
                # para evitar cair no else que valida email
                email_terms = {}
                for email in current_emails:
                    email_terms[email] = get_email_terms(email)

                return render_template('main.html',
                                            message=message,
                                            results=search_results,
                                            search_term=search_term,
                                            use_ai=use_ai,
                                            emails=list(current_emails),
                                            email_terms=email_terms,
                                            search_stats=search_stats if 'search_stats' in locals() else {})

            elif action == 'search_all_terms':
                # Search for all terms from all registered emails
                try:
                    all_terms = []
                    for email in current_emails:
                        email_terms = get_email_terms(email)
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
                                result['summary'] = f'Documento oficial relacionado aos termos cadastrados: {", ".join(result["terms_matched"])}'

                            search_results = matches
                            search_term = ", ".join(unique_terms[:3]) + ("..." if len(unique_terms) > 3 else "")
                            message = f"Busca por todos os termos: {len(matches)} artigos encontrados para {len(unique_terms)} termos cadastrados."
                        else:
                            message = f"Nenhum artigo encontrado para os termos cadastrados. Processados {search_stats.get('xml_files_processed', 0)} arquivos XML."
                    else:
                        message = "Nenhum termo de busca cadastrado para os emails registrados."
                        search_stats = {'terms_found': 0}
                except Exception as e:
                    print(f"[ERROR] Search all terms failed: {str(e)}")
                    message = f"Erro na busca por todos os termos: {str(e)}"
                    search_stats = {'error': str(e)}

                # Retornar imediatamente após processar search_all_terms
                email_terms = {}
                for email in current_emails:
                    email_terms[email] = get_email_terms(email)

                return render_template('main.html',
                                            message=message,
                                            results=search_results,
                                            search_term=search_term,
                                            use_ai=use_ai,
                                            emails=list(current_emails),
                                            email_terms=email_terms,
                                            search_stats=search_stats if 'search_stats' in locals() else {})

            elif action == 'refresh_cache':
                # Handle cache refresh
                try:
                    print("[DEBUG] Refreshing cache - downloading fresh DOU data")
                    matches, search_stats = find_matches_vercel(['teste'])  # Use a dummy term to trigger download
                    message = f"Cache atualizado! Processados {search_stats.get('xml_files_processed', 0)} arquivos XML em {search_stats.get('download_time', 0):.2f}s"
                except Exception as e:
                    print(f"[ERROR] Cache refresh failed: {e}")
                    message = f"Erro ao atualizar cache: {str(e)}"
                    search_stats = {'error': str(e)}

                # Retornar imediatamente após processar refresh_cache
                email_terms = {}
                for email in current_emails:
                    email_terms[email] = get_email_terms(email)

                return render_template('main.html',
                                            message=message,
                                            results=search_results,
                                            search_term=search_term,
                                            use_ai=use_ai,
                                            emails=list(current_emails),
                                            email_terms=email_terms,
                                            search_stats=search_stats if 'search_stats' in locals() else {})

            elif action == 'send_now_all':
                # Send emails to all registered users
                try:
                    sent = 0
                    skipped = 0
                    processed = 0
                    for email in current_emails:
                        processed += 1
                        # Get terms for this email using Redis priority
                        terms = get_email_terms(email)

                        if not terms:
                            skipped += 1
                            continue

                        # Search and send
                        matches, _ = find_matches_vercel(terms)
                        if matches:
                            summarized = matches[:5]  # Limit to 5 results
                            smtp_user = os.getenv('SMTP_USER', '')
                            smtp_pass = os.getenv('SMTP_PASS', '')

                            if send_email_notification(email, summarized, smtp_user, smtp_pass):
                                sent += 1

                    message = f"Envio concluído: {sent}/{processed} emails enviados. {skipped} sem termos."
                except Exception as e:
                    message = f"Erro ao enviar para todos: {str(e)}"

                # Retornar imediatamente após processar send_now_all
                email_terms = {}
                for email in current_emails:
                    email_terms[email] = get_email_terms(email)

                return render_template('main.html',
                                            message=message,
                                            results=search_results,
                                            search_term=search_term,
                                            use_ai=use_ai,
                                            emails=list(current_emails),
                                            email_terms=email_terms,
                                            search_stats=search_stats if 'search_stats' in locals() else {})

            elif 'search_term' in request.form:
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


            elif request.form.get('action') == 'send_now_all':
                # Send test email now for all registered emails using fixed Mestrando Exterior terms
                try:
                    processed = 0
                    sent = 0

                    # Usar termos fixos do Mestrando Exterior
                    mestrando_terms = [
                        '23001.000069/2025-95',
                        'Associação Brasileira das Faculdades (Abrafi)',
                        'Resolução CNE/CES',
                        'Resolução CNE/CES nº 2/2024',
                        'reconhecimento de diplomas',
                        '589/2025',
                        'relatado em 4 de setembro de 2025'
                    ]

                    # Buscar documentos com os termos fixos
                    print(f"[DEBUG] Searching for Mestrando Exterior terms for email sending: {mestrando_terms}")
                    matches, _stats = find_matches_vercel(mestrando_terms)

                    # Clean HTML from results
                    if matches:
                        for result in matches:
                            if 'snippets' in result and result['snippets']:
                                result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]

                    try:
                        from summarize import summarize_matches
                        summarized = summarize_matches(matches)
                    except Exception:
                        summarized = matches

                    # Enviar para todos os emails cadastrados
                    for em in current_emails:
                        html = format_email_body_html(em, date.today().strftime('%d/%m/%Y'), summarized)
                        ok = send_email_html(em, f"DOU Mestrando Exterior - {date.today().strftime('%d/%m/%Y')}", html)
                        sent += 1 if ok else 0
                        processed += 1

                    message = f"Envio concluído: {sent}/{processed} emails enviados com resultados da busca Mestrando Exterior."
                except Exception as e:
                    message = f"Erro ao enviar para todos: {str(e)}"

                # Retornar imediatamente após processar send_now_all
                email_terms = {}
                for email in current_emails:
                    email_terms[email] = get_email_terms(email)

                return render_template('main.html',
                                            message=message,
                                            results=search_results,
                                            search_term=search_term,
                                            use_ai=use_ai,
                                            emails=list(current_emails),
                                            email_terms=email_terms,
                                            search_stats=search_stats if 'search_stats' in locals() else {})

            else:
                # Handle email actions and other form actions
                action = request.form.get('action')
                email = request.form.get('email', '').strip().lower()

                # Ações que NÃO precisam de email devem estar nos elif acima
                # Se chegou aqui, são ações relacionadas a email

                if action == 'send_now' and email:
                    # Send test email now for a specific email using fixed Mestrando Exterior terms
                    try:
                        # Usar termos fixos do Mestrando Exterior
                        mestrando_terms = [
                            '23001.000069/2025-95',
                            'Associação Brasileira das Faculdades (Abrafi)',
                            'Resolução CNE/CES',
                            'Resolução CNE/CES nº 2/2024',
                            'reconhecimento de diplomas',
                            '589/2025',
                            'relatado em 4 de setembro de 2025'
                        ]

                        print(f"[DEBUG] Sending individual email to {email} with Mestrando Exterior terms: {mestrando_terms}")
                        matches, _stats = find_matches_vercel(mestrando_terms)

                        # Clean HTML from results
                        if matches:
                            for result in matches:
                                if 'snippets' in result and result['snippets']:
                                    result['snippets'] = [clean_html(snippet) for snippet in result['snippets']]

                        try:
                            from summarize import summarize_matches
                            summarized = summarize_matches(matches)
                        except Exception:
                            summarized = matches

                        html = format_email_body_html(email, date.today().strftime('%d/%m/%Y'), summarized)
                        ok = send_email_html(email, f"DOU Mestrando Exterior - {date.today().strftime('%d/%m/%Y')}", html)
                        if ok:
                            message = f"Email de teste enviado para {email} com {len(summarized)} ocorrência(s) da busca Mestrando Exterior."
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
                            if save_emails(current_emails):
                                message = f'Email {email} cadastrado com sucesso!'
                            else:
                                message = f'Erro ao cadastrar email {email}'

                    elif action == 'unregister':
                        if email in current_emails:
                            current_emails.remove(email)
                            if save_emails(current_emails):
                                # Remove também os termos do email
                                save_email_terms(email, [])
                                message = f'Email {email} removido com sucesso!'
                            else:
                                message = f'Erro ao remover email {email}'
                        else:
                            message = f'Email {email} não encontrado.'
                else:
                    message = "Por favor, forneça um email válido."
        
        # Carregar termos de busca para cada email usando função unificada
        email_terms = get_all_email_terms()

        return render_template('main.html',
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
