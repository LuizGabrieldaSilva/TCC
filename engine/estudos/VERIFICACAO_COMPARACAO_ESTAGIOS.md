# Comparação didática entre estágios

Iniciada em **09/11/2026** e concluída em **10/11/2026**. A pasta de checkpoint
mantém a data de início: `checkpoints/comparacao_estagios_2026-11-09/`.

Esta implementação atende à parte ainda pendente do item 7 de
`Ideias_Interface_Didatica.md`: visão comparativa por estágio e consulta dos
resultados de um estágio por vez. A prioridade dos candidatos foi mantida;
sua discussão com o professor continua pendente.

## Uso na interface

Nas abas **Compressor** e **Turbina**, abrir **Comparação entre estágios e
estágio em foco**. O usuário escolhe o estágio e a grandeza do gráfico:

- Temperaturas totais de entrada e saída, meanline, em K.
- Pressões totais de entrada e saída, meanline, em kPa.
- Razão de pressão por estágio, meanline, adimensional.
- Reação meanline e extremos radiais.
- Máximo radial do Mach relativo: entrada do rotor no compressor; saída
  do rotor na turbina.
- Número de pás de cada fileira.
- Máximos radiais de DF do rotor e do estator, somente no compressor.

A opção **Mostrar valores e localização dos extremos** revela a tabela do
gráfico escolhido. Reação e Mach identificam também as seções que produzem
os extremos. Empates conservam a primeira seção na ordem calculada.

A linha pontilhada do gráfico marca o estágio em foco. O painel imediatamente
abaixo mostra a tabela radial e a geometria desse estágio. A longa lista de
expanders de todos os estágios foi substituída por esse seletor; todos os
estágios continuam disponíveis. Os painéis de triângulos e de perfis conservam
seus seletores próprios, como informado na interface.

O painel inicia recolhido. Ao recalcular com menos estágios, uma seleção que
deixou de existir volta ao estágio 1, evitando acesso fora dos vetores.

## Bases e limites da apresentação

`webapp/stage_overview.py` apenas lê objetos já calculados. Não instancia
máquinas, não resolve um novo caso, não altera parâmetros e não participa
da seleção automática.

Os extremos são obtidos nas seções radiais efetivamente calculadas, sem busca
contínua em raio ou integração de grandezas. Se uma seção tiver valor não
finito, o extremo daquele conjunto é apresentado como não determinado; o
gráfico mantém a lacuna em vez de representar um máximo/mínimo parcial como
se fosse completo.

As linhas conectam estágios discretos, sem descrever a evolução contínua
dentro das fileiras. A razão de pressão usa a convenção de cada máquina:
saída/entrada no compressor e entrada/saída na turbina; não é acumulada.
Os critérios de Mach e DF usam `design_criteria.py`. A faixa comparativa de
reação do compressor continua aplicada ao meanline, sem nova verificação
de faixa radial.

## Verificações

Script e resultados em `checkpoints/comparacao_estagios_2026-11-09/`:

- Seis conjuntos componente/caso: compressor e turbina manuais em π=8,
  automáticos em π=8, e automáticos em π=6 com três seções radiais.
- Todos os valores das tabelas, extremos e respectivas seções comparados
  diretamente com os objetos de origem. Coordenadas das linhas verificadas.
- Objetos serializados antes/depois: apresentação sem mutação.
- Gráfico de um único estágio e lacuna para valor radial não finito conferidos.
- Imagens de comparação de reação e temperatura renderizadas e inspecionadas.
- AppTest: troca de grandeza/estágio, tabelas de oito e três linhas,
  geometria associada ao estágio escolhido, modos manual/automático e
  redução de quatro para três estágios na turbina aprovados.
- Avisos e potência do caso manual, e metadados completos da seleção
  automática, iguais ao checkpoint anterior. Sensibilidade sem erro de execução.

Evidências: `dados.json`, `interface.json`, `interface.log`, figuras `.png`
e o script `verificar.py`, executável a partir de `NEW` com o Python do projeto.
AppTest confere o comportamento da aplicação; não substitui a avaliação visual
completa no navegador nem a validação física ou experimental da máquina.

## Retorno

O checkpoint preserva `streamlit_app.py` e a matriz de rastreabilidade,
mantendo os caminhos relativos e hashes em `manifesto.json`. Para retornar,
encerrar o Streamlit e copiar esses dois arquivos de volta aos caminhos em
`NEW/engine/`. Os novos `webapp/stage_overview.py` e este relatório podem ser
removidos após a restauração, se desejado. Não é necessário resetar o Git.
