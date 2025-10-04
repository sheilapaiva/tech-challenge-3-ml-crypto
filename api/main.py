from __future__ import annotations
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import get_db, init_db, Price, ModelMetric
from .ingest import run_ingestion
from .train import train_model, MODEL_PATH, MODELS_DIR
from .predict import predict_next

SCHEDULER: Optional[BackgroundScheduler] = None

API_SYMBOLS = os.getenv("INGEST_SYMBOLS", "BTCUSDT").split(",")
API_INTERVAL = os.getenv("INGEST_INTERVAL", "1m")
API_INGEST_LIMIT = int(os.getenv("INGEST_LIMIT", "300"))

RETRAIN_CRON = os.getenv("RETRAIN_CRON", "0 */6 * * *")
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "1") == "1"

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    global SCHEDULER
    if ENABLE_SCHEDULER:
        SCHEDULER = BackgroundScheduler(timezone="UTC")
        SCHEDULER.add_job(
            func=lambda: _safe_ingest_job(),
            trigger=CronTrigger.from_crontab("* * * * *"),  # a cada 1 min
            id="ingest_job",
            replace_existing=True,
            max_instances=1,
        )
        SCHEDULER.add_job(
            func=lambda: _safe_retrain_job(),
            trigger=CronTrigger.from_crontab(RETRAIN_CRON),
            id="retrain_job",
            replace_existing=True,
            max_instances=1,
        )
        SCHEDULER.start()

    yield

    if SCHEDULER:
        SCHEDULER.shutdown(wait=False)

def _safe_ingest_job():
    from .db import SessionLocal
    db = SessionLocal()
    try:
        for sym in API_SYMBOLS:
            try:
                run_ingestion(db, symbol=sym.strip(), interval=API_INTERVAL, limit=API_INGEST_LIMIT)
            except Exception:
                pass
    finally:
        db.close()

def _safe_retrain_job():
    from .db import SessionLocal
    db = SessionLocal()
    try:
        for sym in API_SYMBOLS:
            try:
                train_model(db, symbol=sym.strip())
            except Exception:
                pass
    finally:
        db.close()

app = FastAPI(title="Tech Challenge ML API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "scheduler": bool(SCHEDULER)}

@app.post("/ingest/run")
def ingest(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1m"),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    inserted = run_ingestion(db, symbol=symbol, interval=interval, limit=limit)
    return {"symbol": symbol, "interval": interval, "limit": limit, "inserted": inserted}

@app.get("/prices/latest")
def latest_prices(
    symbol: str = Query("BTCUSDT"),
    n: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Price)
        .filter(Price.symbol == symbol)
        .order_by(Price.ts.desc())
        .limit(n)
        .all()
    )
    data = [{"ts": r.ts.isoformat(), "close": float(r.close)} for r in reversed(rows)]
    return {"symbol": symbol, "data": data}

@app.post("/train")
def train(symbol: str = Query("BTCUSDT"), db: Session = Depends(get_db)):
    res = train_model(db, symbol=symbol)
    return res

@app.post("/predict")
def predict(
    symbol: str = Query("BTCUSDT"),
    ingest_interval: str = Query("1m"),
    ingest_limit: int = Query(5, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    try:
        run_ingestion(db, symbol=symbol, interval=ingest_interval, limit=ingest_limit)
    except Exception:
        pass
    res = predict_next(db, symbol=symbol)
    return res

@app.get("/model/info")
def model_info():
    import os
    exists = os.path.exists(MODEL_PATH)
    listing = sorted(os.listdir(MODELS_DIR)) if os.path.isdir(MODELS_DIR) else []
    return {"models_dir": MODELS_DIR, "model_path": MODEL_PATH, "exists": bool(exists), "listing": listing}


@app.get("/metrics")
def list_metrics(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ModelMetric)
        .order_by(ModelMetric.created_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for m in rows:
        out.append({
            "model_version": m.model_version,
            "train_end_ts": m.train_end_ts.isoformat() if m.train_end_ts else None,
            "mae": float(m.mae),
            "rmse": float(m.rmse),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return {"items": out}

@app.post("/export/parquet")
def export_parquet(
    symbol: str = Query("BTCUSDT"),
    n: int = Query(10000, ge=1, le=500000),
    db: Session = Depends(get_db),
):
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(DATA_DIR, exist_ok=True)

    rows = (
        db.query(Price)
        .filter(Price.symbol == symbol)
        .order_by(Price.ts.desc())
        .limit(n)
        .all()
    )
    rows = list(reversed(rows))
    if not rows:
        return {"ok": False, "message": "Sem dados para exportar."}

    df = pd.DataFrame([{
        "symbol": r.symbol, "ts": r.ts, "open": float(r.open), "high": float(r.high),
        "low": float(r.low), "close": float(r.close), "volume": float(r.volume)
    } for r in rows])

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"{symbol}_{ts}.parquet"
    fpath = os.path.join(DATA_DIR, fname)

    table = pa.Table.from_pandas(df)
    pq.write_table(table, fpath)

    return {"ok": True, "path": fpath, "rows": int(len(df))}
