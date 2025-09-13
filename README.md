# FiscalDOU - Monitoramento do Diário Oficial da União

Aplicação web para monitoramento e busca automatizada no Diário Oficial da União (DOU). Sistema completo com interface web Flask para cadastro de emails, busca inteligente por termos específicos, geração de resumos com IA e notificações automáticas por email.

🔗 **Deploy no Vercel:** [https://vercel.com/joao-silvas-projects-c4cdd3fc/fiscaldou](https://vercel.com/joao-silvas-projects-c4cdd3fc/fiscaldou)

✅ **Status:** Deploy automático configurado - última atualização: 13/09/2025

## Configuração Inicial

1. **Instale as dependências:**

   ```
   pip install -r requirements.txt
   ```

2. **Configure credenciais INLABS (download.py):**

   - Atualize `LOGIN` e `SENHA` com suas credenciais do INLABS (https://inlabs.in.gov.br).

3. **Configure SMTP para emails (notify.py):**

   - Atualize `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` (ex: Gmail com app password).

4. **Configure OpenAI (env var):**

   - Defina `export OPENAI_API_KEY=sk-your-key` (opcional, usa fallback sem API).

5. **Execute o app web para cadastro de emails:**

   ```
   python app.py
   ```

   - Acesse http://localhost:5000 para cadastrar/remover emails (armazenados em emails.db).

6. **Execute o scheduler para buscas diárias:**
   ```
   python main.py
   ```
   - Rodará diariamente às 8h. Press Ctrl+C para parar.

## Funcionamento

- **Download:** Baixa XMLs do DOU de hoje (todas seções).
- **Extração:** Descompacta e extrai texto de artigos.
- **Busca:** Procura termos: "23001.000069/2025-95", "Resolução CNE/CES nº 2/2024", "reconhecimento de diplosmas de pós-graduação stricto sensu obtidos no exterior", "Parecer 589/2025".
- **Resumo:** Gera resumos elaborados com OpenAI ou trechos simples.
- **Notificação:** Envia HTML email com resumos para emails cadastrados.

## Diretórios

- `downloads/`: ZIPs baixados por data.
- `extracted/`: XMLs extraídos por data.
- `logs/`: Logs de execução.
- `emails.db`: Banco de emails cadastrados.

## Teste Manual

```
python -c "from search import find_matches; from summarize import summarize_matches; from notify import send_notifications; m = find_matches(); if m: s = summarize_matches(m); send_notifications(s)"
```

## Deploy no Vercel

### Configuração das Variáveis de Ambiente

No painel do Vercel, configure as seguintes variáveis de ambiente:

```
OPENAI_API_KEY=sua_chave_openai_aqui
SMTP_SERVER=smtp.gmail.com  
SMTP_PORT=465
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_app_gmail
```

### Conectar Repositório GitHub

1. Acesse [Vercel Dashboard](https://vercel.com/dashboard)
2. Clique em "New Project"
3. Conecte com GitHub e selecione o repositório `fiscaldou`
4. Configure as variáveis de ambiente
5. Deploy automático a cada push na branch `main`

### Estrutura de Arquivos para Vercel

- `vercel.json` - Configuração do runtime Python
- `requirements.txt` - Dependências Python
- `app.py` - Aplicação Flask principal

## Notas

- Variáveis de ambiente gerenciadas pelo Vercel
- Logs disponíveis no painel do Vercel
- Deploy automático via GitHub integration
- Banco SQLite local (não persistente entre deployments)
