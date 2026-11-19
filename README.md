# Cardorama Forge Simulation API

Integração **experimental** de simulações Magic: The Gathering via motor Forge oficial, isolado em processo Java. Não representa um fork nem uma atualização do módulo Java de jwgerlach00/card-forge.

## Status

Servidor HTTP, validação, autenticação por `X-API-Key` e execução de subprocesso implementados. **Partidas reais foram executadas no Railway; simulador detalhado segue em homologação**. `/readyz` apenas verifica a presença do JAR; use o teste real de partida antes de considerar o motor funcional. Jobs em memória se perdem no restart; não usar em produção multiusuário.

## Deploy (Railway)

- Serviço existente: `cardorama-forge / staging / forge-simulation-api`
- Fonte: este repositório, branch `main`.
- Dockerfile: instala Java 17, Python 3.12 e obtém a release oficial Forge 2.0.16 no build.
- Configure **CARDORAMA_API_KEY** como segredo privado; nunca coloque a chave no GitHub.
- Variáveis: `FORGE_HEAP_MB=512`, `FORGE_GAME_CLOCK=300` (5 minutos por partida), `FORGE_TIMEOUT=3600` (limite total do lote).
- Limite atual Railway: 1 GB de RAM. Pode ser insuficiente para Commander.
- Não exponha domínio público para simulações antes de quotas, armazenamento persistente e autenticação por usuário.

### Endpoints

- `GET /healthz`: aplicação ativa.
- `GET /readyz`: verifica se o arquivo JAR foi localizado.
- `POST /v1/simulations`: enfileira até 100 jogos, requer `X-API-Key`.
- `GET /v1/simulations/{id}`: obtém resultado, requer `X-API-Key`.

Exemplo JSON: `{"format":"commander","games":1,"decks":[{"name":"Deck A","decklist":"[Commander]\\n1 ...\\n[Main]\\n..."},{"name":"Deck B","decklist":"..."}]}` (cada deck deve totalizar 100 cartas).

## Pontos críticos

1. Verificar build e layout da release oficial; o Docker falha se não identificar o JAR executável.
2. Rodar partida real e analisar logs de cartas/decks antes da homologação.
3. Implementar fila persistente e controle de usuários no Cardorama.
4. Avaliar licença GPL-3.0 do Forge e condições de uso.
