# 📈 Quant Dashboard — Analisis Estadistico de Mercados

Dashboard cuantitativo de analisis estadistico avanzado para activos financieros.
Incluye indicadores tecnicos, regresiones, distribucion de retornos y generacion de reportes PDF.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://quant-dashboard-jnrc.streamlit.app)

---

## Funcionalidades

| Modulo | Descripcion |
|---|---|
| **Estadistica descriptiva** | Media, mediana, desviacion estandar, sesgo, curtosis de retornos |
| **Distribucion** | Histograma de retornos + ajuste a distribucion normal |
| **Regresion lineal** | Regresion simple y multivariante entre activos |
| **Correlacion** | Mapa de calor de correlaciones, scatter matrix |
| **Analisis tecnico** | Medias moviles, RSI, MACD, Bandas Bollinger |
| **Señales** | Generacion automatica de señales de compra/venta |
| **Comparativo** | Comparacion de multiples activos simultaneamente |
| **Reporte PDF** | Exportacion de informe estadistico completo con graficas |

---

## Instalacion local

```bash
git clone https://github.com/jnicolas1551/quant-dashboard.git
cd quant-dashboard
pip install -r requirements.txt
streamlit run app.py
```

---

## Estructura del proyecto

```
quant-dashboard/
├── app.py               # Aplicacion Streamlit completa (standalone)
├── requirements.txt
└── .streamlit/
    └── config.toml      # Tema oscuro
```

> El dashboard es completamente autonomo: toda la logica esta integrada
> en `app.py` sin dependencias de modulos locales.

---

## Analisis disponibles

### Estadistica de retornos
- Retorno diario, semanal, mensual y anual
- Distribucion de retornos con test de normalidad (Shapiro-Wilk, Jarque-Bera)
- Percentiles (5%, 25%, 50%, 75%, 95%)
- VaR historico al 95% y 99%

### Indicadores tecnicos
- **Medias moviles:** SMA 20, SMA 50, SMA 200, EMA 20
- **RSI:** 14 periodos con zonas de sobrecompra/sobreventa
- **MACD:** (12, 26) con linea de señal (9)
- **Bandas Bollinger:** 20 periodos, 2 desviaciones

### Regresion
- Regresion lineal simple: activo vs benchmark
- Coeficiente beta, alpha de Jensen, R²
- Intervalo de confianza 95%

### Reporte PDF
- Generado con ReportLab
- Incluye graficas embebidas, tablas estadisticas y señales
- Descargable directamente desde el dashboard

---

## Mercados soportados

| Region | Ejemplos |
|---|---|
| USA | AAPL, MSFT, GOOGL, ^GSPC, ^VIX |
| Colombia (BVC) | ECOPETROL.CL, PFBCOLOM.CL |
| Europa | SAP.DE, NESN.SW |
| Cualquier ticker Yahoo Finance | Acciones, ETFs, indices, divisas |

---

## Disclaimer

Herramienta educativa e informativa. Las señales generadas no constituyen
recomendacion de inversion. Consulte con un asesor financiero certificado.

---

*Desarrollado con Python + Streamlit + yfinance + scipy + ReportLab + Plotly*
