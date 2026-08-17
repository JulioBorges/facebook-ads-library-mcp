# SPEC v3 — Facebook Ads Intelligence MCP (Hardening, Refatoração, Deploy Seguro e Gestão de Campanhas)

**Projeto base:** `RamsesAguirre777/facebook-ads-library-mcp` (fork próprio)
**Infraestrutura alvo:** VPS privada + Docker + Coolify + Traefik
**Modo de operação:** leitura da Ads Library **e** gestão de campanhas (write-capable)
**Status:** Specification v3 — consolida a v2 + decisões do grill (Q1–Q42)

> Este documento é a única fonte da verdade. As decisões numeradas (Q1–Q42) registram o histórico do grill e têm precedência sobre qualquer seção anterior da v2.

---

# 1. Objetivo

Refatorar e endurecer o projeto para execução contínua em VPS gerenciada pelo Coolify, com token real da Meta, foco em segurança, isolamento e previsibilidade operacional — e, por decisão do grill (**Q13**), também capaz de **gerenciar campanhas** (criar campaign/ad set/ad) com upload de criativos via Cloudinary.

A aplicação final deverá:

- impedir vazamento do `FACEBOOK_ACCESS_TOKEN`;
- impedir vazamento do `MCP_AUTH_TOKEN`;
- impedir vazamento de credenciais Cloudinary;
- impedir SSRF;
- impedir acesso arbitrário a URLs;
- impedir acesso à rede privada da VPS pelo crawler;
- impedir leitura de arquivos locais;
- impedir execução arbitrária de JavaScript fornecido pelo caller;
- impedir exposição de secrets em respostas, logs e exceptions;
- impedir secrets em argumentos de processo;
- utilizar versões suportadas e pinadas das dependências;
- rodar como usuário não-root;
- utilizar filesystem read-only sempre que possível;
- não possuir acesso ao Docker socket;
- não possuir mounts do host;
- não utilizar modo privileged;
- limitar CPU, memória e quantidade de processos;
- proteger o MCP remoto com autenticação;
- expor o MCP apenas através do proxy HTTPS do Coolify;
- limitar entradas e outputs;
- implementar testes automáticos de regressão de segurança;
- permitir auditoria futura de dependências;
- criar campanhas com **teto financeiro** (`MAX_CAMPAIGN_BUDGET`);
- exigir **dry-run** por padrão nas operações de escrita.

---

# 2. Decisões do grill (resumo)

As decisões numeradas abaixo são vinculantes. Detalhe por seção ao longo do documento.

