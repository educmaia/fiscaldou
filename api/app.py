from flask import Flask, request, render_template, jsonify, send_from_directory
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
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv não disponível, continuando sem carregar .env")

app = Flask(__name__, 
            template_folder='templates',
            static_folder='templates/static')

# Configurações
INLABS_EMAIL = os.getenv('INLABS_EMAIL', 'educmaia@gmail.com')
INLABS_PASSWORD = os.getenv('INLABS_PASSWORD', 'maia2807')
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"
URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

# Configurações SMTP
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

# Configuração do Edge Config
EDGE_CONFIG_ID = os.getenv('EDGE_CONFIG')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN')

# Armazenamento em memória (fallback)
emails_storage = set()
search_terms_storage = {}
cache_storage = {}

# Funções de utilidade
def clean_html(text):
    """Remove HTML tags from text for better readability."""
    if not text:
        return text
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

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
        logger.error(f"Error reading from Edge Config: {e}")
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
        logger.error(f"Error writing to Edge Config: {e}")
        return False

def get_current_emails():
    """Get current emails - Edge Config > Memory fallback"""
    try:
        emails = get_from_edge_config('emails')
        if emails and isinstance(emails, list):
            return set(emails)
        return emails_storage
    except Exception as e:
        logger.error(f"Error getting current emails: {e}")
        return emails_storage

def save_emails(emails_set):
    """Save emails - Edge Config > Memory fallback"""
    try:
        emails_list = list(emails_set)
        success = set_edge_config_item('emails', emails_list)
        emails_storage.clear()
        emails_storage.update(emails_set)
        return True
    except Exception as e:
        logger.error(f"Error saving emails: {e}")
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
    except Exception as e:
        logger.error(f"Error getting email terms: {e}")
        return search_terms_storage.get(email, [])

def save_email_terms(email, terms_list):
    """Save search terms for email"""
    try:
        terms_key = f'terms_{email.replace("@", "_at_").replace(".", "_dot_")}'
        success = set_edge_config_item(terms_key, terms_list)
        search_terms_storage[email] = terms_list
        return True
    except Exception as e:
        logger.error(f"Error saving email terms: {e}")
        search_terms_storage[email] = terms_list
        return True

def get_all_email_terms():
    """Get terms for all registered emails"""
    current_emails = get_current_emails()
    email_terms = {}
    for email in current_emails:
        email_terms[email] = get_email_terms(email)
    return email_terms

def is_valid_zip_content(content):
    """Check if content is a valid ZIP file by checking its signature."""
    try:
        if len(content) < 4:
            return False
        signature = content[:4]
        return signature.startswith(b'PK')
    except Exception:
        return False

def create_inlabs_session():
    """Create and login to INLABS session."""
    try:
        logger.info("Attempting INLABS login")
        payload = {"email": INLABS_EMAIL, "password": INLABS_PASSWORD}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        session = requests.Session()
        response = session.post(URL_LOGIN, data=payload, headers=headers, timeout=30)
        
        if session.cookies.get('inlabs_session_cookie'):
            logger.info("INLABS login successful")
            return session
        else:
            logger.error("INLABS login failed")
            raise ValueError("Login failed: No session cookie obtained.")
    except Exception as e:
        logger.error(f"INLABS login error: {e}")
        raise

def try_download_for_date(session, data_completa, sections):
    """Try to download DOU files for a specific date."""
    downloaded_data = {}
    
    for dou_secao in sections.split():
        logger.info(f"Downloading {data_completa}-{dou_secao}.zip")
        url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"
        
        try:
            response = session.get(url_arquivo, timeout=60)
            
            if response.status_code == 200:
                if is_valid_zip_content(response.content):
                    downloaded_data[dou_secao] = response.content
                    logger.info(f"Downloaded valid ZIP: {data_completa}-{dou_secao}.zip ({len(response.content)} bytes)")
                else:
                    logger.warning(f"Downloaded content for {dou_secao} is NOT a valid ZIP")
            elif response.status_code == 404:
                logger.info(f"Not found: {data_completa}-{dou_secao}.zip")
            else:
                logger.warning(f"Error downloading {dou_secao}: status {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading {dou_secao}: {e}")
    
    logger.info(f"Download attempt for {data_completa} completed. Valid files: {len(downloaded_data)}")
    return downloaded_data

