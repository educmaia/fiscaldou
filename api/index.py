from flask import Flask, request, render_template_string
import os
import re
from datetime import datetime

app = Flask(__name__)

def clean_html(text):
    """Remove HTML tags from text for better readability."""
    if not text:
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Clean up extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# Template HTML inline (sem arquivos externos)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FiscalDOU - Monitoramento DOU</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { 
            color: #333; 
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .status {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
        }
        .info {
            background: #f0f8ff;
            border: 1px solid #2196f3;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .feature {
            background: #f9f9f9;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 15px 0;
        }
        .env-vars {
            background: #fffacd;
            border: 1px solid #ffd700;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .github-link {
            text-align: center;
            margin: 30px 0;
        }
        .github-link a {
            background: #333;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }
        .github-link a:hover {
            background: #555;
        }
        ul { list-style-type: none; padding: 0; }
        li { 
            background: white; 
            margin: 10px 0; 
            padding: 10px; 
            border-radius: 5px; 
            border-left: 3px solid #2196f3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏛️ FiscalDOU</h1>
        <h2 style="text-align: center; color: #666;">Sistema de Monitoramento do Diário Oficial da União</h2>
        
        <div class="status">
            ✅ <strong>Aplicação deployada com sucesso no Vercel!</strong><br>
            <small>Deploy realizado em: {{ deploy_time }}</small>
        </div>

        <div class="info">
            <h3>📋 Sobre o Sistema</h3>
            <p>O FiscalDOU é uma aplicação completa para monitoramento automatizado do Diário Oficial da União (DOU), 
            com funcionalidades de busca inteligente, resumos com IA e notificações por email.</p>
        </div>

        <div class="feature">
            <h3>🚀 Funcionalidades Principais</h3>
            <ul>
                <li>🔍 <strong>Busca Automatizada:</strong> Pesquisa diária no DOU por termos específicos</li>
                <li>🤖 <strong>Resumos com IA:</strong> Geração de resumos inteligentes usando OpenAI</li>
                <li>📧 <strong>Notificações:</strong> Sistema de emails automáticos para usuários cadastrados</li>
                <li>🌐 <strong>Interface Web:</strong> Painel para gestão de emails e termos de busca</li>
                <li>📊 <strong>Dashboard:</strong> Visualização de resultados e estatísticas</li>
            </ul>
        </div>

        <div class="env-vars">
            <h3>⚙️ Configuração das Variáveis de Ambiente</h3>
            <p><strong>Status das configurações:</strong></p>
            <ul>
                <li>OpenAI API Key: {{ 'Configurada ✅' if openai_key else 'Não configurada ❌' }}</li>
                <li>SMTP Server: {{ smtp_server or 'Não configurado ❌' }}</li>
                <li>SMTP User: {{ smtp_user or 'Não configurado ❌' }}</li>
                <li>SMTP Pass: {{ 'Configurada ✅' if smtp_pass else 'Não configurada ❌' }}</li>
            </ul>
        </div>

        <div class="info">
            <h3>🔧 Versão Serverless</h3>
            <p>Esta é uma versão adaptada para o ambiente serverless do Vercel. 
            Para funcionalidades completas incluindo scheduler e processamento de arquivos, 
            consulte o código fonte no GitHub.</p>
        </div>

        <div class="github-link">
            <a href="https://github.com/educmaia/fiscaldou" target="_blank">
                📂 Ver Código Fonte no GitHub
            </a>
        </div>

        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
            <p>Desenvolvido para monitoramento eficiente do DOU</p>
            <p>Deploy automático via GitHub → Vercel</p>
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    """Página principal com status do deploy e configurações."""
    
    # Verificar variáveis de ambiente
    openai_key = bool(os.getenv('OPENAI_API_KEY'))
    smtp_server = os.getenv('SMTP_SERVER', '')
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_pass = bool(os.getenv('SMTP_PASS'))
    
    deploy_time = datetime.now().strftime('%d/%m/%Y às %H:%M:%S UTC')
    
    return render_template_string(HTML_TEMPLATE, 
                                openai_key=openai_key,
                                smtp_server=smtp_server,
                                smtp_user=smtp_user,
                                smtp_pass=smtp_pass,
                                deploy_time=deploy_time)

@app.route('/health')
def health():
    """Endpoint de health check."""
    return {
        "status": "ok",
        "service": "FiscalDOU",
        "timestamp": datetime.now().isoformat(),
        "environment": "production",
        "platform": "vercel"
    }

@app.route('/config')
def config():
    """Endpoint para verificar configurações (sem expor valores sensíveis)."""
    return {
        "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
        "smtp_configured": bool(os.getenv('SMTP_SERVER') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASS')),
        "environment_variables": {
            "OPENAI_API_KEY": "configured" if os.getenv('OPENAI_API_KEY') else "missing",
            "SMTP_SERVER": "configured" if os.getenv('SMTP_SERVER') else "missing",
            "SMTP_USER": "configured" if os.getenv('SMTP_USER') else "missing", 
            "SMTP_PASS": "configured" if os.getenv('SMTP_PASS') else "missing"
        }
    }

# Export the Flask app for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True)