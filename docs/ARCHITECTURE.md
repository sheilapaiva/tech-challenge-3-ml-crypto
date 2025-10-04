# Arquitetura

## Visão Geral
O sistema realiza ingestão de cotações de cripto (ex.: **BTCUSDT**) em tempo real, persiste no **PostgreSQL**, treina um modelo de ML e expõe previsões via **FastAPI**. Um **dashboard Streamlit** consome a API para visualização e operação (“Ingerir agora”, “Treinar modelo”, “Prever próximo fechamento”).

[Usuário] ⇄ [Streamlit Dashboard] ⇄ [FastAPI] ⇄ [PostgreSQL]
│
└── [Artefatos do Modelo (.pkl)]


## Componentes
- **PostgreSQL (db)**: Armazena OHLCV por minuto (tabela `prices`) e métricas internas (endpoint `/metrics`).
- **API FastAPI (api)**:
  - `/ingest/run`: busca candles recentes (fonte pública) e grava em `prices`.
  - `/train`: treina modelo (janela deslizante + features) e salva `model.pkl`.
  - `/predict`: carrega `model.pkl` e prevê o próximo **fechamento**.
  - `/prices/latest`: retorna últimas linhas para o dashboard.
  - `/model/info`: diagnostica existência/versão do modelo.
- **Dashboard Streamlit (dashboard)**:
  - Botões para **ingestão**, **treino** e **previsão**.
  - Cards com último fechamento e **“Próximo fechamento (previsto)”**.

## Fluxo de Dados
1. **Ingestão**: coleta últimos N candles → `prices`.
2. **Features**: janela móvel e derivadas (retornos, médias, volatilidade).
3. **Treino**: split temporal (train/val/test), regressão (ex.: RandomForest), persistência via `joblib`.
4. **Previsão**: seleciona últimas janelas, aplica o modelo e retorna valor previsto.

## Decisões de Design
- **Postgres** (simplicidade e SQL puro).
- **FastAPI** (rápida, tipada).
- **Streamlit** (MVP de UI).
- **RandomForestRegressor** (robusto sem tuning pesado).
- **Volumes Docker** para persistir base e modelos no host.

## Trade-offs
- **Modelo básico** (não captura sazonalidade complexa).
- **Sem scheduler embutido** (orquestração pode ser feita externamente — Cron/K8s).
- **Previsão de “um passo à frente”** (foco em MVP).

## Segurança & Observabilidade
- CORS liberado para o dashboard interno.
- Métricas simples: `/metrics`.
- Logs nas três camadas (Docker/uvicorn/Streamlit).

## Extensões Futuras
- Hyperparameter tuning (Optuna).
- Múltiplos símbolos e horizontes.
- CI/CD (+ testes).
- Monitoramento de drift.
