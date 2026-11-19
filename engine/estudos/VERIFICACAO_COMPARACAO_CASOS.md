# Comparação de projetos, discretização radial e falhas das varreduras

Bloco de interface implementado em **14/11/2026**. Cálculos, critérios e prioridades dos candidatos permanecem os mesmos. A alteração em `plot_sensibilidade.py` é exclusivamente de apresentação: mantém lacunas em vez de unir os pontos vizinhos de uma avaliação inviável.

## Comparar projetos

1. Calcular o caso desejado e abrir **Comparar projetos**.
2. Clicar em **Fixar execução atual como referência**. A referência é uma cópia independente de entradas, resultados escalares e tabelas, identificada por nome e ID.
3. Alterar as entradas e calcular outro caso. A referência permanece até o usuário substituí-la explicitamente pelo mesmo botão.
4. Conferir entradas alteradas, modos manual/automático, estágios adotados, indicadores, extremos radiais, dimensões e avisos.

A referência fica na memória da sessão. O download de comparação JSON reúne as duas fotografias para consulta posterior; não é um arquivo de entradas para importação. Para recuperar as entradas, usar os JSONs de casos do bloco de reprodutibilidade. Mudanças ainda não calculadas não entram na comparação.

As tabelas mostram valores e diferenças assinadas: `Δ = atual − referência`, `Δ% = 100 Δ / |referência|`. Referência zero ou resultado não determinado não recebe percentual. Para eficiências expressas em %, a diferença absoluta é em pontos percentuais. Contagem de mensagens não é índice de gravidade. A extensão axial usa a convenção existente da montagem CAD, sem interpretação de dimensionamento mecânico.

## Distribuições radiais, reação e torção

Os estágios são selecionados separadamente para cada caso. Isso evita emparelhar automaticamente o último estágio de uma turbina de três estágios com o terceiro de uma turbina de quatro. Mesmo quando os números ordinais coincidem, a posição física e a parcela do trabalho podem diferir.

As curvas usam pontos efetivamente calculados, sem interpolação ou reamostragem entre malhas. O eixo de altura relativa é `(r − r_hub) / (r_tip − r_hub)`, de 0 no cubo a 1 na ponta. As tabelas preservam os raios em cm. Sobrepor distribuições nessa coordenada permite comparar a forma; não identifica automaticamente a mesma posição física em geometrias diferentes.

Torção relativa: `Δζ(r) = ζ(r) − ζ(cubo)`, onde ζ é o stagger metálico do perfil entregue ao loft. A diferença é assinada e distingue-se de câmber e deflexão do escoamento. O painel mostra torção ao longo da altura e sua associação com a reação do estágio nas mesmas seções. A fileira é selecionável. Reação é resultado do modelo, não uma nova entrada independente; as entradas alteradas e os modos ficam identificados acima. A associação não constitui uma lei causal universal.

## Estudo de seções

Disponível na própria aba, executado somente pelo botão **Executar estudo de seções**. Opções: 3, 5, 7, 9 e 11 seções, com ao menos duas selecionadas. Cada avaliação usa uma cópia dos parâmetros da execução calculada e o pipeline já existente. O caso principal, a referência, as entradas do formulário e as curvas de sensibilidade atuais não são substituídos. Não se reexecutam as oito varreduras de sensibilidade para cada discretização.

Falhas continuam na tabela com suas razões; gráficos mantêm lacunas. O estudo registra o ID de origem e suas seções. Depois de nova execução, os resultados anteriores são identificados como pertencentes a outro caso. Alterar somente as opções não dispara cálculo: os resultados exibidos continuam identificados como o último estudo executado.

No automático, cada malha também pode escolher outros estágios. A tabela mostra estágios e ψ efetivo; se o número de estágios mudar, a interface avisa que a comparação inclui uma mudança de projeto. Para estudar amostragem com N fixo, usar estágios manuais. As malhas não são necessariamente aninhadas, nem os extremos e avisos precisam variar monotonicamente. Não se apresenta certificado de convergência ou precisão física. Os dados completos do estudo têm download JSON próprio.

## Sensibilidade

O painel **Condições das varreduras e pontos não calculados** identifica a entrada variada, os modos, as entradas mantidas, estágios adotados e o estado de cada ponto. Razões de falha possuem seleção para leitura completa.

Os dois plotadores preservam a sequência original de abscissas. Um caso inválido ou sem métrica finita produz `NaN` apenas na série de apresentação, interrompendo a linha. Um × vermelho na base indica a posição do parâmetro, sem valor físico no eixo vertical. Uma referência inviável não recebe estrela sobre um valor inventado. Pontos válidos mantêm os mesmos valores. O retorno dos cálculos e suas mensagens não são alterados.

## Evidências e limites

Verificadores em `checkpoints/comparacao_casos_2026-11-14/`:

- `verificar_dados.py`: usa as funções reais do pipeline, preservadas por comparação AST; confere referência manual e escolhas automáticas contra a regressão histórica, cópias independentes, discretizações 3/7/11, raios/altura relativa, torção assinada, diferenças com referência zero, falhas sintéticas e lacunas nas figuras.
- `verificar_interface.py`: AppTest com resultados reais previamente calculados; testa referência, rascunho ignorado, seletores com três/quatro estágios, estudo sem substituir o caso, opções pendentes, falhas e modos Guiado/Técnico.
- `verificar_refinamentos.py`: conferência focal das dimensões do combustor e dos seletores de motivos completos.
- Resultados JSON, fotografias numéricas e PNGs registram as verificações. As figuras são inspecionadas diretamente; AppTest não substitui avaliação visual integral no navegador.

Da pasta `NEW`, executar os scripts por seus caminhos relativos no checkpoint. Não se afirma validação física/experimental das configurações nem nova auditoria bibliográfica.

## Restauração

`manifesto.json` preserva cópias e hashes anteriores de `streamlit_app.py`, `reading_mode.py` e `plot_sensibilidade.py`. Para reverter este bloco, restaurar esses três arquivos e retirar os novos módulos `comparison_data.py`, `case_comparison.py` e `sensitivity_context.py`, preservando antes quaisquer alterações posteriores. Os hashes da implementação final constam em `arquivos_depois.json`.
