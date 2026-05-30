import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# PDF generation
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURACION PAGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Quant Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0d0f14;
    color: #e2e8f0;
}
h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }

.metric-card {
    background: #161b26;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 16px;
    margin: 6px 0;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #63b3ed;
    margin-top: 4px;
}
.positive { color: #68d391 !important; }
.negative { color: #fc8181 !important; }
.neutral  { color: #fbd38d !important; }

.section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #4299e1;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding: 8px 0;
    border-bottom: 1px solid #2d3748;
    margin: 20px 0 14px 0;
}
.signal-buy  { background:#1a3a2a; color:#68d391; border:1px solid #2f855a; border-radius:6px; padding:6px 14px; font-family:'IBM Plex Mono',monospace; font-size:13px; }
.signal-sell { background:#3a1a1a; color:#fc8181; border:1px solid #9b2c2c; border-radius:6px; padding:6px 14px; font-family:'IBM Plex Mono',monospace; font-size:13px; }
.signal-hold { background:#2a2a1a; color:#fbd38d; border:1px solid #975a16; border-radius:6px; padding:6px 14px; font-family:'IBM Plex Mono',monospace; font-size:13px; }

.stSelectbox label, .stMultiSelect label, .stSlider label, .stNumberInput label {
    color: #a0aec0 !important;
    font-size: 12px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
PERIODOS = {
    "1 Mes":  "1mo",
    "3 Meses": "3mo",
    "6 Meses": "6mo",
    "1 Año":   "1y",
    "2 Años":  "2y",
    "3 Años":  "3y",
    "5 Años":  "5y",
    "10 Años": "10y",
    "Máximo":  "max",
}

PERCENTILES_LIST = [0, 1, 5, 15, 25, 50, 75, 95, 99, 100]

def color_val(val, fmt=".2%"):
    if isinstance(val, float):
        c = "positive" if val > 0 else ("negative" if val < 0 else "neutral")
        return f'<span class="{c}">{val:{fmt}}</span>'
    return str(val)

# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
def load_from_yahoo(tickers, period, start_date=None):
    """Descarga ticker por ticker con reintentos. Robusto contra rate limits de Yahoo."""
    import time

    all_series = {}
    failed = []

    progress_bar = st.progress(0, text="Descargando datos de Yahoo Finance...")

    for i, ticker in enumerate(tickers):
        success = False
        last_error = None

        # Hasta 3 intentos por ticker
        for attempt in range(3):
            try:
                if start_date is not None:
                    df = yf.download(ticker, start=start_date, auto_adjust=True,
                                     progress=False, threads=False)
                else:
                    df = yf.download(ticker, period=period, auto_adjust=True,
                                     progress=False, threads=False)

                if df is None or df.empty:
                    last_error = "DataFrame vacío"
                    time.sleep(1)
                    continue

                # Extraer Close (puede venir con MultiIndex incluso para 1 ticker)
                if isinstance(df.columns, pd.MultiIndex):
                    if "Close" in df.columns.get_level_values(0):
                        serie = df["Close"]
                        if isinstance(serie, pd.DataFrame):
                            serie = serie.iloc[:, 0]
                    else:
                        last_error = "Sin columna Close"
                        continue
                else:
                    if "Close" in df.columns:
                        serie = df["Close"]
                    else:
                        last_error = "Sin columna Close"
                        continue

                serie = pd.to_numeric(serie, errors='coerce').dropna()

                if serie.empty:
                    last_error = "Serie vacía tras limpieza"
                    time.sleep(1)
                    continue

                all_series[ticker] = serie
                success = True
                break

            except Exception as e:
                last_error = str(e)
                time.sleep(1.5)

        if not success:
            failed.append((ticker, last_error))

        progress_bar.progress((i + 1) / len(tickers),
                              text=f"Descargando {ticker} ({i+1}/{len(tickers)})")

    progress_bar.empty()

    if failed:
        st.warning("⚠️ Tickers que fallaron tras 3 intentos:\n" +
                   "\n".join([f"- **{t}**: {e}" for t, e in failed]))

    if not all_series:
        return pd.DataFrame()

    prices = pd.DataFrame(all_series)
    prices = prices.sort_index()
    cols_present = [t for t in tickers if t in prices.columns]
    prices = prices[cols_present]
    return prices

def unify_dates(prices_df):
    """Recorta el DataFrame a partir de la primera fecha en que TODOS los activos tienen datos."""
    if prices_df.empty:
        return prices_df
    # primera fecha en que cada columna tiene datos
    first_valid_per_col = prices_df.apply(lambda c: c.first_valid_index()).dropna()
    if len(first_valid_per_col) == 0:
        return prices_df
    # tomamos el MÁXIMO = la fecha más tardía = el activo con menos histórico
    common_start = first_valid_per_col.max()
    df_cut = prices_df[prices_df.index >= common_start].copy()
    # rellenar gaps puntuales (festivos diferentes entre mercados, etc.) hacia adelante
    df_cut = df_cut.ffill().bfill()
    # eliminar filas que sigan teniendo NaN (caso extremo)
    df_cut = df_cut.dropna(how='any')
    return df_cut

def get_ticker_names(tickers):
    """Obtiene nombres completos de los tickers desde Yahoo Finance."""
    names = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            name = info.get('longName') or info.get('shortName') or t
            names[t] = name
        except Exception:
            names[t] = t
    return names

def load_from_excel(file):
    df = pd.read_excel(file, index_col=0, parse_dates=True)
    df = df.sort_index()
    df = df.dropna(how="all")
    return df

# ─────────────────────────────────────────────
# CALCULOS ESTADISTICOS
# ─────────────────────────────────────────────
def calc_returns(prices):
    return prices.pct_change().dropna()

def calc_base100(prices):
    returns = calc_returns(prices)
    base = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    base.iloc[0] = 100.0
    for i in range(1, len(prices)):
        base.iloc[i] = base.iloc[i-1] * (1 + returns.iloc[i-1])
    return base

def calc_ln(prices):
    return np.log(prices)

def calc_stats(ln_prices, benchmark_col):
    results = {}
    bench = ln_prices[benchmark_col]
    for col in ln_prices.columns:
        if col == benchmark_col:
            continue
        asset = ln_prices[col].dropna()
        b_aligned = bench.reindex(asset.index).dropna()
        a_aligned = asset.reindex(b_aligned.index)

        slope, intercept, r, p, se = stats.linregress(b_aligned, a_aligned)
        r2 = r**2
        corr = np.corrcoef(a_aligned, b_aligned)[0,1]

        last_ln = a_aligned.iloc[-1]
        last_bench_ln = b_aligned.iloc[-1]
        val_stat = np.exp(intercept + slope * last_bench_ln)
        last_price = np.exp(last_ln)
        pot_val_reg = val_stat / last_price - 1

        last_20 = a_aligned.iloc[-20:]
        std_20 = last_20.std()
        mean_20 = last_20.mean()
        cv_20 = std_20 / mean_20 if mean_20 != 0 else np.nan

        pct_vals = {p: np.percentile(a_aligned, p) for p in PERCENTILES_LIST}
        pct_rank = stats.percentileofscore(a_aligned, last_ln) / 100
        pct50_price = np.exp(pct_vals[50])
        pot_val_pct = pct50_price / last_price - 1

        results[col] = {
            "corr": corr,
            "alpha": intercept,
            "beta": slope,
            "r2": r2,
            "val_stat": val_stat,
            "pot_val_reg": pot_val_reg,
            "std_20": std_20,
            "mean_20": mean_20,
            "cv_20": cv_20,
            "percentiles": pct_vals,
            "pct_rank": pct_rank,
            "pot_val_pct": pot_val_pct,
            "last_price": last_price,
        }
    return results

def calc_precio_valorado(stats_result, w_reg, w_pct):
    """Precio valorado final ponderando regresion y percentil."""
    out = {}
    for col, s in stats_result.items():
        suma_producto = s["pot_val_reg"] * w_reg + s["pot_val_pct"] * w_pct
        precio_valorado = s["last_price"] * (1 + suma_producto)
        out[col] = {**s, "suma_producto": suma_producto, "precio_valorado": precio_valorado}
    return out

# ─────────────────────────────────────────────
# ANALISIS TECNICO
# ─────────────────────────────────────────────
MM_DEFAULT_PERIODS = [5, 20, 100, 200]

def calc_mm(prices_series, periods=None):
    if periods is None:
        periods = MM_DEFAULT_PERIODS
    df = pd.DataFrame({"price": prices_series})
    for w in periods:
        df[f"MM{w}"] = df["price"].rolling(w).mean()
    return df

def get_mm_signal(df, periods=None):
    """Devuelve señal basada en cruce precio vs MMs y cruce entre MMs."""
    if periods is None:
        periods = MM_DEFAULT_PERIODS
    signals = []
    if len(df) < 2:
        return ["⏸ HOLD: Datos insuficientes"]

    last = df.iloc[-1]
    prev = df.iloc[-2]

    p = last["price"]
    for w in periods:
        col = f"MM{w}"
        if col not in df.columns or pd.isna(last[col]) or pd.isna(prev[col]):
            continue
        if prev["price"] < prev[col] and p > last[col]:
            signals.append(f"✅ COMPRA: Precio cruzó MM{w} al alza")
        elif prev["price"] > prev[col] and p < last[col]:
            signals.append(f"🔴 VENTA: Precio cruzó MM{w} a la baja")

    # Cruces entre MMs (golden/death cross) — se generan pares (fast, slow) consecutivos
    sorted_periods = sorted(periods)
    pairs = [(sorted_periods[i], sorted_periods[j])
             for i in range(len(sorted_periods))
             for j in range(i+1, len(sorted_periods))]
    for fast, slow in pairs:
        cf, cs = f"MM{fast}", f"MM{slow}"
        if cf not in df.columns or cs not in df.columns:
            continue
        if pd.isna(last[cf]) or pd.isna(last[cs]) or pd.isna(prev[cf]) or pd.isna(prev[cs]):
            continue
        if prev[cf] < prev[cs] and last[cf] > last[cs]:
            signals.append(f"✅ GOLDEN CROSS: MM{fast} cruzó MM{slow} al alza")
        elif prev[cf] > prev[cs] and last[cf] < last[cs]:
            signals.append(f"🔴 DEATH CROSS: MM{fast} cruzó MM{slow} a la baja")

    if not signals:
        signals.append("⏸ HOLD: Sin cruces recientes detectados")
    return signals

def get_mm_summary(signals):
    """Devuelve una sola señal resumen: COMPRA/VENTA/HOLD."""
    has_buy  = any("COMPRA" in s or "GOLDEN" in s for s in signals)
    has_sell = any("VENTA"  in s or "DEATH"  in s for s in signals)
    if has_buy and not has_sell:  return "COMPRA"
    if has_sell and not has_buy:  return "VENTA"
    if has_buy and has_sell:       return "MIXTO"
    return "HOLD"

def calc_macd(prices_series, fast=12, slow=26, signal=9):
    df = pd.DataFrame({"price": prices_series})
    df["ema_fast"] = df["price"].ewm(span=fast, adjust=False).mean()
    df["ema_slow"] = df["price"].ewm(span=slow, adjust=False).mean()
    df["macd"]     = df["ema_fast"] - df["ema_slow"]
    df["signal"]   = df["macd"].ewm(span=signal, adjust=False).mean()
    df["hist"]     = df["macd"] - df["signal"]
    return df

def get_macd_signal(df):
    if len(df) < 2:
        return "⏸ HOLD: Datos insuficientes"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if pd.isna(last["macd"]) or pd.isna(last["signal"]) or pd.isna(prev["macd"]) or pd.isna(prev["signal"]):
        return "⏸ HOLD: Datos insuficientes"
    if prev["macd"] < prev["signal"] and last["macd"] > last["signal"]:
        return "✅ COMPRA: MACD cruzó Signal al alza"
    elif prev["macd"] > prev["signal"] and last["macd"] < last["signal"]:
        return "🔴 VENTA: MACD cruzó Signal a la baja"
    elif last["macd"] > last["signal"]:
        return "⏸ HOLD: MACD por encima de Signal (tendencia alcista)"
    else:
        return "⏸ HOLD: MACD por debajo de Signal (tendencia bajista)"

def get_macd_summary(signal_text):
    if "COMPRA" in signal_text: return "COMPRA"
    if "VENTA"  in signal_text: return "VENTA"
    return "HOLD"

def calc_rsi(prices_series, period=14):
    delta = prices_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_rsi_signal(rsi_series, buy_th=30, sell_th=70):
    rsi_clean = rsi_series.dropna()
    if len(rsi_clean) < 2:
        return "⏸ HOLD: Datos insuficientes"
    last = rsi_clean.iloc[-1]
    prev = rsi_clean.iloc[-2]
    if prev >= buy_th and last < buy_th:
        return f"🔴 VENTA/SOBREVENDIDO: RSI = {last:.1f}"
    elif prev <= buy_th and last > buy_th:
        return f"✅ COMPRA: RSI salió de zona sobrevendida = {last:.1f}"
    elif prev <= sell_th and last > sell_th:
        return f"🔴 VENTA: RSI entró zona sobrecompra = {last:.1f}"
    elif last < buy_th:
        return f"⏸ SOBREVENDIDO: RSI = {last:.1f} (posible rebote)"
    elif last > sell_th:
        return f"⏸ SOBRECOMPRADO: RSI = {last:.1f} (posible corrección)"
    else:
        return f"⏸ HOLD: RSI = {last:.1f} (zona neutral)"

def get_rsi_summary(signal_text):
    if "COMPRA" in signal_text: return "COMPRA"
    if "VENTA"  in signal_text: return "VENTA"
    return "HOLD"

def get_fib_summary(signal_text):
    if "COMPRA" in signal_text: return "COMPRA"
    if "VENTA"  in signal_text: return "VENTA"
    return "HOLD"

def detect_zigzag_pivots(prices_series, reversal_pct=0.05, min_duration_days=30):
    """
    Detecta pivotes (máximos y mínimos significativos) usando el algoritmo ZigZag.

    Args:
        prices_series: serie de precios indexada por fecha
        reversal_pct: % mínimo de reversión para considerar un nuevo pivote (default 5%)
        min_duration_days: duración mínima del swing en días (default 30)

    Returns:
        Lista de tuplas (fecha, precio, tipo) donde tipo es 'H' (high) o 'L' (low)
    """
    if len(prices_series) < 2:
        return []

    prices = prices_series.dropna()
    if len(prices) < 2:
        return []

    pivots = []
    # Primer punto: inicializar con el primer precio como pivote tentativo
    # Determinamos dirección inicial buscando primero un movimiento significativo
    first_date  = prices.index[0]
    first_price = prices.iloc[0]

    # Buscar dirección inicial
    direction = None  # 'up' o 'down'
    pivot_date  = first_date
    pivot_price = first_price

    for date, price in prices.items():
        if direction is None:
            # Aún no hay dirección establecida
            change = (price - pivot_price) / pivot_price
            if change >= reversal_pct:
                direction = 'up'
                pivots.append((pivot_date, pivot_price, 'L'))
                pivot_date, pivot_price = date, price
            elif change <= -reversal_pct:
                direction = 'down'
                pivots.append((pivot_date, pivot_price, 'H'))
                pivot_date, pivot_price = date, price
            else:
                # Actualizar pivote tentativo si el precio sigue siendo extremo
                if price > pivot_price:
                    pivot_date, pivot_price = date, price
                elif price < pivot_price:
                    pivot_date, pivot_price = date, price
        elif direction == 'up':
            # Estamos en tendencia alcista, buscando un nuevo máximo o una reversión
            if price > pivot_price:
                # Nuevo máximo tentativo
                pivot_date, pivot_price = date, price
            else:
                # Verificar si la caída desde el pivote es suficiente para revertir
                drop = (pivot_price - price) / pivot_price
                duration = (date - pivot_date).days
                if drop >= reversal_pct and duration >= min_duration_days:
                    # Confirmamos el pivote alto y cambiamos dirección
                    pivots.append((pivot_date, pivot_price, 'H'))
                    direction = 'down'
                    pivot_date, pivot_price = date, price
        elif direction == 'down':
            # Tendencia bajista, buscando nuevo mínimo o reversión
            if price < pivot_price:
                pivot_date, pivot_price = date, price
            else:
                rise = (price - pivot_price) / pivot_price
                duration = (date - pivot_date).days
                if rise >= reversal_pct and duration >= min_duration_days:
                    pivots.append((pivot_date, pivot_price, 'L'))
                    direction = 'up'
                    pivot_date, pivot_price = date, price

    # Agregar el último pivote tentativo (la tendencia en curso)
    if direction is not None and (len(pivots) == 0 or pivots[-1][0] != pivot_date):
        last_type = 'H' if direction == 'up' else 'L'
        pivots.append((pivot_date, pivot_price, last_type))

    return pivots


def calc_fibonacci(prices_series, reversal_pct=0.05, min_duration_days=30):
    """
    Calcula niveles de Fibonacci basados en el último swing significativo detectado por ZigZag.

    Si el último pivote es un MÁXIMO (tendencia alcista terminó) → traza retrocesos de la subida
    Si el último pivote es un MÍNIMO (tendencia bajista terminó) → traza rebotes de la caída
    """
    pivots = detect_zigzag_pivots(prices_series, reversal_pct, min_duration_days)

    # Fallback: si no se detectan al menos 2 pivotes, usar max/min global del período
    if len(pivots) < 2:
        high = prices_series.max()
        low  = prices_series.min()
        high_date = prices_series.idxmax()
        low_date  = prices_series.idxmin()
        trend = "Alcista (fallback global)" if high_date > low_date else "Bajista (fallback global)"
    else:
        # Tomar los dos últimos pivotes — definen el swing actual
        p1 = pivots[-2]  # pivote anterior
        p2 = pivots[-1]  # último pivote
        if p2[2] == 'H':
            # Última tendencia fue alcista (terminó en máximo)
            low,  low_date  = p1[1], p1[0]
            high, high_date = p2[1], p2[0]
            trend = "Alcista (esperando retroceso)"
        else:
            # Última tendencia fue bajista (terminó en mínimo)
            high, high_date = p1[1], p1[0]
            low,  low_date  = p2[1], p2[0]
            trend = "Bajista (esperando rebote)"

    diff = high - low
    levels = {
        "0% (Mínimo)":   low,
        "23.6%":          low + 0.236 * diff,
        "38.2%":          low + 0.382 * diff,
        "50%":            low + 0.500 * diff,
        "61.8%":          low + 0.618 * diff,
        "100% (Máximo)":  high,
    }
    meta = {
        "trend": trend,
        "high_date": high_date,
        "low_date":  low_date,
        "pivots": pivots,
    }
    return levels, high, low, meta


def get_fib_signal(prices_series, reversal_pct=0.05, min_duration_days=30):
    fib_out = calc_fibonacci(prices_series, reversal_pct, min_duration_days)
    levels, high, low, meta = fib_out
    last = prices_series.iloc[-1]
    ordered = sorted(levels.items(), key=lambda x: x[1])
    below = [l for l in ordered if l[1] <= last]
    above = [l for l in ordered if l[1] > last]
    support    = below[-1] if below else ordered[0]
    resistance = above[0]  if above else ordered[-1]
    pct_from_support    = (last - support[1])    / support[1]    if support[1] != 0 else 0
    pct_from_resistance = (resistance[1] - last) / last          if last != 0        else 0
    if pct_from_support < 0.02:
        signal = f"✅ COMPRA: Precio cerca del soporte Fib {support[0]} (${support[1]:.2f}) — {meta['trend']}"
    elif pct_from_resistance < 0.02:
        signal = f"🔴 VENTA: Precio cerca de resistencia Fib {resistance[0]} (${resistance[1]:.2f}) — {meta['trend']}"
    else:
        signal = f"⏸ HOLD: Entre {support[0]} (${support[1]:.2f}) y {resistance[0]} (${resistance[1]:.2f}) — {meta['trend']}"
    return signal, levels, meta

# ─────────────────────────────────────────────
# PLOTLY HELPERS
# ─────────────────────────────────────────────
DARK_LAYOUT = dict(
    paper_bgcolor="#0d0f14",
    plot_bgcolor="#0d0f14",
    font=dict(color="#e2e8f0", family="IBM Plex Mono"),
    xaxis=dict(gridcolor="#1e2535", showgrid=True),
    yaxis=dict(gridcolor="#1e2535", showgrid=True),
    legend=dict(bgcolor="#161b26", bordercolor="#2d3748", borderwidth=1),
    margin=dict(l=40, r=20, t=40, b=40),
)
COLORS = ["#63b3ed","#68d391","#fc8181","#fbd38d","#b794f4","#76e4f7","#f6ad55","#9ae6b4"]

def fig_base100(base100, benchmark_col):
    fig = go.Figure()
    for i, col in enumerate(base100.columns):
        lw = 2.5 if col == benchmark_col else 1.5
        dash = "dash" if col == benchmark_col else "solid"
        fig.add_trace(go.Scatter(
            x=base100.index, y=base100[col],
            name=col, line=dict(color=COLORS[i % len(COLORS)], width=lw, dash=dash)
        ))
    fig.update_layout(title="Base 100", **DARK_LAYOUT)
    return fig

def fig_mm(mm_df, ticker, periods=None):
    if periods is None:
        periods = MM_DEFAULT_PERIODS
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mm_df.index, y=mm_df["price"], name="Precio",
                             line=dict(color="#e2e8f0", width=1.5)))
    palette = ["#63b3ed","#68d391","#f6ad55","#fc8181","#b794f4","#76e4f7","#9ae6b4","#fbd38d"]
    for i, w in enumerate(periods):
        col = f"MM{w}"
        if col in mm_df.columns:
            fig.add_trace(go.Scatter(x=mm_df.index, y=mm_df[col], name=f"MM {w}",
                                     line=dict(color=palette[i % len(palette)], width=1, dash="dot")))
    fig.update_layout(title=f"Medias Móviles — {ticker}", **DARK_LAYOUT)
    return fig

def fig_macd(macd_df, ticker):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4],
                        vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=macd_df.index, y=macd_df["price"], name="Precio",
                             line=dict(color="#e2e8f0", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=macd_df.index, y=macd_df["macd"], name="MACD",
                             line=dict(color="#63b3ed", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=macd_df.index, y=macd_df["signal"], name="Signal",
                             line=dict(color="#fc8181", width=1.2, dash="dot")), row=2, col=1)
    colors_hist = ["#68d391" if v >= 0 else "#fc8181" for v in macd_df["hist"]]
    fig.add_trace(go.Bar(x=macd_df.index, y=macd_df["hist"], name="Histograma",
                         marker_color=colors_hist, opacity=0.7), row=2, col=1)
    fig.update_layout(
        title=f"MACD — {ticker}",
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0d0f14",
        font=dict(color="#e2e8f0", family="IBM Plex Mono"),
        legend=dict(bgcolor="#161b26", bordercolor="#2d3748", borderwidth=1),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    fig.update_xaxes(gridcolor="#1e2535")
    fig.update_yaxes(gridcolor="#1e2535")
    return fig

def fig_rsi(rsi_series, ticker, period=14, buy_th=30, sell_th=70):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rsi_series.index, y=rsi_series, name="RSI",
                             line=dict(color="#b794f4", width=1.5)))
    fig.add_hline(y=sell_th, line=dict(color="#fc8181", dash="dash", width=1))
    fig.add_hline(y=buy_th,  line=dict(color="#68d391", dash="dash", width=1))
    fig.add_hrect(y0=sell_th, y1=100, fillcolor="#fc8181", opacity=0.05, line_width=0)
    fig.add_hrect(y0=0,       y1=buy_th, fillcolor="#68d391", opacity=0.05, line_width=0)
    layout = {**DARK_LAYOUT, "yaxis": dict(range=[0,100], gridcolor="#1e2535", showgrid=True)}
    fig.update_layout(title=f"RSI({period}) — {ticker} [buy≤{buy_th} / sell≥{sell_th}]", **layout)
    return fig

def fig_fibonacci(prices_series, levels, ticker, meta=None):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices_series.index, y=prices_series, name="Precio",
                             line=dict(color="#e2e8f0", width=1.5)))
    fib_colors = ["#fc8181","#f6ad55","#fbd38d","#68d391","#63b3ed","#b794f4"]
    for i, (label, val) in enumerate(levels.items()):
        fig.add_hline(y=val, line=dict(color=fib_colors[i % len(fib_colors)],
                                       dash="dot", width=1),
                      annotation_text=label, annotation_position="right")
    # Marcar pivotes ZigZag si están disponibles
    if meta and "pivots" in meta and meta["pivots"]:
        highs_x = [p[0] for p in meta["pivots"] if p[2] == 'H']
        highs_y = [p[1] for p in meta["pivots"] if p[2] == 'H']
        lows_x  = [p[0] for p in meta["pivots"] if p[2] == 'L']
        lows_y  = [p[1] for p in meta["pivots"] if p[2] == 'L']
        if highs_x:
            fig.add_trace(go.Scatter(x=highs_x, y=highs_y, name="Pivote Alto",
                                     mode="markers", marker=dict(color="#fc8181", size=10, symbol="triangle-down")))
        if lows_x:
            fig.add_trace(go.Scatter(x=lows_x, y=lows_y, name="Pivote Bajo",
                                     mode="markers", marker=dict(color="#68d391", size=10, symbol="triangle-up")))
        # Línea conectando los pivotes (línea ZigZag)
        zz_x = [p[0] for p in meta["pivots"]]
        zz_y = [p[1] for p in meta["pivots"]]
        fig.add_trace(go.Scatter(x=zz_x, y=zz_y, name="ZigZag",
                                 line=dict(color="#b794f4", width=1, dash="dash"), opacity=0.6))
    title = f"Fibonacci — {ticker}"
    if meta and "trend" in meta:
        title += f" | Tendencia: {meta['trend']}"
    fig.update_layout(title=title, **DARK_LAYOUT)
    return fig

