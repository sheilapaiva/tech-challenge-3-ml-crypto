# Referência de API & Guia do Dashboard

**Base:** `http://localhost:8000`

---

## Endpoints

### GET `/prices/latest`
Retorna as últimas **N** linhas de `prices`.

**Parâmetros (query):**
- `symbol` *(str, default: `BTCUSDT`)*
- `n` *(int, default: `720`)*

---

### POST `/ingest/run`
Ingere candles recentes no DB.

**Parâmetros (query):**
- `symbol` *(str, default: `BTCUSDT`)*
- `interval` *(str, default: `1m`)*
- `limit` *(int, default: `1000`)*

---

### POST `/train`
Treina e salva `model.pkl`.

**Parâmetros (query):**
- `symbol` *(str, default: `BTCUSDT`)*

---

### POST `/predict`
Prevê **próximo fechamento**.

**Parâmetros (query):**
- `symbol` *(str, default: `BTCUSDT`)*

**Response (exemplo):**
```json
{
  "symbol": "BTCUSDT",
  "predicted_next_close": 122427.63,
  "last_close": 122295.85,
  "delta": 131.78,
  "delta_pct": 0.108,
  "model_version": "v1.0.0",
  "generated_at": "2025-10-03T23:12:34Z"
}
```

---

### GET `/model/info`
Diagnóstico do artefato de modelo.

**Response (exemplo):**
```json
{
  "models_dir": "/app/api/models",
  "model_path": "/app/api/models/model.pkl",
  "exists": true,
  "listing": ["model.pkl"]
}
```

---

### GET `/metrics`
Resumo de métricas do(s) último(s) treino(s).

**Parâmetros (query):**
- `limit` *(int, default: `50`)*

---

## Guia do Dashboard (Streamlit)

### Seções
- **Predição rápida**
  - **Último fechamento**: último `close` da base.
  - **Próximo fechamento (previsto)**: saída do modelo.
  - **Delta previsto**: valor e % em relação ao último fechamento.
- **Ações**
  - **Ingerir agora**: executa `/ingest/run`.
  - **Treinar modelo**: executa `/train`.
  - **Prever próximo fechamento**: executa `/predict`.

### Boas práticas de uso
1. **Ingerir → Treinar → Prever**.
2. Caso “**Modelo não encontrado**”, treine novamente.
3. Para dados mais frescos, clique **Ingerir agora** antes de prever.

### Erros e Mensagens
- **Poucos dados**: aumente `limit` na ingestão.
- **BitGenerator (NumPy/Joblib)**: reconstrua a imagem Docker para alinhar versões.

---

© MIT