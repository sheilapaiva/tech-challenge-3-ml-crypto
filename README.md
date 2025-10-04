# Tech Challenge – ML Crypto 

> Este projeto coleta *candles* do par **BTCUSDT** (Binance), armazena em **PostgreSQL**, treina um modelo de **Machine Learning** (Scikit-learn) para prever o **próximo preço de fechamento** e expõe tudo via **API (FastAPI)** e **Dashboard (Streamlit)**. Toda a solução sobe via **Docker Compose**.

---

## Sumário
- [Arquitetura](#arquitetura)
- [Principais componentes](#principais-componentes)
- [Endpoints da API](#endpoints-da-api)
- [Como executar](#como-executar)
- [Variáveis de ambiente](#variaveis-de-ambiente)
- [Fluxo típico de uso](#fluxo-tipico-de-uso)
- [Esquema de dados](#esquema-de-dados)
- [Treinamento e previsão](#treinamento-e-previsao)
- [Dashboard](#dashboard)
- [Boas práticas implementadas](#boas-praticas-implementadas)
- [Resolução de problemas](#resolucao-de-problemas)
- [Roadmap](#roadmap)
- [Licença](#licenca)

---

<a id="arquitetura"></a>
## Arquitetura
```
┌────────────────────────┐              ┌─────────────────────────┐
│        Streamlit       │   HTTP       │         FastAPI         │
│ (Dashboard + Story)    │ <──────────> │ /ingest /train /predict │
└───────────┬────────────┘              └───────────┬─────────────┘
            │                                          SQLAlchemy
            │
            ▼
   ┌────────────────────┐
   │     PostgreSQL     │
   │   (tabela prices)  │
   └────────────────────┘

      (coleta externa - Binance API)
```

- **Coleta**: endpoint `/ingest/run` chama a API pública da Binance para obter candles (intervalo e quantidade configuráveis).
- **Armazenamento**: Postgres com constraint de unicidade por `(symbol, ts)` evita duplicatas.
- **Modelagem**: features de séries temporais (lags, médias móveis, volatilidade) com alvo **próximo fechamento** (`next_close`).
- **Serving**: `/predict` carrega o modelo versionado (`model.pkl`) e calcula a previsão.
- **Dashboard**: orquestra ingestão, treino e previsão; exibe últimos preços, **último fechamento** e **próximo fechamento (previsto)**.

---

<a id="principais-componentes"></a>
## Principais componentes

```
api/
  main.py           # rotas FastAPI, CORS, swagger, orquestração
  db.py             # engine SQLAlchemy, ORM, inicialização, sessão
  ingest.py         # cliente de coleta na Binance + persistência no Postgres
  features.py       # engenharia de atributos (lags, SMAs, volatilidade)
  train.py          # treinamento (RandomForestRegressor), avaliação, salvamento
  predict.py        # carregamento do modelo e inferência do próximo fechamento
  models/           # pasta montada em volume com model.pkl

dashboard/
  app.py            # UI em Streamlit: Ingerir, Treinar, Prever próximo fechamento

sql/
  schema.sql        # DDL da tabela prices

docker/
  Dockerfile.api
  Dockerfile.dashboard
  docker-compose.yml

docs/
  README (este), ARCHITECTURE, MODEL_CARD, HOWTO_DEPLOY
```

---

<a id="endpoints-da-api"></a>
## Endpoints da API

**Base:** `http://localhost:8000`

| Método | Rota | Descrição |
|:------:|:-----|:----------|
| GET | `/health` | Saúde da API. |
| POST | `/ingest/run?symbol=BTCUSDT&interval=1m&limit=1000` | Coleta candles na Binance e grava no Postgres. |
| GET | `/prices/latest?symbol=BTCUSDT&n=720` | Retorna os últimos `n` candles. |
| POST | `/train?symbol=BTCUSDT` | Treina o modelo e salva `api/models/model.pkl`. |
| POST | `/predict?symbol=BTCUSDT` | **Prevê o próximo fechamento** com base nos dados mais recentes. |
| GET | `/model/info` | Mostra diretório de modelos, existência e listagem de arquivos. |
| GET | `/metrics?limit=50` | Métricas do último treino (RMSE/MAE/R², timestamp, tamanho do dataset, janelas de features etc.). |

> **Nota**: o símbolo padrão **BTCUSDT** representa o par **Bitcoin/Tether** negociado na Binance.

---

<a id="como-executar"></a>
## Como executar

1. **Pré-requisitos**
   - Docker e Docker Compose instalados.
   - Portas `8000` (API) e `8501` (Dashboard) livres.

2. **Subir os serviços**
   ```bash
   cd docker
   docker compose up --build
   ```

3. **Acessos**
   - Dashboard: <http://localhost:8501>  
   - Swagger da API: <http://localhost:8000/docs>

---

<a id="variaveis-de-ambiente"></a>
## Variáveis de ambiente

### API
- `DATABASE_URL`: conexão do Postgres. Ex.:  
  `postgresql+psycopg2://postgres:postgres@db:5432/postgres`
- *(opcional)* `MODELS_DIR`: diretório onde o `model.pkl` é salvo (padrão: `/app/api/models`).

### Dashboard
- `API_BASE_URL`: base da API (padrão no compose: `http://api:8000`).

---

<a id="fluxo-tipico-de-uso"></a>
## Fluxo típico de uso

1. Abra o Dashboard.  
2. Clique **Ingerir agora** para popular a base (`prices`).  
3. Clique **Treinar modelo** e acompanhe as métricas.  
4. Clique **Prever próximo fechamento** e veja:
   - **Último fechamento**
   - **Próximo fechamento (previsto)**
   - **Delta previsto (absoluto e %)**  
5. Visualize séries e métricas; repita o ciclo quando quiser atualizar o modelo.

---

<a id="esquema-de-dados"></a>
## Esquema de dados

**Tabela principal (`prices`):**

```sql
CREATE TABLE IF NOT EXISTS prices (
  id       BIGSERIAL PRIMARY KEY,
  symbol   TEXT NOT NULL,
  ts       TIMESTAMPTZ NOT NULL,
  open     DOUBLE PRECISION NOT NULL,
  high     DOUBLE PRECISION NOT NULL,
  low      DOUBLE PRECISION NOT NULL,
  close    DOUBLE PRECISION NOT NULL, -- 'fechamento' no sentido de negócio
  volume   DOUBLE PRECISION NOT NULL,
  CONSTRAINT uq_prices_symbol_ts UNIQUE (symbol, ts)
);
CREATE INDEX IF NOT EXISTS idx_prices_symbol_ts ON prices(symbol, ts DESC);
```

> **Terminologia:** “**fechamento**” (negócios/UX) ↔ coluna `close` (técnica/DB/ML).

---

<a id="treinamento-e-previsao"></a>
## Treinamento e previsão

- **Alvo:** `next_close = close` deslocado em -1 (próximo fechamento).  
- **Features (exemplos):**
  - Lags `close_t-1 ... close_t-5`
  - Médias móveis (SMA 5, 10, 20)
  - Volatilidade (desvio padrão rolante 10)
- **Modelo:** `RandomForestRegressor` (robusto e rápido).
- **Avaliação:** RMSE, MAE, R².
- **Persistência:** `api/models/model.pkl` (volume montado no host).
- **Serviço de previsão:** `/predict` lê os últimos candles, gera features e retorna o **próximo fechamento** previsto.

---

<a id="dashboard"></a>
## Dashboard

- **Botões:** *Ingerir agora*, *Treinar modelo*, *Prever próximo fechamento*.
- **Cards:** *Último fechamento*, *Próximo fechamento (previsto)*, *Delta previsto (abs e %)*.
- **Gráficos:** série temporal dos fechamentos recentes; histórico de métricas.
- **Feedback:** mensagens de sucesso/erro da API.

---

<a id="boas-praticas-implementadas"></a>
## Boas práticas implementadas

- Idempotência na ingestão (`UNIQUE(symbol, ts)`).
- Separação de responsabilidades (*ingest*/*feats*/*train*/*predict*).
- Versionamento simples de modelo (arquivo + endpoint `/model/info`).
- Observabilidade básica: endpoint `/metrics`.
- Infra-as-code: Dockerfiles + Compose.
- Documentação: arquitetura, modelo, deploy e este README.

---

<a id="resolucao-de-problemas"></a>
## Resolução de problemas

- **“Modelo não encontrado. Treine primeiro (/train).”**  
  Rode ingestão e `/train` antes de `/predict`.

- **`duplicate key value violates unique constraint "uq_prices_symbol_ts"`**  
  Esperado ao re-ingestar candles já existentes; os duplicados são ignorados.

- **`ValueError: MT19937 is not a known BitGenerator module` ao carregar `model.pkl`**  
  Vem de incompatibilidades de versão entre `numpy`/`joblib`. Garanta que o treino e a previsão ocorram na mesma imagem/ambiente (como no Docker Compose). Se persistir, faça novo `/train` e tente `/predict` novamente.

- **Modelos não aparecem no host**  
  Confirme o volume:
  - Compose: `../api/models:/app/api/models`
  - Container (API): `ls -lah /app/api/models`
  - Host: `ls -lah api/models`

---

<a id="roadmap"></a>
## Roadmap

- Agendador de ingestão/treino (cron).
- Tracking de experimentos (MLflow).
- Parametrização de hiperparâmetros (RandomizedSearch).
- Mais sinais (RSI, MACD, etc.).
- Feature store simples.
- Exportação de métricas para Prometheus/Grafana.

---

<a id="licenca"></a>
## Licença

[MIT](./LICENSE)