| # | Decisão | Resumo |
|---|---------|--------|
| Q1 | Crawler validado | Creative analysis por `ad_id`; crawler mantido (não há Caminho B) |
| Q2 | 8 tools mantidas | Todas as tools existentes sobrevivem; `date_range` removido |
| Q3 | Stack | FastMCP **3.4.7** + Python **3.12** (container) |
| Q4 | Transporte | Dual transport stdio/http; `TokenVerifier` custom; Profile B é alvo de produção |
| Q5 | Params mortos | Remover `performance_metrics`, `metrics_comparison`, `analysis_depth`, `report_depth` |
| Q6 | Creative = 100% crawl | Nenhuma Graph API no caminho do creative; erro `CREATIVE_FETCH_ERROR` + `correlation_id` |
| Q7 | Secrets | `read_secret` dual-path; compose env-var-only |
| Q8 | Chromium | `--no-sandbox` + `--disable-dev-shm-usage`, decisão consciente e documentada |
| Q9 | Paginação | Client paginado com teto; eliminar hack `limit * 3` |
| Q10 | Graph API | Default **v26.0**; `time_period` implementado via `since`/`until` |
| Q11 | `ad_type` | Allowlist com 5 valores; default `ALL` |
| Q12 | Export | 3 formatos (json/csv/markdown); `include_creatives` removido |
| Q13 | **Escopo C** | **Write-capable**, mesmo token, Cloudinary + criação de campanhas |
| Q14 | Imagens | **Base64 inline** como único mecanismo de entrada |
| Q15 | Tools de escrita | 4 tools granulares; targeting básico server-side; vídeo adiado |
| Q16/17 | Conta | `ad_account_id` explícito validado contra `/me/adaccounts` (cache 5 min); `MAX_CAMPAIGN_BUDGET` |
| Q18 | Auxiliares | `list_ad_accounts` read-only; contrato do upload; `MAX_IMAGE_BYTES=10MB` |
| Q19 | Cloudinary | SDK oficial pinado; credenciais no redaction; image-only; timeout |
| Q20 | Contratos | Objetivos allowlist; budget convertido server-side; targeting básico; CTA enum |
| Q21 | Moeda | Budget **na moeda da conta**; `MAX_CAMPAIGN_BUDGET` default **R$10,00/dia** |
| Q22 | Dry-run | `dry_run=True` default nas tools de escrita |
| Q23 | Camadas | Services compartilhados; orquestração em nível de service; tools finas |
| Q24 | Documento | Consolidar em `docs/spec-v3.md` |
| Q25 | Client | **`MetaAdsClient` único** read+write; retry só em GET |
| Q26 | CI | Pipeline §120 + **Gitleaks**; Trivy P2; CI em push/PR na main |
| Q27 | Coolify | Compose no painel; `context` → clone do repo; versão com default; `CLOUDINARY_*` env |
| Q28 | Startup | stdio exige token+versão; `MCP_AUTH_TOKEN` opcional no stdio; http exige os 3 + Cloudinary |
| Q29 | Dockerfile | **Multi-stage desde o início** |
| Q30 | Analyzer | **Regex-only**; LLM de análise é evolução futura |
| Q31 | Testes | `responses` (dev-dep) + `CloudinaryClient` com interface mockável |
| Q32 | Defaults | `country`/`region` default **BR**; nome "Facebook Ads Intelligence MCP" |
| Q33 | Health | `/health` público com `{"status":"ok"}`; healthcheck socket no compose |
| Q34 | Runtime | **ASGI + uvicorn** para http; stdio via `MCP_TRANSPORT` |
| Q35 | Config | `python-dotenv` dev-only; config manual (sem pydantic-settings) |
| Q36 | Limits | Política C: trunca texto sempre; erro `RESPONSE_TOO_LARGE` se ainda estourar |
| Q37 | Campos Meta | `reach` fora do `fields` (not_available); `demographic_distribution`/`delivery_by_region` opcionais |
| Q38 | Legacy | `facebook_ads_mcp_complete.py` → `legacy/` + `.dockerignore`; `.python-version` 3.12 |
| Q39 | Budget | Conversão `x100` (inteiro); teto no decimal; mínimo `> 0` (Meta rejeita) |
| Q40 | Snapshot | `ad_snapshot_url` **removido dos `fields`**; `special_ad_categories` opcional |
| Q41 | CTA | 11 valores allowlist; `link_url` https-only sem fetch |
| Q42 | Estrutura | Árvore de arquivos revisada (ver §16) |

---

# 3. Principios de segurança

Mantidos da v2, com nota do escopo C.

## 3.1. Nunca confiar no caller MCP

Todo input de LLM/agente/cliente MCP/usuário é não confiável. O caller nunca controla:

```text
URL, hostname, IP, port, HTTP headers, Authorization header,
proxy, filesystem path, shell command, browser argument,
JavaScript, redirect target, webhook URL, output file path
```

**Exceção deliberada (Q13/Q41):** `link_url` da `create_ad` é texto do caller, validado `https://`-only e **nunca** fetado pelo servidor (não é superfície SSRF).

## 3.2. Nunca confiar em conteúdo externo

Conteúdo de Meta/HTML/creative/response HTTP é `UNTRUSTED_EXTERNAL_CONTENT`: pode ser analisado, nunca controla execução. (**Q30:** análise por regex, sem LLM interpretando conteúdo externo neste corte.)

## 3.3. Secrets ficam na camada de infraestrutura/client

```text
Coolify Secret → MetaAdsClient → Meta Graph API
```

O `FACEBOOK_ACCESS_TOKEN` vive **apenas** dentro do `MetaAdsClient` (**Q25** — client único). Não atravessa service → tool → LLM. O `MCP_AUTH_TOKEN` vive apenas na camada de autenticação HTTP. As credenciais Cloudinary vivem apenas no `CloudinaryClient`.

## 3.4. Allowlist em vez de blocklist

DTOs com allowlist; validação por enums; nunca "remover campos perigosos".

