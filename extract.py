import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import os
from logging_config import setup_logger

logger = setup_logger('extract')


def extract_articles(zip_paths, extract_dir="extracted"):
    """
    Unzip XML ZIPs, parse XML files, extract article texts.

    Args:
        zip_paths (list): List of ZIP file paths.
        extract_dir (str): Base directory for extracted files.

    Returns:
        list: [{'section': str, 'filename': str, 'text': str, 'xml_path': str}, ...]
    """
    if not zip_paths:
        logger.warning("No ZIP files provided for extraction.")
        return []

    articles = []
    today_str = Path(zip_paths[0]).parent.name if zip_paths else "unknown"
    date_dir = Path(extract_dir) / today_str
    date_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Extraction directory: {date_dir}")

    # Check if already extracted
    existing_files = list(date_dir.glob("*.xml"))
    if existing_files:
        logger.info(
            f"Files already extracted in {date_dir}. Parsing existing files.")
        # Parse existing files instead of extracting
        for xml_path in existing_files:
            try:
                # e.g., DO1 from DO1_filename.xml
                section = xml_path.stem.split('_')[0]
                # reconstruct original filename
                xml_filename = '_'.join(xml_path.stem.split('_')[1:]) + '.xml'

                tree = ET.parse(xml_path)
                root = tree.getroot()

                # Extract artCategory if available (it's an attribute)
                art_category_elem = root.find('.//*[@artCategory]')
                art_category_text = art_category_elem.get(
                    'artCategory', 'N/A') if art_category_elem is not None else "N/A"

                # Extract text from article tags (actual structure)
                text_parts = []
                for article in root.findall('.//article'):
                    article_text = ET.tostring(
                        article, encoding='unicode', method='text').strip()
                    if article_text:
                        text_parts.append(article_text)

                full_text = ' '.join(text_parts).strip()
                if full_text:
                    articles.append({
                        'section': section,
                        'filename': xml_filename,
                        'text': full_text,
                        'xml_path': f"/xml/{xml_path.relative_to(Path(extract_dir))}",
                        'artCategory': art_category_text
                    })
                    logger.info(
                        f"Parsed text from {xml_filename} ({len(text_parts)} articles)")
                else:
                    logger.warning(
                        f"No text parsed from {xml_filename}")
            except ET.ParseError as e:
                logger.error(
                    f"XML parsing error in {xml_path.name}: {e}")
            except Exception as e:
                logger.error(f"Error processing {xml_path.name}: {e}")
        logger.info(f"Extraction completed. Total articles: {len(articles)}")
        return articles

    try:
        for zip_path in zip_paths:
            section = Path(zip_path).stem.split(
                '-')[-1].upper()  # e.g., DO1 from filename
            logger.info(f"Processing ZIP: {zip_path} (section: {section})")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                xml_files = [f for f in zip_ref.namelist()
                             if f.endswith('.xml')]
                logger.info(f"Found {len(xml_files)} XML files in {zip_path}")

                for xml_filename in xml_files:
                    try:
                        # Extract to temp, parse, then move to date_dir
                        temp_path = date_dir / f"{section}_{xml_filename}"
                        zip_ref.extract(xml_filename, date_dir)
                        xml_path = date_dir / xml_filename
                        # Rename with section prefix, remove if exists to avoid conflict
                        if temp_path.exists():
                            temp_path.unlink()
                        os.rename(xml_path, temp_path)
                        xml_path = temp_path

                        tree = ET.parse(xml_path)
                        root = tree.getroot()

                        # Extract artCategory if available (it's an attribute)
                        art_category_elem = root.find('.//*[@artCategory]')
                        art_category_text = art_category_elem.get(
                            'artCategory', 'N/A') if art_category_elem is not None else "N/A"

                        # Extract text from article tags (actual structure)
                        text_parts = []
                        for article in root.findall('.//article'):
                            article_text = ET.tostring(
                                article, encoding='unicode', method='text').strip()
                            if article_text:
                                text_parts.append(article_text)

                        full_text = ' '.join(text_parts).strip()
                        if full_text:
                            articles.append({
                                'section': section,
                                'filename': xml_filename,
                                'text': full_text,
                                'xml_path': f"/xml/{xml_path.relative_to(Path(extract_dir))}",
                                'artCategory': art_category_text
                            })
                            logger.info(
                                f"Extracted text from {xml_filename} ({len(text_parts)} articles)")
                        else:
                            logger.warning(
                                f"No text extracted from {xml_filename}")
                    except ET.ParseError as e:
                        logger.error(
                            f"XML parsing error in {xml_filename}: {e}")
                    except Exception as e:
                        logger.error(f"Error processing {xml_filename}: {e}")
    except Exception as e:
        logger.error(f"Error in extract_articles: {e}")
        raise

    logger.info(f"Extraction completed. Total articles: {len(articles)}")
    return articles


if __name__ == "__main__":
    # Example: Assume zip paths from download
    try:
        from download import download_dou_xml
        zip_files = download_dou_xml()
        articles = extract_articles(zip_files)
        print(f"Extracted {len(articles)} articles")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
