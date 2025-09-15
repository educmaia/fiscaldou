#!/usr/bin/env python3
"""
Teste específico para o botão "Buscar Todas as Sugestões"
"""

import requests

def test_search_suggestions_button():
    """Testa se o botão funciona sem exigir email"""

    BASE_URL = "http://localhost:5000"  # Ajuste conforme necessário

    print("=== Teste: Botão 'Buscar Todas as Sugestões' ===")

    try:
        # Simula o clique no botão "Buscar Todas as Sugestões"
        form_data = {
            'action': 'search_all_suggestions'
        }

        print("Enviando requisição POST com action=search_all_suggestions...")

        response = requests.post(BASE_URL, data=form_data, timeout=30)

        if response.status_code == 200:
            response_text = response.text

            # Verifica se NÃO contém a mensagem de erro de email
            if "Por favor, forneça um email válido" in response_text:
                print("❌ FALHOU: Ainda está pedindo email válido")
                return False

            # Verifica se contém indicações de busca por sugestões
            success_indicators = [
                "Busca por todas as sugestões",
                "artigos encontrados",
                "termos sugeridos",
                "Nenhum artigo encontrado para as sugestões"
            ]

            found_indicators = []
            for indicator in success_indicators:
                if indicator in response_text:
                    found_indicators.append(indicator)

            if found_indicators:
                print("✅ SUCESSO: Botão funcionou corretamente!")
                print(f"   Indicadores encontrados: {found_indicators}")

                # Extrai a mensagem de resultado
                if "Busca por todas as sugestões" in response_text:
                    # Tenta extrair a mensagem
                    import re
                    pattern = r'Busca por todas as sugestões[^<]*'
                    match = re.search(pattern, response_text)
                    if match:
                        print(f"   Resultado: {match.group()}")

                return True
            else:
                print("⚠️  INCERTO: Não encontrou indicadores de sucesso")
                print("   Primeiros 500 caracteres da resposta:")
                print(response_text[:500] + "...")
                return False
        else:
            print(f"❌ ERRO HTTP: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def test_other_actions():
    """Testa se outras ações ainda funcionam corretamente"""

    BASE_URL = "http://localhost:5000"

    print("\n=== Teste: Outras Ações ===")

    # Testa busca normal
    try:
        form_data = {
            'search_term': 'teste',
            'use_ai': 'off'
        }

        print("Testando busca normal...")
        response = requests.post(BASE_URL, data=form_data, timeout=15)

        if response.status_code == 200:
            if "Por favor, forneça um email válido" not in response.text:
                print("✅ Busca normal funcionando")
            else:
                print("❌ Busca normal com problema")
        else:
            print(f"⚠️  Busca normal: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Erro na busca normal: {e}")

    # Testa cadastro de email
    try:
        form_data = {
            'email': 'teste@exemplo.com',
            'action': 'register'
        }

        print("Testando cadastro de email...")
        response = requests.post(BASE_URL, data=form_data, timeout=15)

        if response.status_code == 200:
            if "cadastrado com sucesso" in response.text:
                print("✅ Cadastro de email funcionando")
            elif "já está cadastrado" in response.text:
                print("✅ Cadastro de email funcionando (já existia)")
            else:
                print("⚠️  Cadastro de email com resposta inesperada")
        else:
            print(f"⚠️  Cadastro de email: HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Erro no cadastro: {e}")

def main():
    """Função principal"""
    print("🚀 TESTE DO BOTÃO 'BUSCAR TODAS AS SUGESTÕES'")
    print("=" * 50)

    # Teste principal
    success = test_search_suggestions_button()

    # Testes auxiliares
    test_other_actions()

    # Resultado final
    print("\n" + "=" * 50)
    if success:
        print("🎉 TESTE PASSOU!")
        print("✅ O botão 'Buscar Todas as Sugestões' está funcionando sem exigir email!")
    else:
        print("❌ TESTE FALHOU!")
        print("🔧 O botão ainda tem problemas - verifique o código")

    print("\n💡 DICAS:")
    print("- Certifique-se que o servidor está rodando em http://localhost:5000")
    print("- Teste manualmente clicando no botão na interface web")
    print("- Verifique os logs do servidor para mais detalhes")

if __name__ == "__main__":
    main()