# ULTRON API

API do sistema de inteligência para marketplaces.

## Setup

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Copiar variáveis de ambiente
cp .env.example .env

# Executar
uvicorn src.main:app --reload
```

## Variáveis de Ambiente (.env)

```env
# Supabase
SUPABASE_URL=sua_url_supabase
SUPABASE_KEY=sua_chave_supabase

# Mercado Livre
ML_CLIENT_ID=seu_client_id
ML_CLIENT_SECRET=seu_client_secret

# Magalu
MAGALU_CLIENT_ID=seu_client_id
MAGALU_CLIENT_SECRET=seu_client_secret

# Redis (para Celery)
REDIS_URL=redis://localhost:6379/0

# BigQuery (opcional)
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

## Endpoints

- `GET /health` - Health check
- `POST /search` - Buscar anúncios
- `POST /audit` - Auditar anúncio
- `POST /suggest-title` - Sugerir títulos
- `POST /extract-keywords` - Extrair keywords

## Documentação

Acesse `/docs` para documentação Swagger.
