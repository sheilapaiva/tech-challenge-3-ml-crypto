import os
import shutil
import tempfile
import pandas as pd
from sqlalchemy.orm import Session
from types import SimpleNamespace

from api.train import train_model, MODELS_DIR, MODEL_PATH
from api.db import Price

def _fake_session_with_data():
    class FakeRow: 
        def __init__(self, ts, close): self.ts, self.close = ts, close

    rows = [FakeRow(pd.Timestamp(f"2024-01-01 00:{i:02d}:00Z"), 100 + i*0.5) for i in range(400)]
    class FakeQuery:
        def __init__(self, rows): self._rows = rows
        def filter(self, *_args, **_kwargs): return self
        def order_by(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self
        def all(self): return self._rows
    class FakeSession:
        def query(self, _): return FakeQuery(rows)
        def add(self, _): pass
        def commit(self): pass
    return FakeSession()

def test_train_model_saves_artifact(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("PYTHONHASHSEED", "42")

    from api import train as tr
    orig_models_dir, orig_model_path = tr.MODELS_DIR, tr.MODEL_PATH
    try:
        tr.MODELS_DIR = tmpdir
        tr.MODEL_PATH = os.path.join(tmpdir, "model.pkl")

        db = _fake_session_with_data()
        out = tr.train_model(db, symbol="BTCUSDT")
        assert os.path.exists(tr.MODEL_PATH), "modelo não foi salvo"
        assert "mae" in out and "rmse" in out
    finally:
        tr.MODELS_DIR, tr.MODEL_PATH = orig_models_dir, orig_model_path
        shutil.rmtree(tmpdir, ignore_errors=True)
