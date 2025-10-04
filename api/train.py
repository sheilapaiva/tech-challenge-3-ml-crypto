from __future__ import annotations
from datetime import datetime, timezone
import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .db import Price, ModelMetric
from .features import build_features

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "model.pkl")

def _load_prices_df(db: Session, symbol: str, limit: int = 5000) -> pd.DataFrame:
    q = (
        db.query(Price)
        .filter(Price.symbol == symbol)
        .order_by(Price.ts.desc())
        .limit(limit)
    )
    rows = q.all()
    if not rows:
        raise RuntimeError("Sem dados para treino. Rode a ingestão primeiro.")
    rows = list(reversed(rows))
    df = pd.DataFrame([{"ts": r.ts, "close": float(r.close)} for r in rows])
    return df

def train_model(db: Session, symbol: str = "BTCUSDT") -> dict:
    os.makedirs(MODELS_DIR, exist_ok=True)

    df = _load_prices_df(db, symbol)
    X, y = build_features(df)
    if len(X) < 200:
        raise RuntimeError("Poucos dados após feature engineering (mín. 200 linhas).")

    split_idx = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

    model = GradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    preds = model.predict(X_val)
    mae = float(mean_absolute_error(y_val, preds))
    rmse = float(np.sqrt(mean_squared_error(y_val, preds)))

    version = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle = {"model": model, "version": version}
    joblib.dump(bundle, MODEL_PATH)
    print(f"[train] model saved to: {MODEL_PATH}")

    metric = ModelMetric(
        model_version=version,
        train_end_ts=df["ts"].max(),
        mae=mae,
        rmse=rmse,
    )
    db.add(metric)
    db.commit()

    return {
        "version": version,
        "mae": mae,
        "rmse": rmse,
        "model_path": MODEL_PATH,
        "n_rows": int(len(df)),
        "n_features": int(X.shape[1]),
    }