## 3.5. Eliminar superfícies perigosas em vez de validá-las

Nenhuma tool aceita URL de destino para crawling. Análise de criativos recebe somente `ad_id`.

---

# 4. Problema crítico atual — vazamento do token

`params["access_token"] = self.access_token` e reuso do objeto em respostas: **eliminado por completo** (SEC-001). O token vai no header `Authorization: Bearer` interno ao client (§7).

---

# 5. Autenticação Meta isolada — `MetaAdsClient` único (Q25)

`app/meta/client.py`:

```python
class MetaAdsClient:
    def __init__(self, access_token: str, graph_api_version: str):
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        self.base_url = f"https://graph.facebook.com/{graph_api_version}/ads_archive"
```

Regras do client:

- Token nunca entra em `params`/payload.
- **Retry somente em GET** (§28); **POST sem retry** (não-idempotente, evita campanha duplicada) (**Q25**).
- `allow_redirects=False` (SEC-007).
- Timeouts obrigatórios (connect 5s / read 30s).
- `trust_env = False` (SEC-023 → na verdade §25 da v2).
- Métodos de leitura e escrita no mesmo client (**Q25**).

---

# 6. Nunca retornar token em `search_params`

Tools que reportam parâmetros usados constroem versão segura:

```python
safe_search_params = {"search_terms": ..., "country": ..., "limit": ...}
```

Nunca retornam `params` do client.

---

# 7. SEC-002 — Remover token de argumentos do processo

Removidos: `--facebook-token`, `sys.argv`, argparse para secrets. Secrets nunca aparecem em `ps`/`/proc/<pid>/cmdline`/logs/startup/histórico.

---

# 8. Configuração do token (Q7)

`read_secret(file_path, env_name)` dual-path (arquivo de secret, depois env var) conforme v2 §8. **O compose do Coolify usa env-var-only** — o caminho de arquivo existe para flexibilidade futura, não é usado no deploy (§27).

---

# 9. SEC-003 — Nenhum payload bruto da Meta vira output MCP

Fluxo obrigatório: Meta response → raw parser → safe mapper → Pydantic DTO → output sanitizer → MCP response.

---

# 10. Modelos seguros de saída — `SafeAd` revisado (Q2/Q37)

`app/meta/schemas.py`. Permitido na allowlist:

```text
id, page_id, page_name, ad_creation_time,
ad_creative_bodies, ad_creative_link_captions,
ad_creative_link_descriptions, ad_creative_link_titles,
publisher_platforms, currency, impressions, spend,
public_ad_url,
demographic_distribution (opcional, Q37),
delivery_by_region (opcional, Q37),
reach (opcional, tratado como not_available, Q37)
```

**Removido dos `fields` da requisição:** `ad_snapshot_url` (**Q40**) e `reach` (**Q37**). Campos ausentes da Meta → `None`/`[]`.

---

# 11. SEC-004 — `ad_snapshot_url` nunca existe no fluxo (Q40)

Não é solicitado à Meta e nunca aparece em output/log/erro/export. Garantia por **ausência de design**.

---

# 12. URL pública de anúncio

Construída apenas do `ad_id`:

```python
def build_public_ad_url(ad_id: str) -> str:
    return f"https://www.facebook.com/ads/library/?id={ad_id}"
```

---

# 13. SEC-005 — Creative analysis aceita somente `ad_id` (Q6)

```python
@mcp.tool
async def analyze_ad_creative_elements(
    ad_id: str,
    extract_text: bool = True,
    detect_cta: bool = True,
) -> dict: ...
```

**Nenhuma Graph API neste caminho.** `ad_id` → `MetaSnapshotService` → URL interna → crawler → extração → truncamento → análise regex → DTO seguro. Falha de crawl → erro sanitizado `CREATIVE_FETCH_ERROR` + `correlation_id` (**Q6**).

---

# 14. Validação de `ad_id`

```python
AD_ID_PATTERN = re.compile(r"^\d{1,32}$")
```

Rejeita URL/querystring/hostname/slashes/colon/espaços/HTML/JS.

---

# 15. Arquitetura segura da análise de criativos

Mantida da v2 (§15) com as decisões: crawler validado (**Q1**), analyzer regex-only (**Q30**), timeout 45s, semaphore (§45), conteúdo só como texto (§38).

---

