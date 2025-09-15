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
import redis

# Carregar variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se python-dotenv não estiver disponível, continua sem
    pass

app = Flask(__name__)

# Edge Config configuration
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL')
redis_client = None

def get_redis_client():
    """Inicializa cliente Redis se disponível"""    
    global redis_client
    if redis_client is None and REDIS_URL:
        try:
            redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.ping()  # Testa conexão
            print("Redis conectado com sucesso!")
        except Exception as e:
            print(f"Erro ao conectar Redis: {e}")
            redis_client = None
    return redis_client

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
            'Authorization': f'Bearer {VERCEL_TOKEN}' if VERCEL_TOKEN else ''     }
        
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
    """Get search terms for a specific email from Edge Config"/>
    terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
    terms = get_from_edge_config(terms_key)
    if terms and isinstance(terms, list):
        return terms
    return []
"""
def save_search_terms_to_edge_config(email, terms_list):    
    """Save search terms for a specific email to Edge Config"""
    terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
    return set_edge_config_item(terms_key, terms_list)

# ===================== REDIS FUNCTIONS =====================

def get_emails_from_redis():
    """Get emails list from Redis"""    
    try:
        r = get_redis_client()
        if r:
            emails = r.smembers("emails:active")
            return set(emails)
        return set()
    except Exception as e:
        print(f"Erro ao buscar emails no Redis: {e}")
        return set()

def save_emails_to_redis(emails_set):
    """Save emails list to Redis"""
    try:
        r = get_redis_client()
        if r:
            # Limpa e recria o set
            r.delete("emails:active")
            r.delete("emails:all")

            for email in emails_set:
                email_data = {
                    "email": email,
                    "name": "",
                    "active": True,
                    "created_at": datetime.now().isoformat()
                }

                r.set(f"email:{email}", json.dumps(email_data))
                r.sadd("emails:all", email)
                r.sadd("emails:active", email)

            return True
        return False
    except Exception as e:
        print(f"Erro ao salvar emails no Redis: {e}")
        return False

def get_search_terms_from_redis(email):    
    """Get search terms for a specific email from Redis"""    
    try:
        r = get_redis_client()
        if r:
            terms_key = f"email_terms:{email}"
            terms_data = r.get(terms_key)
            if terms_data:
                return json.loads(terms_data)
            return []
        return []
    except Exception as e:
        print(f"Erro ao buscar termos no Redis para {email}: {e}")
        return []

def save_search_terms_to_redis(email, terms_list):    
    """Save search terms for a specific email to Redis"""
    try:
        r = get_redis_client()
        if r:
            terms_key = f"email_terms:{email}"
            r.set(terms_key, json.dumps(terms_list))
            return True
        return False
    except Exception as e:
        print(f"Erro ao salvar termos no Redis para {email}: {e}")
        return False

def add_search_term_to_redis(email, term):
    """Add a search term for an email in Redis"""
    try:
        current_terms = get_search_terms_from_redis(email)
        if term not in current_terms:
            current_terms.append(term)
            return save_search_terms_to_redis(email, current_terms)
        return True
    except Exception as e:
        print(f"Erro ao adicionar termo no Redis: {e}")
        return False

def remove_search_term_from_redis(email, term):
    """Remove a search term for an email in Redis"""
    try:
        current_terms = get_search_terms_from_redis(email)
        if term in current_terms:        
            current_terms.remove(term)
            return save_search_terms_to_redis(email, current_terms)
        return True
    except Exception as e:
        print(f"Erro ao remover termo no Redis: {e}")
        return False

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

# INLABS Credentials
INLABS_EMAIL = os.getenv('INLABS_EMAIL', 'educmaia@gmail.com')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD', 'maia2807')

# DOU sections - Start with just DO1 to test
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"
URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

# Sugestões fixas utilizadas pelo botão "Buscar Todas as Sugestões"
SUGGESTION_TERMS = [
    "23001.000069/2025-95",
    "Associação Brasileira das Faculdades (ABRAFI)",
    "Resolução CNE/CES nº 2/2024",
    "reconhecimento de diplomas de pós-graduação stricto sensu obtidos no exterior",
    "589/2025",
    "relatado em 4 de setembro de 2025"
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
        print(f"[ERROR] INLABS Connectivity test failed: {e}")
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
            print("[DEBUG] ✅ INLABS login successful. " )

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
        raise Exception(f"Erro ao criar sessão INLABS: {e}")

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
        raise HTTPException(
            status_code=500,
            detail="Erro ao baixar DOU"
        )

def extract_articles_vercel(zip_data):
    """Extract articles from ZIP data - Vercel version."""
    articles = []

    try:
        print(f"[DEBUG] Starting extraction from {len(zip_data)} ZIP files...")
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
                            art_category_text = art_category_elem.get('artCategory') if art_category_elem is not None else "N/A"

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

            except Exception as e:    
                print(f"[ERROR] Error processing section {section}: {e}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")

    except Exception as e:    
        print(f"[ERROR] Error in extract_articles_vercel: {e}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao extrair artigos"
        )

    print(f"[DEBUG] Extraction completed. Total articles: {len(articles)}")
    return articles

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
        return f"""<html><body>
        <h2>DOU Notificações - {date_str}</h2>
        <p>Olá {email},</p>
        <p>Nenhuma ocorrência encontrada hoje no DOU para seus termos.</p>
        <p>Até breve,</p>
        </body></html>"""

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
            f"<h3>{i}. {art.get('filename','(Sem nome)')} - {art.get('section','')}</h3>"
            f"<p><strong>Termos:</strong> {terms}</p>"
            f"<p><strong>Resumo:</strong><br>{summary}</p>"
            f"</div>"
        )
    parts.append("<p>Até breve,</p>")
    return f"<html><body>{''.join(parts)}</body></html>"
