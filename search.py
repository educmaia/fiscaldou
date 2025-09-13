from download import download_dou_xml
from extract import extract_articles
from pathlib import Path
import re
from logging_config import setup_logger

logger = setup_logger('search')


def find_matches(search_terms=None):
    """
    Orchestrate download, extraction, and search for terms.

    Args:
        search_terms (list): List of terms to search for. If None, uses terms from DB.

    Returns:
        list: [{'article': dict, 'terms_matched': list[str], 'snippets': list[str]}, ...]
    """
    if search_terms is None:
        # Get all unique terms from database
        import sqlite3
        from pathlib import Path
        DB_PATH = Path('emails.db')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT term FROM search_terms ORDER BY term')
        search_terms = [row[0] for row in cursor.fetchall()]
        conn.close()
        if not search_terms:
            logger.info("No search terms in database.")
            return []
    try:
        # Download today's XML ZIPs
        logger.info("Starting download for today's DOU XMLs.")
        zip_files = download_dou_xml()
        if not zip_files:
            logger.warning("No files downloaded today.")
            return []

        # Extract articles
        logger.info("Starting extraction of articles.")
        articles = extract_articles(zip_files)
        if not articles:
            logger.warning("No articles extracted.")
            return []

        logger.info(f"Searching {len(articles)} articles for terms.")
        matches = []
        for article in articles:
            text_lower = article['text'].lower()
            matched_terms = []
            snippets = []

            for term in search_terms:
                if term.lower() in text_lower:
                    matched_terms.append(term)

                    # Find match positions and extract snippets (100 chars context)
                    positions = [m.start() for m in re.finditer(
                        re.escape(term.lower()), text_lower)]
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
                logger.info(
                    f"Match found in {article['filename']} ({article['section']}): {matched_terms}")

        logger.info(
            f"Search completed. Found {len(matches)} matching articles.")
        return matches
    except Exception as e:
        logger.error(f"Error in find_matches: {e}")
        raise


if __name__ == "__main__":
    try:
        # Allow passing terms via command line or use defaults
        import sys
        if len(sys.argv) > 1:
            search_terms = sys.argv[1:]
        else:
            search_terms = None
        matches = find_matches(search_terms)
        for match in matches:
            print(f"Article: {match['article']['filename']}")
            print(f"Terms: {match['terms_matched']}")
            # Print first snippet for demo
            print("Snippets:", match['snippets'][:1])
            print("---")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
