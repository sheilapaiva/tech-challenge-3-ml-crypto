from __future__ import annotations
from datetime import datetime, timezone
import requests
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .db import Price

BINANCE_BASE = "https://api.binance.com/api/v3/klines"

def _ms_to_dt_utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).replace(microsecond=999000)

def _fetch_binance_klines(symbol: str, interval: str, limit: int) -> list[dict]:
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(BINANCE_BASE, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    rows = []
    for k in data:
        open_time = int(k[0])
        ts = _ms_to_dt_utc(int(k[6])) 
        rows.append({
            "symbol": symbol,
            "ts": ts,
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return rows

def _bulk_upsert_prices(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Price.__table__).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "ts"])
    db.execute(stmt)
    db.commit()
    return len(rows)

def run_ingestion(db: Session, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 1000) -> int:
    rows = _fetch_binance_klines(symbol=symbol, interval=interval, limit=limit)
    inserted = _bulk_upsert_prices(db, rows)
    return inserted
