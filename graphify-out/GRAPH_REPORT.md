# Graph Report - .  (2026-05-30)

## Corpus Check
- 3 files · ~7,500 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 107 nodes · 109 edges · 28 communities (6 shown, 22 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_PDF Generation & Valuation|PDF Generation & Valuation]]
- [[_COMMUNITY_Technical Indicators (AST)|Technical Indicators (AST)]]
- [[_COMMUNITY_PDF Report Engine|PDF Report Engine]]
- [[_COMMUNITY_Chart Visualization Layer|Chart Visualization Layer]]
- [[_COMMUNITY_Fibonacci ZigZag Analysis|Fibonacci ZigZag Analysis]]
- [[_COMMUNITY_Yahoo Finance Data|Yahoo Finance Data]]
- [[_COMMUNITY_Ticker Name Resolution|Ticker Name Resolution]]
- [[_COMMUNITY_Base Return Calculations|Base Return Calculations]]
- [[_COMMUNITY_Price Valuation Model|Price Valuation Model]]
- [[_COMMUNITY_Data Loading|Data Loading]]
- [[_COMMUNITY_Moving Average Signals|Moving Average Signals]]
- [[_COMMUNITY_Date Harmonization|Date Harmonization]]
- [[_COMMUNITY_MA Summary|MA Summary]]
- [[_COMMUNITY_Project Documentation|Project Documentation]]
- [[_COMMUNITY_Statistical Analysis Docs|Statistical Analysis Docs]]
- [[_COMMUNITY_Technical Indicators Docs|Technical Indicators Docs]]
- [[_COMMUNITY_PDF Report Docs|PDF Report Docs]]
- [[_COMMUNITY_Supported Markets Docs|Supported Markets Docs]]
- [[_COMMUNITY_Base100 Chart|Base100 Chart]]
- [[_COMMUNITY_Correlation Chart|Correlation Chart]]
- [[_COMMUNITY_Excel Data Source|Excel Data Source]]
- [[_COMMUNITY_Date Utilities|Date Utilities]]
- [[_COMMUNITY_Ticker Names Helper|Ticker Names Helper]]
- [[_COMMUNITY_Streamlit Dependency|Streamlit Dependency]]
- [[_COMMUNITY_Plotly Dependency|Plotly Dependency]]
- [[_COMMUNITY_Pandas Dependency|Pandas Dependency]]
- [[_COMMUNITY_NumPy Dependency|NumPy Dependency]]

