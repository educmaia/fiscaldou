from datetime import date
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


def create_session():
    """Create and login to INLABS session."""
    payload = {"email": email, "password": senha}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    s = requests.Session()
    try:
        response = s.post(URL_LOGIN, data=payload, headers=headers)
        if s.cookies.get('inlabs_session_cookie'):
            logger.info("INLABS login successful.")
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


def download_dou_xml(sections=None, download_dir="downloads"):
    """
    Download DOU XML ZIPs for today.

    Args:
        sections (str): Space-separated DOU sections, e.g., "DO1 DO2". Defaults to all.
        download_dir (str): Directory to save downloads.

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

        # Setup download directory with today's date
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        download_path = Path(download_dir) / today_str
        download_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Download directory set up: {download_path}")

        downloaded_files = []
        ano = today.strftime("%Y")
        mes = today.strftime("%m")
        dia = today.strftime("%d")
        data_completa = f"{ano}-{mes}-{dia}"

        for dou_secao in sections.split():
            zip_path = download_path / f"{data_completa}-{dou_secao}.zip"

            if zip_path.exists():
                logger.info(
                    f"File already exists: {zip_path}. Skipping download.")
                downloaded_files.append(str(zip_path))
                continue

            logger.info(f"Downloading {data_completa}-{dou_secao}.zip...")
            url_arquivo = f"{URL_DOWNLOAD}{data_completa}&dl={data_completa}-{dou_secao}.zip"
            cabecalho_arquivo = {
                'Cookie': f'inlabs_session_cookie={cookie}',
                'origem': '736372697074'
            }
            response = s.get(url_arquivo, headers=cabecalho_arquivo)

            if response.status_code == 200:
                with open(zip_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded successfully: {zip_path}")
                downloaded_files.append(str(zip_path))
            elif response.status_code == 404:
                logger.warning(f"Not found: {data_completa}-{dou_secao}.zip")
            else:
                logger.error(
                    f"Error downloading {dou_secao}: status {response.status_code}")

        s.close()
        logger.info(f"Download completed. Files: {len(downloaded_files)}")
        return downloaded_files
    except Exception as e:
        logger.error(f"Error in download_dou_xml: {e}")
        if 's' in locals():
            s.close()
        raise


if __name__ == "__main__":
    # Example usage
    try:
        files = download_dou_xml()
        print(f"Downloaded {len(files)} files: {files}")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
