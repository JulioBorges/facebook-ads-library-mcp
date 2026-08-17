Status: ready-for-agent

## What to build

Implementar o módulo isolado e seguro de crawling e análise de criativos de anúncios (`analyze_ad_creative_elements`). Restringir o ponto de entrada estritamente a um `ad_id` numérico validado (`^\d{1,32}$`), construindo o endereço de snapshot internamente no servidor sem aceitar URLs do chamador nem consultar a Graph API neste caminho. Configurar o crawler Crawl4AI 0.9.2 assíncrono com semáforo de concorrência unitária, timeout de 45s, flags `--no-sandbox` e `--disable-dev-shm-usage`, analisador de copy baseado exclusivamente em expressões regulares e tratamento de erro sanitizado `CREATIVE_FETCH_ERROR`.

## Acceptance criteria

- [x] Validação rigorosa de `ad_id` rejeita URLs, caracteres especiais, injeções e caminhos inválidos
- [x] Crawl4AI 0.9.2 opera com `AsyncWebCrawler`, semáforo limitando a 1 execução concorrente e timeout de 45s
- [x] Analisador de criativo opera exclusivamente via regex para detectar CTAs, gatilhos de urgência e padrões de texto
- [x] Falhas no crawler retornam erro padronizado `CREATIVE_FETCH_ERROR` com `correlation_id` sem vazar detalhes internos
- [x] Tool `analyze_ad_creative_elements` exposta no FastMCP e testada contra injeção de prompt, SSRF e tentativas de bypass de URL

## Blocked by

- `.scratch/spec-v3/issues/01-project-skeleton-tooling.md`

## Comments