# 16. Estrutura de arquivos (Q42 — revisa §55 da v2)

```text
facebook-ads-library-mcp/
├── app/
│   ├── __init__.py
│   ├── server.py                  # FastMCP + dual transport (stdio/http) + /health
│   ├── config.py                  # Settings manual + read_secret (Q35)
│   ├── exceptions.py
│   │
│   ├── meta/
│   │   ├── __init__.py
│   │   ├── client.py              # MetaAdsClient (read + write, retry só GET)
│   │   ├── schemas.py             # SafeAd + DTOs de escrita
│   │   ├── mapper.py              # raw Meta → SafeAd (allowlist, sem snapshot_url/reach)
│   │   ├── ad_account_service.py  # /me/adaccounts + cache 5min + validação (Q17)
│   │   ├── service.py             # AdsService (search, performance, discover)
│   │   └── campaign_service.py    # create_campaign/ad_set/ad (dry-run, budget)
│   │
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── browser_config.py      # server-side, --no-sandbox/--disable-dev-shm-usage (Q8)
│   │   └── creative_analyzer.py   # regex-only (CTA, urgencia, sentimento) (Q30)
│   │
│   ├── cloudinary/
│   │   ├── __init__.py
│   │   └── client.py              # CloudinaryClient fino (upload image, timeout) (Q19/Q31)
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── redaction.py           # sanitize_for_output, sanitize_url, safe_log_value
│   │   ├── validation.py          # AD_ID_PATTERN, AD_TYPE_ALLOWED, CTA_ALLOWED, etc.
│   │   ├── url_policy.py          # https-only + host allowlist
│   │   └── response_limits.py     # enforce_response_limits (política C, Q36)
│   │
│   └── tools/
│       ├── __init__.py
│       ├── search.py
│       ├── creative.py
│       ├── competitive.py
│       ├── reporting.py
│       ├── export.py
│       └── management.py          # list_ad_accounts, upload_creative_asset,
│                                  # create_campaign, create_ad_set, create_ad
│
├── legacy/                        # facebook_ads_mcp_complete.py (descontinuado, Q38)
├── tests/
│   ├── conftest.py
│   ├── test_secret_leak.py
│   ├── test_redaction.py
│   ├── test_meta_client.py
│   ├── test_url_policy.py
│   ├── test_tool_inputs.py
│   ├── test_snapshot_security.py
│   ├── test_prompt_injection.py
│   ├── test_exports.py
│   ├── test_response_limits.py
│   ├── test_ad_accounts.py
│   ├── test_management_tools.py
│   ├── test_cloudinary.py
│   └── test_budget_conversion.py
│
├── Dockerfile                     # multi-stage (Q29)
├── docker-compose.yml             # compose para Coolify (Q27)
├── pyproject.toml                 # deps pinadas + dev group
├── uv.lock
├── .python-version                # 3.12 (Q38)
├── .dockerignore                  # inclui legacy/ (Q38)
├── .gitignore
├── .env.example
└── README.md
```

---

# 17. Tools finais (Q2/Q5/Q15/Q18/Q32/Q41)

## 17.1. Leitura (herdadas da v2, com params podados)

| Tool | Assinatura |
|---|---|
| `search_facebook_ads` | `(brand_name, country="BR", ad_type="ALL", limit=50)` — **sem `date_range`** (Q2) |
| `discover_competitor_brands` | `(industry_keywords, region="BR", min_ads=5, limit=100)` |
| `analyze_ad_creative_elements` | `(ad_id, extract_text=True, detect_cta=True)` — **URLs eliminadas** (Q6) |
| `analyze_ad_performance_metrics` | `(brand_name, time_period=30)` — `time_period` **implementado via since/until** (Q10); **sem `performance_metrics`** (Q5) |
| `competitive_ad_analysis` | `(brands_list)` — max 10, dedupe; **sem `metrics_comparison`/`analysis_depth`** (Q5) |
| `generate_facebook_intelligence_report` | `(brand_name, include_competitors=True)` — **sem `report_depth`** (Q5) |
| `export_facebook_ads_data` | `(brand_name, export_format="json", limit=100)` — **sem `include_creatives`** (Q12) |

Validações: `brand_name` 1..200 chars (§48); `country`/`region` `^[A-Z]{2}$` (§49); `limit` 1..100 (§50); `ad_type` allowlist (§11/Q11); `time_period` >= 1.