def fig_correlacion(ln_prices, stats_result, benchmark_col):
    activos = [c for c in ln_prices.columns if c != benchmark_col]
    corrs = [stats_result[a]["corr"] for a in activos]
    colors = ["#68d391" if c > 0 else "#fc8181" for c in corrs]
    fig = go.Figure(go.Bar(x=activos, y=corrs, marker_color=colors))
    layout = {**DARK_LAYOUT, "yaxis": dict(range=[-1,1], gridcolor="#1e2535", showgrid=True)}
    fig.update_layout(title=f"Correlación vs {benchmark_col}", **layout)
    return fig

# ─────────────────────────────────────────────
# GENERACIÓN DE PDF
# ─────────────────────────────────────────────
def plotly_to_image(fig, width=900, height=500, scale=1.5):
    """Convierte una figura Plotly a imagen PNG en memoria usando kaleido.
    Adapta el layout a fondo blanco para mejor lectura en PDF."""
    # Clonar y forzar tema claro para PDF
    fig_pdf = go.Figure(fig)
    fig_pdf.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black", family="Helvetica"),
        xaxis=dict(gridcolor="#cccccc", showgrid=True, color="black"),
        yaxis=dict(gridcolor="#cccccc", showgrid=True, color="black"),
        legend=dict(bgcolor="white", bordercolor="#cccccc", borderwidth=1, font=dict(color="black")),
    )
    # Algunos sub-axes en make_subplots no se tocan con update_layout: forzar de uno
    fig_pdf.update_xaxes(gridcolor="#cccccc", color="black")
    fig_pdf.update_yaxes(gridcolor="#cccccc", color="black")
    try:
        img_bytes = fig_pdf.to_image(format="png", width=width, height=height, scale=scale, engine="kaleido")
        return BytesIO(img_bytes)
    except Exception:
        # Fallback: imagen en blanco si kaleido no esta disponible
        return None


