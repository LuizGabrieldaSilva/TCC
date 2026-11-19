# Seleção automática entre números de estágios vizinhos

Implementação autorizada em 06/11/2026. Política `vizinhos_criterios_v1` em `engine/stage_selection.py`.

## Comportamento

O modo manual permanece com o número de estágios e ψ fornecidos. No automático, o programa avalia `max(1,floor(N_estimado))` e `max(1,ceil(N_estimado))`, sem duplicatas. Para cada candidato, o trabalho total do ciclo é redistribuído e ψ efetivo é recalculado. Portanto, ψ solicitado é uma preferência e pode ser ultrapassado: não é mais um teto garantido pela antiga regra de arredondar para cima.

Cada candidato executa os modelos existentes de meanline, radial e geração de perfis. Não há otimização contínua, CFD, busca de outros números de estágios, análise estrutural ou teste de colisões. A escolha de cada componente é independente: não é uma otimização conjunta compressor–turbina.

Os objetos são selecionados em `resolver()`. Antes disso, os construtores mantêm uma inicialização provisória dos vetores, sem representar a seleção final. A malha usada na avaliação é informada por `n_secoes_avaliacao`, com padrão de sete seções; interface e sensibilidades enviam a discretização da execução.

## Política de comparação

1. Descartar candidatos que falhem no cálculo/construção ou não fechem Tt/Pt com os alvos do ciclo (tolerâncias numéricas relativa 1e-9 e absoluta 1e-7 nas unidades SI).
2. Minimizar o maior excesso aerodinâmico normalizado.
3. Minimizar a soma dos excessos aerodinâmicos por família.
4. Minimizar o excesso de câmber do perfil circular.
5. Minimizar o maior excesso nas faixas comparativas e, depois, sua soma por família.
6. Minimizar `abs(psi_efetivo/psi_solicitado−1)`.
7. Desempatar pelo menor número de estágios.

As chaves de comparação são arredondadas a 12 casas decimais para não decidir por diferenças menores que essa resolução dos índices. Para estimativas exatamente inteiras existe um único candidato; abaixo de um estágio, o candidato é um. Não se aplica a regra decimal de 0,5: a escolha considera os critérios acima.

Essa ordem é uma **política adotada no projeto**, não uma regra universal dos livros. Em particular, priorizar câmber sobre faixas comparativas é uma decisão explícita que pode ser revisada pelo autor após observar os resultados.

| Grupo | Critérios avaliados |
| --- | --- |
| Aerodinâmica do compressor | Mach relativo >1; DF rotor/estator >0,6; reação negativa |
| Aerodinâmica da turbina | Mach relativo de saída >1; Mach do bocal >1,3; reação fora de 0–1 |
| Geometria aproximada | Câmber em módulo >60° no compressor e >90° na turbina, conforme os alertas do gerador |
| Faixas comparativas | ψ de 0,3–0,6 no compressor e 1,0–2,5 na turbina; reação meanline de 0,4–0,6 no compressor e meanline/radial de 0,3–0,7 na turbina; swirl de escape da turbina com abs(Ctheta/U)>0,15 |

Para limite superior, o excesso é `max(0,valor/limite−1)`. Para faixa, usa-se a distância para fora dividida pela largura da faixa. Para reação negativa/acima de um, usa-se a distância para o intervalo. Não há interpretação probabilística desses índices.

Usa-se o pior excesso por família entre os locais avaliados. A repetição do mesmo problema em muitos estágios/seções não soma votos; a contagem bruta de mensagens não participa da escolha. O método privilegia o pior caso e não mede a extensão espacial da região afetada. Critérios gerais iguais nos dois candidatos, como HTR e φ prescritos, não são fatores diferenciadores desta classificação.

Os limites usados para medir excessos são os critérios já adotados no código; não foram relaxados para favorecer um resultado. As temperaturas/pressões de saída que fecham o ciclo não comprovam uma interface física de difusor.

## Resultado de referência

Com as entradas atuais e sete seções:

| Componente | Candidato inferior | Candidato superior | Escolha e motivo |
| --- | --- | --- | --- |
| Compressor | 7 estágios, ψ=0,398480057 | 8 estágios, ψ=0,348670050 | 8: demais critérios de classificação empatam na resolução adotada; menor afastamento do ψ solicitado |
| Turbina | 3 estágios, ψ=1,198736089 | 4 estágios, ψ=0,899052067 | 4: menor excesso de câmber, apesar de maior desvio nas faixas comparativas e no ψ solicitado |