## God Nodes (most connected - your core abstractions)
1. `tec_cache (per-period indicator cache)` - 14 edges
2. `tec_figs_pdf` - 7 edges
3. `build_pdf_report` - 6 edges
4. `consol_rows` - 6 edges
5. `Investing Memo Section` - 6 edges
6. `build_pdf_report()` - 5 edges
7. `stats_result (per period)` - 5 edges
8. `Excel Export (openpyxl)` - 5 edges
9. `calc_fibonacci()` - 4 edges
10. `_safe_rl_image()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `build_pdf_report` --references--> `reportlab>=4.0.0`  [EXTRACTED]
  app.py → requirements.txt
- `_rec_color` --references--> `reportlab>=4.0.0`  [INFERRED]
  app.py → requirements.txt
- `Excel Export (openpyxl)` --references--> `openpyxl>=3.1.0`  [EXTRACTED]
  app.py → requirements.txt
- `plotly_to_image` --references--> `kaleido==0.2.1`  [EXTRACTED]
  app.py → requirements.txt
- `calc_stats` --references--> `scipy>=1.12.0`  [EXTRACTED]
  app.py → requirements.txt

## Hyperedges (group relationships)
- **PDF Investing Memo Generation Pipeline** — app_build_pdf_report, app_tec_figs_pdf, app_consol_rows, app_stats_result, app__rec_color, app_conclusion_box, app_investing_memo [EXTRACTED 1.00]
- **Technical Indicator Computation per Period** — app_tec_cache, app_calc_mm, app_calc_macd, app_calc_rsi, app_calc_fibonacci, app_get_mm_signal, app_get_mm_summary, app_get_macd_signal, app_get_macd_summary, app_get_rsi_signal, app_get_rsi_summary, app_get_fib_signal, app_get_fib_summary, app_detect_zigzag_pivots [EXTRACTED 1.00]
- **Consolidation and Final Score Pipeline** — app_consol_rows, app_signal_to_vote, app_stat_to_vote, app_stats_result, app_tec_cache, app_consenso_técnico [EXTRACTED 1.00]
- **Excel Export with try/except per Indicator Sheet** — app_excel_export, app_calc_mm, app_calc_macd, app_calc_rsi, app_calc_fibonacci, req_openpyxl [EXTRACTED 1.00]
- **Plotly to PDF Image Rendering** — app_plotly_to_image, app__safe_rl_image, req_kaleido, req_reportlab [EXTRACTED 1.00]
- **report_data Accumulator (all periods)** — app_report_data, app_tec_figs_pdf, app_consol_rows, app_stats_result, app_build_pdf_report [EXTRACTED 1.00]

## Communities (28 total, 22 thin omitted)

### Community 1 - "PDF Generation & Valuation"
Cohesion: 0.16
Nodes (17): _rec_color, _safe_rl_image, build_pdf_report, calc_precio_valorado, calc_stats, Conclusion Buy/Sell Box, consol_rows, df_to_pdf_table (+9 more)

### Community 2 - "Technical Indicators (AST)"
Cohesion: 0.14
Nodes (17): calc_fibonacci, calc_macd, calc_mm, calc_rsi, Consenso Técnico Block, detect_zigzag_pivots, Excel Export (openpyxl), get_fib_signal (+9 more)

### Community 3 - "PDF Report Engine"
Cohesion: 0.20
Nodes (10): build_pdf_report(), df_to_pdf_table(), plotly_to_image(), Convierte una figura Plotly a imagen PNG en memoria usando kaleido.     Adapta, Convierte un DataFrame de pandas a una tabla ReportLab estilizada., Convierte figura Plotly a RLImage; retorna Spacer si kaleido falla., Color ReportLab según recomendación., Construye el PDF completo: resumen ejecutivo + análisis estadístico + investing (+2 more)

### Community 4 - "Chart Visualization Layer"
Cohesion: 0.40
Nodes (5): fig_fibonacci, fig_macd, fig_mm, fig_rsi, tec_figs_pdf

### Community 5 - "Fibonacci ZigZag Analysis"
Cohesion: 0.40
Nodes (5): calc_fibonacci(), detect_zigzag_pivots(), get_fib_signal(), Detecta pivotes (máximos y mínimos significativos) usando el algoritmo ZigZag., Calcula niveles de Fibonacci basados en el último swing significativo detectado

## Knowledge Gaps
- **34 isolated node(s):** `Quant Dashboard Documentation`, `Statistical Analysis Module Description`, `Technical Indicators Module Description`, `PDF Report Export Feature Description`, `Supported Markets and Tickers` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `tec_cache (per-period indicator cache)` connect `Technical Indicators (AST)` to `PDF Generation & Valuation`, `Chart Visualization Layer`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `tec_figs_pdf` connect `Chart Visualization Layer` to `PDF Generation & Valuation`, `Technical Indicators (AST)`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Why does `consol_rows` connect `PDF Generation & Valuation` to `Technical Indicators (AST)`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **What connects `Quant Dashboard Documentation`, `Statistical Analysis Module Description`, `Technical Indicators Module Description` to the rest of the system?**
  _48 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core App Module` be split into smaller, more focused modules?**
  _Cohesion score 0.09090909090909091 - nodes in this community are weakly interconnected._
- **Should `Technical Indicators (AST)` be split into smaller, more focused modules?**
  _Cohesion score 0.13970588235294118 - nodes in this community are weakly interconnected._