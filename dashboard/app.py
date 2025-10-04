import os
import requests
import pandas as pd
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Tech Challenge — Cripto", layout="wide")

# Sidebar
st.sidebar.header("Parâmetros")
SYMBOL = st.sidebar.text_input("Symbol", value="BTCUSDT")
N_POINTS = st.sidebar.number_input("Pontos (últimos N)", min_value=50, max_value=2000, value=720, step=10)
LIMIT = st.sidebar.number_input("Limit (ingestão manual)", min_value=50, max_value=1000, value=1000, step=50)
INTERVAL = st.sidebar.selectbox("Intervalo", options=["1m", "3m", "5m", "15m", "30m", "1h"], index=0)

st.title("Tech Challenge — Preço e Predição (real-time)")

# Botões
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Ingerir agora", use_container_width=True):
        try:
            r = requests.post(
                f"{API_BASE}/ingest/run",
                params={"symbol": SYMBOL, "interval": INTERVAL, "limit": LIMIT},
                timeout=30,
            )
            st.toast(f"Ingest: {r.json()}", icon="✅")
        except Exception as e:
            st.error(f"Falha ao ingerir dados: {e}")

with col2:
    if st.button("Treinar modelo", use_container_width=True):
        try:
            r = requests.post(f"{API_BASE}/train", params={"symbol": SYMBOL}, timeout=180)
            st.toast(f"Train: {r.json()}", icon="✅")
        except Exception as e:
            st.error(f"Falha ao treinar: {e}")

with col3:
    if st.button("Prever próximo fechamento", use_container_width=True):
        try:
            r = requests.post(
                f"{API_BASE}/predict",
                params={"symbol": SYMBOL, "ingest_interval": INTERVAL, "ingest_limit": 5},
                timeout=30,
            )
            st.session_state["last_predict"] = r.json()
            st.toast(f"Predict: {st.session_state['last_predict']}", icon="🔮")
        except Exception as e:
            st.error(f"Falha ao prever: {e}")

st.divider()

# Gráfico de preços recentes
st.subheader(f"Preço — {SYMBOL}")
try:
    r = requests.get(f"{API_BASE}/prices/latest", params={"symbol": SYMBOL, "n": N_POINTS}, timeout=30)
    js = r.json()
    df = pd.DataFrame(js.get("data", []))
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"])
        st.line_chart(df.set_index("ts")["close"])
    else:
        st.info("Sem dados ainda. Clique em **Ingerir agora**.")
except Exception as e:
    st.warning(f"API indisponível para /prices/latest: {e}")

# Bloco de predição rápida + timestamps
st.subheader("Predição rápida")
pr = st.session_state.get("last_predict")
if pr:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Último fechamento", f"{pr['last_close']:.2f}")
    with c2:
        st.metric("Próximo fechamento (previsto)", f"{pr['predicted_next_close']:.2f}")
    with c3:
        st.metric("Delta previsto", f"{pr['delta']:.2f}", f"{pr['delta_pct']*100:.3f}%")
    st.caption(f"Modelo: {pr['model_version']} • Dados até: {pr['last_ts']} • Previsto em: {pr['predicted_at']}")
else:
    try:
        r = requests.post(f"{API_BASE}/predict", params={"symbol": SYMBOL}, timeout=30)
        pr = r.json()
        st.session_state["last_predict"] = pr
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Último fechamento", f"{pr['last_close']:.2f}")
        with c2:
            st.metric("Próximo fechamento (previsto)", f"{pr['predicted_next_close']:.2f}")
        with c3:
            st.metric("Delta previsto", f"{pr['delta']:.2f}", f"{pr['delta_pct']*100:.3f}%")
        st.caption(f"Modelo: {pr['model_version']} • Dados até: {pr['last_ts']} • Previsto em: {pr['predicted_at']}")
    except Exception:
        st.info("Treine o modelo para visualizar a predição.")

with st.sidebar:
    if st.button("Exportar Parquet (data lake)"):
        try:
            r = requests.post(f"{API_BASE}/export/parquet", params={"symbol": SYMBOL, "n": 20000}, timeout=120)
            st.success(r.json())
        except Exception as e:
            st.error(f"Falha ao exportar: {e}")


st.subheader("Métricas do Modelo")
try:
    r = requests.get(f"{API_BASE}/metrics", params={"limit": 50}, timeout=30)
    items = r.json().get("items", [])
    if items:
        import pandas as pd
        st.dataframe(pd.DataFrame(items))
    else:
        st.info("Sem métricas registradas ainda.")
except Exception as e:
    st.warning(f"API indisponível para /metrics: {e}")
