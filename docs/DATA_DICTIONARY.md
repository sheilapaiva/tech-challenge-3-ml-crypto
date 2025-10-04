# Dicionário de Dados

## Tabela: prices
| Campo  | Tipo        | Descrição                                  |
|--------|-------------|---------------------------------------------|
| id     | SERIAL PK   | Identificador                               |
| symbol | TEXT        | Par (ex.: BTCUSDT)                          |
| ts     | TIMESTAMPTZ | Timestamp do candle (fechado)               |
| open   | NUMERIC     | Preço de abertura                           |
| high   | NUMERIC     | Máximo                                      |
| low    | NUMERIC     | Mínimo                                      |
| close  | NUMERIC     | **Fechamento**                              |
| volume | NUMERIC     | Volume no intervalo                         |

- **Constraint**: `UNIQUE(symbol, ts)`.

## Features (derivadas)
- `ret_1m`, `ret_5m`, `ret_15m`
- `ma_5`, `ma_15`, `ma_30`
- `vol_15`
- `lag_close_1..lag_close_30`