## 17.2. Escrita (escopo C, Q13/Q15/Q22)

| Tool | Assinatura |
|---|---|
| `list_ad_accounts` | `()` — read-only, retorna `[{ad_account_id, name, currency, account_status}]` |
| `upload_creative_asset` | `(image_base64, mime_type, filename)` — retorna `{asset_id, public_url, mime_type, width, height, bytes}` |
| `create_campaign` | `(ad_account_id, name, objective, daily_budget, special_ad_categories=None, dry_run=True)` |
| `create_ad_set` | `(ad_account_id, campaign_id, name, countries, age_min=18, age_max=65, genders=0, publisher_platforms=None, daily_budget, dry_run=True)` |
| `create_ad` | `(ad_account_id, ad_set_id, image_url, title, body, link_url, call_to_action, dry_run=True)` |

Regras transversais:

- **`dry_run=True` default** — produção exige `dry_run=False` explícito (Q22).
- `ad_account_id` validado contra `/me/adaccounts` cacheado (Q17).
- Budget **decimal na moeda da conta**, convertido `x100` para menor unidade inteira; teto `MAX_CAMPAIGN_BUDGET` aplicado **no decimal** (Q21/Q39).
- Objetivos allowlist: `OUTCOME_TRAFFIC | OUTCOME_ENGAGEMENT | OUTCOME_LEADS | OUTCOME_SALES | OUTCOME_APP_PROMOTION` (Q20).
- `special_ad_categories` opcional: `EMPLOYMENT | HOUSING | CREDIT | FINANCIAL_PRODUCTS_AND_SERVICES_ADS` (Q40).
- CTA allowlist (11): `SHOP_NOW, LEARN_MORE, SIGN_UP, DOWNLOAD, CONTACT_US, GET_OFFER, GET_QUOTE, SUBSCRIBE, INSTALL_APP, BOOK_TRAVEL` (Q41).
- `link_url` `https://`-only, sem credenciais, sem fetch server-side (Q41).
- Targeting básico server-side: `countries`, `age_min`/`age_max` (18–65), `genders` (0=all, 1=male, 2=female), `publisher_platforms` (facebook, instagram, audience_network, messenger). Sem interests/behaviors (Q15/Q20).
- Imagem: base64 inline, mime `image/png|jpeg|webp|gif`, `MAX_IMAGE_BYTES=10MB` decodificado (Q14/Q18).

---

# 18. URL policy (SEC-006)

- Protocolos: somente `https` (bloqueia http/file/ftp/data/javascript/ws/wss/chrome/about/blob).
- Hosts: `facebook.com`, `www.facebook.com` — nunca substring.
- Defesa em profundidade; nenhuma URL dinâmica hoje (Q6).
- `link_url` de `create_ad`: validado https-only, **não** entra no URL policy de crawl (destino de campanha, não fetch).

---

# 19. SEC-007 — Redirects controlados

`allow_redirects=False` nas chamadas à Graph API. Redirect inesperado = erro. Nunca seguir redirect com headers de auth.

---

# 20. Paginação segura (Q9)

- `MetaAdsClient` tem paginação interna opcional (cursor `after` + base URL conhecida), com **teto** de páginas e `MAX_SEARCH_RESULTS`.
- `discover_competitor_brands` usa paginação para coletar além do limite por request — **hack `limit*3` eliminado**.
- `search`/`export` em 1 página.
- Nunca navegar para `paging.next` retornado pela Meta.

---

# 21. Cliente HTTP seguro / SSL / Timeouts / Retry

- `requests.Session()` com `trust_env=False`.
- Nunca `verify=False`.
- Timeouts `(5, 30)` sempre.
- Retry idempotente (429/500/502/503/504), máx 3, backoff 1s/2s/4s + jitter, **somente GET** (Q25).
- Nunca retry infinito.

---

# 22. SEC-008 — Exceptions sanitizadas

Erros externos:

```json
{
  "success": false,
  "error": {
    "code": "META_API_ERROR",
    "message": "Meta API request failed",
    "correlation_id": "..."
  }
}
```

