# FiscalDOU API - Implantação no Vercel

Este documento contém instruções para implantar e testar a aplicação FiscalDOU no Vercel.

## Estrutura do Projeto

```
api/
├── app.py              # Aplicação Flask principal
├── index.py            # Aplicação Flask alternativa (legado)
├── fiscaldou.py        # Handler HTTP básico (legado)
├── email_search_api.py # API para busca de emails
├── requirements.txt   # Dependências Python
├── templates/
│   ├── main.html      # Template HTML principal
│   └── static/
│       ├── style.css  # Estilos CSS
│       └── script.js  # Scripts JavaScript
└── storage/           # Módulos de armazenamento
```

## Pré-requisitos

1. **Node.js e npm** - Para instalar a CLI do Vercel
2. **Python 3.9** - Versão compatível com o Vercel
3. **Conta no Vercel** - Para implantar a aplicação

## Configuração do Ambiente

### 1. Instalar a CLI do Vercel

```bash
npm i -g vercel
```

### 2. Configurar variáveis de ambiente

No painel do Vercel, configure as seguintes variáveis de ambiente:

- `INLABS_EMAIL` - Email para acesso ao INLABS
- `INLABS_PASSWORD` - Senha para acesso ao INLABS
- `SMTP_SERVER` - Servidor SMTP (ex: smtp.gmail.com)
- `SMTP_PORT` - Porta SMTP (ex: 587)
- `SMTP_USER` - Usuário SMTP
- `SMTP_PASS` - Senha SMTP
- `OPENAI_API_KEY` - Chave da API OpenAI (opcional, para resumos)
- `EDGE_CONFIG` - ID do Edge Config (opcional, para armazenamento)
- `VERCEL_TOKEN` - Token da API Vercel (opcional, para Edge Config)

## Implantação

### 1. Fazer login no Vercel

```bash
vercel login
```

### 2. Implantar a aplicação

```bash
# Para ambiente de desenvolvimento
vercel

# Para ambiente de produção
vercel --prod
```

## Testes Locais

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Executar localmente

```bash
cd api
python app.py
```

A aplicação estará disponível em `http://localhost:5000`

### 3. Testar com a CLI do Vercel

```bash
vercel dev
```

## Endpoints Principais

- `/` - Página principal
- `/health` - Verificação de saúde
- `/config` - Verificação de configurações
- `/api/cron/daily` - Tarefa agendada para busca diária

## Melhorias Implementadas

1. **Estrutura do Projeto**

   - Criado um novo arquivo `app.py` como ponto de entrada principal
   - Organizado o código em funções modulares e reutilizáveis
   - Implementado logging estruturado para melhor debugging

2. **Configuração do Vercel**

   - Atualizado `vercel.json` para usar o runtime Python 3.9
   - Configurado `rewrites` para redirecionar todas as rotas para o app.py
   - Adicionado headers de segurança

3. **Dependências**

   - Atualizado `requirements.txt` com todas as dependências necessárias
   - Incluído Flask e bibliotecas relacionadas

4. **Gerenciamento de Estado**

   - Implementado Edge Config como armazenamento primário
   - Mantido armazenamento em memória como fallback
   - Melhorado tratamento de erros nas operações de armazenamento

5. **Tratamento de Erros**

   - Adicionado tratamento de erros em todas as funções principais
   - Implementado logging para facilitar debugging
   - Adicionado mensagens de erro amigáveis

6. **Performance**
   - Otimizado funções para execução serverless
   - Implementado cache para operações repetitivas
   - Reduzido tempo de execução das funções

## Boas Práticas

1. **Serverless Functions**

   - Mantenha as funções pequenas e rápidas
   - Evite operações de longa duração
   - Use armazenamento externo para persistência

2. **Variáveis de Ambiente**

   - Nunca armazene credenciais no código
   - Use o painel do Vercel para configurar variáveis sensíveis
   - Documente todas as variáveis necessárias

3. **Logging**

   - Implemente logging estruturado
   - Use níveis de log apropriados (INFO, WARNING, ERROR)
   - Inclua contexto suficiente nos logs

4. **Segurança**
   - Implemente headers de segurança
   - Valide e sanitize todas as entradas
   - Use HTTPS para todas as comunicações

## Solução de Problemas

### Erros Comuns

1. **ModuleNotFoundError**

   - Verifique se todas as dependências estão em `requirements.txt`
   - Certifique-se de que a versão do Python é compatível

2. **Timeout de Função**

   - Reduza o tempo de execução das funções
   - Otimize operações de rede e E/S

3. **Variáveis de Ambiente Não Definidas**
   - Verifique se todas as variáveis estão configuradas no Vercel
   - Reinicie a implantação após alterar variáveis

### Debugging

1. **Logs no Vercel**

   ```bash
   vercel logs
   ```

2. **Executar Localmente**

   ```bash
   vercel dev
   ```

3. **Verificar Configurações**
   - Acesse `/config` para verificar configurações
   - Acesse `/health` para verificar saúde da aplicação
