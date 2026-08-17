Status: ready-for-agent

## What to build

Implementar as tools de criação e gestão de campanhas (`create_campaign`, `create_ad_set`, `create_ad`) com salvaguardas financeiras e operacionais rigorosas. Todas as operações de escrita devem utilizar `dry_run=True` por padrão, aplicar o teto financeiro `MAX_CAMPAIGN_BUDGET` sobre o valor decimal informado na moeda da conta, converter o orçamento em menor unidade inteira (`x100`), validar a conta contra a lista de contas autorizadas em cache, e validar inputs contra allowlists de objetivos (5 permitidos), categorias especiais de anúncio, chamadas para ação (11 CTAs permitidos) e destino `link_url` exclusivamente `https://` sem fetch no servidor.

## Acceptance criteria

- [x] Requisições POST na Meta executadas sem retry automático no cliente
- [x] Validação de `ad_account_id` contra o cache de `/me/adaccounts`
- [x] Parâmetro `dry_run` padrão em `True` para todas as ferramentas de escrita, retornando payload simulado e sanitizado
- [x] Validação do teto financeiro `MAX_CAMPAIGN_BUDGET` diretamente sobre o valor decimal, rejeitando valores que excedam o limite ou sejam menores/iguais a zero
- [x] Conversão exata de orçamento para inteiro multiplicado por 100
- [x] Tool `create_campaign` valida enum de objetivos e categorias especiais
- [x] Tool `create_ad_set` suporta targeting básico validado no servidor (países, faixa etária 18-65, gênero, plataformas)
- [x] Tool `create_ad` valida formato de imagem URL, allowlist de 11 CTAs e `link_url` HTTPS sem efetuar requisições externas para o link
- [x] Testes automatizados cobrem cenários com `dry_run=True` e `dry_run=False`, validações de limites de budget e rejeição de entradas inválidas

## Blocked by

- `.scratch/spec-v3/issues/02-search-ads-tracer-bullet.md`
- `.scratch/spec-v3/issues/06-ad-accounts-creative-upload.md`

## Comments
