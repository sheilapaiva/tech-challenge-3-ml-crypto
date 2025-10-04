# Guia de Deploy (Local com Docker)

## Pré-requisitos
- Docker + Docker Compose
- Porta livre: 5432, 8000, 8501

## Estrutura
tech-challenge-ml-crypto/
├─ api/
│  ├─ main.py, train.py, ingest.py, ...
│  └─ models/            # montado como volume
├─ dashboard/
│  └─ app.py
├─ sql/
│  └─ schema.sql
├─ docker/
│  ├─ Dockerfile.api
│  ├─ Dockerfile.dashboard
│  └─ docker-compose.yml
└─ .env.example

## Variáveis de Ambiente
- `DATABASE_URL` (API): ex. `postgresql+psycopg2://postgres:postgres@db:5432/postgres`
- `API_BASE_URL` (Dashboard): ex. `http://api:8000`

## Subir os serviços
```bash
cd docker
docker compose up --build
```

- API: http://localhost:8000/docs

- Dashboard: http://localhost:8501

## Volumes

- pgdata → dados do Postgres.

- ../api/models:/app/api/models → artefatos do modelo no host (api/models).

## Primeira execução (passo a passo)

1. Acesse o Dashboard.

2. Ingerir agora (baixa últimos candles).

3. Treinar modelo (gera model.pkl).

4. Prever próximo fechamento (usa o modelo salvo).

## Reset (limpar tudo)

```bash
docker compose down -v
# (opcional) apagar modelos no host
rm -f ../api/models/*.pkl
```

## Logs úteis

```bash
# API
docker compose logs -f api
# Dashboard
docker compose logs -f dashboard
# DB
docker compose logs -f db
```

## Problemas comuns

- Modelo não encontrado: treinar antes de prever.

- Poucos dados: aumente limit em /ingest/run?limit=1000.

- Conflito de portas: verifique se 8000/8501/5432 estão livres.