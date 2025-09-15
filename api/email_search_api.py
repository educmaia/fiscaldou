from flask import Flask, request, jsonify
import os
import sys

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_search_manager import email_search_manager

app = Flask(__name__)

# ===================== ROTAS PARA EMAILS =====================

@app.route('/emails', methods=['GET'])
def get_emails():
    """Lista todos os emails"""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        emails = email_search_manager.get_all_emails(active_only=active_only)

        return jsonify({
            "success": True,
            "emails": emails,
            "count": len(emails)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/emails', methods=['POST'])
def add_email():
    """Adiciona um novo email"""
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({"error": "Email é obrigatório"}), 400

        email = data['email']
        name = data.get('name', '') 
        active = data.get('active', True)

        success = email_search_manager.add_email(email, name, active)

        if success:
            return jsonify({
                "success": True,
                "message": f"Email {email} adicionado com sucesso"
            })
        else:
            return jsonify({"error": "Falha ao adicionar email"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/emails/<email>', methods=['GET'])
def get_email(email):
    """Recupera dados de um email específico"""
    try:
        email_data = email_search_manager.get_email(email)

        if email_data:
            return jsonify({
                "success": True,
                "email": email_data
            })
        else:
            return jsonify({
                "success": False,
                "message": "Email não encontrado"
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/emails/<email>', methods=['PUT'])
def update_email(email):
    """Atualiza dados de um email"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados de atualização necessários"}), 400

        name = data.get('name')
        active = data.get('active')

        success = email_search_manager.update_email(email, name=name, active=active)

        if success:
            return jsonify({
                "success": True,
                "message": f"Email {email} atualizado com sucesso"
            })
        else:
            return jsonify({"error": "Email não encontrado ou falha na atualização"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/emails/<email>', methods=['DELETE'])
def delete_email(email):
    """Remove um email"""
    try:
        success = email_search_manager.remove_email(email)

        if success:
            return jsonify({"success": True, "message": f"Email {email} removido com sucesso"})
        else:
            return jsonify({"success": False, "message": "Email não encontrado"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================== ROTAS PARA TERMOS DE BUSCA =====================

@app.route('/search-terms', methods=['GET']) 
def get_search_terms() -> str:
    """Lista termos de busca"""

    try:
        category = request.args.get('category')
        active_only = request.args.get('active_only', 'false').lower() == 'true'

        terms = email_search_manager.get_search_terms(
            category=category,
            active_only=active_only
        )

        return jsonify({
            "success": True,
            "search_terms": terms,
            "count": len(terms)
        })\

    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/search-terms', methods=['POST']) 
def add_search_term() -> str:
    """Adiciona um novo termo de busca"""
    try:
        data = request.get_json()
        if not data or 'term' not in data:
            return jsonify({"error": "Termo é obrigatório"}), 400

        term = data['term']
        category = data.get('category', 'geral')
        active = data.get('active', True)

        success = email_search_manager.add_search_term(term, category, active)

        if success:
            return jsonify({
                "success": True,
                "message": f"Termo '{term}' adicionado com sucesso"
            })
        else:
            return jsonify({"error": "Falha ao adicionar termo"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/search-terms/<term_id>', methods=['GET']) 
def get_search_term(term_id: str) -> str:
    """Recupera dados de um termo específico""" 
    try:
        term_data = email_search_manager.get_search_term(term_id)

        if term_data:
            return jsonify({
                "success": True,
                "search_term": term_data
            })       
        else:
            return jsonify({
                "success": False,
                "message": "Termo não encontrado"
            }), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search-terms/<term_id>', methods=['PUT']) 
def update_search_term(term_id: str) -> str:
    """Atualiza um termo de busca""" 
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados de atualização necessários"}), 400

        success = email_search_manager.update_search_term(term_id, **data)

        if success:
            return jsonify({
                "success": True,
                "message": f"Termo {term_id} atualizado com sucesso"
            })        
        else:
            return jsonify({"error": "Termo não encontrado ou falha na atualização"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search-terms/<term_id>', methods=['DELETE']) 
def delete_search_term(term_id: str) -> str:
    """Remove um termo de busca"""
    try:
        success = email_search_manager.remove_search_term(term_id)

        if success:
            return jsonify({
                "success": True,
                "message": f"Termo {term_id} removido com sucesso"
            })        
        else:
            return jsonify({"error": "Termo não encontrado"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search-terms/<term_id>/search', methods=['POST']) 
def increment_search_count(term_id: str) -> str:
    """Incrementa contador de busca de um termo""" 
    try:
        success = email_search_manager.increment_search_count(term_id)

        if success:
            return jsonify({
                "success": True,
                "message": f"Contador do termo {term_id} incrementado"
            })        
        else:
            return jsonify({"error": "Termo não encontrado"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===================== ROTAS DE UTILIDADE =====================

@app.route('/stats', methods=['GET'])
def get_stats() -> str:
    """Retorna estatísticas do sistema""" 
    try:
        stats = email_search_manager.get_stats()
        return jsonify({
            "success": True,
            "stats": stats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET']) 
def health_check() -> str:
    """Verifica se o sistema está funcionando""" 
    try:
        # Testa conexão Redis
        email_search_manager.redis.client.ping()

        return jsonify({
            "success": True,
            "message": "Sistema funcionando normalmente",
            "redis_connected": True
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "redis_connected": False
        }), 500

# ===================== OPERAÇÕES EM LOTE =====================

@app.route('/emails/bulk', methods=['POST'])
def bulk_add_emails() -> str:
    """Adiciona múltiplos emails de uma vez""" 
    try:
        data = request.get_json()
        if not data or 'emails' not in data:
            return jsonify({"error": "Lista de emails necessária"}), 400

        emails = data['emails']
        results = []

        for email_data in emails:
            if isinstance(email_data, str):
                # Se for apenas string, usa como email
                success = email_search_manager.add_email(email_data)
                results.append({"email": email_data, "success": success})

            elif isinstance(email_data, dict) and 'email' in email_data:
                # Se for objeto, extrai dados
                email = email_data['email']
                name = email_data.get('name', '')
                active = email_data.get('active', True)
                success = email_search_manager.add_email(email, name, active)
                results.append({"email": email, "success": success})

        successful = sum(1 for r in results if r['success'])

        return jsonify({
            "success": True,
            "message": f"{successful}/{len(results)} emails adicionados com sucesso",
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/search-terms/bulk', methods=['POST'])
def bulk_add_search_terms() -> str:
    """Adiciona múltiplos termos de busca""" 
    try:
        data = request.get_json()
        if not data or 'terms' not in data:
            return jsonify({"error": "Lista de termos necessária"}), 400

        terms = data['terms']
        results = []

        for term_data in terms:
            if isinstance(term_data, str):
                # Se for apenas string, usa como termo
                success = email_search_manager.add_search_term(term_data)
                results.append({"term": term_data, "success": success})

            elif isinstance(term_data, dict) and 'term' in term_data:
                # Se for objeto, extrai dados
                term = term_data['term']
                category = term_data.get('category', 'geral') 
                active = term_data.get('active', True)
                success = email_search_manager.add_search_term(term, category, active)
                results.append({"term": term, "success": success})

        successful = sum(1 for r in results if r['success'])

        return jsonify({
            "success": True,
            "message": f"{successful}/{len(results)} termos adicionados com sucesso",
            "results": results
        })

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)