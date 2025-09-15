"""
Exemplo de integração do Redis com o sistema FiscalDOU
"""

from email_search_manager import email_search_manager
import json

def setup_initial_data():
    """
    Configuração inicial de emails e termos de busca
    Execute uma vez para popular o Redis
    """

    # ===== EMAILS DE EXEMPLO =====
    emails_to_add = [
        {"email": "admin@empresa.com", "name": "Administrador", "active": True},
        {"email": "juridico@empresa.com", "name": "Departamento Jurídico", "active": True},
        {"email": "compras@empresa.com", "name": "Departamento de Compras", "active": True},
        {"email": "backup@empresa.com", "name": "Email Backup", "active": False}
    ]

    print("Adicionando emails...")
    for email_data in emails_to_add:
        success = email_search_manager.add_email(
            email_data["email"],
            email_data["name"],
            email_data["active"]
        )
        print(f"Email {email_data['email']}: {'✓' if success else '✗'}")

    # ===== TERMOS DE BUSCA =====
    search_terms_to_add = [
        # Licitações
        {"term": "pregão eletrônico", "category": "licitacao", "active": True},
        {"term": "tomada de preços", "category": "licitacao", "active": True},
        {"term": "concorrência pública", "category": "licitacao", "active": True},

        # Contratos
        {"term": "contrato administrativo", "category": "contrato", "active": True},
        {"term": "aditivo contratual", "category": "contrato", "active": True},
        {"term": "rescisão contratual", "category": "contrato", "active": True},

        # Nomeações
        {"term": "nomeação", "category": "pessoal", "active": True},
        {"term": "exoneração", "category": "pessoal", "active": True},
        {"term": "aposentadoria", "category": "pessoal", "active": False},

        # Termos específicos da empresa
        {"term": "CNPJ 12.345.678/0001-90", "category": "empresa", "active": True},
        {"term": "Razão Social Ltda", "category": "empresa", "active": True}
    ]

    print("\nAdicionando termos de busca...")
    for term_data in search_terms_to_add:
        success = email_search_manager.add_search_term(
            term_data["term"],
            term_data["category"],
            term_data["active"]
        )
        print(f"Termo '{term_data['term']}': {'✓' if success else '✗'}")

def search_in_dou_content(content: str) -> dict:
    """
    Busca termos ativos no conteúdo do DOU
    Retorna quais termos foram encontrados
    """
    found_terms = []
    active_terms = email_search_manager.get_search_terms(active_only=True)

    for term_data in active_terms:
        term = term_data["term"].lower()
        term_id = term_data["term_id"]

        if term in content.lower():
            # Incrementa contador de uso do termo
            email_search_manager.increment_search_count(term_id)

            found_terms.append({
                "term": term_data["term"],
                "term_id": term_id,
                "category": term_data["category"]
            })

    return {
        "found_terms": found_terms,
        "total_found": len(found_terms)
    }

def get_notification_emails() -> list:
    """
    Recupera lista de emails ativos para notificação
    """
    active_emails = email_search_manager.get_all_emails(active_only=True)
    return [email["email"] for email in active_emails]

def process_dou_article(article_content: str, article_title: str = "") -> dict:
    """
    Processa um artigo do DOU verificando termos de busca
    """
    # Combina título e conteúdo para busca
    full_content = f"{article_title} {article_content}"

    # Busca termos no conteúdo
    search_results = search_in_dou_content(full_content)

    # Se encontrou termos relevantes, prepare para notificação
    if search_results["total_found"] > 0:
        notification_emails = get_notification_emails()

        return {
            "relevant": True,
            "found_terms": search_results["found_terms"],
            "notification_emails": notification_emails,
            "summary": f"Encontrados {search_results['total_found']} termos relevantes"
        }

    return {
        "relevant": False,
        "found_terms": [],
        "notification_emails": [],
        "summary": "Nenhum termo relevante encontrado"
    }

def manage_subscription(email: str, action: str, **kwargs) -> dict:
    """
    Gerencia inscrições de email
    Actions: 'subscribe', 'unsubscribe', 'activate', 'deactivate'
    """
    if action == "subscribe":
        name = kwargs.get("name", "")
        success = email_search_manager.add_email(email, name, active=True)
        return {"success": success, "message": "Email inscrito" if success else "Falha na inscrição"}

    elif action == "unsubscribe":
        success = email_search_manager.remove_email(email)
        return {"success": success, "message": "Email removido" if success else "Email não encontrado"}

    elif action == "activate":
        success = email_search_manager.update_email(email, active=True)
        return {"success": success, "message": "Email ativado" if success else "Falha na ativação"}

    elif action == "deactivate":
        success = email_search_manager.update_email(email, active=False)
        return {"success": success, "message": "Email desativado" if success else "Falha na desativação"}

    return {"success": False, "message": "Ação inválida"}

def get_system_stats() -> dict:
    """
    Retorna estatísticas completas do sistema
    """
    stats = email_search_manager.get_stats()

    # Adiciona informações extras
    active_emails = email_search_manager.get_all_emails(active_only=True)
    active_terms = email_search_manager.get_search_terms(active_only=True)

    # Estatísticas por categoria
    category_stats = {}
    for term in active_terms:
        category = term["category"]
        if category not in category_stats:
            category_stats[category] = {"count": 0, "total_searches": 0}

        category_stats[category]["count"] += 1
        category_stats[category]["total_searches"] += term.get("search_count", 0)

    return {
        "basic_stats": stats,
        "active_emails": len(active_emails),
        "active_terms": len(active_terms),
        "category_breakdown": category_stats,
        "most_searched_terms": sorted(
            active_terms,
            key=lambda x: x.get("search_count", 0),
            reverse=True
        )[:5]
    }

# ===== EXEMPLOS DE USO =====

if __name__ == "__main__":
    print("=== CONFIGURAÇÃO INICIAL ===")
    setup_initial_data()

    print("\n=== ESTATÍSTICAS ===")
    stats = get_system_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    print("\n=== TESTE DE BUSCA ===")
    test_content = """
    PREGÃO ELETRÔNICO Nº 123/2024

    A empresa Razão Social Ltda, CNPJ 12.345.678/0001-90,
    participou da licitação para fornecimento de materiais.

    Foi assinado contrato administrativo no valor de R$ 100.000,00.
    """

    result = process_dou_article(test_content)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== GERENCIAMENTO DE EMAIL ===")
    # Teste de inscrição
    subscription_result = manage_subscription(
        "novo@email.com",
        "subscribe",
        name="Novo Usuário"
    )
    print(f"Inscrição: {subscription_result}")

    # Lista emails ativos
    active_emails = get_notification_emails()
    print(f"Emails ativos: {active_emails}")