"""
Email storage module for FiscalDOU
Provides unified interface for email and search terms storage
Uses Redis -> Edge Config -> Memory fallback hierarchy
"""

from .redis_client import (
    get_redis_client,
    get_emails_from_redis,
    save_emails_to_redis,
    get_search_terms_from_redis,
    save_search_terms_to_redis,
    add_search_term_to_redis,
    remove_search_term_from_redis
)

from .edge_config import (
    get_emails_from_edge_config,
    save_emails_to_edge_config,
    get_search_terms_from_edge_config,
    save_search_terms_to_edge_config,
    add_search_term_to_edge_config,
    remove_search_term_from_edge_config
)


# Fallback storage (usado se Redis e Edge Config não estiverem disponíveis)
emails_storage = set()
search_terms_storage = {}


def get_current_emails():
    """
    Get current emails with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True  # Assume available, will fail gracefully

    if redis_available:
        current_emails = get_emails_from_redis()
        if not current_emails and edge_config_available:
            # Fallback para Edge Config se Redis vazio
            current_emails = get_emails_from_edge_config()
            if current_emails is None:
                current_emails = emails_storage  # Fallback final
        elif not current_emails:
            current_emails = emails_storage
    elif edge_config_available:
        current_emails = get_emails_from_edge_config()
        if current_emails is None:
            current_emails = emails_storage  # Fallback
    else:
        current_emails = emails_storage

    return current_emails


def save_emails(emails_set):
    """
    Save emails with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True

    success = False

    if redis_available:
        success = save_emails_to_redis(emails_set)
        if not success and edge_config_available:
            success = save_emails_to_edge_config(emails_set)
    elif edge_config_available:
        success = save_emails_to_edge_config(emails_set)

    # Always update memory fallback
    emails_storage.clear()
    emails_storage.update(emails_set)

    return success or True  # Memory fallback always succeeds


def get_email_terms(email):
    """
    Get search terms for email with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True

    if redis_available:
        terms = get_search_terms_from_redis(email)
        if not terms and edge_config_available:
            terms = get_search_terms_from_edge_config(email)
        if not terms:
            terms = search_terms_storage.get(email, [])
    elif edge_config_available:
        terms = get_search_terms_from_edge_config(email)
        if not terms:
            terms = search_terms_storage.get(email, [])
    else:
        terms = search_terms_storage.get(email, [])

    return terms


def save_email_terms(email, terms_list):
    """
    Save search terms for email with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True

    success = False

    if redis_available:
        success = save_search_terms_to_redis(email, terms_list)
        if not success and edge_config_available:
            success = save_search_terms_to_edge_config(email, terms_list)
    elif edge_config_available:
        success = save_search_terms_to_edge_config(email, terms_list)

    # Always update memory fallback
    search_terms_storage[email] = terms_list

    return success or True  # Memory fallback always succeeds


def add_email_term(email, term):
    """
    Add search term for email with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True

    success = False

    if redis_available:
        success = add_search_term_to_redis(email, term)
        if not success and edge_config_available:
            success = add_search_term_to_edge_config(email, term)
    elif edge_config_available:
        success = add_search_term_to_edge_config(email, term)

    # Always update memory fallback
    if email not in search_terms_storage:
        search_terms_storage[email] = []
    if term not in search_terms_storage[email]:
        search_terms_storage[email].append(term)

    return success or True  # Memory fallback always succeeds


def remove_email_term(email, term):
    """
    Remove search term for email with priority: Redis > Edge Config > Memory
    """
    redis_available = get_redis_client() is not None
    edge_config_available = True

    success = False

    if redis_available:
        success = remove_search_term_from_redis(email, term)
        if not success and edge_config_available:
            success = remove_search_term_from_edge_config(email, term)
    elif edge_config_available:
        success = remove_search_term_from_edge_config(email, term)

    # Always update memory fallback
    if email in search_terms_storage and term in search_terms_storage[email]:
        search_terms_storage[email].remove(term)

    return success or True  # Memory fallback always succeeds


def get_all_email_terms():
    """
    Get terms for all registered emails
    """
    current_emails = get_current_emails()
    email_terms = {}

    for email in current_emails:
        email_terms[email] = get_email_terms(email)

    return email_terms