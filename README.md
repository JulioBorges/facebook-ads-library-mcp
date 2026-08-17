# Facebook Ads Intelligence MCP

MCP server para inteligência de anúncios da Meta (Facebook Ads Library) com hardening de segurança, deploy via Docker/Coolify e gestão de campanhas com controle financeiro.

> **Stack:** FastMCP 3.4.7 · Python 3.12 · Crawl4AI 0.9.2 · Graph API v26.0
> **Spec:** [docs/spec-v3.md](docs/spec-v3.md) (fonte da verdade — consolida todas as decisões de arquitetura e segurança)

## Ferramentas

### Leitura (Ads Library)

- `search_facebook_ads` — busca de anúncios por marca, país e tipo
- `discover_competitor_brands` — descoberta de concorrentes por indústria
- `analyze_ad_creative_elements` — análise de criativo por `ad_id` (crawl, regex-only)
- `analyze_ad_performance_metrics` — métricas de desempenho (time_period implementado)
- `competitive_ad_analysis` — comparação multi-marca
- `generate_facebook_intelligence_report` — relatório executivo
- `export_facebook_ads_data` — exportação JSON / CSV / Markdown

### Gestão (escopo C — write-capable)

- `list_ad_accounts` — contas acessíveis pelo token (read-only)
- `upload_creative_asset` — upload de imagem base64 → Cloudinary
- `create_campaign` — criação de campaign com teto de budget
- `create_ad_set` — criação de ad set (targeting básico)
- `create_ad` — criação de anúncio (CTA allowlist)

Todas as tools de escrita exigem **`dry_run=True` por padrão** — produção exige `dry_run=False` explícito. Budget em moeda da conta com `MAX_CAMPAIGN_BUDGET` (default R$10,00/dia) validado antes da conversão.

## Quick Start

### 1. Instalação

```bash
git clone git@github.com-julio:JulioBorges/facebook-ads-library-mcp.git
cd facebook-ads-library-mcp
uv sync --frozen
```

### 2. Ambiente

```bash
cp .env.example .env
# FACEBOOK_ACCESS_TOKEN=<token com ads_read>
# META_GRAPH_API_VERSION=v26.0
# MCP_AUTH_TOKEN=<gerado com: openssl rand -hex 32>  # opcional no stdio
# CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET  # para gestão
```

**Nunca** passe o token por argumento de processo (`--facebook-token` não existe mais). O token vive apenas dentro do `MetaAdsClient`.

### 3. Execução

```bash
# Dev (stdio)
MCP_TRANSPORT=stdio python -m app.server

# Produção (http + ASGI)
MCP_TRANSPORT=http uvicorn app.server:app --host 0.0.0.0 --port 8000
```

No modo http, o servidor exige `FACEBOOK_ACCESS_TOKEN`, `META_GRAPH_API_VERSION`, `MCP_AUTH_TOKEN` e credenciais Cloudinary no boot (fail-fast).

### 4. Deploy (Coolify + Docker)

1. Adicione a aplicação no Coolify com o `docker-compose.yml` deste repo (`build.context` → clone do repo na VPS)
2. Configure os secrets runtime-only no painel (nunca em `.env` commitado)
3. O serviço fica atrás do Traefik com HTTPS forçado; o endpoint MCP é `/mcp` e o healthcheck `/health` é público

## Segurança

- **Token Meta** restrito ao `MetaAdsClient` (header Bearer, `trust_env=False`); nunca em `params`, output, logs, exceptions ou argv
- **Redaction global** de secrets (`access_token`, Cloudinary, etc.) em respostas e logs
- **URL policy** https-only; análise de criativos recebe **somente `ad_id`** (URL interna construída pelo servidor) — sem SSRF
- **DTOs com allowlist**; `ad_snapshot_url` ausente por design
- **Container hardening**: multi-stage, non-root (UID 10001), read-only rootfs, `cap_drop: ALL`, sem Docker socket, sem host mounts, sem privileged, limites de CPU/mem/PID, tmpfs + shm configurados
- **Retry idempotente** apenas em GET; `allow_redirects=False`; timeouts obrigatórios
- **CI** com `ruff`, `pytest`, `pip-audit`, `docker build` e **Gitleaks**
- Resposta do MCP limitada a 1MB (política C: trunca textos; erro `RESPONSE_TOO_LARGE` se ainda estourar)

Detalhes completos, decisões numeradas (Q1–Q42) e testes em [docs/spec-v3.md](docs/spec-v3.md).

## Desenvolvimento

```bash
uv sync --frozen          # instala runtime + dev
uv run pytest             # testes (inclui secret leak, SSRF, redaction, budget)
uv run ruff check .       # lint
uv run pip-audit          # auditoria de dependências
```

### Repositório

O arquivo original vulnerável foi movido para `legacy/` — descontinuado, mantido apenas para referência e **excluído** do build via `.dockerignore`.

## Licença

MIT — veja [LICENSE](LICENSE).