def df_to_pdf_table(df, col_widths=None, font_size=7, max_rows=None):
    """Convierte un DataFrame de pandas a una tabla ReportLab estilizada."""
    if max_rows and len(df) > max_rows:
        df = df.head(max_rows)
    # Incluir índice como primera columna
    if df.index.name:
        idx_name = df.index.name
    else:
        idx_name = ""
    data = [[idx_name] + [str(c) for c in df.columns]]
    for idx, row in df.iterrows():
        data.append([str(idx)] + [str(v) for v in row.values])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0), rl_colors.HexColor("#2d3748")),
        ('TEXTCOLOR',   (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, -1), font_size),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',        (0, 0), (-1, -1), 0.3, rl_colors.HexColor("#cbd5e0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#f7fafc")]),
        ('LEFTPADDING',  (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING',   (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
    ]))
    return tbl


def _safe_rl_image(fig, width_cm, height_cm):
    """Convierte figura Plotly a RLImage; retorna Spacer si kaleido falla."""
    from reportlab.platypus import Spacer
    buf = plotly_to_image(fig, width=900, height=int(height_cm * 60))
    if buf is None:
        return Spacer(1, 0.2)
    try:
        return RLImage(buf, width=width_cm, height=height_cm)
    except Exception:
        return Spacer(1, 0.2)


