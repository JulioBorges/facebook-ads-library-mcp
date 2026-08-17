# Roadmap

Guia de implementação para a **SPEC v3** ([docs/spec-v3.md](docs/spec-v3.md)): hardening de segurança, deploy seguro em VPS + Docker + Coolify e gestão de campanhas com controle financeiro.

## Estado atual

- [x] Spec consolidada (`docs/spec-v3.md`, decisões Q1–Q42)
- [x] Repo higienizado: `legacy/` + `.dockerignore` + `.python-version` 3.12
- [ ] FASES 1–12 abaixo (implementação)

---

## FASES de implementação

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

Não iniciar produção antes de completar todos os itens P0 (§36 da spec).

---

## Roadmap futuro (evoluções pós-v3)

Priorizado por ordem de valor para o caso de uso (analista de mídia paga + agência).

### v4.0 — Automação operacional
- **Webhooks/notificações** de novas campanhas de concorrentes monitorados
- **Agendamento** de relatórios recorrentes (via n8n / cron + Coolify)
- **Cache** de resultados frequentes (respeitando limites de rate da Meta)

### v4.1 — Análise de criativos com LLM (regex → LLM)
- Substituir o analyzer regex por LLM **somente como evolução isolada**, com prompt anti-injection e conteúdo externo tratado estritamente como dados (ver spec §30 / P2)
- OCR de imagens, detecção de CTA/urgência por semântica

### v5.0 — Multi-conta e multi-agência
- Autenticação OAuth/JWT multi-usuário no MCP (hoje é bearer single-user, §29 da spec)
- Separação de tokens por conta Meta (hoje 1 token, decisão Q13)

### v5.1 — Integrações de plataforma
- TikTok Ads, Google Ads, LinkedIn Ads (mesmo padrão de hardening da spec)
- Exportação para BI (BigQuery/Snowflake) e dashboards

---

## Manutenção contínua

- **Dependências**: `uv lock` revisado em todo release; `pip-audit` no CI
- **CVE**: Trivy + SBOM + alertas (P2, ver spec §38)
- **Rotação de secrets**: documentada, ver spec §38
- **Staging**: ambiente de teste antes de produção (P2)

---

*Last updated: agosto 2026*
