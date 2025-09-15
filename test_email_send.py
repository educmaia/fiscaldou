#!/usr/bin/env python3
"""
Teste específico para envio de email teste
"""

import requests
import json

def test_email_send():
    """Testa envio de email teste"""

    BASE_URL = "http://localhost:5000"

    print("=== Teste: Envio de Email Teste ===")

    try:
        # Primeiro, cadastra um email se não existir
        form_data = {
            'email': 'educmaia@gmail.com',
            'action': 'register'
        }

        print("1. Cadastrando email...")
        response = requests.post(BASE_URL, data=form_data, timeout=15)
        if response.status_code == 200:
            print("   Email cadastrado/confirmado")

        # Depois, adiciona um termo se não existir
        form_data = {
            'email': 'educmaia@gmail.com',
            'term': '23001.000069/2025-95',
            'action': 'add_term'
        }

        print("2. Adicionando termo de teste...")
        response = requests.post(BASE_URL, data=form_data, timeout=15)
        if response.status_code == 200:
            print("   Termo adicionado/confirmado")

        # Agora testa o envio de email
        form_data = {
            'email': 'educmaia@gmail.com',
            'action': 'send_now'
        }

        print("3. Testando envio de email...")
        response = requests.post(BASE_URL, data=form_data, timeout=30)

        if response.status_code == 200:
            response_text = response.text

            # Verifica se o erro "não possui termos" aparece
            if "não possui termos cadastrados" in response_text:
                print("   ❌ ERRO: Email ainda não possui termos cadastrados")
                return False

            # Verifica indicadores de sucesso
            success_indicators = [
                "Email de teste enviado",
                "enviado com sucesso",
                "ocorrência",
                "artigos encontrados"
            ]

            found_indicators = []
            for indicator in success_indicators:
                if indicator in response_text:
                    found_indicators.append(indicator)

            if found_indicators:
                print(f"   ✅ SUCESSO: Email enviado! Indicadores: {found_indicators}")

                # Extrai mensagem de resultado se possível
                import re
                # Procura por mensagens de sucesso
                patterns = [
                    r'Email de teste enviado[^<]*',
                    r'enviado com sucesso[^<]*',
                    r'\d+ ocorrência[^<]*'
                ]

                for pattern in patterns:
                    match = re.search(pattern, response_text)
                    if match:
                        print(f"   Resultado: {match.group()}")
                        break

                return True
            else:
                print("   ⚠️ INCERTO: Não encontrou indicadores claros de sucesso")

                # Verifica se há indicadores de erro
                error_indicators = [
                    "Falha no envio",
                    "Erro ao enviar",
                    "Verifique as credenciais SMTP"
                ]

                found_errors = []
                for error in error_indicators:
                    if error in response_text:
                        found_errors.append(error)

                if found_errors:
                    print(f"   ❌ ERROS ENCONTRADOS: {found_errors}")
                else:
                    print("   Primeiros 300 caracteres da resposta:")
                    print("   " + response_text[:300].replace('\n', ' ') + "...")

                return False
        else:
            print(f"   ❌ ERRO HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return False

def test_redis_data():
    """Verifica dados no Redis"""

    print("\n=== Verificação Redis ===")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        from redis_client import redis_client

        # Testa conexão
        redis_client.client.ping()
        print("✅ Redis conectado")

        # Verifica email
        test_email = "educmaia@gmail.com"
        email_data = redis_client.get(f"email:{test_email}")
        if email_data:
            print(f"✅ Email {test_email} encontrado no Redis")
        else:
            print(f"⚠️ Email {test_email} não encontrado no Redis")

        # Verifica termos
        terms_data = redis_client.get(f"email_terms:{test_email}")
        if terms_data:
            import json
            terms = json.loads(terms_data)
            print(f"✅ Termos para {test_email}: {terms}")
        else:
            print(f"⚠️ Nenhum termo encontrado para {test_email}")

        return True

    except Exception as e:
        print(f"❌ Erro Redis: {e}")
        return False

def main():
    """Função principal"""

    print("📧 TESTE DE ENVIO DE EMAIL")
    print("=" * 50)

    # Verifica Redis primeiro
    redis_ok = test_redis_data()

    # Testa envio de email
    email_ok = test_email_send()

    # Resultado final
    print("\n" + "=" * 50)
    print("📊 RESULTADO FINAL:")
    print(f"Redis funcionando: {'✅' if redis_ok else '❌'}")
    print(f"Envio de email: {'✅' if email_ok else '❌'}")

    if redis_ok and email_ok:
        print("\n🎉 TESTE COMPLETO PASSOU!")
        print("✅ Redis está funcionando e email foi enviado com sucesso!")
    elif redis_ok and not email_ok:
        print("\n⚠️ REDIS OK, MAS PROBLEMA NO ENVIO")
        print("🔧 Verifique as credenciais SMTP ou configuração de email")
    elif not redis_ok:
        print("\n❌ PROBLEMA NO REDIS")
        print("🔧 Verifique se REDIS_URL está configurada e o serviço está rodando")

    print("\n💡 DICAS:")
    print("- Certifique-se que o servidor está rodando em http://localhost:5000")
    print("- Verifique se as credenciais SMTP estão corretas no .env")
    print("- Teste manualmente através da interface web")

if __name__ == "__main__":
    main()