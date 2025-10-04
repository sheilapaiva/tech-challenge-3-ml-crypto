# Model Card — Previsão do Próximo Fechamento (BTCUSDT)

## Tarefa
Regressão do **próximo preço de fechamento (close t+1)** a partir de janelas recentes de OHLCV.

## Dados
- **Fonte**: candles públicos de cripto (intervalo 1m).
- **Tabela**: `prices(symbol, ts, open, high, low, close, volume)` com restrição única `(symbol, ts)`.
- **Pré-processamento**:
  - Ordenação temporal e remoção de duplicatas.
  - Reamostragem/ajuste de timezones quando necessário.

## Features (exemplos)
- Retornos log/percentuais (1, 5, 15 min).
- Médias móveis (MA 5/15/30).
- Volatilidade (rolling std).
- Razões high/low/close.
- Lags de fechamento (ex.: close_{t-1..t-30}).

## Modelo
- **Algoritmo**: `RandomForestRegressor` (sklearn).
- **Target**: `close_{t+1}`.
- **Split**: temporal (treino/val/test).
- **Persistência**: `joblib` → `api/models/model.pkl`.
- **Determinismo**: `random_state` fixo.

## Métricas
- RMSE / MAE / MAPE (em validação e teste).
- Exibidas no log do treino e em `/metrics` (resumo).

## Limitações
- Série de alta volatilidade (ruído grande).
- Sem exógenas (macro, funding, orderbook…).
- Um passo à frente (1-step ahead).

## Riscos & Uso Responsável
- **Não** usar como conselho financeiro.
- Testar robustez sob regimes de mercado distintos.

## Versão
- **v1.0.0**: MVP com RandomForest, features hand-crafted, 1-step.