A turbina com três estágios fecha o ciclo: não foi rejeitada pelo pequeno erro de arredondamento do ψ manual. Seu excesso relativo de câmber é aproximadamente 0,086224. O candidato de quatro estágios não apresenta esse excesso, mas tem excesso máximo de faixas de aproximadamente 0,430026; seu ψ fica abaixo da faixa comparativa de 1,0–2,5. **Assim, quatro estágios não é uma aprovação física nem uma solução que satisfaça todos os critérios.** A justificativa é a prioridade de classificação adotada.

O compressor mantém Mach relativo de ponta ligeiramente acima de um em ambos os candidatos; essa condição não é removida pela seleção. No caso automático de razão de pressão 12, o compressor passou de onze estágios pela antiga regra para dez com a comparação. A regressão termodinâmica desses casos deve exigir fechamento, não igualdade com as geometrias automáticas anteriores.

## Interface, avisos e exportações

O painel “Seleção automática — comparação dos candidatos” aparece nas abas Compressor/Turbina quando o respectivo modo automático está ativo. Mostra candidatos, ψ, índices e justificativa, com seleção de detalhes por candidato. Selecionar uma linha/candidato para consulta não troca o projeto escolhido.

Quando a solução escolhida ultrapassa critérios comparados, há uma ressalva explícita. Os avisos dos candidatos descartados ficam fora da contagem do caso; os verificadores habituais do candidato escolhido continuam sendo executados. O diagnóstico de seleção não conta como certificação ou novo aviso físico artificial.

Se todos os candidatos falharem, o programa informa os motivos e não retorna silenciosamente ao antigo arredondamento para cima. Se apenas um for calculável, isso é registrado como justificativa. A indicação “calculável” não significa “atende a todos os critérios”.

O JSON de fechamento e áreas inclui os candidatos, métricas, decisão, política e malha de avaliação. Os CSVs/lofts/DXFs continuam sendo gerados a partir do modelo escolhido. Os rótulos dos ZIPs passaram a mostrar o número efetivo de peças, em vez de fixar 16/6.

As sensibilidades usam a mesma política da interface. Continuam sendo reconstruções de projeto: decisões discretas podem mudar N, os triângulos, a reação e os perfis ao longo da curva.

## Ajuste de dependências

Os radiais importavam `compr1`/`turb1`, exemplos meanline executados durante importação. A avaliação inversa meanline → radial gerava dependência circular. As duas importações de exemplos foram movidas para os blocos `if __name__ == '__main__'` dos radiais. As classes e os cálculos radiais foram preservados; seus exemplos continuam acessíveis na execução direta.

## Verificações

Evidências em `checkpoints/selecao_estagios_2026-11-06/`:

- `acoplamento_depois.json`: oito casos, Euler/geometria e fechamento automático aprovados.
- `selecao_estagios.json`: vizinhos, entradas inválidas, classificação por severidade e independência da contagem de mensagens; escolha entre candidatos reais; repetição determinística de `resolver()`; rejeição explícita de ambos os candidatos com grade inadmissível. Os dois casos manuais de três/sete seções foram comparados com o snapshot anterior e preservados.
- `geometria_perfis.json`: oito casos, Carter, solidez e tangentes do loft; 960 perfis nos casos atuais (o número mudou porque o automático pode escolher outro número de estágios).
- `estagios_turbina.json`, `diagnosticos.json`, `combustor.json`, `indicadores.json`: verificadores existentes aprovados sem exigir igualdade com o antigo número de estágios automático.
- `interface.json` e `interface.log`: AppTest aprovado para referência manual (8/3 estágios e dois avisos preservados), ambos os modos automáticos, consulta do candidato alternativo sem mudar a solução e recálculo com vazão de 16 kg/s e três seções radiais. Conferidos fechamento, metadados de seleção no JSON, rótulos dinâmicos dos downloads e execução das sensibilidades. Todos os arquivos Python do engine passaram por análise sintática. Os testes da interface foram programáticos, não inspeção visual em navegador.

Reprodução a partir de `NEW`:

```powershell
python -X utf8 -m engine.estudos.verificar_selecao_estagios --antes ../checkpoints/matriz_rastreabilidade_2026-11-06/acoplamento.json --saida ../checkpoints/selecao_estagios_2026-11-06/selecao_estagios.json
python -X utf8 -m engine.estudos.verificar_acoplamento --saida ../checkpoints/selecao_estagios_2026-11-06/acoplamento_depois.json
```

