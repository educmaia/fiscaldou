from datetime import date, datetime, timedelta
import requests
import os
from pathlib import Path
from logging_config import setup_logger

logger = setup_logger('download')

# Hardcoded INLABS credentials (replace with actual values)
email = "educmaia@gmail.com"
senha = "maia2807"

# All DOU sections for comprehensive coverage
DEFAULT_SECTIONS = "DO1 DO1E DO2 DO3 DO2E DO3E"

URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="


def is_valid_zip(file_path):
    """Check if a file is a valid ZIP file by checking its signature."""
    try:
        with open(file_path, 'rb') as f:
            signature = f.read(4)
            return signature.startswith(b'PK')
    except Exception:
        return False


def create_session():
    """Create and login to INLABS session."""
    payload = {"email": email, "password": senha}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    s = requests.Session()
    try:
        logger.debug(f"Attempting login with email: {email}")
        response = s.post(URL_LOGIN, data=payload, headers=headers)
        logger.debug(f"Login response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response cookies: {dict(response.cookies)}")

        if s.cookies.get('inlabs_session_cookie'):
            logger.debug("INLABS login successful.")
            # Test access to main interface
            logger.debug("Testing access to main INLABS interface...")
            test_response = s.get("https://inlabs.in.gov.br/index.php")
            logger.debug(f"Main interface status: {test_response.status_code}")
            if test_response.status_code == 200:
                logger.debug("Successfully logged into INLABS interface")
            return s
        else:
            raise ValueError(
                "Login failed: No session cookie obtained. Check credentials.")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error during login: {e}. Retrying...")
        return create_session()
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise


def download_dou_xml(sections=None, download_dir="downloads", test_date=None, max_fallback_days=2):
    """
    Download DOU XML ZIPs for today or specified date with fallback to previous days.

    Args:
        sections (str): Space-separated DOU sections, e.g., "DO1 DO2". Defaults to all.
        download_dir (str): Directory to save downloads.
        test_date (str): Date in YYYY-MM-DD format for testing. If None, uses today.
        max_fallback_days (int): Maximum number of days to go back if no valid DOU found.

    Returns:
        list: Paths to downloaded ZIP files.
    """
    if sections is None:
        sections = DEFAULT_SECTIONS

    try:
        s = create_session()
        cookie = s.cookies.get('inlabs_session_cookie')
        if not cookie:
            raise ValueError("No cookie after login.")

        # Determine starting date
        if test_date:
            target_date = datetime.strptime(test_date, "%Y-%m-%d").date()
        else:
            target_date = date.today()

        # Try downloading for up to max_fallback_days
        for days_back in range(max_fallback_days + 1):
            current_date = target_date - timedelta(days=days_back)
            data_completa = current_date.strftime("%Y-%m-%d")
            data_formatada = current_date.strftime("%d/%m/%Y")

            if days_back == 0:
                print(f"Verificando DOU de hoje ({data_formatada})...")
                logger.info(f"Attempting download for today: {data_completa}")
            else:
                print(f"DOU de hoje não disponível. Verificando {days_back} dia(s) atrás ({data_formatada})...")
                logger.info(f"Fallback: Attempting download for {days_back} day(s) ago: {data_completa}")

            # Setup download directory for current date
            download_path = Path(download_dir) / data_completa
            download_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Download directory set up: {download_path}")

            downloaded_files = try_download_for_date(s, cookie, data_completa, sections, download_path)

            if downloaded_files:
                print(f"SUCCESS: DOU encontrado para {data_formatada}! {len(downloaded_files)} arquivo(s) baixado(s).")
                logger.info(f"Successfully downloaded {len(downloaded_files)} files for date {data_completa}")
                return downloaded_files
            else:
                print(f"Nenhum DOU válido encontrado para {data_formatada}")
                logger.warning(f"No valid DOU files found for date {data_completa}")

        print(f"ERRO: Nenhum DOU válido encontrado após verificar {max_fallback_days + 1} dias.")
        logger.error(f"No valid DOU files found after trying {max_fallback_days + 1} days")
        return []

    except Exception as e:
        logger.error(f"Error in download_dou_xml: {e}")
        if 's' in locals():
            s.close()
        raise


def try_download_for_date(session, cookie, data_completa, sections, download_path):
    """
    Try to download DOU files for a specific date.

    Returns:
        list: Paths to successfully downloaded ZIP files, empty if none found.
    """
    downloaded_files = []

    for dou_secao in sections.split():
        zip_path = download_path / f"{data_completa}-{dou_secao}.zip"

        if zip_path.exists():
            # Check if existing file is a valid ZIP
            if is_valid_zip(zip_path):
                logger.debug(f"Valid ZIP file already exists: {zip_path}. Skipping download.")
                downloaded_files.append(str(zip_path))
                continue
            else:
                logger.debug(f"Invalid ZIP file found: {zip_path}. Re-downloading...")
                zip_path.unlink()  # Delete invalid file

        logger.debug(f"Downloading {data_completa}-{dou_secao}.zip...")
        url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"

        cabecalho_arquivo = {
            'Cookie': f'inlabs_session_cookie={cookie}',
            'origem': '736372697074'
        }

        response = session.request("GET", url_arquivo, headers=cabecalho_arquivo)

        if response.status_code == 200:
            # Check if content is actually a ZIP file
            if response.content.startswith(b'PK'):
                with open(zip_path, "wb") as f:
                    f.write(response.content)
                logger.debug(f"Downloaded valid ZIP: {zip_path}")
                downloaded_files.append(str(zip_path))
            else:
                logger.debug(f"Downloaded content for {dou_secao} is NOT a valid ZIP (got HTML page)")
                # Don't save invalid files for this date

        elif response.status_code == 404:
            logger.debug(f"Not found: {data_completa}-{dou_secao}.zip")
        else:
            logger.debug(f"Error downloading {dou_secao}: status {response.status_code}")

    logger.debug(f"Download attempt for {data_completa} completed. Valid files: {len(downloaded_files)}")
    return downloaded_files


if __name__ == "__main__":
    # Example usage - test fallback functionality
    try:
        # Test with today's date (will fallback to previous days if no DOU today)
        files = download_dou_xml(sections="DO1", max_fallback_days=2)
        print(f"Downloaded {len(files)} files: {files}")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
