"""
Edge Config module for FiscalDOU
Handles all Vercel Edge Config operations for email and search terms storage
"""

import os
import requests


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