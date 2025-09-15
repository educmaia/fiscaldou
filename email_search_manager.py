import redis
import json
import os
from typing import List, Dict, Optional, Set
from datetime import datetime
from redis_client import redis_client

class EmailSearchManager:
    """Gerenciador de emails e termos de busca usando Redis"""

    def __init__(self):
        self.redis = redis_client

    # ===================== EMAILS =====================

    def add_email(self, email: str, name: str = "", active: bool = True) -> bool:
        """
        Adiciona um email à lista de monitoramento
        Args:
            email: Endereço de email
            name: Nome associado ao email (opcional)
            active: Se o email está ativo para notificações
        """
        try:
            email_data = {
                "email": email.lower().strip(),
                "name": name.strip(),
                "active": active,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Armazena dados do email
            self.redis.set(f"email:{email.lower()}", json.dumps(email_data))

            # Adiciona à lista de emails
            self.redis.client.sadd("emails:all", email.lower())

            if active:
                self.redis.client.sadd("emails:active", email.lower())

            print(f"Email {email} adicionado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao adicionar email {email}: {e}")
            return False

    def get_email(self, email: str) -> Optional[Dict]:
        """Recupera dados de um email específico"""
        try:
            email_data = self.redis.get(f"email:{email.lower()}")
            if email_data:
                return json.loads(email_data)
            return None
        except Exception as e:
            print(f"Erro ao recuperar email {email}: {e}")
            return None

    def get_all_emails(self, active_only: bool = False) -> List[Dict]:
        """
        Recupera todos os emails
        Args:
            active_only: Se True, retorna apenas emails ativos
        """
        try:
            if active_only:
                emails_set = "emails:active"
            else:
                emails_set = "emails:all"

            email_addresses = self.redis.client.smembers(emails_set)
            emails = []

            for email in email_addresses:
                email_data = self.get_email(email)
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Erro ao recuperar emails: {e}")
            return []

    def update_email(self, email: str, name: str = None, active: bool = None) -> bool:
        """Atualiza dados de um email"""
        try:
            current_data = self.get_email(email)
            if not current_data:
                return False

            if name is not None:
                current_data["name"] = name.strip()

            if active is not None:
                current_data["active"] = active

                # Atualiza sets de emails ativos
                if active:
                    self.redis.client.sadd("emails:active", email.lower())
                else:
                    self.redis.client.srem("emails:active", email.lower())

            current_data["updated_at"] = datetime.now().isoformat()

            self.redis.set(f"email:{email.lower()}", json.dumps(current_data))
            return True

        except Exception as e:
            print(f"Erro ao atualizar email {email}: {e}")
            return False

    def remove_email(self, email: str) -> bool:
        """Remove um email do sistema"""
        try:
            # Remove dados do email
            self.redis.delete(f"email:{email.lower()}")

            # Remove dos sets
            self.redis.client.srem("emails:all", email.lower())
            self.redis.client.srem("emails:active", email.lower())

            print(f"Email {email} removido com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao remover email {email}: {e}")
            return False

    # ===================== TERMOS DE BUSCA =====================

    def add_search_term(self, term: str, category: str = "geral", active: bool = True) -> bool:
        """
        Adiciona um termo de busca
        Args:
            term: Termo a ser buscado
            category: Categoria do termo (licitação, contrato, etc.)
            active: Se o termo está ativo para busca
        """
        try:
            term_id = term.lower().strip().replace(" ", "_")

            term_data = {
                "term": term.strip(),
                "term_id": term_id,
                "category": category.lower().strip(),
                "active": active,
                "search_count": 0,
                "last_search": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            # Armazena dados do termo
            self.redis.set(f"search_term:{term_id}", json.dumps(term_data))

            # Adiciona aos sets
            self.redis.client.sadd("search_terms:all", term_id)
            self.redis.client.sadd(f"search_terms:category:{category.lower()}", term_id)

            if active:
                self.redis.client.sadd("search_terms:active", term_id)

            print(f"Termo '{term}' adicionado com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao adicionar termo '{term}': {e}")
            return False

    def get_search_term(self, term_id: str) -> Optional[Dict]:
        """Recupera dados de um termo específico"""
        try:
            term_data = self.redis.get(f"search_term:{term_id}")
            if term_data:
                return json.loads(term_data)
            return None
        except Exception as e:
            print(f"Erro ao recuperar termo {term_id}: {e}")
            return None

    def get_search_terms(self, category: str = None, active_only: bool = False) -> List[Dict]:
        """
        Recupera termos de busca
        Args:
            category: Filtrar por categoria específica
            active_only: Se True, retorna apenas termos ativos
        """
        try:
            if category:
                if active_only:
                    # Interseção entre categoria e ativos
                    term_ids = self.redis.client.sinter(
                        f"search_terms:category:{category.lower()}",
                        "search_terms:active"
                    )
                else:
                    term_ids = self.redis.client.smembers(f"search_terms:category:{category.lower()}")
            else:
                if active_only:
                    term_ids = self.redis.client.smembers("search_terms:active")
                else:
                    term_ids = self.redis.client.smembers("search_terms:all")

            terms = []
            for term_id in term_ids:
                term_data = self.get_search_term(term_id)
                if term_data:
                    terms.append(term_data)

            return terms

        except Exception as e:
            print(f"Erro ao recuperar termos: {e}")
            return []

    def update_search_term(self, term_id: str, **kwargs) -> bool:
        """Atualiza um termo de busca"""
        try:
            current_data = self.get_search_term(term_id)
            if not current_data:
                return False

            # Campos atualizáveis
            updatable_fields = ["term", "category", "active"]

            for field, value in kwargs.items():
                if field in updatable_fields:
                    current_data[field] = value

            # Atualiza sets se necessário
            if "active" in kwargs:
                if kwargs["active"]:
                    self.redis.client.sadd("search_terms:active", term_id)
                else:
                    self.redis.client.srem("search_terms:active", term_id)

            if "category" in kwargs:
                old_category = current_data.get("category", "geral")
                new_category = kwargs["category"].lower()

                # Remove da categoria antiga
                self.redis.client.srem(f"search_terms:category:{old_category}", term_id)
                # Adiciona na nova categoria
                self.redis.client.sadd(f"search_terms:category:{new_category}", term_id)

            current_data["updated_at"] = datetime.now().isoformat()

            self.redis.set(f"search_term:{term_id}", json.dumps(current_data))
            return True

        except Exception as e:
            print(f"Erro ao atualizar termo {term_id}: {e}")
            return False

    def increment_search_count(self, term_id: str) -> bool:
        """Incrementa contador de buscas de um termo"""
        try:
            current_data = self.get_search_term(term_id)
            if not current_data:
                return False

            current_data["search_count"] = current_data.get("search_count", 0) + 1
            current_data["last_search"] = datetime.now().isoformat()
            current_data["updated_at"] = datetime.now().isoformat()

            self.redis.set(f"search_term:{term_id}", json.dumps(current_data))
            return True

        except Exception as e:
            print(f"Erro ao incrementar contador do termo {term_id}: {e}")
            return False

    def remove_search_term(self, term_id: str) -> bool:
        """Remove um termo de busca"""
        try:
            term_data = self.get_search_term(term_id)
            if not term_data:
                return False

            category = term_data.get("category", "geral")

            # Remove dados do termo
            self.redis.delete(f"search_term:{term_id}")

            # Remove dos sets
            self.redis.client.srem("search_terms:all", term_id)
            self.redis.client.srem("search_terms:active", term_id)
            self.redis.client.srem(f"search_terms:category:{category}", term_id)

            print(f"Termo {term_id} removido com sucesso")
            return True

        except Exception as e:
            print(f"Erro ao remover termo {term_id}: {e}")
            return False

    # ===================== ESTATÍSTICAS =====================

    def get_stats(self) -> Dict:
        """Retorna estatísticas do sistema"""
        try:
            return {
                "emails": {
                    "total": self.redis.client.scard("emails:all"),
                    "active": self.redis.client.scard("emails:active")
                },
                "search_terms": {
                    "total": self.redis.client.scard("search_terms:all"),
                    "active": self.redis.client.scard("search_terms:active")
                },
                "categories": self._get_categories_stats()
            }
        except Exception as e:
            print(f"Erro ao obter estatísticas: {e}")
            return {}

    def _get_categories_stats(self) -> Dict:
        """Estatísticas por categoria"""
        try:
            categories = {}
            # Busca todas as chaves de categoria
            category_keys = self.redis.client.keys("search_terms:category:*")

            for key in category_keys:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')

                category = key.replace("search_terms:category:", "")
                count = self.redis.client.scard(key)
                categories[category] = count

            return categories
        except Exception as e:
            print(f"Erro ao obter estatísticas de categorias: {e}")
            return {}

# Instância global
email_search_manager = EmailSearchManager()