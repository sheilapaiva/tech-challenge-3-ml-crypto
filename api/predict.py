from __future__ import annotations
import os
from datetime import datetime, timezone
import joblib
import pandas as pd
from sqlalchemy.orm import Session

from .db import Price
from .features import build_features
from .train import MODEL_PATH

def _load_latest_df(db: Session, symbol: str, limit: int = 5000) -> pd.DataFrame:
    rows = (
        db.query(Price)
        .filter(Price.symbol == symbol)
        .order_by(Price.ts.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise RuntimeError("Sem dados no banco. Rode ingestão.")
    rows = list(reversed(rows))
    df = pd.DataFrame([{"ts": r.ts, "close": float(r.close)} for r in rows])
    return df

def _load_model():
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError("Modelo não encontrado. Treine primeiro (/train).")
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"], bundle.get("version", "unknown")

def predict_next(db: Session, symbol: str = "BTCUSDT") -> dict:
    model, version = _load_model()
    df = _load_latest_df(db, symbol)
    X, y = build_features(df)
    if len(X) == 0:
        raise RuntimeError("Sem features para prever. Treine novamente.")

    last_close = float(df["close"].iloc[-1])
    last_ts = df["ts"].iloc[-1].astimezone(timezone.utc)

    yhat = float(model.predict(X.iloc[[-1]])[0])
    delta = yhat - last_close
    delta_pct = delta / last_close if last_close != 0 else 0.0

    return {
        "symbol": symbol,
        "predicted_next_close": yhat,
        "last_close": last_close,
        "delta": delta,
        "delta_pct": delta_pct,
        "model_version": version,
        "last_ts": last_ts.isoformat(),
        "predicted_at": datetime.now(timezone.utc).isoformat(),
    }
