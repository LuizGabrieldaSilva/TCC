# Padronização numérica da interface — 12/11/2026

Autorização: concluir a apresentação com vírgula decimal nos modos Guiado e Técnico. O formulário aprovado foi mantido.

## Abrangência

- Indicadores do ciclo e das turbomáquinas, ψ solicitado/efetivo, razões de pressão, textos do percurso do fluido e referência da sensibilidade.
- Tabelas do ciclo, combustor, estágios, anular, áreas, perfis, triângulos, candidatos e diagnósticos.
- Números dimensionais, percentuais, valores pequenos em notação científica, resíduos e anotações.
- Eixos de gráficos Matplotlib, inclusive os dois eixos de sensibilidade e os eixos da geometria 3D. Rótulos radiais fixos conservam as seções e usam vírgula nos raios.
- Eixos e tooltips dos gráficos interativos: configuração de locale numérico do Vega, sem converter dados em strings.
- Mensagens de verificações e de erro: conversão apenas na vista da mensagem, preservando o conteúdo original nos resultados e arquivos técnicos.

`engine/webapp/number_format.py` concentra as funções de apresentação. As interpolações preservam a precisão e o tipo de notação originalmente solicitados em cada ponto. Os locais que já usavam `_numero_br` mantêm essa função e seus separadores de milhares. Tabelas novas usam uma vista Styler; números pequenos usam notação científica para não serem apresentados como zero. Tabelas com estilos/precisão próprios conservam essas definições e recebem a convenção decimal apropriada.

O conteúdo numérico de DataFrames, perfis e modelos não é convertido. IDs dos avisos, índices, ordenação, expressões numéricas do Vega e formatos técnicos de entrada/exportação continuam com seus tipos e convenções originais. Citações como Eqs. 3.34–3.35 e nomes de arquivos não são reescritos como se fossem números decimais. A conversão textual de mensagens não é aplicada indiscriminadamente a parágrafos ou bibliografia.

## Verificação

Da pasta `NEW`:

```powershell
python -X utf8 ../checkpoints/virgula_interface_completa_2026-11-12/verificar.py
```

O verificador confere números fixos, percentuais e científicos; preservação do DataFrame e dos pontos de um gráfico; locale e preservação do gráfico Altair original. Compara por AST o pipeline, inicialização de etapas e argumentos das chamadas de download com a cópia anterior.

AppTest confere métricas e tabelas formatadas, HTML do combustor, referências bibliográficas preservadas, alternância para Técnico sem modificar o caso, vistas tabulares adicionais e renderizadores interativos. Compara avisos e potência manual com a evidência anterior e a seleção automática dos dois componentes com sua referência. Os avisos originais e seus IDs permanecem disponíveis para as exportações; a localização é apenas de apresentação.

Evidências em `checkpoints/virgula_interface_completa_2026-11-12/resultado.json`, `interface.log` e `eixos.png`. `interpolacoes.json` registra 71 pontos de interpolação numérica tratados. A migração editorial usa AST para identificar formatos e altera apenas esses pontos de apresentação e suas chamadas de renderização.

Limite: teste automatizado do Streamlit, validação do esquema Vega e inspeção de imagem Matplotlib; não é captura do navegador completo nem validação física ou experimental. CSV, JSON, DXF e outros formatos técnicos não recebem separadores brasileiros nesta tarefa.

## Checkpoint e reversão

`checkpoints/virgula_interface_completa_2026-11-12/manifesto.json` contém as cópias anteriores dos módulos web e hashes. `arquivos_depois.json` identifica os fontes finais. Para reverter, restaurar os módulos alterados a partir dessas cópias e remover `engine/webapp/number_format.py` e este relatório. Comparar eventuais alterações posteriores antes de restaurar arquivos antigos. Nenhum módulo de cálculo, exportador ou política de escolha de estágios foi alterado.
