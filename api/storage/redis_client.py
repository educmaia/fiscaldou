"""
Redis client module for FiscalDOU
Handles all Redis operations for email and search terms storage
"""

import os
import json
import redis
from datetime import datetime


# Global Redis client
redis_client = None
REDIS_URL = os.getenv('REDIS_URL')


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