def download_dou_xml(sections=None, max_fallback_days=2):
    """Download DOU XML ZIPs with fallback to previous days."""
    if sections is None:
        sections = DEFAULT_SECTIONS
    
    try:
        session = create_inlabs_session()
        cookie = session.cookies.get('inlabs_session_cookie')
        if not cookie:
            raise ValueError("No cookie after login.")
        
        target_date = date.today()
        
        for days_back in range(max_fallback_days + 1):
            current_date = target_date - timedelta(days=days_back)
            data_completa = current_date.strftime("%Y-%m-%d")
            data_formatada = current_date.strftime("%d/%m/%Y")
            
            if days_back == 0:
                logger.info(f"Checking DOU for today ({data_formatada})...")
            else:
                logger.info(f"DOU for today not available. Checking {days_back} day(s) back ({data_formatada})...")
            
            downloaded_data = try_download_for_date(session, data_completa, sections)
            
            if downloaded_data:
                logger.info(f"DOU found for {data_formatada}! {len(downloaded_data)} file(s) downloaded.")
                session.close()
                return downloaded_data
            else:
                logger.warning(f"No valid DOU found for {data_formatada}")
        
        logger.error(f"No valid DOU found after checking {max_fallback_days + 1} days.")
        session.close()
        return {}
    except Exception as e:
        logger.error(f"Error in download_dou_xml: {e}")
        if 'session' in locals():
            session.close()
        raise

def extract_articles(zip_data):
    """Extract articles from ZIP data."""
    articles = []
    
    try:
        logger.info(f"Starting extraction from {len(zip_data)} zip files")
        for section, zip_bytes in zip_data.items():
            logger.info(f"Processing section: {section}, ZIP size: {len(zip_bytes)} bytes")
            
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_ref:
                    all_files = zip_ref.namelist()
                    xml_files = [f for f in all_files if f.endswith('.xml')]
                    
                    if not xml_files:
                        logger.warning(f"No XML files found in {section}. All files: {all_files}")
                        continue
                    
                    for xml_filename in xml_files:
                        try:
                            xml_content = zip_ref.read(xml_filename)
                            root = ET.fromstring(xml_content)
                            
                            # Extract artCategory
                            art_category_elem = root.find('.//*[@artCategory]')
                            art_category_text = art_category_elem.get('artCategory', 'N/A') if art_category_elem is not None else "N/A"
                            
                            # Extract text from article tags
                            text_parts = []
                            for article in root.findall('.//article'):
                                article_text = ET.tostring(article, encoding='unicode', method='text').strip()
                                if article_text:
                                    text_parts.append(article_text)
                            
                            full_text = ' '.join(text_parts).strip()
                            if full_text:
                                articles.append({
                                    'section': section,
                                    'filename': xml_filename,
                                    'text': full_text,
                                    'xml_path': f"#xml-{section}-{xml_filename}",
                                    'artCategory': art_category_text
                                })
                                logger.info(f"Successfully extracted text from {xml_filename}")
                        except ET.ParseError as e:
                            logger.error(f"XML parsing error in {xml_filename}: {e}")
                        except Exception as e:
                            logger.error(f"Error processing {xml_filename}: {e}")
            except zipfile.BadZipFile as e:
                logger.error(f"Bad ZIP file for section {section}: {e}")
            except Exception as e:
                logger.error(f"Error opening ZIP for section {section}: {e}")
    
    except Exception as e:
        logger.error(f"Error in extract_articles: {e}")
        raise
    
    logger.info(f"Extraction completed. Total articles: {len(articles)}")
    return articles

def find_matches(search_terms):
    """Find matches in DOU."""
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
        logger.info("Starting download for today's DOU XMLs.")
        zip_data = download_dou_xml()
        stats['download_time'] = round(time.time() - start_time, 2)
        
        if not zip_data:
            logger.info("No files downloaded today.")
            return [], stats
        
        stats['sections_downloaded'] = len(zip_data)
        stats['zip_files_downloaded'] = len(zip_data)
        
        # Extract articles
        start_time = time.time()
        logger.info("Starting extraction of articles.")
        articles = extract_articles(zip_data)
        stats['extraction_time'] = round(time.time() - start_time, 2)
        
        if not articles:
            logger.info("No articles extracted.")
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
        logger.info(f"Searching {len(articles)} articles for terms.")
        matches = []
        
        for article in articles:
            text_lower = article['text'].lower()
            matched_terms = []
            snippets = []
            
            for term in search_terms:
                if term.lower() in text_lower:
                    matched_terms.append(term)
                    
                    # Find match positions and extract snippets
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
                logger.info(f"Match found in {article['filename']} ({article['section']}): {matched_terms}")
        
        stats['search_time'] = round(time.time() - start_time, 2)
        stats['matches_found'] = len(matches)
        
        logger.info(f"Search completed. Found {len(matches)} matching articles.")
        return matches, stats
    
    except Exception as e:
        logger.error(f"Error in find_matches: {e}")
        return [], stats

