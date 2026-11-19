# Painel didático da distribuição radial

Implementado e verificado em **10/11/2026**. Checkpoint anterior:
`checkpoints/distribuicao_radial_didatica_2026-11-10/`.

## Funcionalidade

As abas Compressor e Turbina passam a incluir **Distribuição radial — do cubo
à ponta e vórtice livre**, logo após a comparação entre estágios. O painel usa
o mesmo estágio em foco, evitando um segundo seletor de estágio com resultado
potencialmente diferente. Há um seletor próprio de seção radial e duas áreas:

1. **Grandezas ao longo do raio:** ângulos absolutos e relativos do modelo,
   Mach, reação e, no compressor, fator de difusão. São apresentados apenas
   campos já disponíveis nos objetos radiais.
2. **Conferência de r·Cθ:** estação local selecionável, constante em cada seção,
   referência meanline, diferença assinada e percentual correspondente.

O eixo horizontal informa raio em cm e identifica hub, intermediárias e tip.
A seção em foco é marcada por linha pontilhada nos gráficos e destaque na
tabela. As tabelas só aparecem quando solicitadas pelos controles de exibição.

As estações locais disponíveis são 1 e 2 no compressor, e 1, 2 e 3 na turbina.
O painel não inventa valores não calculados para uma estação adicional.
Os ângulos mantêm as convenções de sinais do núcleo, explicadas no painel de
triângulos. O número de seções exibido é o da execução calculada; mudar a
amostragem exige alterar o formulário e recalcular.

## Origem dos dados e alcance

O novo `webapp/radial_distribution.py` é somente uma camada de apresentação.
As curvas leem as listas/dicionários dos modelos já resolvidos. Não há nova
solução radial, interpolação física ou mudança de geometria, hipóteses,
parâmetros, critérios ou política de seleção de candidatos.

A conferência usa a relação já implementada nos módulos radiais:

`r Cθ(r) = r_m Cθ,m`.

`v1`, `v2` e `v3` minúsculos no núcleo são componentes tangenciais absolutas,
não os módulos `V1`, `V2`, `V3` nem a velocidade relativa W. O produto é
calculado com raio em metros, resultando em m²/s. A referência usa o raio
médio aritmético do componente e a componente tangencial meanline da mesma
estação e estágio.

A constante é conferida ao longo do raio **em cada estação**; pode mudar
entre estações e estágios. A interface explicita que o rotor altera Cθ e que
verificar uma relação imposta pelo próprio modelo não é validação independente
do escoamento real.

Diferença = produto radial − referência; percentual = 100 × diferença /
|referência|. Para referência zero, o percentual fica ausente, exibido como
“—”; a diferença dimensional continua disponível. Os resíduos são exibidos
em notação científica, para não ocultar arredondamento como um zero exato.
A escala do gráfico de constantes evita ampliar diferenças mínimas até
parecerem uma tendência física. Valores não finitos mantêm lacunas nas curvas.

Mais seções refinam a amostragem; não eliminam as limitações 1D e de vórtice
livre. Não foi acrescentada sobreposição de duas malhas de execuções distintas
nem destaque da seção dentro do desenho 3D da pá nesta etapa. O destaque
implementado é nos gráficos radiais e tabelas.

## Verificações

Script reproduzível: `checkpoints/distribuicao_radial_didatica_2026-11-10/verificar.py`,
executado a partir de `NEW` com o Python do ambiente do projeto.

- Seis conjuntos componente/caso: compressor e turbina manuais em π=8 com
  sete seções; automáticos em π=8 com três seções; automáticos em π=6 com
  quatro seções, incluindo uma malha sem seção exatamente no raio médio.
- Todos os campos, raios, produtos, referências, resíduos e percentuais
  comparados com os valores dos objetos de origem em cada estágio/seção.
- Maior |resíduo de r·Cθ| observado: **1,4210854715202004 × 10⁻¹⁴ m²/s**.
  É uma identidade numérica do modelo, não um erro experimental medido.
- Objetos serializados antes/depois: nenhuma mutação pela apresentação.
- Figuras de todas as grandezas geradas; coordenadas conferidas. Exemplos
  de difusão e de referência zero renderizados e inspecionados visualmente.
- Referência nula na primeira entrada do bocal tratada sem divisão por zero;
  percentual ausente e renderização do traço conferidos.
- Valor radial não finito representado como lacuna, sem conexão artificial.
- AppTest aprovado: estágio 8 do compressor, seção tip/hub, tabela de DF,
  tabelas de constantes e referência zero na turbina. Troca de sete para três
  seções com seleção anterior r5 reiniciada para uma seção existente, sem erro.
- Avisos e potência do caso manual preservados; consulta aos controles não
  modifica os modelos. Recalculo automático e sensibilidade sem exceções.

Evidências em `dados.json`, `interface.json`, `interface.log` e figuras `.png`
na pasta de checkpoint. AppTest não substitui inspeção visual completa no
navegador nem validação física ou experimental.

## Retorno

O checkpoint preserva `streamlit_app.py` e a matriz de rastreabilidade, com
caminhos relativos e hashes SHA-256 em `manifesto.json`. Para voltar, encerrar
o Streamlit e copiar esses dois arquivos para os caminhos correspondentes em
`NEW/engine/`. Os novos `webapp/radial_distribution.py` e este relatório podem
ser removidos após a restauração, se desejado. Não é necessário resetar o Git.
