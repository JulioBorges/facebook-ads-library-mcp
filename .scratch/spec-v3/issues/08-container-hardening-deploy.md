Status: ready-for-agent

## What to build

Configurar o empacotamento em container seguro com Dockerfile multi-stage, compose para deploy no Coolify, autenticação remota no FastMCP e suite de verificação. Executar a aplicação com usuário não-root (`UID 10001`), sistema de arquivos somente-leitura, tmpfs em `/tmp`, isolamento de privilégios (`cap_drop: ALL`, `no-new-privileges: true`) e limites de recursos. Implementar o verificador customizado de token `TokenVerifier` comparando `MCP_AUTH_TOKEN` com tempo constante para o transporte HTTP exposto via ASGI/uvicorn, e disponibilizar documentação e script de teste de aceite com token fictício.

## Acceptance criteria

- [x] `Dockerfile` multi-stage com compilação isolada de dependências, runtime Python 3.12 slim, dependências do Chromium e usuário não-root (UID 10001)
- [x] `docker-compose.yml` compatível com Coolify e Traefik contendo `read_only: true`, `/tmp` tmpfs, limits de CPU/memória/PIDs, `shm_size: 1gb` e healthcheck via socket local
- [x] Autenticação Bearer para o transporte HTTP do FastMCP implementada via `TokenVerifier` usando `secrets.compare_digest` contra `MCP_AUTH_TOKEN`
- [x] Entrypoint configurado para inicialização via uvicorn com app ASGI e fallback para stdio
- [x] Arquivo `.env.example` atualizado refletindo todas as variáveis necessárias
- [x] Teste de aceite com token falso implementado para validação de vazamento de secrets em stdout/stderr/logs
- [x] README documentando a execução local, deploy no Coolify e salvaguardas operacionais

## Blocked by

- `.scratch/spec-v3/issues/02-search-ads-tracer-bullet.md`
- `.scratch/spec-v3/issues/05-creative-analysis-crawler.md`
- `.scratch/spec-v3/issues/07-campaign-management-write.md`

## Comments
