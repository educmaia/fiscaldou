#!/usr/bin/env python3
"""
Debug do problema do botão Buscar Todas as Sugestões
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Carregar .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Simular request do Flask
class MockRequest:
    def __init__(self, method='POST', form_data=None):
        self.method = method
        self.form = form_data or {}

def debug_post_logic():
    """Simula a lógica POST do index.py"""

    print("=== DEBUG: Simulando POST request ===")

    # Simula o request POST do botão
    form_data = {'action': 'search_all_suggestions'}
    request = MockRequest('POST', form_data)

    print(f"request.method: {request.method}")
    print(f"request.form: {request.form}")

    # Simula a lógica do index.py
    if request.method == 'POST':
        print("OK: Entrou no bloco POST")

        # Prioritizar ações específicas antes de verificar search_term
        action = request.form.get('action')
        print(f"action obtida: '{action}'")

        if action == 'search_all_suggestions':
            print("OK: Entrou no bloco search_all_suggestions")
            print("OK: Deveria executar a busca sem pedir email")
            return "SUCCESS: search_all_suggestions"

        elif 'search_term' in request.form:
            print("ERRO: Entrou no bloco search_term (não deveria)")
            return "ERROR: search_term"

        else:
            print("ERRO: Caiu no bloco else (problema!)")
            # Simula o que acontece no else
            action = request.form.get('action')
            email = request.form.get('email', '').strip().lower()
            print(f"else - action: '{action}', email: '{email}'")

            # Simula as condições do else
            if action == 'add_term':
                print("else - seria add_term")
            elif action == 'remove_term':
                print("else - seria remove_term")
            elif action in ['register', 'unregister'] and email:
                print("else - seria register/unregister com email")
            else:
                print("ERRO: else - cairia na mensagem de email válido")
                return "ERROR: Por favor, forneça um email válido"

    return "UNKNOWN"

def debug_redis_terms():
    """Debug da vinculação de termos ao email"""

    print("\n=== DEBUG: Vinculação de termos ao email ===")

    # Testa a conexão Redis
    try:
        from redis_client import redis_client

        # Testa conexão
        redis_client.client.ping()
        print("OK: Redis conectado")

        # Verifica se há emails
        emails = redis_client.client.smembers("emails:active")
        print(f"Emails ativos no Redis: {list(emails)}")

        # Verifica se há termos
        test_email = "educmaia@gmail.com"
        terms_key = f"email_terms:{test_email}"
        terms = redis_client.client.get(terms_key)
        print(f"Termos para {test_email}: {terms}")

        # Lista todas as chaves de termos
        all_term_keys = redis_client.client.keys("email_terms:*")
        print(f"Todas as chaves de termos: {list(all_term_keys)}")

        return True

    except Exception as e:
        print(f"ERRO Redis: {e}")
        return False

def debug_email_functions():
    """Debug das funções de email do index.py"""

    print("\n=== DEBUG: Funções de email ===")

    try:
        # Importa as funções do index.py
        import importlib.util
        spec = importlib.util.spec_from_file_location("index", "api/index.py")
        index_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(index_module)

        # Testa as funções Redis
        test_email = "educmaia@gmail.com"

        print(f"Testando funções para email: {test_email}")

        # Testa get_search_terms_from_redis
        if hasattr(index_module, 'get_search_terms_from_redis'):
            terms = index_module.get_search_terms_from_redis(test_email)
            print(f"get_search_terms_from_redis: {terms}")

        # Testa get_emails_from_redis
        if hasattr(index_module, 'get_emails_from_redis'):
            emails = index_module.get_emails_from_redis()
            print(f"get_emails_from_redis: {emails}")

        return True

    except Exception as e:
        print(f"ERRO ao importar index.py: {e}")
        return False

def main():
    """Função principal de debug"""

    print("DEBUG DO FISCALDOU")
    print("=" * 50)

    # Debug 1: Lógica POST
    result1 = debug_post_logic()
    print(f"Resultado POST: {result1}")

    # Debug 2: Redis
    result2 = debug_redis_terms()

    # Debug 3: Funções de email
    result3 = debug_email_functions()

    print("\n" + "=" * 50)
    print("RESUMO DO DEBUG:")
    print(f"1. Lógica POST: {result1}")
    print(f"2. Redis funcionando: {result2}")
    print(f"3. Funções de email: {result3}")

    if result1 == "SUCCESS: search_all_suggestions":
        print("OK: Botão deveria funcionar corretamente")
    else:
        print("ERRO: Problema identificado na lógica POST")

if __name__ == "__main__":
    main()