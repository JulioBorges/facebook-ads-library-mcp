Status: ready-for-agent

## What to build

Implementar o primeiro tracer bullet vertical completo de leitura: tool `search_facebook_ads`. Conectar a camada de transporte ao cliente Meta unificado com autenticação via cabeçalho Bearer interno (sem passar token em parâmetros de query ou expor em `search_params`), DTOs seguros com allowlist explícita (sem `ad_snapshot_url` nem `reach`), redaction global em saídas e logs, tratamento sanitizado de exceções (`META_API_ERROR` com correlation ID) e validações estritas de entrada.

## Acceptance criteria

- [x] `MetaAdsClient` envia token Meta exclusivamente via header `Authorization: Bearer`, com `trust_env=False`, `allow_redirects=False`, timeouts explícitos (5s connect, 30s read) e retry apenas para métodos GET
- [x] DTO `SafeAd` aceita apenas campos na allowlist e constrói `public_ad_url` exclusivamente a partir do `ad_id`
- [x] Tool `search_facebook_ads` exposta com validação de parâmetros (`brand_name` 1..200 chars, `country` padrão "BR", `ad_type` em allowlist, `limit` 1..100) sem o parâmetro `date_range`
- [x] Retorno da tool nunca ecoa o token ou parâmetros brutos de requisição
- [x] Redaction global higieniza saídas e URLs de qualquer secret listado
- [x] Erros da API Meta são interceptados e retornados no formato de erro sanitizado com `correlation_id`
- [x] Testes automatizados cobrem ausência de vazamento de token, sanitização de saídas e validação de inputs inválidos

## Blocked by

- `.scratch/spec-v3/issues/01-project-skeleton-tooling.md`

## Comments
