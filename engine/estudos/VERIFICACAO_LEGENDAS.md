# Revisão de legendas, explicações e contagens

Concluída em **09/11/2026**, com autorização do autor. Esta etapa revisa a
apresentação e as expectativas de scripts auxiliares; os modelos físicos,
limites, parâmetros de referência e prioridades de seleção foram preservados.

## Mudanças

- CSV: as linhas de dados esperadas agora são `n_estagios × número de seções
  efetivamente geradas`, com indicação de que o cabeçalho é contado à parte.
- Loft: títulos, quantidade esperada de fileiras e sequência rotor/estator ou
  bocal/rotor seguem o número de estágios do objeto calculado. Foram removidas
  as expectativas fixas de três estágios/seis fileiras na turbina.
- O exemplo comentado de exportação DXF também usa duas fileiras por estágio.
- O teste de loft passou a dizer que confere contagens, ordem e espaçamentos
  geométricos, sem chamar isso de aprovação de resistência estrutural.
- Sensibilidade: a legenda sombreada agora diz **“Faixa comparativa (projeto)”**.
  A linha de DF diz **“Critério de difusão”**, evitando tratá-la como previsão
  exata de separação. Mach = 1 permanece identificado como condição sônica.
- A interface explica a origem das faixas, o alcance da triagem de DF e os
  possíveis saltos quando a seleção automática muda os estágios entre pontos.
  Também distingue o mínimo radial de reação mostrado no gráfico do compressor
  da aplicação da faixa de reação no verificador meanline.
- A tabela de origens informa os limiares geométricos de câmber dos dois
  componentes (60° e 90°), sem atribuí-los a uma regra física universal.
- Interpretações dos avisos distinguem limiar de emissão, coincidência numérica
  e tolerância de projeto. A mistura global não é apresentada como previsão
  de flameout, fuligem ou temperaturas de parede.
- O aviso de espessura informa o limiar realmente usado: `t/c > 0,25`.
  A referência anterior a 0,05–0,15 foi removida desse aviso. O disparo e o
  valor do limiar não mudaram; o texto preserva a precisão do valor exibido.
- Comentários e docstrings do ciclo, meanlines, verificadores, perfis e
  sensibilidade foram alinhados ao comportamento atual. O limite de TIT é
  prescrito pelo usuário, não uma previsão universal para materiais sem
  resfriamento. `valido=True` na varredura significa cálculo concluído.

As faixas de orientação, os critérios empíricos e as relações teóricas têm
papéis diferentes. Esta revisão não acrescentou citações bibliográficas
precisas não verificadas nem envolveu uma nova leitura integral dos livros.

## Evidências

Pasta: `checkpoints/revisao_legendas_2026-11-09/`.

| Conferência | Resultado |
|---|---|
| Regressão de acoplamento | Oito casos, resultados preservados |
| Detalhes da seleção | 90 valores/limites/localizações; escores e escolhas iguais |
| Verificadores de critérios | 612 comparações; assinaturas, mensagens e disparos preservados nessas funções |
| Geometria dos perfis | Oito casos conferidos |
| CSV e loft, exemplo automático | 8/4 estágios, 7 seções; 56/28 linhas; sem divergências de contagem/ordem/gaps |
| CSV e loft, caso alternativo | 7/3 estágios, 3 seções; 21/9 linhas; sem divergências de contagem/ordem/gaps |
| Espessura | 0,25 não dispara; 0,2501 dispara e mostra o valor corretamente |
| Gráficos | Coordenadas das curvas/estrelas preservadas; legendas renderizadas e inspecionadas |
| Entradas | 155 recusas de domínio, quatro fronteiras válidas e ordem de chamadas aprovadas |
| Importações | 60 arquivos sem cálculos, mensagens ou arquivos de saída; estados dos exemplos iguais |
| Interface | AppTest manual/automático aprovado; avisos de referência, potência e seleção preservados; 56 pontos de sensibilidade sem erro computacional |

O script `verificar.py` registra a regressão e os casos de apresentação;
`conferir_aviso_final.py` confere a precisão final do texto de espessura;
`verificar_interface.py` executa o AppTest. Resultados em `execucoes.json`,
`apresentacao.json`, `importacoes.json`, `entradas.json`, `interface.json`
e logs correspondentes. CSVs de teste permanecem apenas no checkpoint.

As imagens `reacao_legenda.png` e `difusao_legenda.png` usam dados de amostra
para conferir a apresentação. A interface foi testada com os cálculos reais
do caso. Não foi feita uma inspeção visual completa do aplicativo no navegador.

O verificador de importações mantém sua comparação de estados e independência
dos exemplos. A comparação estrita de definições da versão histórica, que
inclui docstrings e textos, passou a exigir `--comparar-definicoes`: ela é uma
auditoria daquela versão, não uma regressão numérica que deva aprovar revisões
posteriores de textos e expectativas. A evidência histórica foi preservada.

## Alcance

Esta revisão resolve as contagens e os textos inconsistentes identificados
no código atual de `NEW/engine`. Não reescreve os materiais históricos em
`Arquivos de apoio`, feedbacks ou checkpoints. Relatórios anteriores descrevem
suas versões; pendências de contagem/legendas neles mencionadas são superadas
por este registro.

Os testes não certificam estabilidade, resistência, combustão real ou
fabricabilidade. A política de seleção continua favorecendo câmber antes das
faixas comparativas; a decisão do autor sobre essa prioridade permanece aberta.

## Checkpoint e retorno

Foram preservados **15 arquivos**, com caminhos relativos e SHA-256 em
`manifesto.json`. Para retornar, encerrar o Streamlit e copiar somente esses
arquivos de `checkpoints/revisao_legendas_2026-11-09/NEW/engine/` para os caminhos
correspondentes em `NEW/engine/`. Este relatório é novo e pode ser removido
após a restauração, se desejado. Não é necessário resetar o repositório.