def build_pdf_report(report_data):
    """
    Construye el PDF completo con todos los períodos analizados.

    report_data: dict con la siguiente estructura:
    {
        'meta': {
            'tickers': [...], 'benchmark': str, 'fecha_ini': str, 'fecha_fin': str,
            'nombres': dict, 'activos': [...], 'activo_limitante': str, 'fecha_corte': str,
            'config': dict con todos los parámetros
        },
        'periodos': {
            'periodo_label': {
                'figs': {'base100': fig, 'corr': fig},
                'tables': {'stat': df, 'percentiles': df, 'resumen': df,
                           'mm': df, 'macd': df, 'rsi': df, 'fib': df,
                           'consenso': df, 'consolidado': df},
                'tec_figs': {ticker: {'mm': fig, 'macd': fig, 'rsi': fig, 'fib': fig}},
                'score_fig': fig
            }
        }
    }
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1c', parent=styles['Heading1'], fontSize=22,
                        textColor=rl_colors.HexColor("#2d3748"), spaceAfter=10, alignment=TA_CENTER)
    h2 = ParagraphStyle('h2c', parent=styles['Heading2'], fontSize=16,
                        textColor=rl_colors.HexColor("#2b6cb0"), spaceAfter=8, spaceBefore=14)
    h3 = ParagraphStyle('h3c', parent=styles['Heading3'], fontSize=12,
                        textColor=rl_colors.HexColor("#2d3748"), spaceAfter=6, spaceBefore=10)
    normal = ParagraphStyle('normal_c', parent=styles['Normal'], fontSize=9,
                            textColor=rl_colors.HexColor("#1a202c"), leading=12)
    small = ParagraphStyle('small_c', parent=styles['Normal'], fontSize=8,
                           textColor=rl_colors.HexColor("#4a5568"), leading=10)

    story = []
    meta = report_data['meta']

    # ─────── PORTADA ───────
    story.append(Spacer(1, 4*cm))
    story.append(Paragraph("QUANT ANALYSIS DASHBOARD", h1))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("Informe de Análisis Técnico y Estadístico", h2))
    story.append(Spacer(1, 1.5*cm))

    cover_tbl = Table([
        ["Fecha del reporte:", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Benchmark:",          f"{meta['benchmark']} ({meta['nombres'].get(meta['benchmark'], meta['benchmark'])})"],
        ["Activos analizados:", ", ".join(meta['activos'])],
        ["Rango de datos:",     f"{meta['fecha_ini']}  →  {meta['fecha_fin']}"],
        ["Períodos:",            ", ".join(report_data['periodos'].keys())],
    ], colWidths=[5*cm, 11*cm])
    cover_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), rl_colors.HexColor("#2d3748")),
        ('TEXTCOLOR', (1, 0), (1, -1), rl_colors.HexColor("#1a202c")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cover_tbl)
    story.append(PageBreak())

    # ─────── PARÁMETROS DE CONFIGURACIÓN ───────
    story.append(Paragraph("Parámetros de Configuración", h2))
    cfg = meta['config']
    config_data = [
        ["Pesos macro — Estadístico vs Técnico", f"{cfg['w_stat_total']*100:.0f}%  /  {cfg['w_tec_total']*100:.0f}%"],
        ["Pesos estadístico — Regresión / Percentil", f"{cfg['w_reg']*100:.0f}%  /  {cfg['w_pct']*100:.0f}%"],
        ["Pesos técnico — MM / RSI / MACD / Fib", f"{cfg['mm_w']}% / {cfg['rsi_w']}% / {cfg['macd_w']}% / {cfg['fib_w']}%"],
        ["Períodos Medias Móviles",         ", ".join(str(p) for p in cfg['mm_periods'])],
        ["Período RSI",                      str(cfg['rsi_period'])],
        ["Umbrales RSI (compra/venta)",     f"≤{cfg['rsi_buy_threshold']}  /  ≥{cfg['rsi_sell_threshold']}"],
        ["MACD (fast / slow / signal)",     f"{cfg['macd_fast']} / {cfg['macd_slow']} / {cfg['macd_signal']}"],
        ["Fibonacci — % reversión ZigZag",  f"{cfg['fib_reversal_pct']*100:.1f}%"],
        ["Fibonacci — Duración mínima swing", f"{cfg['fib_min_duration']} días"],
        ["Umbral estadístico (suma_producto)", f"±{cfg['stat_threshold']*100:.1f}%"],
        ["Umbral decisión final (score)",   f"±{cfg['final_threshold']:.2f}"],
    ]
    cfg_tbl = Table(config_data, colWidths=[8*cm, 8*cm])
    cfg_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor("#edf2f7")),
        ('FONTNAME',   (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 9),
        ('GRID',       (0, 0), (-1, -1), 0.3, rl_colors.HexColor("#cbd5e0")),
        ('LEFTPADDING',(0, 0), (-1, -1), 6),
        ('RIGHTPADDING',(0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
    ]))
    story.append(cfg_tbl)
    story.append(Spacer(1, 0.5*cm))

    if meta.get('activo_limitante'):
        story.append(Paragraph(
            f"<b>Fecha unificada:</b> el análisis arranca en <b>{meta['fecha_corte']}</b> "
            f"porque <b>{meta['activo_limitante']}</b> es el activo con menor histórico disponible.",
            normal
        ))
    story.append(PageBreak())

    # ─────── RESUMEN EJECUTIVO ───────
    story.append(Paragraph("Resumen Ejecutivo", h2))
    story.append(Paragraph(
        "Consolidado de recomendaciones finales por período. "
        "Cada activo recibe una recomendación (COMPRA / VENTA / MANTENER) basada en el score ponderado "
        "que combina las señales estadísticas y técnicas según los pesos y umbrales configurados.",
        normal
    ))
    story.append(Spacer(1, 0.4*cm))

    for periodo, pdata in report_data['periodos'].items():
        story.append(Paragraph(f"Período: {periodo}", h3))
        if 'consolidado' in pdata['tables']:
            # Subset de columnas claves para resumen
            df_consol = pdata['tables']['consolidado']
            cols_resumen = [c for c in ['Score Final', 'RECOMENDACIÓN'] if c in df_consol.columns]
            if cols_resumen:
                df_show = df_consol[cols_resumen].copy()
                df_show.index.name = "Activo"
                story.append(df_to_pdf_table(df_show, font_size=8, col_widths=[3.5*cm, 3*cm, 4*cm]))
                story.append(Spacer(1, 0.3*cm))
    story.append(PageBreak())

    # ─────── POR CADA PERÍODO ───────
    for periodo, pdata in report_data['periodos'].items():
        story.append(Paragraph(f"Análisis del período: {periodo}", h1))
        story.append(Spacer(1, 0.4*cm))

        # ── Bloque Estadístico ──
        story.append(Paragraph("Bloque Estadístico", h2))

        if 'base100' in pdata['figs']:
            story.append(_safe_rl_image(pdata['figs']['base100'], 17*cm, 7.5*cm))
            story.append(Spacer(1, 0.3*cm))

        if 'corr' in pdata['figs']:
            story.append(_safe_rl_image(pdata['figs']['corr'], 17*cm, 7.5*cm))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("Métricas estadísticas por activo", h3))
        if 'stat' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['stat'], font_size=6.5))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("Análisis de percentiles (precio LN)", h3))
        if 'percentiles' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['percentiles'], font_size=6.5))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("Resumen de valoración estadística", h3))
        if 'resumen' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['resumen'], font_size=7))
        story.append(PageBreak())

        # ── Bloque Técnico ──
        story.append(Paragraph("Bloque Técnico", h2))

        story.append(Paragraph("Medias Móviles — Tabla resumen", h3))
        if 'mm' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['mm'], font_size=7))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("MACD — Tabla resumen", h3))
        if 'macd' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['macd'], font_size=7))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("RSI — Tabla resumen", h3))
        if 'rsi' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['rsi'], font_size=7))
            story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph("Fibonacci (ZigZag) — Niveles detectados", h3))
        if 'fib' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['fib'], font_size=6.5))
        story.append(PageBreak())

        # ── Consenso Técnico ──
        story.append(Paragraph("Consenso Técnico", h2))
        if 'consenso' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['consenso'], font_size=7))
        story.append(Spacer(1, 0.4*cm))

        # ── Consolidado Final ──
        story.append(Paragraph("Consolidado Final — Decisión", h2))
        if 'consolidado' in pdata['tables']:
            story.append(df_to_pdf_table(pdata['tables']['consolidado'], font_size=6))
            story.append(Spacer(1, 0.4*cm))

        if 'score' in pdata['figs']:
            story.append(_safe_rl_image(pdata['figs']['score'], 17*cm, 8.5*cm))

        story.append(PageBreak())

    # Footer en última página
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(
        f"<i>Reporte generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} — "
        "Quant Dashboard · Datos: Yahoo Finance / Excel</i>",
        small
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 QUANT DASHBOARD")
    st.markdown('<div class="section-header">FUENTE DE DATOS</div>', unsafe_allow_html=True)
    fuente = st.radio("", ["Yahoo Finance", "Excel"], horizontal=True)

    tickers_input, excel_file = [], None
    if fuente == "Yahoo Finance":
        raw_input = st.text_input(
            "Tickers (separados por coma — el último es el benchmark)",
            value="AAPL, ^GSPC"
        )
        tickers_input = [t.strip().upper() for t in raw_input.split(",") if t.strip()]
    else:
        excel_file = st.file_uploader(
            "Sube tu Excel (filas=fechas, columnas=activos, último=benchmark)",
            type=["xlsx","xls"]
        )

    st.markdown('<div class="section-header">PERÍODO DE ANÁLISIS</div>', unsafe_allow_html=True)
    periodos_sel = st.multiselect(
        "Selecciona uno o varios períodos",
        options=list(PERIODOS.keys()),
        default=["1 Año"]
    )

    st.markdown('<div class="section-header">PESOS VALORACIÓN</div>', unsafe_allow_html=True)
    w_stat_total = st.slider("Peso bloque estadístico (%)", 0, 100, 50, step=5) / 100
    w_tec_total  = 1 - w_stat_total
    st.caption(f"Técnico: {w_tec_total*100:.0f}%  |  Estadístico: {w_stat_total*100:.0f}%")

    st.markdown('<div class="section-header">PESOS ESTADÍSTICO</div>', unsafe_allow_html=True)
    w_reg_raw = st.slider("Regresión lineal (%)", 0, 100, 50, step=5)
    w_pct_raw = 100 - w_reg_raw
    st.caption(f"Regresión: {w_reg_raw}%  |  Percentil 50: {w_pct_raw}%")
    w_reg = w_reg_raw / 100
    w_pct = w_pct_raw / 100

    st.markdown('<div class="section-header">PESOS TÉCNICO</div>', unsafe_allow_html=True)
    mm_w   = st.slider("MM (%)",        0, 100, 17, step=1)
    rsi_w  = st.slider("RSI (%)",       0, 100, 17, step=1)
    macd_w = st.slider("MACD (%)",      0, 100, 17, step=1)
    fib_w  = st.slider("Fibonacci (%)", 0, 100, 49, step=1)
    total_tec = mm_w + rsi_w + macd_w + fib_w
    st.caption(f"Total técnico: {total_tec}% {'✅' if total_tec==100 else '⚠️ ≠100%'}")

    # ─────────────────────────────────────────────
    # PARÁMETROS DE INDICADORES (períodos)
    # ─────────────────────────────────────────────
    st.markdown('<div class="section-header">PARÁMETROS INDICADORES</div>', unsafe_allow_html=True)

    # Medias Móviles
    mm_periods_str = st.text_input(
        "Períodos MM (separados por coma)",
        value="5, 20, 100, 200",
        help="Ejemplo: 20, 30, 40 — generará MM20, MM30, MM40"
    )
    try:
        mm_periods = sorted({int(x.strip()) for x in mm_periods_str.split(",") if x.strip().isdigit() and int(x.strip()) > 0})
        if not mm_periods:
            mm_periods = MM_DEFAULT_PERIODS
            st.warning(f"Períodos MM inválidos. Usando default: {MM_DEFAULT_PERIODS}")
    except Exception:
        mm_periods = MM_DEFAULT_PERIODS
        st.warning(f"Períodos MM inválidos. Usando default: {MM_DEFAULT_PERIODS}")
    st.caption(f"MMs activas: {mm_periods}")

    # RSI
    rsi_period = st.number_input("Período RSI", min_value=2, max_value=200, value=14, step=1)
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        rsi_buy_threshold  = st.number_input("RSI Compra (≤)", min_value=1,  max_value=99, value=30, step=1)
    with col_r2:
        rsi_sell_threshold = st.number_input("RSI Venta (≥)",  min_value=1,  max_value=99, value=70, step=1)
    if rsi_buy_threshold >= rsi_sell_threshold:
        st.warning("⚠️ RSI Compra debe ser menor que RSI Venta")

    # MACD
    col_mc1, col_mc2, col_mc3 = st.columns(3)
    with col_mc1:
        macd_fast = st.number_input("MACD Fast", min_value=2, max_value=200, value=12, step=1)
    with col_mc2:
        macd_slow = st.number_input("MACD Slow", min_value=2, max_value=200, value=26, step=1)
    with col_mc3:
        macd_signal = st.number_input("MACD Signal", min_value=2, max_value=200, value=9, step=1)
    if macd_fast >= macd_slow:
        st.warning("⚠️ MACD Fast debe ser menor que Slow")

    # Fibonacci ZigZag
    st.markdown('<div class="section-header">FIBONACCI (ZIGZAG)</div>', unsafe_allow_html=True)
    fib_reversal_pct = st.number_input(
        "% reversión mínima",
        min_value=1.0, max_value=30.0, value=5.0, step=0.5,
        help="% de movimiento contrario para confirmar cambio de tendencia. "
             "Más alto = swings más significativos. 3% para índices, 5-10% para acciones volátiles."
    ) / 100
    fib_min_duration = st.number_input(
        "Duración mínima swing (días)",
        min_value=5, max_value=365, value=30, step=5,
        help="Días mínimos entre pivotes. Evita detectar swings muy cortos."
    )

    # Threshold estadístico (para convertir suma_producto en voto -1/0/+1)
    st.markdown('<div class="section-header">UMBRAL ESTADÍSTICO</div>', unsafe_allow_html=True)
    stat_threshold = st.number_input(
        "Umbral señal estadística (%)",
        min_value=0.0, max_value=50.0, value=5.0, step=0.5,
        help="Si potencial > +umbral → COMPRA. Si < -umbral → VENTA. En medio → HOLD."
    ) / 100

    # Threshold del score final consolidado
    st.markdown('<div class="section-header">UMBRAL DECISIÓN FINAL</div>', unsafe_allow_html=True)
    final_threshold = st.slider(
        "Umbral score final (zona muerta alrededor de 0)",
        min_value=0.0, max_value=1.0, value=0.35, step=0.05,
        help="Score > +umbral → COMPRA. Score < -umbral → VENTA. Entre -umbral y +umbral → MANTENER. "
             "Más alto = más exigente, más HOLD. Más bajo = más laxo, más señales."
    )
    st.caption(f"Zona MANTENER: score entre **{-final_threshold:+.2f}** y **{+final_threshold:+.2f}**")

    run_btn = st.button("▶  EJECUTAR ANÁLISIS", use_container_width=True)

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.markdown("# QUANT ANALYSIS DASHBOARD")
st.markdown("---")

if not run_btn:
    st.info("Configura los parámetros en el panel izquierdo y presiona **EJECUTAR ANÁLISIS**.")
    st.stop()

# Limpiar PDF anterior al ejecutar un análisis nuevo
if 'pdf_buffer' in st.session_state:
    del st.session_state['pdf_buffer']

if not periodos_sel:
    st.warning("Selecciona al menos un período.")
    st.stop()

# Cargar datos crudos (precios completos para análisis técnico)
with st.spinner("Cargando datos..."):
    try:
        if fuente == "Yahoo Finance":
            if len(tickers_input) < 2:
                st.error("Ingresa al menos 2 tickers (el último es el benchmark).")
                st.stop()
            benchmark_col = tickers_input[-1]
            # Cargar desde 2000-01-01 (suficiente para cualquier análisis técnico)
            prices_full = load_from_yahoo(tickers_input, period=None, start_date="2000-01-01")
        else:
            if excel_file is None:
                st.error("Sube un archivo Excel.")
                st.stop()
            prices_full = load_from_excel(excel_file)
            tickers_input = list(prices_full.columns)
            benchmark_col = tickers_input[-1]

        # ── DETECTAR TICKERS SIN DATOS ──
        empty_tickers = [c for c in prices_full.columns if prices_full[c].dropna().empty]
        if empty_tickers:
            st.warning(f"⚠️ Los siguientes tickers no devolvieron datos y serán excluidos: "
                       f"**{', '.join(empty_tickers)}**")
            prices_full = prices_full.drop(columns=empty_tickers)
            tickers_input = [t for t in tickers_input if t not in empty_tickers]

            # Verificar que el benchmark sigue presente
            if benchmark_col in empty_tickers:
                st.error(f"❌ El benchmark **{benchmark_col}** no devolvió datos. "
                         "Reemplázalo por uno válido (ej: ^GSPC, SPY, ^IXIC).")
                st.stop()

            if len(tickers_input) < 2:
                st.error("❌ Después de excluir tickers vacíos quedan menos de 2 activos.")
                st.stop()

        # ── UNIFICACIÓN DE FECHAS ──
        # Recortamos al primer día en que TODOS los activos tienen datos.
        # Esto garantiza que todas las estadísticas comparen el mismo período.
        prices_full_raw = prices_full.copy()
        prices_full = unify_dates(prices_full)

        if prices_full.empty:
            st.error("❌ Después de unificar fechas no quedaron datos comunes entre todos los activos. "
                     "Revisa que los tickers existan y tengan histórico solapado.")
            st.stop()

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

# ─────────────────────────────────────────────
# RESUMEN INICIAL
# ─────────────────────────────────────────────
with st.spinner("Obteniendo nombres de activos..."):
    if fuente == "Yahoo Finance":
        nombres = get_ticker_names(tickers_input)
    else:
        # En Excel los nombres son las columnas mismas
        nombres = {t: t for t in tickers_input}

activos_lista = [c for c in tickers_input if c != benchmark_col]

st.markdown('<div class="section-header">📋 RESUMEN DEL ANÁLISIS</div>', unsafe_allow_html=True)

# Detectar cuál activo determinó la fecha de inicio
first_valid_raw = prices_full_raw.apply(lambda c: c.first_valid_index()).dropna()
activo_limitante = first_valid_raw.idxmax() if len(first_valid_raw) > 0 else "—"
fecha_corte = first_valid_raw.max() if len(first_valid_raw) > 0 else None

col_r1, col_r2, col_r3 = st.columns(3)
with col_r1:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">📊 BENCHMARK</div>
      <div class="metric-value" style="font-size:16px">{nombres.get(benchmark_col, benchmark_col)}</div>
      <div class="metric-label">{benchmark_col}</div>
    </div>
    """, unsafe_allow_html=True)
