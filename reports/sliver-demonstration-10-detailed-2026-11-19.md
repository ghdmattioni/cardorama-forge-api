# Cardorama — análise das 10 partidas detalhadas: Sliver Demonstration

Data: **19/11/2026** · Ambiente: Railway `staging` · Forge **2.0.16** · `-f commander` · `-c 300` · 10 partidas espelhadas IA × IA.

## Resultado confirmado
- **10 partidas processadas**: 7 vitórias IA 1, 2 vitórias IA 2, 1 interrompida após 300 segundos (partida 10).
- **9 partidas concluídas com vencedor confiável**; duração média de aproximadamente **14,2 segundos** nessas nove.
- **4.265 eventos registrados**, **294.822 bytes de saída**, sem truncamento e sem atingir o limite de eventos.
- O status técnico do lote foi `partial` por uma partida interrompida; **não significa 10 partidas terminadas normalmente**.

## Ranking de observações em jogo (dois jogadores somados)

| Carta | Partidas em que foi utilizada | Outros eventos relevantes |
|---|---:|---|
| Venom Sliver | 7 | 12 habilidades desencadeadas registradas |
| Brood Sliver | 5 | 35 eventos de habilidade desencadeada |
| Outcaster Trailblazer | 5 | 14 eventos de habilidade desencadeada |
| Tempered Sliver | 5 | 10 eventos de habilidade desencadeada |
| Elda, Conjurer of Spectacle | 5 | Comandante conjurado em parte das partidas |
| Thrumming Hivepool | 4 | 12 eventos de habilidade desencadeada |
| Firemane Commando | 4 | 11 eventos de habilidade desencadeada |
| Realmwalker | 4 | Histórico de conjuração registrado |
| Cultivate | 4 | Rampa registrada |
| Constricting Sliver | 2 | 11 eventos de habilidade desencadeada |

**Observação:** números agrupados por partida e carta nos dois decks, não por jogador; número de conjurações/efeitos pode incluir cópias e efeitos de fichas. Uma habilidade registrada não garante valor líquido positivo.

## Cinco cartas que não apareceram nos logs de nenhuma das dez partidas

- Lucy MacLean, Positively Armed
- Silverquill Lecturer
- Sinew Sliver
- Trostani, Selesnya's Voice
- Song of the Worldsoul

**Não são cinco cartas ruins.** O GameLog padrão não mostra todas as cartas compradas ou mantidas na mão, então ausência pode significar apenas não ter sido comprada, não ter sido conjurada ou não ter gerado um evento identificado. *Sinew Sliver*, por exemplo, dá +1/+1 a todos os Fractius e não deve ser cortada por esse motivo isolado.

## Riscos de construção — hipóteses para investigar

1. **Elda em confronto espelhado:** demonstrate dá uma cópia ao oponente quando decidimos copiar a criatura. Especialmente perigoso com Fractius que beneficiam todos os Fractius, incluindo os inimigos.
2. **Efeitos globais dos Fractius antigos:** Muscle Sliver, Sinew Sliver, Gemhide Sliver, Horned Sliver e Ward Sliver podem beneficiar Fractius adversários. Quick Sliver também beneficia jogadores adversários que conjuram Fractius.
3. **Harmonic Sliver e as próprias permanentes:** a habilidade de destruir artefatos/encantamentos dos Fractius é obrigatória e pode atingir Hivestone, Vanquisher's Banner ou Growing Ranks quando não houver alvo inimigo adequado. É uma questão de sequência de jogadas, não prova de que Harmonic Sliver seja uma carta ruim.
4. **Groundshaker Sliver:** custa 7 manas, tem alguma redundância com Horned Sliver (custa 3), e só teve jogada identificada em **1/10 partidas**. Primeiro candidato a investigar, não corte definitivo.
5. **First Sliver's Chosen:** custa 5 manas, apareceu em **2/10 partidas**, e o plano *exalted* favorece ataque isolado, enquanto a lista prioriza múltiplas fichas e ataques em grupo.
6. **Song of the Worldsoul:** 6 manas, nenhum evento identificado no lote. Testar se o motor de geração de fichas chega tarde para influenciar as partidas.
7. **Interação com criaturas:** a lista depende muito de Constricting Sliver para exilar criaturas adversárias, sem diversidade de remoções pontuais. Testar contra decks que façam ameaças cedo.
8. **Alta concentração de criaturas de custo elevado:** Groundshaker Sliver (7), Megantic Sliver (6), Constricting Sliver (6), Song of the Worldsoul (6), Rishkar's Expertise (6) e Vanquisher's Banner (5). O número de terrenos é 36; dados de mão e compra serão necessários antes de afirmar que a curva prejudicou vitórias.

## Limitações metodológicas

- Os dois adversários tinham a mesma lista; este teste **não calcula a taxa real de vitória do deck**.
- O Forge não garante decisões ótimas, especialmente em partidas com muitas fichas e habilidades.
- Dados de mão inicial, compras e cartas que ficaram presas na mão **não foram coletados**. Ainda não existe uma classificação confiável de “carta ruim”.
- Uma das partidas atingiu 5 minutos. Isso é um limite de execução do motor/IA, não automaticamente uma falha do deck.
- Para recomendações de cortes, é preciso executar confrontos contra listas diferentes e coletar métricas por jogador, carta, mão e turno.

O relatório JSON nesta pasta preserva o resultado individual das 10 partidas e as métricas de eventos por carta.