Os testes são verificações de implementação e coerência. Não constituem nova comparação experimental ou validação integral da política pela literatura. Não foi feita inspeção visual em navegador ou importação CAD nesta etapa.

## Recuperação

O checkpoint contém cópias anteriores e hashes em `manifesto.json`. Para reverter, restaure somente os arquivos listados nos respectivos caminhos, incluindo os dois radiais e a matriz. Os novos módulos `stage_selection.py`, `verificar_selecao_estagios.py` e este relatório podem permanecer sem uso na versão restaurada. Não é necessário reverter o repositório inteiro ou alterar o caso de referência.

## Refinamento posterior — valores reais e localização dos critérios

Em 06/11/2026 foram acrescentados nomes legíveis, valores reais, limites/faixas e localizações dos extremos em cada candidato. A política `vizinhos_criterios_v1`, sua ordem de prioridade, os escores e as escolhas foram preservados. A revisão de prioridade continua dependendo da decisão do autor.

O novo campo `detalhes_criterios` no diagnóstico de cada candidato registra grupo, identificador, valor, unidade, limites, origem do dado, estágio, seção, fileira, posição e excesso normalizado. A interface traduz os identificadores para nomes explicativos e permite consultar a localização completa em tabela vertical. Consultar outro critério ou outro candidato não troca o projeto escolhido. Sessões com resultados anteriores precisam recalcular para preencher os novos metadados.

Para limite inferior mostra-se o mínimo; para limite superior, o máximo. Para faixa, mostra-se o valor com maior distância assinada para fora dela; se todos os valores estão dentro, o extremo mais próximo de uma borda. Em empate, mostra-se a primeira ocorrência na ordem de avaliação. Câmber e swirl são apresentados em módulo. Um valor meanline é identificado como tal, sem atribuí-lo a uma seção radial amostrada. ψ é identificado como carga uniforme de todos os estágios.

Na referência de sete seções:

| Candidato | Critério | Valor real | Limite/faixa | Localização |
| --- | --- | ---: | --- | --- |
| Compressor, 8 estágios | Mach relativo | 1,001189 | ≤1 | Entrada do rotor do estágio 1, tip, estação local 1, radial |
| Turbina, 3 estágios | Câmber metálico em módulo | 97,760174° | ≤90° | Rotor do estágio 3, hub, perfil |
| Turbina, 4 estágios | Câmber metálico em módulo | 89,475713° | ≤90° | Rotor do estágio 4, hub, perfil |
| Turbina, 4 estágios | Reação do estágio | 0,127990 | 0,3–0,7 | Estágio 4, hub, radial |

Verificações registradas em `checkpoints/detalhes_criterios_2026-11-06/`:

- `detalhes.json`: 90 registros conferidos contra os valores originais de meanline, radial e perfis dos candidatos. Limites reconstituem os excessos existentes. Classificação, justificativas e escolhas idênticas ao snapshot anterior, excluindo apenas os novos metadados.
- `acoplamento.json`: oito casos com estados, velocidades, áreas e números de estágios preservados em comparação com a versão anterior a este refinamento.
- `interface.json`: AppTest do painel real de produção aprovado; nomes e formato brasileiro conferidos; consulta da turbina de três estágios mostra rotor 3/hub e permite mudar para ψ sem alterar a solução calculada de quatro estágios. Não houve inspeção visual em navegador nesta etapa.

Comandos a partir de `NEW`:

```powershell
python -X utf8 -m engine.estudos.verificar_detalhes_selecao --antes ../checkpoints/selecao_estagios_2026-11-06/selecao_estagios.json --saida ../checkpoints/detalhes_criterios_2026-11-06/detalhes.json
python -X utf8 -m engine.estudos.verificar_acoplamento --antes ../checkpoints/selecao_estagios_2026-11-06/acoplamento_depois.json --saida ../checkpoints/detalhes_criterios_2026-11-06/acoplamento.json
```

Para reverter somente este refinamento, use as três cópias listadas no manifesto de `checkpoints/detalhes_criterios_2026-11-06/`. Os módulos novos `webapp/stage_selection_details.py` e `estudos/verificar_detalhes_selecao.py` podem permanecer sem uso após essa restauração. O checkpoint anterior de seleção continua preservado e não foi sobrescrito.