Novos códigos: `CREATIVE_FETCH_ERROR` (Q6), `RESPONSE_TOO_LARGE` (Q36), `CLOUDINARY_NOT_CONFIGURED` (Q28), `INVALID_INPUT`, `AD_ACCOUNT_NOT_FOUND`, `BUDGET_EXCEEDED`.

---

# 23. Correlation ID

`uuid.uuid4().hex[:16]` por execução de tool; presente em resposta e logs; nunca vaza dado sensível.

---

# 24. Redaction global (SEC-009) + Cloudinary (Q19)

- `SENSITIVE_KEYS` inclui: `access_token`, `authorization`, `token`, `api_key`, `apikey`, `client_secret`, `secret`, `password`, `cookie`, `set-cookie`, `cloudinary_api_key`, `cloudinary_api_secret`, `cloud_name`, `mcp_auth_token`.
- `sanitize_url` remove query params sensíveis.
- `safe_log_value` aplica redaction em logs.
- **URL pública Cloudinary (`res.cloudinary.com/...`) NÃO é redactada** — é o propósito do upload; credenciais nunca saem.

---

# 25. Limites (SEC-015/016, Q36)

```text
MAX_BRAND_NAME_CHARS=200
MAX_SEARCH_RESULTS=100
MAX_EXPORT_RECORDS=250
MAX_BRANDS_COMPARISON=10
MAX_CREATIVE_TEXT_CHARS=20000
MAX_TOOL_RESPONSE_BYTES=1000000
MAX_IMAGE_BYTES=10485760        # 10MB decodificado
MAX_CAMPAIGN_BUDGET=10.00       # moeda da conta (BRL default) — teto no decimal
```

**Política C (Q36):** trunca textos automaticamente (`truncated=true`); se ainda estourar 1MB, **erro `RESPONSE_TOO_LARGE`** sugerindo `limit` menor. JSON sempre válido.

---

# 26. Export CSV seguro (SEC-017)

`csv.writer` + `sanitize_csv_cell` (escaping `= + - @`) para formula injection. Markdown via join estruturado (sem f-string crua) (Q12).

---

# 27. Prompt injection (SEC-011) — conteúdo externo só como dados

Crawler nunca executa comandos/tools/secrets/JS de conteúdo; extração e interpretação separadas; regex-only (Q30).

---

# 28. Crawler hardening

- Crawl4AI **0.9.2** pinado (SEC-012/§40); API `AsyncWebCrawler` moderna (§41).
- Browser config 100% server-side (SEC-013).
- Contexto efêmero, `/tmp` tmpfs (SEC-044 → §44).
- `--no-sandbox` + `--disable-dev-shm-usage` — **decisão consciente** (Q8): isolamento do Chromium delegado às proteções de container (§30). Documentado no README.
- `crawler_semaphore` (CRAWLER_CONCURRENCY=1), timeout 45s.

---

# 29. SEC-020 — Token MCP separado

`MCP_AUTH_TOKEN` (gerado com `openssl rand -hex 32`), distinto do token Meta. Bearer via `TokenVerifier` custom do FastMCP 3.4.7 comparando com `secrets.compare_digest` (Q4). Para single-user privado, bearer é suficiente; OAuth/JWT é P2.

---

# 30. Docker hardening (P0/P1)

- Non-root `UID 10001` (§81).
- `privileged: false`; sem Docker socket; sem host mounts; sem host network.
- `cap_drop: ALL`; `no-new-privileges: true`; `read_only: true`; `/tmp` tmpfs 512m; `shm_size: 1gb`; `mem_limit: 2g`; `cpus: 2.0`; `pids_limit: 256`.
- **Multi-stage** (Q29): stage deps (`ghcr.io/astral-sh/uv`) + stage final `python:3.12-slim` + deps Chromium; `uv sync --frozen --no-dev --no-install-project`; `.venv` copiado. `uv`/`pip` fora da imagem final.
- `expose: 8000` (sem `ports`) atrás do Traefik (§78).
- `META_GRAPH_API_VERSION: ${META_GRAPH_API_VERSION:-v26.0}` (Q27); secrets `:?`; `CLOUDINARY_*` no environment (Q27).
- Healthcheck socket `127.0.0.1:8000` (Q33).

---

# 31. Runtime / Entrypoint (Q34)