def send_email_html(recipient, subject, html_body):
    """Send HTML email."""
    if not (SMTP_SERVER and SMTP_PORT and SMTP_USER and SMTP_PASS):
        logger.error("SMTP environment variables not fully configured.")
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
                logger.warning(f"STARTTLS not available/failed: {e}")
        
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipient, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email send failed for {recipient}: {e}")
        try:
            server.quit()
        except Exception:
            pass
        return False

def format_email_body_html(email, date_str, matches):
    """Format email body as HTML."""
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
    
    # Calculate statistics
    total_terms_found = sum(len(m.get('terms_matched', [])) for m in matches)
    sections = set(m.get('article', {}).get('section', 'N/A') for m in matches)
    sections_list = ', '.join(sorted(sections))
    
    # Header with complete style
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
    
    # Iterate through matches
    for i, m in enumerate(matches, 1):
        art = m.get('article', {})
        terms = m.get('terms_matched', [])
        summary = m.get('summary', 'Resumo não disponível')
        snippets = m.get('snippets', [])
        
        # Article information
        filename = art.get('filename', 'Arquivo não identificado')
        section = art.get('section', 'Seção não especificada')
        xml_path = art.get('xml_path', '')
        
        # Terms badges
        terms_badges = ''.join([f'<span class="terms-badge">{term}</span>' for term in terms])
        
        # Structured metadata
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
        
        # Highlighted snippets
        snippets_html = ""
        if snippets:
            snippets_html = "<div style='margin: 15px 0;'><strong>📄 Trechos relevantes:</strong></div>"
            for idx, snippet in enumerate(snippets[:3], 1):  # Maximum 3 snippets
                # Highlight found terms in snippet
                highlighted_snippet = snippet
                for term in terms:
                    highlighted_snippet = highlighted_snippet.replace(
                        term, f'<span class="highlight"><strong>{term}</strong></span>'
                    )
                snippets_html += f'<div class="snippet"><strong>Trecho {idx}:</strong> {highlighted_snippet}</div>'
        
        # Match section
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
    
    # Footer
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

# Rotas da aplicação
@app.route('/')
def home():
    """Main page with complete FiscalDOU functionality."""
    try:
        message = request.args.get('message', '')
        search_results = None
        search_term = ''
        use_ai = False
        
        # Check environment variables
        openai_key = bool(os.getenv('OPENAI_API_KEY'))
        smtp_server = os.getenv('SMTP_SERVER', '')
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_pass = bool(os.getenv('SMTP_PASS'))
        edge_config_available = bool(EDGE_CONFIG_ID)
        
        # Load emails using unified function
        current_emails = get_current_emails()
        
        # Load search terms for each email using unified function
        email_terms = get_all_email_terms()
        
        return render_template('main.html',
                                    message=message,
                                    results=search_results,
                                    search_term=search_term,
                                    use_ai=use_ai,
                                    emails=list(current_emails),
                                    email_terms=email_terms,
                                    search_stats={},
                                    openai_configured=openai_key,
                                    smtp_configured=bool(smtp_server and smtp_user and smtp_pass),
                                    edge_config_available=edge_config_available)
    
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return f"Error: {str(e)}", 500

@app.route('/api/cron/daily', methods=['GET'])
def cron_daily():
    """Vercel Cron target. Fetch emails and terms from Edge Config,
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
            
            matches, stats = find_matches(terms)
            
            # Summaries (use AI if key configured; summarize.py falls back gracefully)
            try:
                from summarize import summarize_matches
                summarized = summarize_matches(matches)
            except Exception as e:
                logger.warning(f"Summarization failed, sending without summaries: {e}")
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
        logger.error(f"Cron execution failed: {e}")
        return ({'ok': False, 'error': str(e)}, 500)

@app.route('/health')
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "FiscalDOU",
        "timestamp": datetime.now().isoformat(),
        "environment": "production",
        "platform": "vercel"
    }

@app.route('/config')
def config():
    """Endpoint to check configurations (without exposing sensitive values)."""
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
    logger.error(f"Internal server error: {error}")
    return f"Internal Server Error: {str(error)}", 500

@app.errorhandler(404)  
def not_found(error):
    """Handle 404 errors."""
    return "Page not found", 404

# Handler for Vercel serverless functions
def handler(event, context):
    """Handler for Vercel serverless functions."""
    return app(event, context)

if __name__ == '__main__':
    app.run(debug=True)