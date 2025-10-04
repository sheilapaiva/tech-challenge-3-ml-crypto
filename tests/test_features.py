import pandas as pd
from api.features import build_features

def test_build_features_minimal():
    data = [{"ts": pd.Timestamp(f"2024-01-01 00:{i:02d}:00Z"), "close": 100 + i} for i in range(20)]
    df = pd.DataFrame(data)
    X, y = build_features(df)

    assert len(X) == len(y) > 0
    assert X.index.max() == y.index.max()
    assert not X.isna().any().any()
    assert not y.isna().any()
