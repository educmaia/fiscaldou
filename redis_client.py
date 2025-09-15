import redis
import os
from typing import Optional

class RedisClient:
    _instance: Optional['RedisClient'] = None
    _redis_client: Optional[redis.Redis] = None

    def __new__(cls) -> 'RedisClient':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._redis_client is None:
            self._connect()

    def _connect(self):
        """Conecta ao Redis usando a URL de ambiente"""
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            raise ValueError("REDIS_URL environment variable is not set")

        try:
            self._redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Teste a conexão
            self._redis_client.ping()
            print("Redis connected successfully")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self._redis_client = None
            raise

    @property
    def client(self) -> redis.Redis:
        """Retorna o cliente Redis"""
        if self._redis_client is None:
            self._connect()
        return self._redis_client

    def get(self, key: str) -> Optional[str]:
        """Recupera um valor do Redis"""
        try:
            return self.client.get(key)
        except Exception as e:
            print(f"Error getting key {key}: {e}")
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Define um valor no Redis"""
        try:
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            print(f"Error setting key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Remove uma chave do Redis"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Error deleting key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Verifica se uma chave existe no Redis"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            print(f"Error checking key {key}: {e}")
            return False

    def close(self):
        """Fecha a conexão com o Redis"""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None

# Instância singleton global
redis_client = RedisClient()