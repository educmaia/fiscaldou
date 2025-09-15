import redis
import json
from datetime import datetime

# Sua conexão Redis que já funciona
r = redis.Redis.from_url("redis://default:oGJa1ny0G2E4ZLgZT3SQqMF83dYe05io@redis-12998.c15.us-east-1-4.ec2.redns.redis-cloud.com:12998")

def test_basic_connection():
    """Testa conexão básica"""
    print("=== Testando Conexão ===")
    success = r.set("test_connection", "ok")
    result = r.get("test_connection")
    print(f"Conexão: {'✓' if result else '✗'}")
    print(f"Resultado: {result.decode('utf-8') if result else 'None'}")
    return bool(result)

def setup_demo_data():
    """Configura dados de demonstração"""
    print("\n=== Configurando Dados Demo ===")

    # Emails
    emails = [
        {"email": "admin@empresa.com", "name": "Administrador"},
        {"email": "juridico@empresa.com", "name": "Jurídico"},
        {"email": "compras@empresa.com", "name": "Compras"}
    ]

    for email_data in emails:
        email = email_data["email"]
        data = {
            "email": email,
            "name": email_data["name"],
            "active": True,
            "created_at": datetime.now().isoformat()
        }

        r.set(f"email:{email}", json.dumps(data))
        r.sadd("emails:all", email)
        r.sadd("emails:active", email)
        print(f"Email adicionado: {email}")

    # Termos de busca
    terms = [
        {"term": "pregão eletrônico", "category": "licitacao"},
        {"term": "licitação", "category": "licitacao"},
        {"term": "contrato administrativo", "category": "contrato"},
        {"term": "CNPJ 12.345.678/0001-90", "category": "empresa"}
    ]

    for term_data in terms:
        term = term_data["term"]
        term_id = term.lower().replace(" ", "_").replace("/", "_").replace("-", "_")

        data = {
            "term": term,
            "term_id": term_id,
            "category": term_data["category"],
            "active": True,
            "search_count": 0,
            "created_at": datetime.now().isoformat()
        }

        r.set(f"term:{term_id}", json.dumps(data))
        r.sadd("terms:all", term_id)
        r.sadd(f"terms:{term_data['category']}", term_id)
        r.sadd("terms:active", term_id)
        print(f"Termo adicionado: {term} (ID: {term_id})")

def test_search():
    """Testa busca em conteúdo"""
    print("\n=== Testando Busca ===")

    content = """
    PREGÃO ELETRÔNICO Nº 123/2024

    Objeto: Aquisição de equipamentos de informática

    A empresa XYZ Ltda, CNPJ 12.345.678/0001-90, foi classificada
    em primeiro lugar na licitação e irá assinar contrato administrativo
    no valor de R$ 50.000,00.
    """

    # Busca termos ativos
    term_ids = r.smembers("terms:active")
    found_terms = []
    content_lower = content.lower()

    print(f"Conteúdo a ser analisado:")
    print(content[:100] + "...")

    for term_id in term_ids:
        term_id_str = term_id.decode('utf-8') if isinstance(term_id, bytes) else term_id
        term_data_raw = r.get(f"term:{term_id_str}")

        if term_data_raw:
            term_data = json.loads(term_data_raw)
            if term_data["term"].lower() in content_lower:
                # Incrementa contador
                term_data["search_count"] += 1
                term_data["last_search"] = datetime.now().isoformat()
                r.set(f"term:{term_id_str}", json.dumps(term_data))

                found_terms.append(term_data)
                print(f"✓ Encontrado: '{term_data['term']}' (categoria: {term_data['category']})")

    if not found_terms:
        print("Nenhum termo encontrado.")

    return found_terms

def get_notification_emails():
    """Recupera emails para notificação"""
    print("\n=== Emails para Notificação ===")

    emails = r.smembers("emails:active")
    notification_list = []

    for email in emails:
        email_str = email.decode('utf-8') if isinstance(email, bytes) else email
        email_data_raw = r.get(f"email:{email_str}")

        if email_data_raw:
            email_data = json.loads(email_data_raw)
            notification_list.append(email_data)
            print(f"📧 {email_data['email']} ({email_data['name']})")

    return notification_list

def show_stats():
    """Mostra estatísticas"""
    print("\n=== Estatísticas ===")

    total_emails = len(r.smembers("emails:all"))
    active_emails = len(r.smembers("emails:active"))
    total_terms = len(r.smembers("terms:all"))
    active_terms = len(r.smembers("terms:active"))

    print(f"📧 Emails: {active_emails}/{total_emails} ativos")
    print(f"🔍 Termos: {active_terms}/{total_terms} ativos")

    # Termos mais buscados
    print("\n🏆 Termos mais buscados:")
    all_term_ids = r.smembers("terms:all")
    terms_with_count = []

    for term_id in all_term_ids:
        term_id_str = term_id.decode('utf-8') if isinstance(term_id, bytes) else term_id
        term_data_raw = r.get(f"term:{term_id_str}")
        if term_data_raw:
            term_data = json.loads(term_data_raw)
            terms_with_count.append(term_data)

    # Ordena por contador
    sorted_terms = sorted(terms_with_count, key=lambda x: x.get('search_count', 0), reverse=True)

    for i, term in enumerate(sorted_terms[:3], 1):
        print(f"  {i}. '{term['term']}' - {term.get('search_count', 0)} buscas")

def main():
    """Função principal"""
    print("🚀 Teste Redis para FiscalDOU")
    print("=" * 50)

    # Testa conexão
    if not test_basic_connection():
        print("❌ Falha na conexão com Redis!")
        return

    # Configura dados demo
    setup_demo_data()

    # Testa busca
    found_terms = test_search()

    # Lista emails para notificação
    emails = get_notification_emails()

    # Mostra estatísticas
    show_stats()

    # Resultado final
    print("\n" + "=" * 50)
    print("✅ RESULTADO:")
    if found_terms:
        print(f"📋 {len(found_terms)} termos encontrados no conteúdo")
        print(f"📧 {len(emails)} emails receberão notificação")
        print("\nPróximos passos:")
        print("1. Enviar email para:", [e["email"] for e in emails])
        print("2. Termos encontrados:", [t["term"] for t in found_terms])
    else:
        print("🔍 Nenhum termo relevante encontrado no conteúdo")

if __name__ == "__main__":
    main()