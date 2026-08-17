Status: ready-for-agent

## What to build

Implementar a camada de gestão de contas e upload de criativos: tools `list_ad_accounts` e `upload_creative_asset`. Implementar serviço para consultar contas autorizadas em `/me/adaccounts` com cache de 5 minutos (para posterior validação de permissão de escrita). Criar cliente Cloudinary isolado com o SDK oficial pinado, aceitando imagens em Base64 inline com validação estrita de MIME type e limite de tamanho (`MAX_IMAGE_BYTES=10MB`). Garantir que credenciais Cloudinary sejam omitidas de qualquer saída/log, permitindo a exposição apenas da URL pública final da imagem gerada.

## Acceptance criteria

- [x] Serviço de contas busca `/me/adaccounts` e armazena em cache por 5 minutos
- [x] Tool `list_ad_accounts` retorna lista higienizada de contas (`ad_account_id`, `name`, `currency`, `account_status`)
- [x] Tool `upload_creative_asset` aceita payload Base64 inline, valida tipos MIME permitidos (`image/png`, `image/jpeg`, `image/webp`, `image/gif`) e tamanho máximo de 10MB decodificado
- [x] Upload para Cloudinary utiliza SDK oficial com timeout configurado
- [x] Credenciais e chaves do Cloudinary são devidamente redigidas em logs e saídas de erro, enquanto a URL pública de entrega é preservada
- [x] Falhas por ausência de configuração retornam erro limpo `CLOUDINARY_NOT_CONFIGURED`
- [x] Testes unitários com mocks de API cobrem listagem de contas e upload de assets

## Blocked by

- `.scratch/spec-v3/issues/01-project-skeleton-tooling.md`

## Comments
