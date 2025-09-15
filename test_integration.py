#!/usr/bin/env python3
"""
Teste de integração Redis com o index.py
Verifica se os botões cadastrar/remover estão funcionando com Redis
"""

import requests
import json
import redis

# Configuração
BASE_URL = "http://localhost:5000"  # Ajuste conforme necessário
REDIS_URL = "redis://default:oGJa1ny0G2E4ZLgZT3SQqMF83dYe05io@redis-12998.c15.us-east-1-4.ec2.redns.redis-cloud.com:12998"

def test_redis_connection():
    """Testa conexão direta com Redis"""
    print("=== Testando Conexão Redis ===")
    try:
        r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        print("✅ Redis conectado com sucesso!")
        return r
    except Exception as e:
        print(f"❌ Erro na conexão Redis: {e}")
        return None

def test_web_interface():
    """Testa a interface web"""
    print("\n=== Testando Interface Web ===")
    try:
        response = requests.get(BASE_URL, timeout=10)
        if response.status_code == 200:
            print("✅ Interface web acessível")

            # Verifica se menciona Redis na página
            if "Redis" in response.text:
                print("✅ Interface menciona Redis")
            else:
                print("⚠️  Interface não menciona Redis explicitamente")

            return True
        else:
            print(f"❌ Interface retornou código: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar interface: {e}")
        return False

def test_email_registration():
    """Testa cadastro de email via form"""
    print("\n=== Testando Cadastro de Email ===")

    test_email = "teste@redis.com"

    try:
        # Dados do formulário
        form_data = {
            'email': test_email,
            'action': 'register'
        }

        response = requests.post(BASE_URL, data=form_data, timeout=10)

        if response.status_code == 200:
            if "Redis" in response.text and "cadastrado com sucesso" in response.text:
                print(f"✅ Email {test_email} cadastrado via Redis!")
                return True
            elif "cadastrado com sucesso" in response.text:
                print(f"✅ Email {test_email} cadastrado (sem Redis explícito)")
                return True
            else:
                print(f"⚠️  Resposta não confirma cadastro: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro no cadastro: {e}")
        return False

def test_email_removal():
    """Testa remoção de email via form"""
    print("\n=== Testando Remoção de Email ===")

    test_email = "teste@redis.com"

    try:
        # Dados do formulário
        form_data = {
            'email': test_email,
            'action': 'unregister'
        }

        response = requests.post(BASE_URL, data=form_data, timeout=10)

        if response.status_code == 200:
            if "Redis" in response.text and "removido com sucesso" in response.text:
                print(f"✅ Email {test_email} removido via Redis!")
                return True
            elif "removido com sucesso" in response.text:
                print(f"✅ Email {test_email} removido (sem Redis explícito)")
                return True
            else:
                print(f"⚠️  Resposta não confirma remoção: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Erro HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Erro na remoção: {e}")
        return False

def test_search_term_management():
    """Testa adição e remoção de termos de busca"""
    print("\n=== Testando Gerenciamento de Termos ===")

    # Primeiro cadastra um email
    test_email = "termo@teste.com"

    # Cadastra email
    form_data = {
        'email': test_email,
        'action': 'register'
    }
    response = requests.post(BASE_URL, data=form_data, timeout=10)

    if "cadastrado com sucesso" not in response.text:
        print(f"❌ Falha ao cadastrar email para teste de termos")
        return False

    # Adiciona termo
    print(f"  Adicionando termo para {test_email}...")
    form_data = {
        'email': test_email,
        'term': 'licitação teste',
        'action': 'add_term'
    }
    response = requests.post(BASE_URL, data=form_data, timeout=10)

    if "adicionado" in response.text:
        if "Redis" in response.text:
            print("  ✅ Termo adicionado via Redis!")
        else:
            print("  ✅ Termo adicionado")
    else:
        print("  ❌ Falha ao adicionar termo")
        return False

    # Remove termo
    print(f"  Removendo termo de {test_email}...")
    form_data = {
        'email': test_email,
        'term': 'licitação teste',
        'action': 'remove_term'
    }
    response = requests.post(BASE_URL, data=form_data, timeout=10)

    if "removido" in response.text:
        if "Redis" in response.text:
            print("  ✅ Termo removido via Redis!")
        else:
            print("  ✅ Termo removido")
    else:
        print("  ❌ Falha ao remover termo")
        return False

    # Remove email de teste
    form_data = {
        'email': test_email,
        'action': 'unregister'
    }
    requests.post(BASE_URL, data=form_data, timeout=10)

    return True

def check_redis_data():
    """Verifica dados no Redis diretamente"""
    print("\n=== Verificando Dados no Redis ===")

    r = test_redis_connection()
    if not r:
        return False

    try:
        # Lista emails
        emails = r.smembers("emails:active")
        print(f"  Emails ativos no Redis: {len(emails)}")
        for email in list(emails)[:3]:  # Mostra apenas 3
            print(f"    - {email}")

        # Lista algumas chaves
        keys = r.keys("email:*")[:5]  # Primeiras 5 chaves
        print(f"  Chaves de email encontradas: {len(r.keys('email:*'))}")

        # Lista termos
        term_keys = r.keys("email_terms:*")
        print(f"  Chaves de termos encontradas: {len(term_keys)}")

        return True

    except Exception as e:
        print(f"  ❌ Erro ao verificar dados: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🚀 TESTE DE INTEGRAÇÃO REDIS + INDEX.PY")
    print("=" * 50)

    # Lista de testes
    tests = [
        ("Conexão Redis", test_redis_connection),
        ("Interface Web", test_web_interface),
        ("Cadastro Email", test_email_registration),
        ("Remoção Email", test_email_removal),
        ("Gerenciamento Termos", test_search_term_management),
        ("Dados Redis", check_redis_data)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))

    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:.<25} {status}")
        if result:
            passed += 1

    print("-" * 50)
    print(f"RESULTADO: {passed}/{total} testes passaram")

    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Redis está integrado e funcionando com os botões!")
    elif passed > total // 2:
        print("⚠️  MAIORIA DOS TESTES PASSOU")
        print("🔧 Redis parcialmente integrado, verifique falhas acima")
    else:
        print("❌ MUITOS TESTES FALHARAM")
        print("🚨 Verifique a integração Redis")

    print("\n💡 DICAS:")
    print("- Certifique-se que o servidor está rodando em http://localhost:5000")
    print("- Verifique se REDIS_URL está configurado no .env")
    print("- Teste manualmente os botões na interface web")

if __name__ == "__main__":
    main()