Status: ready-for-agent

## What to build

Implementar as tools analíticas e de exportação de dados (`analyze_ad_performance_metrics`, `competitive_ad_analysis`, `generate_facebook_intelligence_report`, `export_facebook_ads_data`). Remover todos os parâmetros mortos legados (`performance_metrics`, `metrics_comparison`, `analysis_depth`, `report_depth`, `include_creatives`), implementar filtro temporal via `since`/`until` para `time_period`, aplicar política C de limites de resposta (truncamento automático de texto e erro `RESPONSE_TOO_LARGE` se exceder 1MB) e proteger o exportador de CSV contra ataques de formula injection.

## Acceptance criteria

- [x] Tool `analyze_ad_performance_metrics` calcula métricas agregadas por período usando parâmetros `since`/`until`
- [x] Tool `competitive_ad_analysis` realiza comparação de até 10 marcas com deduplicação de entradas
- [x] Tool `generate_facebook_intelligence_report` consolida métricas e concorrência sem parâmetros de profundidade mortos
- [x] Tool `export_facebook_ads_data` exporta dados em formatos JSON, CSV e Markdown
- [x] Células de CSV sanitizadas contra formula injection (escapando prefixos `=`, `+`, `-`, `@`)
- [x] Política de limites de resposta trunca textos excessivos e retorna código de erro `RESPONSE_TOO_LARGE` caso o payload exceda 1MB
- [x] Testes unitários cobrem cálculos de métricas, segurança da exportação CSV/Markdown e limites de tamanho de payload

## Blocked by

- `.scratch/spec-v3/issues/02-search-ads-tracer-bullet.md`

## Comments
