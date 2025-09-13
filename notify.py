import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from pathlib import Path
from typing import List, Dict
from logging_config import setup_logger
import os
from dotenv import load_dotenv

load_dotenv()

logger = setup_logger('notify')

DB_PATH = Path('emails.db')

# SMTP Configuration from environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', 'monitoradouniao@gmail.com')
SMTP_PASS = os.getenv('SMTP_PASS', '.Maia2807@')


def get_registered_emails():
    """Fetch list of registered emails from DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT email FROM emails ORDER BY email')
        emails = [row[0] for row in cursor.fetchall()]
        conn.close()
        logger.info(f"Retrieved {len(emails)} registered emails.")
        return emails
    except sqlite3.Error as e:
        logger.error(f"Database error fetching emails: {e}")
        return []


def format_email_body(matches: List[Dict]) -> str:
    """Format HTML email body with summaries."""
    if not matches:
        return "Nenhuma ocorrência encontrada hoje no DOU para os termos monitorados."

    body = """
    <html>
    <body>
    <h2>Notificações Diárias DOU - Ocorrências Encontradas</h2>
    <p>Olá! Foram encontradas as seguintes ocorrências hoje:</p>
    """

    for i, match in enumerate(matches, 1):
        article = match['article']
        terms = ', '.join(match['terms_matched'])
        summary = match['summary']
        body += f"""
        <div style="border: 1px solid #ccc; margin: 10px 0; padding: 10px;">
            <h3>Artigo {i}: {article['filename']} ({article['section']})</h3>
            <p><strong>Termos encontrados:</strong> {terms}</p>
            <p><strong>Resumo:</strong></p>
            <p>{summary}</p>
            <p><strong>Link XML:</strong> {article['xml_path']}</p>
        </div>
        """

    body += """
    <p>Atenciosamente,<br>DOU Notifier</p>
    </body>
    </html>
    """
    return body


def send_notifications(matches: List[Dict]):
    """
    Send email notifications to registered users.

    Args:
        matches (List[Dict]): Summarized matches from search.
    """
    if not matches:
        logger.info("No matches to notify about.")
        return

    emails = get_registered_emails()
    if not emails:
        logger.warning("No registered emails to notify.")
        return

    logger.info(
        f"Sending notifications to {len(emails)} emails for {len(matches)} matches.")
    subject = f"DOU Notificações - {len(matches)} ocorrência(s) encontrada(s) hoje"
    body = format_email_body(matches)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SMTP_USER, SMTP_PASS)
        logger.info("SMTP connection and login successful.")

        sent_count = 0
        for email in emails:
            msg['To'] = email
            text = msg.as_string()
            server.sendmail(SMTP_USER, email, text)
            logger.info(f"Notification sent to {email}")
            sent_count += 1

        server.quit()
        logger.info(f"All {sent_count} notifications sent successfully.")
    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            f"SMTP authentication error: {e}. Check SMTP_USER and SMTP_PASS.")
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP server disconnected: {e}")
    except Exception as e:
        logger.error(f"Email sending error: {e}")
    finally:
        if 'server' in locals():
            try:
                server.quit()
            except:
                pass


if __name__ == "__main__":
    # Example: Assume matches from search + summarize
    try:
        from search import find_matches
        from summarize import summarize_matches
        matches = find_matches()
        if matches:
            summarized = summarize_matches(matches)
            send_notifications(summarized)
        else:
            logger.info("No matches to notify.")
    except Exception as e:
        logger.error(f"Main execution error: {e}")
