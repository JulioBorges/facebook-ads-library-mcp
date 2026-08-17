# Facebook Ads Intelligence & Campaign Management MCP Server (v3)

Hardened, secure Model Context Protocol (MCP) server built with **FastMCP 3.4.7** and **Python 3.12** for querying the Meta Ads Library, performing competitive intelligence analysis, and managing Facebook ad campaigns with strict financial controls.

---

## Architecture & Security Highlights

1. **Complete Credential Isolation (SEC-001, SEC-002, Q25):**
   - `FACEBOOK_ACCESS_TOKEN` is strictly contained within `MetaAdsClient`. It is never passed via query parameters, command-line arguments, tool return payloads, logs, or error responses.
   - Separate `MCP_AUTH_TOKEN` protects remote HTTP calls via constant-time verification (`secrets.compare_digest`).
   - Cloudinary credentials reside strictly within `CloudinaryClient`.
2. **SSRF & Browser Hardening (SEC-005, SEC-006, Q6, Q8):**
   - Creative crawling exclusively accepts validated numeric `ad_id` parameters (`^\d{1,32}$`). No arbitrary caller URLs are accepted.
   - Crawl4AI 0.9.2 operates in isolated headless mode with concurrency limited to 1 execution (`asyncio.Semaphore(1)`) and 45s timeouts.
3. **Financial Safeguards (Q13, Q17, Q21, Q22, Q39):**
   - All write operations default to `dry_run=True`. Production writes require explicit `dry_run=False`.
   - Daily budgets are capped by `MAX_CAMPAIGN_BUDGET` (default R$10.00) in the account's currency.
   - Budgets are converted server-side into integer subunits (x100).
   - Ad accounts are strictly validated against authorized `/me/adaccounts` (cached for 5 minutes).
4. **Output Sanitization & Limits (SEC-003, SEC-017, Q36):**
   - Global recursive redaction on all tool outputs, error responses, and structured logs.
   - CSV formula injection protection escaping `=`, `+`, `-`, `@`, `\t`, `\r`.
   - Response size ceiling of 1MB (Policy C) with automatic string truncation and `RESPONSE_TOO_LARGE` error protection.
5. **Container Hardening (Q29, §30):**
   - Multi-stage Dockerfile running as non-root user (`UID 10001`).
   - Read-only root filesystem (`read_only: true`), tmpfs mounts, dropped Linux capabilities (`cap_drop: ALL`), and `no-new-privileges: true`.

---

## MCP Tools Reference

### Intelligence & Reading Tools

| Tool | Parameters | Description |
|---|---|---|
| `search_facebook_ads` | `brand_name`, `country="BR"`, `ad_type="ALL"`, `limit=50` | Search ads in Facebook Ads Library with allowlisted `SafeAd` schema. |
| `discover_competitor_brands` | `industry_keywords`, `region="BR"`, `min_ads=5`, `limit=100` | Discover and rank competitor brands using cursor pagination. |
| `analyze_ad_creative_elements` | `ad_id`, `extract_text=True`, `detect_cta=True` | Crawl and analyze ad creative copy, CTAs, and urgency triggers by ad ID. |
| `analyze_ad_performance_metrics` | `brand_name`, `time_period=30` | Aggregate ad metrics and platform distribution filtered via `since`/`until` dates. |
| `competitive_ad_analysis` | `brands_list` | Compare ad volume and platform presence across up to 10 brands. |
| `generate_facebook_intelligence_report` | `brand_name`, `include_competitors=True` | Consolidated intelligence report on brand copy, headlines, and competitor landscape. |
| `export_facebook_ads_data` | `brand_name`, `export_format="json"`, `limit=100` | Export ad records in JSON, formula-safe CSV, or Markdown format. |

### Campaign Management & Asset Tools (Scope C)

| Tool | Parameters | Description |
|---|---|---|
| `list_ad_accounts` | *(none)* | List authorized Meta ad accounts (read-only, cached 5 min). |
| `upload_creative_asset` | `file_path=None`, `image_base64=None`, `mime_type=None`, `filename=None` | Upload image asset to Cloudinary (direct file streaming or Base64 fallback, max 10MB). |
| `create_campaign` | `ad_account_id`, `name`, `objective`, `daily_budget`, `special_ad_categories=None`, `dry_run=True` | Create campaign with budget ceiling and dry-run safety default. |
| `create_ad_set` | `ad_account_id`, `campaign_id`, `name`, `countries`, `age_min=18`, `age_max=65`, `genders=0`, `publisher_platforms=None`, `daily_budget=None`, `dry_run=True` | Create ad set with validated server-side targeting. |
| `create_ad` | `ad_account_id`, `ad_set_id`, `image_url`, `title`, `body`, `link_url`, `call_to_action`, `dry_run=True` | Create ad with image URL, link destination, and CTA allowlist. |

---

## Environment Variables

Copy `.env.example` to `.env` and set your credentials:

```bash
# Meta Graph API
FACEBOOK_ACCESS_TOKEN=EAA...
META_GRAPH_API_VERSION=v26.0

# MCP Authentication & Transport
MCP_AUTH_TOKEN=your_secure_bearer_token_here
MCP_TRANSPORT=stdio # Use 'http' in production

# Operational Limits
MAX_CAMPAIGN_BUDGET=10.00

# Cloudinary Credentials (for asset uploads)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
CLOUDINARY_FOLDER=facebook_ads_creatives # Exclusive target directory in Cloudinary
```

---

## Local Development & Testing

1. **Install dependencies:**
   ```bash
   uv sync --extra dev
   ```

2. **Run test suite:**
   ```bash
   uv run pytest -v
   ```

3. **Run code linter:**
   ```bash
   uv run ruff check .
   ```

4. **Run acceptance test with fake token:**
   ```bash
   uv run python scripts/fake_token_acceptance_test.py
   ```

5. **Start server locally (stdio mode):**
   ```bash
   uv run python -m app.server
   ```

6. **Start server in HTTP mode (uvicorn ASGI):**
   ```bash
   MCP_TRANSPORT=http uv run uvicorn app.server:app --host 0.0.0.0 --port 8000
   ```

---

## Production Deployment with Coolify & Traefik

1. In the Coolify dashboard, create a new service with Docker Compose using the provided `docker-compose.yml`.
2. Configure the required secrets as environment variables:
   - `FACEBOOK_ACCESS_TOKEN`
   - `MCP_AUTH_TOKEN`
   - `CLOUDINARY_CLOUD_NAME`
   - `CLOUDINARY_API_KEY`
   - `CLOUDINARY_API_SECRET`
   - `MAX_CAMPAIGN_BUDGET` (optional, default `10.00`)
3. Deploy the container. The public `/health` endpoint is available for health checks.