with col_r2:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">📈 ACTIVOS ANALIZADOS</div>
      <div class="metric-value">{len(activos_lista)}</div>
      <div class="metric-label">+ 1 benchmark</div>
    </div>
    """, unsafe_allow_html=True)
with col_r3:
    fecha_ini = prices_full.index[0].strftime("%Y-%m-%d")
    fecha_fin = prices_full.index[-1].strftime("%Y-%m-%d")
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">📅 DATOS UNIFICADOS</div>
      <div class="metric-value">{len(prices_full)}</div>
      <div class="metric-label">{fecha_ini} → {fecha_fin}</div>
    </div>
    """, unsafe_allow_html=True)

# Aviso de fecha unificada
if activo_limitante != "—":
    st.info(f"📌 **Fecha unificada:** El análisis arranca desde **{fecha_corte.strftime('%Y-%m-%d')}** "
            f"porque **{activo_limitante}** ({nombres.get(activo_limitante, activo_limitante)}) "
            f"es el activo con menor histórico disponible. "
            f"Esto garantiza que todas las métricas estadísticas comparen el mismo período.")

# Tabla con nombres completos
st.markdown("**Activos en el análisis:**")
nombres_rows = []
for t in activos_lista:
    nombres_rows.append({"Ticker": t, "Nombre": nombres.get(t, t), "Rol": "Activo"})
