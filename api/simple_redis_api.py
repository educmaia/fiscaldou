from flask import Flask, request, jsonify
import redis
import json
from datetime import datetime

app = Flask(__name__)

# Conexão Redis
r = redis.Redis.from_url("redis://default:oGJa1ny0G2E4ZLgZT3SQqMF83dYe05io@redis-12998.c15.us-east-1-4.ec2.redns.redis-cloud.com:12998")

# ===================== ROTAS PARA EMAILS =====================

@app.route('/api/emails', methods=['POST'])
def add_email():
    """Adiciona um email"""
    try:
        data = request.get_json()
        email = data.get('email')
        name = data.get('name', '')
        active = data.get('active', True)

        if not email:
            return jsonify({"error": "Email é obrigatório"}), 400

        email_data = {
            "email": email,
            "name": name,
            "active": active,
            "created_at": datetime.now().isoformat()
        }

        # Armazena no Redis
        r.set(f"email:{email}", json.dumps(email_data))
        r.sadd("emails:all", email)
        if active:
            r.sadd("emails:active", email)

        return jsonify({
            "success": True,
            "message": f"Email {email} adicionado com sucesso"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Lista emails"""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'

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

        return jsonify({
            "success": True,
            "emails": result,
            "count": len(result)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/emails/<email>', methods=['DELETE'])
def remove_email(email):
    """Remove um email"""
    try:
        r.delete(f"email:{email}")
        r.srem("emails:all", email)
        r.srem("emails:active", email)

        return jsonify({
            "success": True,
            "message": f"Email {email} removido com sucesso"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================== ROTAS PARA TERMOS =====================

@app.route('/api/search-terms', methods=['POST'])
def add_search_term():
    """Adiciona um termo de busca"""
    try:
        data = request.get_json()
        term = data.get('term')
        category = data.get('category', 'geral')
        active = data.get('active', True)

        if not term:
            return jsonify({"error": "Termo é obrigatório"}), 400

        term_id = term.lower().replace(" ", "_")

        term_data = {
            "term": term,
            "term_id": term_id,
            "category": category,
            "active": active,
            "search_count": 0,
            "created_at": datetime.now().isoformat()
        }

        # Armazena no Redis
        r.set(f"term:{term_id}", json.dumps(term_data))
        r.sadd("terms:all", term_id)
        r.sadd(f"terms:{category}", term_id)
        if active:
            r.sadd("terms:active", term_id)

        return jsonify({
            "success": True,
            "message": f"Termo '{term}' adicionado com sucesso",
            "term_id": term_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search-terms', methods=['GET'])
def get_search_terms():
    """Lista termos de busca"""
    try:
        category = request.args.get('category')
        active_only = request.args.get('active_only', 'false').lower() == 'true'

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

        return jsonify({
            "success": True,
            "search_terms": result,
            "count": len(result)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/search-terms/<term_id>', methods=['DELETE'])
def remove_search_term(term_id):
    """Remove um termo de busca"""
    try:
        term_data = r.get(f"term:{term_id}")
        if not term_data:
            return jsonify({"error": "Termo não encontrado"}), 404

        data = json.loads(term_data)
        category = data.get('category', 'geral')

        r.delete(f"term:{term_id}")
        r.srem("terms:all", term_id)
        r.srem("terms:active", term_id)
        r.srem(f"terms:{category}", term_id)

        return jsonify({
            "success": True,
            "message": f"Termo {term_id} removido com sucesso"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================== BUSCA NO CONTEÚDO =====================

@app.route('/api/search-content', methods=['POST'])
def search_content():
    """Busca termos no conteúdo fornecido"""
    try:
        data = request.get_json()
        content = data.get('content', '')

        if not content:
            return jsonify({"error": "Conteúdo é obrigatório"}), 400

        # Busca termos ativos
        term_ids = r.smembers("terms:active")
        found_terms = []
        content_lower = content.lower()

        for term_id in term_ids:
            term_id_str = term_id.decode('utf-8') if isinstance(term_id, bytes) else term_id
            term_data = r.get(f"term:{term_id_str}")

            if term_data:
                data = json.loads(term_data)
                if data["term"].lower() in content_lower:
                    # Incrementa contador
                    data["search_count"] += 1
                    data["last_search"] = datetime.now().isoformat()
                    r.set(f"term:{term_id_str}", json.dumps(data))

                    found_terms.append(data)

        # Se encontrou termos, pega emails ativos para notificação
        notification_emails = []
        if found_terms:
            emails = r.smembers("emails:active")
            for email in emails:
                email_str = email.decode('utf-8') if isinstance(email, bytes) else email
                email_data = r.get(f"email:{email_str}")
                if email_data:
                    notification_emails.append(json.loads(email_data))

        return jsonify({
            "success": True,
            "found_terms": found_terms,
            "notification_emails": [e["email"] for e in notification_emails],
            "should_notify": len(found_terms) > 0
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================== ESTATÍSTICAS =====================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retorna estatísticas do sistema"""
    try:
        total_emails = len(r.smembers("emails:all"))
        active_emails = len(r.smembers("emails:active"))
        total_terms = len(r.smembers("terms:all"))
        active_terms = len(r.smembers("terms:active"))

        # Estatísticas por categoria
        categories = {}
        term_ids = r.smembers("terms:all")
        for term_id in term_ids:
            term_id_str = term_id.decode('utf-8') if isinstance(term_id, bytes) else term_id
            term_data = r.get(f"term:{term_id_str}")
            if term_data:
                data = json.loads(term_data)
                category = data.get('category', 'geral')
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1

        return jsonify({
            "success": True,
            "stats": {
                "emails": {
                    "total": total_emails,
                    "active": active_emails
                },
                "search_terms": {
                    "total": total_terms,
                    "active": active_terms
                },
                "categories": categories
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica se Redis está funcionando"""
    try:
        r.ping()
        return jsonify({
            "success": True,
            "message": "Redis conectado com sucesso",
            "redis_connected": True
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "redis_connected": False
        }), 500

if __name__ == '__main__':
    app.run(debug=True)