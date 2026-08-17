Status: ready-for-agent

## What to build

Configurar a base do projeto moderna, dependências pinadas e pipeline de CI com escaneamento de segurança. Mover o script monolítico legado para a pasta de histórico e estabelecer a estrutura inicial modular com servidor FastMCP suportando transportes stdio e http, endpoint `/health` público e carregamento seguro de secrets.

## Acceptance criteria

- [x] `pyproject.toml` criado com versões pinadas das dependências de runtime (`fastmcp==3.4.7`, `crawl4ai==0.9.2`, `requests==2.34.2`, `pydantic`, `cloudinary`, `uvicorn`) e dev (`pytest`, `ruff`, `pip-audit`, `responses`, `python-dotenv`)
- [x] Script original `facebook_ads_mcp_complete.py` movido para `legacy/` e adicionado ao `.dockerignore`
- [x] `.python-version` fixado em 3.12
- [x] Módulo de configuração carrega secrets via leitura de arquivo ou variável de ambiente (`read_secret`), sem expor secrets em logs
- [x] Servidor FastMCP inicializa com endpoint público `/health` retornando `{"status":"ok"}` e suporte a seleção de transporte stdio/http
- [x] Pipeline de CI configurado executando `ruff`, `pytest`, `pip-audit` e `gitleaks`

## Blocked by

None - can start immediately

## Comments
