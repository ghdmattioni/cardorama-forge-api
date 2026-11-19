# Cardorama — Forge Simulation API

Adaptador REST para o modo de simulação headless do [Forge](https://github.com/Card-Forge/forge), para testes de decks do projeto Cardorama.

**Estado:** protótipo em homologação. O motor Forge real ainda não teve partida validada em produção. O serviço Railway staging será conectado a este repositório.

A API emprega processos Java isolados, fila com concorrência limitada, autenticação por chave no servidor e validação conservadora de resultados.

Código baseado no protótipo Cardorama preparado em novembro de 2026. O Forge tem licença GPL-3.0; antes da distribuição comercial, conferir obrigações aplicáveis.
