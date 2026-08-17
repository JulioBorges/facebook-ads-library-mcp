# PRD: Facebook Ads Intelligence MCP (v3 Hardening, Refatoração e Gestão)

Referência da especificação completa: `docs/spec-v3.md`

## Resumo Executivo
Endurecer e modernizar o servidor MCP para Meta Ads, migrando a arquitetura legada para FastMCP 3.4.7 + Python 3.12, eliminando superfícies de vazamento de credenciais e SSRF, isolando o crawler Crawl4AI 0.9.2 por `ad_id`, e adicionando capacidades de gestão de campanhas com salvaguardas financeiras (`MAX_CAMPAIGN_BUDGET`, dry-run padrão) e upload de criativos via Cloudinary.
