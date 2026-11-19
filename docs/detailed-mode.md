# Simulação detalhada (experimental)

O modo \`detailed\` remove \`-q\` da execução headless do Forge 2.0.16, preserva a saída padrão separada das exceções em stderr e extrai eventos \`Turn\`, \`Phase\`, \`Land\`, \`Add To Stack\`, \`Resolve Stack\`, \`Damage\`, \`Combat\`, \`Zone Change\` e outros por partida.

**Endpoints** (ambos exigem \`X-API-Key\` no servidor):
- \`POST /v1/simulations\` com \`{"format":"commander","mode":"detailed","games":2,"decks":[...]}\`
- \`GET /v1/simulations/{jobid}\`: placar, métricas e resumo heurístico por carta
- \`GET /v1/simulations/{jobid}/games/1?turn=3&offset=0&limit=200\`: eventos de um turno, com paginação

**Importante**: \`not_observed\` não significa carta ruim nem que não tenha sido comprada. O Forge não expõe, pelo GameLog, a mão inicial completa, todas as compras ou as cartas não jogadas na mão. A análise por carta a partir de nomes nos textos é heurística, especialmente quando os decks possuem nomes semelhantes ou efeitos que não passam pela pilha.

**Limites atuais de staging:** 10 jogos por requisição detalhada, até 16 MB de log total e 30.000 eventos. O histórico detalhado vive em memória e se perde no redeploy/restart; não usar como armazenamento definitivo. O próximo estágio requer instrumentação Java com IDs de carta e eventos estruturados persistidos em banco e object storage.
