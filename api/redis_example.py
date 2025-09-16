from flask import Flask, request, jsonify
import os
import sys

# Adiciona o diretório raiz ao path para importar o redis_client
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_client import redis_client

app = Flask(__name__)

@app.route('/redis/set', methods=['POST'])
def redis_set():
    """Armazena um valor no Redis"""
    try:
        data = request.get_json()
        if not data or 'key' not in data or 'value' not in data:
            return jsonify({"error": "Key and value are required"}), 400

        key = data['key']
        value = str(data['value'])
        expiry = data.get('expiry', None)  # TTL em segundos

        success = redis_client.set(key, value, ex=expiry)

        if success:
            return jsonify({
                "success": True,
                "message": f"Key '{key}' stored successfully"
            })
        else:
            return jsonify({"error": "Failed to store key"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/redis/get/<key>', methods=['GET'])
def redis_get(key):
    """Recupera um valor do Redis"""
    try:
        value = redis_client.get(key)

        if value is not None:
            return jsonify({
                "success": True,
                "key": key,
                "value": value
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Key '{key}' not found"
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/redis/exists/<key>', methods=['GET'])
def redis_exists(key):
    """Verifica se uma chave existe no Redis"""
    try:
        exists = redis_client.exists(key)
        return jsonify({
            "success": True,
            "key": key,
            "exists": exists
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/redis/delete/<key>', methods=['DELETE'])
def redis_delete(key):
    """Remove uma chave do Redis"""
    try:
        deleted = redis_client.delete(key)

        if deleted:
            return jsonify({
                "success": True,
                "message": f"Key '{key}' deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Key '{key}' not found or already deleted"
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/redis/cache-email', methods=['POST'])
def cache_email():
    """Exemplo específico: cachear dados de email processado"""
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({"error": "Email data is required"}), 400

        email = data['email']
        processed_at = data.get('processed_at', str(datetime.now()))

        # Criar chave única para o email
        cache_key = f"email:processed:{hash(email)}"

        # Dados para cachear
        cache_data = {
            "email": email,
            "processed_at": processed_at,
            "status": "processed"
        }

        # Cache por 24 horas (86400 segundos)
        success = redis_client.set(cache_key, json.dumps(cache_data), ex=86400)

        if success:
            return jsonify({
                "success": True,
                "message": "Email cached successfully",
                "cache_key": cache_key
            })
        else:
            return jsonify({"error": "Failed to cache email"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/redis/health', methods=['GET'])
def redis_health():
    """Verifica se a conexão com Redis está funcionando"""
    try:
        # Tenta fazer ping no Redis
        redis_client.client.ping()
        return jsonify({
            "success": True,
            "message": "Redis connection is healthy"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)