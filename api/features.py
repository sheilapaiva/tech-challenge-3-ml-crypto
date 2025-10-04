from __future__ import annotations
import pandas as pd

def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.sort_values("ts").reset_index(drop=True)

    df["ret_1"] = df["close"].pct_change(1)
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_15"] = df["close"].pct_change(15)

    df["sma_5"] = df["close"].rolling(5).mean()
    df["sma_15"] = df["close"].rolling(15).mean()
    df["ema_5"] = df["close"].ewm(span=5, adjust=False).mean()
    df["ema_15"] = df["close"].ewm(span=15, adjust=False).mean()
    df["std_15"] = df["close"].rolling(15).std()

    df["y"] = df["close"].shift(-1)

    feats = [
        "ret_1", "ret_5", "ret_15",
        "sma_5", "sma_15", "ema_5", "ema_15", "std_15",
        "close"
    ]

    df = df.dropna().reset_index(drop=True)
    X = df[feats]
    y = df["y"]
    return X, y
