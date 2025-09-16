"""
Exemplo de como integrar Redis no seu projeto FiscalDOU
"""

import json
from datetime import datetime, timedelta
from redis_client import redis_client

class CacheManager:
    """Gerenciador de cache usando Redis para o projeto FiscalDOU"""

    @staticmethod
    def cache_email_processing(email: str, processed_data: dict, ttl: int = 86400):
        """
        Cacheia dados de processamento de email
        Args:
            email: Email processado
            processed_data: Dados processados
            ttl: Time to live em segundos (padrão: 24h)
        """
        try:
            cache_key = f"email:processed:{hash(email)}"
            cache_data = {
                "email": email,
                "processed_at": datetime.now().isoformat(),
                "data": processed_data,
                "status": "processed"
            }

            success = redis_client.set(
                cache_key,
                json.dumps(cache_data),
                ex=ttl
            )

            if success:
                print(f"Email {email} cached successfully")
                return cache_key
            else:
                print(f"Failed to cache email {email}")
                return None

        except Exception as e:
            print(f"Error caching email {email}: {e}")
            return None

    @staticmethod
    def get_cached_email(email: str):
        """
        Recupera dados de email do cache
        """
        try:
            cache_key = f"email:processed:{hash(email)}"
            cached_data = redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)
            return None

        except Exception as e:
            print(f"Error retrieving cached email {email}: {e}")
            return None

    @staticmethod
    def cache_dou_data(date: str, data: dict, ttl: int = 3600):
        """
        Cacheia dados do DOU para uma data específica
        Args:
            date: Data no formato YYYY-MM-DD
            data: Dados do DOU
            ttl: Time to live em segundos (padrão: 1h)
        """
        try:
            cache_key = f"dou:data:{date}"
            cache_data = {
                "date": date,
                "cached_at": datetime.now().isoformat(),
                "data": data
            }

            success = redis_client.set(
                cache_key,
                json.dumps(cache_data),
                ex=ttl
            )

            if success:
                print(f"DOU data for {date} cached successfully")
                return cache_key
            else:
                print(f"Failed to cache DOU data for {date}")
                return None

        except Exception as e:
            print(f"Error caching DOU data for {date}: {e}")
            return None

    @staticmethod
    def get_cached_dou_data(date: str):
        """
        Recupera dados do DOU do cache para uma data específica
        """
        try:
            cache_key = f"dou:data:{date}"
            cached_data = redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)
            return None

        except Exception as e:
            print(f"Error retrieving cached DOU data for {date}: {e}")
            return None

    @staticmethod
    def cache_search_results(query: str, results: list, ttl: int = 1800):
        """
        Cacheia resultados de busca
        Args:
            query: Consulta de busca
            results: Resultados da busca
            ttl: Time to live em segundos (padrão: 30min)
        """
        try:
            cache_key = f"search:results:{hash(query)}"
            cache_data = {
                "query": query,
                "cached_at": datetime.now().isoformat(),
                "results": results,
                "count": len(results)
            }

            success = redis_client.set(
                cache_key,
                json.dumps(cache_data),
                ex=ttl
            )

            if success:
                print(f"Search results for '{query}' cached successfully")
                return cache_key
            else:
                print(f"Failed to cache search results for '{query}'")
                return None

        except Exception as e:
            print(f"Error caching search results for '{query}': {e}")
            return None

    @staticmethod
    def get_cached_search_results(query: str):
        """
        Recupera resultados de busca do cache
        """
        try:
            cache_key = f"search:results:{hash(query)}"
            cached_data = redis_client.get(cache_key)

            if cached_data:
                return json.loads(cached_data)
            return None

        except Exception as e:
            print(f"Error retrieving cached search results for '{query}': {e}")
            return None

    @staticmethod
    def invalidate_cache_pattern(pattern: str):
        """
        Remove chaves do cache que correspondem a um padrão
        Nota: Esta operação pode ser custosa em produção
        """
        try:
            # Para simplificar, só remove se conhecemos a chave exata
            # Em produção, considere usar SCAN para patterns
            if redis_client.exists(pattern):
                return redis_client.delete(pattern)
            return False

        except Exception as e:
            print(f"Error invalidating cache pattern '{pattern}': {e}")
            return False

# Exemplos de uso:
if __name__ == "__main__":
    # Exemplo 1: Cache de processamento de email
    email = "exemplo@exemplo.com"
    processed_data = {"status": "processed", "notifications_sent": 3}

    cache_key = CacheManager.cache_email_processing(email, processed_data)
    cached_email = CacheManager.get_cached_email(email)
    print("Cached email:", cached_email)

    # Exemplo 2: Cache de dados do DOU
    today = datetime.now().strftime("%Y-%m-%d")
    dou_data = {"articles": [], "total_count": 0}

    CacheManager.cache_dou_data(today, dou_data)
    cached_dou = CacheManager.get_cached_dou_data(today)
    print("Cached DOU data:", cached_dou)

    # Exemplo 3: Cache de resultados de busca
    query = "licitação"
    results = [{"title": "Exemplo", "content": "..."}]

    CacheManager.cache_search_results(query, results)
    cached_search = CacheManager.get_cached_search_results(query)
    print("Cached search results:", cached_search)