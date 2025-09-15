import redis
import json
from datetime import datetime

# Conexão Redis
r = redis.Redis.from_url("redis://default:oGJa1ny0G2E4ZLgZT3SQqMF83dYe05io@redis-12998.c15.us-east-1-4.ec2.redns.redis-cloud.com:12998")

# ===================== FUNÇÕES PARA EMAILS =====================

def add_email(email, name="", active=True):
    """Adiciona um email à lista de monitoramento"""
    email_data = {
        "email": email,
        "name": name,
        "active": active,
        "created_at": datetime.now().isoformat()
    }

    # Armazena dados do email
    r.set(f"email:{email}", json.dumps(email_data))

    # Adiciona à lista de emails
    r.sadd("emails:all", email)
    if active:
        r.sadd("emails:active", email)

    print(f"Email {email} adicionado!")
    return True

def get_emails(active_only=False):
    """Recupera lista de emails"""
    if active_only:
        emails = r.smembers("emails:active")
    else:
        emails = r.smembers("emails:all")

    result = []
    for email in emails:
        email_str = email.decode('utf-8') if isinstance(email, bytes) else email
        email_data = r.get(f"email:{email_str}")
        if email_data:
            result.append(json.loads(email_data))

    return result

def remove_email(email):
    """Remove um email"""
    r.delete(f"email:{email}")
    r.srem("emails:all", email)
    r.srem("emails:active", email)
    print(f"Email {email} removido!")

# ===================== FUNÇÕES PARA TERMOS DE BUSCA =====================

def add_search_term(term, category="geral", active=True):
    """Adiciona um termo de busca"""
    term_id = term.lower().replace(" ", "_")

    term_data = {
        "term": term,
        "term_id": term_id,
        "category": category,
        "active": active,
        "search_count": 0,
        "created_at": datetime.now().isoformat()
    }

    # Armazena dados do termo
    r.set(f"term:{term_id}", json.dumps(term_data))

    # Adiciona às listas
    r.sadd("terms:all", term_id)
    r.sadd(f"terms:{category}", term_id)
    if active:
        r.sadd("terms:active", term_id)

    print(f"Termo '{term}' adicionado!")
    return term_id

def get_search_terms(category=None, active_only=False):
    """Recupera termos de busca"""
    if category:
        term_ids = r.smembers(f"terms:{category}")
    elif active_only:
        term_ids = r.smembers("terms:active")
    else:
        term_ids = r.smembers("terms:all")

    result = []
    for term_id in term_ids:
        term_id_str = term_id.decode('utf-8') if isinstance(term_id, bytes) else term_id
        term_data = r.get(f"term:{term_id_str}")
        if term_data:
            result.append(json.loads(term_data))

    return result

def increment_search_count(term_id):
    """Incrementa contador de busca de um termo"""
    term_data = r.get(f"term:{term_id}")
    if term_data:
        data = json.loads(term_data)
        data["search_count"] += 1
        data["last_search"] = datetime.now().isoformat()
        r.set(f"term:{term_id}", json.dumps(data))

# ===================== BUSCA NO CONTEÚDO =====================

def search_content(content):
    """Busca termos ativos no conteúdo"""
    found_terms = []
    active_terms = get_search_terms(active_only=True)

    content_lower = content.lower()

    for term_data in active_terms:
        if term_data["term"].lower() in content_lower:
            increment_search_count(term_data["term_id"])
            found_terms.append(term_data)

    return found_terms

# ===================== EXEMPLOS DE USO =====================

if __name__ == "__main__":
    print("=== Testando Redis para Emails e Termos ===\n")

    # Teste básico de conexão
    success = r.set("test", "conexao_ok")
    result = r.get("test")
    print(f"Teste conexão: {result.decode('utf-8')}\n")

    # Adicionar emails
    print("1. Adicionando emails:")
    add_email("admin@empresa.com", "Administrador", True)
    add_email("juridico@empresa.com", "Jurídico", True)
    add_email("backup@empresa.com", "Backup", False)

    # Listar emails ativos
    print("\n2. Emails ativos:")
    active_emails = get_emails(active_only=True)
    for email in active_emails:
        print(f"  - {email['email']} ({email['name']})")

    # Adicionar termos de busca
    print("\n3. Adicionando termos de busca:")
    add_search_term("pregão eletrônico", "licitacao")
    add_search_term("licitação", "licitacao")
    add_search_term("contrato administrativo", "contrato")
    add_search_term("CNPJ 12.345.678/0001-90", "empresa")

    # Listar termos por categoria
    print("\n4. Termos de licitação:")
    licitacao_terms = get_search_terms(category="licitacao")
    for term in licitacao_terms:
        print(f"  - {term['term']} (buscas: {term['search_count']})")

    # Teste de busca em conteúdo
    print("\n5. Testando busca em conteúdo:")
    test_content = """
    PREGÃO ELETRÔNICO Nº 123/2024

    Objeto: Aquisição de materiais de escritório

    A empresa com CNPJ 12.345.678/0001-90 foi vencedora
    da licitação e assinará contrato administrativo.
    """

    found = search_content(test_content)
    print(f"Termos encontrados: {len(found)}")
    for term in found:
        print(f"  - '{term['term']}' (categoria: {term['category']})")

    # Ver estatísticas
    print("\n6. Estatísticas:")
    total_emails = len(r.smembers("emails:all"))
    active_emails_count = len(r.smembers("emails:active"))
    total_terms = len(r.smembers("terms:all"))
    active_terms_count = len(r.smembers("terms:active"))

    print(f"  - Total de emails: {total_emails}")
    print(f"  - Emails ativos: {active_emails_count}")
    print(f"  - Total de termos: {total_terms}")
    print(f"  - Termos ativos: {active_terms_count}")

    # Termos mais buscados
    print("\n7. Termos mais buscados:")
    all_terms = get_search_terms()
    sorted_terms = sorted(all_terms, key=lambda x: x['search_count'], reverse=True)
    for term in sorted_terms[:3]:
        print(f"  - '{term['term']}': {term['search_count']} buscas")