nombres_rows.append({
    "Ticker": benchmark_col,
    "Nombre": nombres.get(benchmark_col, benchmark_col),
    "Rol": "Benchmark"
})
st.dataframe(pd.DataFrame(nombres_rows).set_index("Ticker"), use_container_width=True)

# Tabs por período
tabs = st.tabs(periodos_sel)

# Estructura acumuladora para PDF (se llena dentro del loop y persiste en session_state)
report_data = {
    'meta': {
        'tickers':           tickers_input,
        'benchmark':         benchmark_col,
        'fecha_ini':         prices_full.index[0].strftime("%Y-%m-%d"),
        'fecha_fin':         prices_full.index[-1].strftime("%Y-%m-%d"),
        'nombres':           nombres,
        'activos':           activos_lista,
        'activo_limitante':  activo_limitante if activo_limitante != "—" else None,
        'fecha_corte':       fecha_corte.strftime("%Y-%m-%d") if fecha_corte is not None else None,
        'config': {
            'w_stat_total':       w_stat_total,
            'w_tec_total':        w_tec_total,
            'w_reg':              w_reg,
            'w_pct':              w_pct,
            'mm_w':               mm_w,
            'rsi_w':              rsi_w,
            'macd_w':             macd_w,
            'fib_w':              fib_w,
            'mm_periods':         mm_periods,
            'rsi_period':         rsi_period,
            'rsi_buy_threshold':  rsi_buy_threshold,
            'rsi_sell_threshold': rsi_sell_threshold,
            'macd_fast':          macd_fast,
            'macd_slow':          macd_slow,
            'macd_signal':        macd_signal,
            'fib_reversal_pct':   fib_reversal_pct,
            'fib_min_duration':   fib_min_duration,
            'stat_threshold':     stat_threshold,
            'final_threshold':    final_threshold,
        },
    },
    'periodos': {},
}

