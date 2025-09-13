# DOU Notifier

Programa para busca diária no Diário Oficial da União (DOU) via INLABS, usando os termos especificados. Gera resumos com OpenAI, cadastra emails via interface web Flask, envia notificações por email e executa em horário programado.

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

## Notas

- Credenciais hardcoded por simplicidade (atualize o código).
- Logs em console e arquivos para depuração.
- Para produção, use um servidor (ex: Gunicorn para Flask, systemd para scheduler).
