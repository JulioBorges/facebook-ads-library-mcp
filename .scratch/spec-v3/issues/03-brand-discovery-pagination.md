Status: ready-for-agent

## What to build

Implementar a busca paginada segura no cliente Meta usando cursor interno (`after`) e a tool `discover_competitor_brands`. Eliminar definitivamente o hack legado de `limit * 3`, aplicando paginação com limites rígidos de páginas e de registros totais (`MAX_SEARCH_RESULTS`), com deduplicação segura de marcas e agregação de contagem de anúncios.

## Acceptance criteria

- [x] Paginação segura implementada no `MetaAdsClient` usando apenas parâmetros de cursor e URL base segura (sem seguir links externos de `paging.next`)
- [x] Teto rígido de paginação respeita `MAX_SEARCH_RESULTS`
- [x] Tool `discover_competitor_brands` aceita `industry_keywords`, `region` (padrão "BR"), `min_ads` e `limit`, agrupando e deduplicando concorrentes
- [x] Testes automatizados verificam o comportamento da paginação por cursor, o respeito aos limites máximos e a correta agregação das marcas

## Blocked by

- `.scratch/spec-v3/issues/02-search-ads-tracer-bullet.md`

## Comments