for tab, periodo_label in zip(tabs, periodos_sel):
    with tab:
        # ── Filtrar por período (sobre los datos ya cargados y unificados) ──
        n_map = {"1 Mes":30,"3 Meses":90,"6 Meses":180,"1 Año":365,
                 "2 Años":730,"3 Años":1095,"5 Años":1825,"10 Años":3650,"Máximo":99999}
        days = n_map.get(periodo_label, 365)
        cutoff = prices_full.index[-1] - pd.Timedelta(days=days)
        prices = prices_full[prices_full.index >= cutoff].copy()

        if prices.empty or len(prices) < 5:
            st.warning(f"Datos insuficientes para {periodo_label}.")
            continue

        # Asegurar que benchmark existe
        if benchmark_col not in prices.columns:
            st.error(f"Benchmark {benchmark_col} no encontrado en los datos.")
            continue

        # ── Cálculos base ──
        returns  = calc_returns(prices)
        base100  = calc_base100(prices)
        ln_prices = calc_ln(prices)
        stats_result = calc_stats(ln_prices, benchmark_col)
        stats_result = calc_precio_valorado(stats_result, w_reg, w_pct)
        activos = [c for c in prices.columns if c != benchmark_col]

        # ════════════════════════════════════════════
        # BLOQUE 1: ESTADÍSTICO
        # ════════════════════════════════════════════
        st.markdown(f'<div class="section-header">📐 BLOQUE ESTADÍSTICO — {periodo_label}</div>',
                    unsafe_allow_html=True)

        # Gráfico base 100
        st.plotly_chart(fig_base100(base100, benchmark_col), use_container_width=True,
                        key=f"base100_{periodo_label}")

        # Gráfico correlación
        if activos:
            st.plotly_chart(fig_correlacion(ln_prices, stats_result, benchmark_col),
                            use_container_width=True, key=f"corr_{periodo_label}")

        # Tabla de métricas estadísticas
        st.markdown("**Métricas Estadísticas por Activo**")
        rows_stat = []
        for col in activos:
            s = stats_result[col]
            rows_stat.append({
                "Activo":         col,
                "Correlación":    f"{s['corr']:.4f}",
                "Alpha":          f"{s['alpha']:.6f}",
                "Beta":           f"{s['beta']:.4f}",
                "R²":             f"{s['r2']:.4f}",
                "Val. Estadística": f"{s['val_stat']:.2f}",
                "Pot. Val. Reg (%)": f"{s['pot_val_reg']*100:.2f}%",
                "Std 20d":        f"{s['std_20']:.6f}",
                "Media 20d":      f"{s['mean_20']:.6f}",
                "CV 20d":         f"{s['cv_20']:.4f}",
                "Rango Pct Actual": f"{s['pct_rank']*100:.1f}%",
                "Pot. Val. Pct (%)": f"{s['pot_val_pct']*100:.2f}%",
                "Precio Actual":  f"{s['last_price']:.2f}",
                "Precio Valorado": f"{s['precio_valorado']:.2f}",
                "Suma Ponderada (%)": f"{s['suma_producto']*100:.2f}%",
            })
        df_stat = pd.DataFrame(rows_stat).set_index("Activo")
        st.dataframe(df_stat, use_container_width=True)

        # Tabla de percentiles
        st.markdown("**Análisis de Percentiles (Precio LN)**")
        pct_rows = {}
        for col in activos:
            pct_rows[col] = {f"P{p}%": f"{stats_result[col]['percentiles'][p]:.4f}"
                             for p in PERCENTILES_LIST}
        st.dataframe(pd.DataFrame(pct_rows).T, use_container_width=True)

        # Resumen precio valorado (tabla consolidada)
        st.markdown("**Resumen Valoración Estadística**")
        resumen_rows = []
        for col in activos:
            s = stats_result[col]
            resumen_rows.append({
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "Precio Actual":     f"${s['last_price']:.2f}",
                "Precio Valorado":   f"${s['precio_valorado']:.2f}",
                "Potencial (%)":     f"{s['suma_producto']*100:+.2f}%",
                "Señal Estadística": "COMPRA ▲" if s['suma_producto'] > 0 else ("VENTA ▼" if s['suma_producto'] < 0 else "NEUTRO"),
            })
        df_resumen = pd.DataFrame(resumen_rows).set_index("Activo")
        st.dataframe(df_resumen, use_container_width=True)

        # ════════════════════════════════════════════
        # BLOQUE 2: TÉCNICO
        # ════════════════════════════════════════════
        st.markdown(f'<div class="section-header">📈 BLOQUE TÉCNICO — {periodo_label}</div>',
                    unsafe_allow_html=True)

        # Precalcular indicadores para todos los activos
        tec_cache = {}
        for col in activos:
            if col in prices_full.columns:
                p_tec_i = prices_full[col].dropna()
            else:
                p_tec_i = prices[col].dropna()

            mm_df_i   = calc_mm(p_tec_i, periods=mm_periods)
            mm_sigs_i = get_mm_signal(mm_df_i, periods=mm_periods)
            mm_sum    = get_mm_summary(mm_sigs_i)

            macd_df_i  = calc_macd(p_tec_i, fast=macd_fast, slow=macd_slow, signal=macd_signal)
            macd_sig_i = get_macd_signal(macd_df_i)
            macd_sum   = get_macd_summary(macd_sig_i)

            rsi_series_i = calc_rsi(p_tec_i, period=rsi_period)
            rsi_sig_i    = get_rsi_signal(rsi_series_i, buy_th=rsi_buy_threshold, sell_th=rsi_sell_threshold)
            rsi_sum      = get_rsi_summary(rsi_sig_i)
            rsi_last     = rsi_series_i.dropna().iloc[-1] if len(rsi_series_i.dropna()) > 0 else np.nan

            fib_sig_i, fib_levels_i, fib_meta_i = get_fib_signal(
                p_tec_i, reversal_pct=fib_reversal_pct, min_duration_days=fib_min_duration
            )
            fib_sum                 = get_fib_summary(fib_sig_i)

            tec_cache[col] = {
                "p_tec": p_tec_i,
                "mm_df": mm_df_i, "mm_sigs": mm_sigs_i, "mm_sum": mm_sum,
                "macd_df": macd_df_i, "macd_sig": macd_sig_i, "macd_sum": macd_sum,
                "rsi": rsi_series_i, "rsi_sig": rsi_sig_i, "rsi_sum": rsi_sum, "rsi_last": rsi_last,
                "fib_sig": fib_sig_i, "fib_levels": fib_levels_i, "fib_meta": fib_meta_i, "fib_sum": fib_sum,
                "last_price": p_tec_i.iloc[-1] if len(p_tec_i) > 0 else np.nan,
            }

        # ════════════════════════════════════════════
        # MEDIAS MÓVILES
        # ════════════════════════════════════════════
        st.markdown(f"### 📊 Medias Móviles ({', '.join(str(p) for p in mm_periods)})")
        mm_table = []
        for col in activos:
            c = tec_cache[col]
            mm_last = c["mm_df"].iloc[-1]
            row = {
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "Precio":  f"${c['last_price']:.2f}",
            }
            for w in mm_periods:
                key = f"MM{w}"
                row[f"MM {w}"] = f"${mm_last[key]:.2f}" if pd.notna(mm_last[key]) else "—"
            row["Señal"] = c["mm_sum"]
            mm_table.append(row)
        st.dataframe(pd.DataFrame(mm_table).set_index("Activo"), use_container_width=True)

        ticker_mm = st.selectbox("Ver gráfica de MM:", options=activos, key=f"mm_sel_{periodo_label}")
        if ticker_mm:
            c = tec_cache[ticker_mm]
            st.plotly_chart(fig_mm(c["mm_df"], ticker_mm, periods=mm_periods), use_container_width=True,
                            key=f"mm_chart_{periodo_label}_{ticker_mm}")
            for sig in c["mm_sigs"]:
                if "COMPRA" in sig or "GOLDEN" in sig:
                    st.markdown(f'<span class="signal-buy">{sig}</span>', unsafe_allow_html=True)
                elif "VENTA" in sig or "DEATH" in sig:
                    st.markdown(f'<span class="signal-sell">{sig}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="signal-hold">{sig}</span>', unsafe_allow_html=True)

        # ════════════════════════════════════════════
        # MACD
        # ════════════════════════════════════════════
        st.markdown(f"### 📊 MACD ({macd_fast}, {macd_slow}, {macd_signal})")
        macd_table = []
        for col in activos:
            c = tec_cache[col]
            macd_last = c["macd_df"].iloc[-1]
            macd_table.append({
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "MACD":      f"{macd_last['macd']:.4f}"   if pd.notna(macd_last['macd'])   else "—",
                "Signal":    f"{macd_last['signal']:.4f}" if pd.notna(macd_last['signal']) else "—",
                "Histograma":f"{macd_last['hist']:.4f}"   if pd.notna(macd_last['hist'])   else "—",
                "Señal":     c["macd_sum"],
            })
        st.dataframe(pd.DataFrame(macd_table).set_index("Activo"), use_container_width=True)

        ticker_macd = st.selectbox("Ver gráfica de MACD:", options=activos, key=f"macd_sel_{periodo_label}")
        if ticker_macd:
            c = tec_cache[ticker_macd]
            st.plotly_chart(fig_macd(c["macd_df"], ticker_macd), use_container_width=True,
                            key=f"macd_chart_{periodo_label}_{ticker_macd}")
            sig = c["macd_sig"]
            if "COMPRA" in sig:
                st.markdown(f'<span class="signal-buy">{sig}</span>', unsafe_allow_html=True)
            elif "VENTA" in sig:
                st.markdown(f'<span class="signal-sell">{sig}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="signal-hold">{sig}</span>', unsafe_allow_html=True)

        # ════════════════════════════════════════════
        # RSI
        # ════════════════════════════════════════════
        st.markdown(f"### 📊 RSI ({rsi_period})")
        rsi_table = []
        for col in activos:
            c = tec_cache[col]
            rsi_val = c["rsi_last"]
            if pd.notna(rsi_val):
                if rsi_val < 30:    zona = "Sobrevendido"
                elif rsi_val > 70:  zona = "Sobrecomprado"
                else:               zona = "Neutral"
            else:
                zona = "—"
            rsi_table.append({
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "RSI Actual": f"{rsi_val:.2f}" if pd.notna(rsi_val) else "—",
                "Zona":  zona,
                "Señal": c["rsi_sum"],
            })
        st.dataframe(pd.DataFrame(rsi_table).set_index("Activo"), use_container_width=True)

        ticker_rsi = st.selectbox("Ver gráfica de RSI:", options=activos, key=f"rsi_sel_{periodo_label}")
        if ticker_rsi:
            c = tec_cache[ticker_rsi]
            st.plotly_chart(fig_rsi(c["rsi"], ticker_rsi, period=rsi_period,
                                     buy_th=rsi_buy_threshold, sell_th=rsi_sell_threshold),
                            use_container_width=True,
                            key=f"rsi_chart_{periodo_label}_{ticker_rsi}")
            sig = c["rsi_sig"]
            if "COMPRA" in sig:
                st.markdown(f'<span class="signal-buy">{sig}</span>', unsafe_allow_html=True)
            elif "VENTA" in sig:
                st.markdown(f'<span class="signal-sell">{sig}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="signal-hold">{sig}</span>', unsafe_allow_html=True)

        # ════════════════════════════════════════════
        # FIBONACCI
        # ════════════════════════════════════════════
        st.markdown("### 📊 Fibonacci (Retrocesos)")
        fib_table = []
        for col in activos:
            c = tec_cache[col]
            lvls = c["fib_levels"]
            fib_table.append({
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "Precio Actual": f"${c['last_price']:.2f}",
                "0% (Min)":  f"${lvls['0% (Mínimo)']:.2f}",
                "23.6%":     f"${lvls['23.6%']:.2f}",
                "38.2%":     f"${lvls['38.2%']:.2f}",
                "50%":       f"${lvls['50%']:.2f}",
                "61.8%":     f"${lvls['61.8%']:.2f}",
                "100% (Max)":f"${lvls['100% (Máximo)']:.2f}",
                "Señal":     c["fib_sum"],
            })
        st.dataframe(pd.DataFrame(fib_table).set_index("Activo"), use_container_width=True)

        ticker_fib = st.selectbox("Ver gráfica de Fibonacci:", options=activos, key=f"fib_sel_{periodo_label}")
        if ticker_fib:
            c = tec_cache[ticker_fib]
            st.plotly_chart(fig_fibonacci(c["p_tec"], c["fib_levels"], ticker_fib, meta=c["fib_meta"]),
                            use_container_width=True,
                            key=f"fib_chart_{periodo_label}_{ticker_fib}")
            sig = c["fib_sig"]
            if "COMPRA" in sig:
                st.markdown(f'<span class="signal-buy">{sig}</span>', unsafe_allow_html=True)
            elif "VENTA" in sig:
                st.markdown(f'<span class="signal-sell">{sig}</span>', unsafe_allow_html=True)
            else:
                st.markdown(f'<span class="signal-hold">{sig}</span>', unsafe_allow_html=True)

        # ════════════════════════════════════════════
        # CONSENSO TÉCNICO (resumen)
        # ════════════════════════════════════════════
        st.markdown("### 🎯 Consenso Técnico")
        consenso_table = []
        for col in activos:
            c = tec_cache[col]
            votes = [c["mm_sum"], c["macd_sum"], c["rsi_sum"], c["fib_sum"]]
            n_buy  = sum(1 for v in votes if v == "COMPRA")
            n_sell = sum(1 for v in votes if v == "VENTA")
            if n_buy > n_sell:
                consenso = f"COMPRA ({n_buy}/4)"
            elif n_sell > n_buy:
                consenso = f"VENTA ({n_sell}/4)"
            else:
                consenso = "HOLD / MIXTO"
            consenso_table.append({
                "Activo": col,
                "Nombre": nombres.get(col, col),
                "MM":   c["mm_sum"],
                "MACD": c["macd_sum"],
                "RSI":  c["rsi_sum"],
                "Fib":  c["fib_sum"],
                "Consenso": consenso,
            })
        st.dataframe(pd.DataFrame(consenso_table).set_index("Activo"), use_container_width=True)

        # ════════════════════════════════════════════
        # BLOQUE 3: CONSOLIDADO FINAL — RECOMENDACIÓN
        # ════════════════════════════════════════════
        st.markdown(f'<div class="section-header">⚖️ CONSOLIDADO FINAL — {periodo_label}</div>',
                    unsafe_allow_html=True)

        # Mapeo señal → voto
        def signal_to_vote(sig):
            if sig == "COMPRA": return 1
            if sig == "VENTA":  return -1
            return 0  # HOLD, MIXTO o cualquier otro

        # Voto del bloque estadístico: depende del threshold
        def stat_to_vote(suma_producto, threshold):
            if suma_producto >  threshold: return 1
            if suma_producto < -threshold: return -1
            return 0

        # Mapeo voto → etiqueta
        def vote_label(v):
            if v == 1:  return "COMPRA ▲"
            if v == -1: return "VENTA ▼"
            return "MANTENER ●"

        # Verificación de pesos
        total_tec_check = mm_w + rsi_w + macd_w + fib_w
        if total_tec_check != 100:
            st.warning(f"⚠️ Los pesos técnicos suman {total_tec_check}% (no 100%). "
                       f"El score técnico se normaliza dividiendo por la suma real.")

        st.markdown(f"""
        **Configuración aplicada:**
        - Pesos macro → Estadístico: **{w_stat_total*100:.0f}%** | Técnico: **{w_tec_total*100:.0f}%**
        - Pesos técnicos → MM: **{mm_w}%** | RSI: **{rsi_w}%** | MACD: **{macd_w}%** | Fib: **{fib_w}%**
        - Umbral estadístico: **±{stat_threshold*100:.1f}%** (zona muerta alrededor de cero)
        - Umbrales RSI: compra ≤ **{rsi_buy_threshold}** | venta ≥ **{rsi_sell_threshold}**
        - Umbral decisión final: **±{final_threshold:.2f}** → MANTENER si score ∈ [{-final_threshold:+.2f}, {+final_threshold:+.2f}]
        """)

        # ───────── Construir tabla consolidada ─────────
        consol_rows = []
        # Normalización: si los pesos técnicos no suman 100, los dividimos por la suma real
        tec_weights_sum = mm_w + rsi_w + macd_w + fib_w
        if tec_weights_sum == 0:
            tec_weights_sum = 1  # evita división por cero
        w_mm_n   = mm_w   / tec_weights_sum
        w_rsi_n  = rsi_w  / tec_weights_sum
        w_macd_n = macd_w / tec_weights_sum
        w_fib_n  = fib_w  / tec_weights_sum

        for col in activos:
            c = tec_cache[col]
            s = stats_result[col]

            # Votos individuales
            v_mm   = signal_to_vote(c["mm_sum"])
            v_rsi  = signal_to_vote(c["rsi_sum"])
            v_macd = signal_to_vote(c["macd_sum"])
            v_fib  = signal_to_vote(c["fib_sum"])
            v_stat = stat_to_vote(s["suma_producto"], stat_threshold)

            # Score técnico ponderado [-1, +1]
            score_tec = (v_mm * w_mm_n) + (v_rsi * w_rsi_n) + (v_macd * w_macd_n) + (v_fib * w_fib_n)

            # Score estadístico ya está en [-1, +1] (vino del mapeo binario)
            score_stat = v_stat

            # Score final ponderado entre los dos bloques
            score_final = score_stat * w_stat_total + score_tec * w_tec_total

            # Recomendación final con zona muerta (umbral final_threshold)
            # |score| < threshold → MANTENER
            # score ≥ +threshold → COMPRA
            # score ≤ -threshold → VENTA
            if score_final >=  final_threshold:
                rec_final = 1
            elif score_final <= -final_threshold:
                rec_final = -1
            else:
                rec_final = 0

            consol_rows.append({
                "Activo":         col,
                "Nombre":         nombres.get(col, col),
                "Estadístico":    f"{v_stat:+d} ({vote_label(v_stat)})",
                "MM":             f"{v_mm:+d} ({c['mm_sum']})",
                "RSI":            f"{v_rsi:+d} ({c['rsi_sum']})",
                "MACD":           f"{v_macd:+d} ({c['macd_sum']})",
                "Fibonacci":      f"{v_fib:+d} ({c['fib_sum']})",
                "Score Técnico":  f"{score_tec:+.3f}",
                "Score Estadístico": f"{score_stat:+.3f}",
                "Score Final":    f"{score_final:+.3f}",
                "RECOMENDACIÓN":  vote_label(rec_final),
            })

        df_consol = pd.DataFrame(consol_rows).set_index("Activo")

        # Tabla con los votos absolutos y scores
        st.markdown("### 📋 Tabla consolidada de votos y scores")
        st.dataframe(df_consol, use_container_width=True)

        # ───────── Tarjetas resumen por activo ─────────
        st.markdown("### 🎯 Recomendación final por activo")
        n_cols = min(len(activos), 3)
        if n_cols > 0:
            cols_cards = st.columns(n_cols)
            for i, row in enumerate(consol_rows):
                col_box = cols_cards[i % n_cols]
                rec_text = row["RECOMENDACIÓN"]
                score_f = row["Score Final"]
                if "COMPRA" in rec_text:
                    bg, border, color = "#1a3a2a", "#2f855a", "#68d391"
                elif "VENTA" in rec_text:
                    bg, border, color = "#3a1a1a", "#9b2c2c", "#fc8181"
                else:
                    bg, border, color = "#2a2a1a", "#975a16", "#fbd38d"
                col_box.markdown(f"""
                <div style="background:{bg}; border:1px solid {border}; border-radius:8px; padding:14px; margin:6px 0;">
                  <div style="font-family:'IBM Plex Mono',monospace; font-size:11px; color:#a0aec0; text-transform:uppercase; letter-spacing:1px;">
                    {row['Activo']} — {row['Nombre'][:25]}
                  </div>
                  <div style="font-family:'IBM Plex Mono',monospace; font-size:24px; font-weight:600; color:{color}; margin-top:6px;">
                    {rec_text}
                  </div>
                  <div style="font-family:'IBM Plex Mono',monospace; font-size:13px; color:#a0aec0; margin-top:4px;">
                    Score: <span style="color:{color}">{score_f}</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ───────── Gráfico de scores ─────────
        st.markdown("### 📊 Visualización de scores")
        score_vals = [float(r["Score Final"]) for r in consol_rows]
        labels = [r["Activo"] for r in consol_rows]
        bar_colors = ["#68d391" if v > 0 else ("#fc8181" if v < 0 else "#fbd38d") for v in score_vals]
        fig_score = go.Figure(go.Bar(x=labels, y=score_vals, marker_color=bar_colors,
                                     text=[f"{v:+.3f}" for v in score_vals], textposition="outside"))
        fig_score.add_hline(y=0, line=dict(color="#4a5568", dash="solid", width=1))
        # Líneas del umbral final (zona muerta)
        fig_score.add_hline(y=+final_threshold, line=dict(color="#68d391", dash="dash", width=1),
                            annotation_text=f"Compra ≥ {+final_threshold:+.2f}", annotation_position="right")
        fig_score.add_hline(y=-final_threshold, line=dict(color="#fc8181", dash="dash", width=1),
                            annotation_text=f"Venta ≤ {-final_threshold:+.2f}", annotation_position="right")
        fig_score.add_hrect(y0=-final_threshold, y1=+final_threshold,
                            fillcolor="#fbd38d", opacity=0.08, line_width=0)
        layout_score = {**DARK_LAYOUT, "yaxis": dict(range=[-1.1, 1.1], gridcolor="#1e2535", showgrid=True)}
        fig_score.update_layout(title="Score Final por Activo (rango [-1, +1])", **layout_score)
        st.plotly_chart(fig_score, use_container_width=True, key=f"score_chart_{periodo_label}")

        # Guardar consol_rows para usar en Excel
        consol_df_for_excel = df_consol.copy()

        # ════════════════════════════════════════════
        # ACUMULAR DATOS PARA INFORME PDF
        # ════════════════════════════════════════════
        report_data['periodos'][periodo_label] = {
            'figs': {
                'base100': fig_base100(base100, benchmark_col),
                'corr':    fig_correlacion(ln_prices, stats_result, benchmark_col) if activos else None,
                'score':   fig_score,
            },
            'tables': {
                'stat':         df_stat,
                'percentiles':  pd.DataFrame(pct_rows).T,
                'resumen':      df_resumen,
                'mm':           pd.DataFrame(mm_table).set_index("Activo"),
                'macd':         pd.DataFrame(macd_table).set_index("Activo"),
                'rsi':          pd.DataFrame(rsi_table).set_index("Activo"),
                'fib':          pd.DataFrame(fib_table).set_index("Activo"),
                'consenso':     pd.DataFrame(consenso_table).set_index("Activo"),
                'consolidado':  df_consol,
            },
        }

        # Guardar en session_state para que persista al hacer clic en botón PDF
        st.session_state['report_data'] = report_data

        # ════════════════════════════════════════════
        # EXPORTAR A EXCEL
        # ════════════════════════════════════════════
        st.markdown(f'<div class="section-header">📥 EXPORTAR A EXCEL — {periodo_label}</div>',
                    unsafe_allow_html=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Hoja 1: Precios
            prices.to_excel(writer, sheet_name='Precios')
            # Hoja 2: Rendimientos
            returns.to_excel(writer, sheet_name='Rendimientos')
            # Hoja 3: Base 100
            base100.to_excel(writer, sheet_name='Base 100')
            # Hoja 4: Precios LN
            ln_prices.to_excel(writer, sheet_name='Precios LN')
            # Hoja 5: Métricas estadísticas
            df_stat.to_excel(writer, sheet_name='Estadísticas')
            # Hoja 6: Percentiles
            pd.DataFrame(pct_rows).T.to_excel(writer, sheet_name='Percentiles')
            # Hoja 7: Resumen valoración
            pd.DataFrame(consol_df_for_excel).to_excel(writer, sheet_name='Consolidado Final')
            # Hoja estadisticas sin tilde para compatibilidad
            df_stat.to_excel(writer, sheet_name='Estadisticas')

            # Hojas técnicas por activo
            for col in activos:
                if col in prices_full.columns:
                    p_tec = prices_full[col].dropna()
                else:
                    p_tec = prices[col].dropna()

                # MM
                mm_df_export = calc_mm(p_tec, periods=mm_periods)
                sheet_mm = f'MM_{col}'[:31]  # Excel limita a 31 chars
                mm_df_export.to_excel(writer, sheet_name=sheet_mm)

                # MACD
                macd_df_export = calc_macd(p_tec, fast=macd_fast, slow=macd_slow, signal=macd_signal)
                sheet_macd = f'MACD_{col}'[:31]
                macd_df_export.to_excel(writer, sheet_name=sheet_macd)

                # RSI
                rsi_export = calc_rsi(p_tec, period=rsi_period)
                sheet_rsi = f'RSI_{col}'[:31]
                rsi_export.to_frame(name=f'RSI_{rsi_period}').to_excel(writer, sheet_name=sheet_rsi)

                # Fibonacci (con parámetros ZigZag)
                fib_levels_export = calc_fibonacci(p_tec,
                                                   reversal_pct=fib_reversal_pct,
                                                   min_duration_days=fib_min_duration)[0]
                sheet_fib = f'Fib_{col}'[:31]
                pd.DataFrame(list(fib_levels_export.items()),
                             columns=['Nivel', 'Precio']).to_excel(writer, sheet_name=sheet_fib, index=False)

        buffer.seek(0)
        st.download_button(
            label="⬇  DESCARGAR ANÁLISIS COMPLETO (Excel)",
            data=buffer,
            file_name=f"quant_analysis_{periodo_label.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"download_{periodo_label}"
        )

st.markdown("---")
st.markdown('<div class="section-header">📄 INFORME PDF — TODOS LOS PERÍODOS</div>',
            unsafe_allow_html=True)

# Generar PDF automáticamente después del análisis y guardarlo en session_state
if 'report_data' in st.session_state and st.session_state['report_data']['periodos']:
    # Si no hay PDF generado aún o los datos cambiaron, generarlo automáticamente
    if 'pdf_buffer' not in st.session_state:
        with st.spinner("Construyendo informe PDF (esto puede tardar un momento)..."):
            try:
                pdf_buf = build_pdf_report(st.session_state['report_data'])
                st.session_state['pdf_buffer'] = pdf_buf.getvalue()
                st.success("✅ Informe PDF generado correctamente.")
            except Exception as e:
                st.error(f"❌ Error generando PDF: {e}")
                st.exception(e)

    # Mostrar botón de descarga si el PDF ya existe en session_state
    if 'pdf_buffer' in st.session_state:
        st.download_button(
            label="⬇  DESCARGAR INFORME PDF COMPLETO",
            data=st.session_state['pdf_buffer'],
            file_name=f"quant_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="download_pdf_final"
        )

    # Botón para regenerar (si el usuario cambió parámetros)
    if st.button("🔄  REGENERAR PDF", use_container_width=True, key="regen_pdf_btn"):
        with st.spinner("Regenerando informe PDF..."):
            try:
                pdf_buf = build_pdf_report(st.session_state['report_data'])
                st.session_state['pdf_buffer'] = pdf_buf.getvalue()
                st.success("✅ PDF regenerado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error regenerando PDF: {e}")
                st.exception(e)
else:
    st.info("Ejecuta el análisis primero para generar el informe PDF.")

st.markdown("---")
st.caption("Quant Dashboard · Análisis técnico y estadístico · Datos: Yahoo Finance / Excel")