- `app/server.py` expõe `app = mcp.http_app(path="/mcp")` para uvicorn e `mcp.run()` para stdio.
- Produção: `uvicorn app.server:app --host 0.0.0.0 --port 8000`.
- `MCP_TRANSPORT=stdio|http`; stdio default para dev.
- `/health` via `@mcp.custom_route("/health", methods=["GET"])` → `{"status":"ok"}`, **público**, zero informação interna (Q33).
- Startup: **http** exige `FACEBOOK_ACCESS_TOKEN` + `META_GRAPH_API_VERSION` + `MCP_AUTH_TOKEN` + `CLOUDINARY_*` (Q28); **stdio** exige token+versão, `MCP_AUTH_TOKEN`/Cloudinary opcionais (tools de escrita erram lazy com `CLOUDINARY_NOT_CONFIGURED`).

---

# 32. CI (Q26)

GitHub Actions em push/PR na `main`:

```bash
uv sync --frozen
ruff check .
pytest
pip-audit
docker build .
```

**+ Gitleaks** (secret scanning; build/CI falha em padrões de token/key/bearer em commits novos). **Trivy, Dependabot, Bandit, SBOM, alertas CVE = P2.**

---

# 33. Coolify (Q27)

- Aplicação `facebook-ads-library-mcp-secure`; **Docker Compose colado no painel**; `build.context` → clone do repo na VPS.
- Secrets runtime-only: `FACEBOOK_ACCESS_TOKEN`, `MCP_AUTH_TOKEN`, `META_GRAPH_API_VERSION` (default v26.0 no compose), `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `MAX_CAMPAIGN_BUDGET`.
- Isolamento por container; rede própria (não compartilhar com bancos/Redis); domain próprio `mcp-facebook.<dominio>.com`; HTTPS forçado no Traefik.
- Healthcheck socket; `/health` opcional para Uptime Kuma.

---

# 34. Dependências finais (Q35)

`pyproject.toml` com pins exatos:

```text
runtime: fastmcp==3.4.7, mcp (transitivo), requests==2.34.2, pydantic, crawl4ai==0.9.2,
         cloudinary, uvicorn
