# 📧 Sistema Redis para Emails e Termos de Busca

Este sistema permite armazenar e gerenciar emails e termos de busca usando Redis na Vercel.

## 🚀 Arquivos Criados

- `redis_client.py` - Cliente Redis singleton
- `email_search_manager.py` - Gerenciador principal
- `api/email_search_api.py` - APIs REST
- `integration_example.py` - Exemplos de integração

## 📋 Como Usar

### 1. Configuração Inicial

```python
from email_search_manager import email_search_manager

# Adicionar emails
email_search_manager.add_email("admin@empresa.com", "Admin", active=True)

# Adicionar termos de busca
email_search_manager.add_search_term("licitação", "contratos", active=True)
```

### 2. APIs Disponíveis

#### Emails
- `GET /emails` - Lista emails
- `POST /emails` - Adiciona email
- `GET /emails/<email>` - Busca email específico
- `PUT /emails/<email>` - Atualiza email
- `DELETE /emails/<email>` - Remove email

#### Termos de Busca
- `GET /search-terms` - Lista termos
- `POST /search-terms` - Adiciona termo
- `GET /search-terms/<term_id>` - Busca termo específico
- `PUT /search-terms/<term_id>` - Atualiza termo
- `DELETE /search-terms/<term_id>` - Remove termo

### 3. Exemplos de Uso via API

#### Adicionar Email
```bash
curl -X POST http://localhost:5000/emails \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@email.com",
    "name": "Usuário Teste",
    "active": true
  }'
```

#### Adicionar Termo de Busca
```bash
curl -X POST http://localhost:5000/search-terms \
  -H "Content-Type: application/json" \
  -d '{
    "term": "pregão eletrônico",
    "category": "licitacao",
    "active": true
  }'
```

#### Listar Emails Ativos
```bash
curl "http://localhost:5000/emails?active_only=true"
```

#### Estatísticas do Sistema
```bash
curl "http://localhost:5000/stats"
```

### 4. Integração com Sistema Principal

```python
from integration_example import process_dou_article, get_notification_emails

# Processar artigo do DOU
content = "Pregão eletrônico nº 123..."
result = process_dou_article(content)

if result["relevant"]:
    emails = result["notification_emails"]
    terms = result["found_terms"]
    # Enviar notificações...
```

### 5. Operações em Lote

#### Adicionar Múltiplos Emails
```bash
curl -X POST http://localhost:5000/emails/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      {"email": "email1@test.com", "name": "User 1"},
      {"email": "email2@test.com", "name": "User 2"},
      "email3@test.com"
    ]
  }'
```

#### Adicionar Múltiplos Termos
```bash
curl -X POST http://localhost:5000/search-terms/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "terms": [
      {"term": "licitação", "category": "contratos"},
      {"term": "pregão", "category": "contratos"},
      "concorrência pública"
    ]
  }'
```

## 🔧 Estrutura de Dados

### Email
```json
{
  "email": "user@example.com",
  "name": "Nome do Usuário",
  "active": true,
  "created_at": "2024-09-15T10:00:00",
  "updated_at": "2024-09-15T10:00:00"
}
```

### Termo de Busca
```json
{
  "term": "pregão eletrônico",
  "term_id": "pregao_eletronico",
  "category": "licitacao",
  "active": true,
  "search_count": 15,
  "last_search": "2024-09-15T10:00:00",
  "created_at": "2024-09-15T10:00:00",
  "updated_at": "2024-09-15T10:00:00"
}
```

## 📊 Categorias Sugeridas

- `licitacao` - Pregões, concorrências, etc.
- `contrato` - Contratos administrativos
- `pessoal` - Nomeações, exonerações
- `empresa` - CNPJ, razão social específicos
- `geral` - Termos gerais

## 🔍 Funcionalidades

### Emails
- ✅ Adicionar/remover emails
- ✅ Ativar/desativar notificações
- ✅ Listar emails ativos
- ✅ Operações em lote

### Termos de Busca
- ✅ Adicionar/remover termos
- ✅ Categorizar termos
- ✅ Contador de uso
- ✅ Filtrar por categoria
- ✅ Ativar/desativar termos

### Utilidades
- ✅ Estatísticas do sistema
- ✅ Health check
- ✅ Busca em conteúdo
- ✅ Integração com notificações

## 🚀 Deploy na Vercel

1. A variável `REDIS_URL` já está configurada no `.env`
2. O `requirements.txt` inclui `redis==5.0.1`
3. O sistema está pronto para produção

## 💡 Dicas de Uso

1. **Performance**: Use `active_only=true` para listar apenas itens ativos
2. **Categorias**: Organize termos por categoria para melhor gestão
3. **Estatísticas**: Monitore quais termos são mais buscados
4. **Health Check**: Use `/health` para verificar se Redis está funcionando
5. **Lote**: Use operações em lote para inserção de muitos dados

## 🔧 Manutenção

```python
# Verificar estatísticas
stats = email_search_manager.get_stats()

# Buscar termos mais usados
terms = email_search_manager.get_search_terms()
most_used = sorted(terms, key=lambda x: x.get('search_count', 0), reverse=True)

# Limpar termos inativos antigos
# (implementar conforme necessidade)
```