dev: pytest, ruff, pip-audit, responses
dev-only runtime: python-dotenv (apenas stdio/dev)
```

Removidos: `mcp` direto, `httpx` direto, `beautifulsoup4` direto, `selenium`, `pandas`, `numpy`, `pydantic-settings`, `asyncio` (stdlib), `aiohttp`, `regex`, `typing-extensions` direto, `black`, `flake8`. Config **manual** (sem pydantic-settings) (Q35).

---

# 35. Escopo write-capable — decisão arquitetural (Q13)

O MCP deixa de ser read-only. **Mesmo token** para leitura + gestão (Q13). Riscos financeiros mitigados por `MAX_CAMPAIGN_BUDGET` (Q21/Q39), dry-run (Q22), validação de conta (Q17). **NÃO haverá** separação `facebook-ads-library-mcp` vs `facebook-ads-management-mcp` — escopo C revoga §128-129 da v2. Tokens para outros fins (banco/Coolify/n8n) continuam proibidos de reuso (mantém §132).

---

# 36. P0 — Bloqueadores de produção

P0 herdado da v2 (§145) **+ escopo C**:

- [ ] Tudo do §145 v2 (token fora de params/argv/output/log/exception; `MetaAdsClient`; DTOs; URL policy; redirects; exceptions; redaction; `safe_tool_response`; pins; lock; auth MCP; container non-root; sem socket/mounts; secrets runtime-only; testes de leak/SSRF)
- [ ] Tools de escrita com dry-run default (§17.2)
- [ ] `ad_account_id` validado contra `/me/adaccounts`
- [ ] `MAX_CAMPAIGN_BUDGET` aplicado no decimal
- [ ] Conversão de budget `x100` (testes `test_budget_conversion.py`)
- [ ] Upload base64 → Cloudinary com mime/tamanho validados
- [ ] Gitleaks no CI
- [ ] `/health` público
- [ ] ASGI + uvicorn em produção

---

# 37. P1 — Produção estável

Herdado da v2 (§146) + escopo C:

- [ ] Filesystem read-only; tmpfs; no-new-privileges; cap_drop ALL; CPU/mem/PID limits
- [ ] Concurrency/timeout do crawler; HTTP timeout/retry; paginação segura
- [ ] Structured logging + correlation IDs
- [ ] Response size limit (política C); creative text limit; CSV injection
- [ ] pytest / ruff / pip-audit / Gitleaks
- [ ] Testes: ad accounts, management tools, cloudinary, budget conversion

---

# 38. P2 — Hardening avançado

Herdado da v2 (§147): seccomp Chromium, egress firewall, OAuth/JWT multi-user, Trivy, SBOM, alertas CVE, staging, dependabot, secret rotation documentada. **+ análise de criativos com LLM** (Q30) como feature futura isolada com prompt anti-injection.

---

# 39. Teste de aceite (fake token)

Procedimento da v2 (§148-150) mantido: `TEST_FAKE_TOKEN_DO_NOT_USE_123456`, grep no workspace e logs = 0 ocorrências; teste de erro forçado sem `access_token`/`Bearer`/URL completa.

---

# 40. Smoke test com token real

V2 §151 + escopo C:

1. Cadastrar token real no Coolify; redeploy.
2. `list_ad_accounts` → confirmar contas BRL.
3. `create_campaign` com `dry_run=True` → payload sanitizada, sem gasto.
4. `upload_creative_asset` base64 → URL Cloudinary pública.
5. `create_campaign`/`create_ad_set`/`create_ad` com `dry_run=False` e budget baixo → confirmação.
6. Conferir logs (sem token/credenciais).
7. Autenticação inválida do MCP → 401/403.
8. SSRF em `ad_id` → rejeição.
9. Estabilidade do Chromium.

---

# 41. Definition of Done

DoD da v2 (§153) + escopo C:

```text
✓ nenhum input MCP controla URL externa (exceto link_url https-only de create_ad)
✓ creative analysis recebe somente ad_id
✓ URLs de crawling construídas internamente
✓ token Meta existe somente no MetaAdsClient
✓ token nunca entra em params/output/log/exception/argv
✓ snapshot URL não existe no fluxo (ausência por design)
✓ Meta responses passam por allowlist
✓ responses passam por redaction + limite de tamanho
✓ crawler com timeout + concurrency limit
✓ browser e container rodam non-root
✓ rootfs read-only; sem privileged; sem Docker socket; sem host mounts
✓ MCP remoto exige autenticação (MCP_AUTH_TOKEN ≠ Meta token)
✓ dependências pinadas; lockfile versionado; FastMCP 3.4.7; Crawl4AI 0.9.2
✓ CI executa security tests + Gitleaks
✓ SSRF + secret leak + container security tests passam
✓ write tools com dry-run default
✓ budget com teto validado no decimal + conversão x100
✓ ad_account_id validado contra /me/adaccounts
✓ Cloudinary credentials nunca saem (URL pública sim)
✓ ASGI + uvicorn + /health em produção
```

---

# 42. Resultado esperado

O token deixa de fazer parte de estruturas usadas pelas tools e a maior ameaça do código original (URL arbitrária no crawler) deixa de existir por arquitetura. O escopo C adiciona capacidade de gestão com controle financeiro (`MAX_CAMPAIGN_BUDGET`, dry-run) e isolamento de credenciais (`CloudinaryClient`, token Meta restrito ao client).

---

# 43. Recomendação de implementação (FASES)

```text
FASE 1   Secrets + MetaAdsClient (read + write)
FASE 2   Safe schemas + outputs (SafeAd revisado)
FASE 3   ad_id-only creative analysis
FASE 4   Crawler hardening (Crawl4AI 0.9.2 async)
FASE 5   Global redaction
FASE 6   Input/output limits (política C)
FASE 7   Dependency upgrade + lock (pyproject + uv)
FASE 8   Security tests (+ ad accounts, management, cloudinary, budget)
FASE 9   Docker hardening (multi-stage) + compose
FASE 10  Coolify deployment
FASE 11  Fake-token acceptance test
FASE 12  Real-token smoke test (incluindo dry-run e escrita real de baixo budget)
```

Não iniciar produção antes de completar todos os itens P0 (§36).

---

# 44. Riscos residuais

Comprometimento da VPS/Coolify/conta Meta; zero-day Chromium/dependência; supply chain. Novo no escopo C: exposição financeira de campanhas — mitigada por teto de budget, dry-run e validação de conta, mas não eliminada.
