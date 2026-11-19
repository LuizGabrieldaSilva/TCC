# Modos de leitura e formulário — 12/11/2026

Implementação do bloco 1 do agrupamento aprovado, com base nas seções 2 e 3 de `Ideias_Interface_Didatica.md`. A mudança é de apresentação.

## Uso e comportamento

O controle **Nível de detalhe**, no início da barra lateral, oferece **Guiado** (padrão) e **Técnico**. O modo não integra os parâmetros do caso, não dispara o pipeline e não substitui o botão de cálculo.

Guiado acrescenta orientações curtas em cada um dos seis grupos de resultados: objetivo, percurso recomendado e cuidado de interpretação. Esses guias são recolhíveis. No ciclo, há uma interpretação numérica da eficiência sobre calor útil e do BWR usando os resultados da execução atual, distinguindo seus significados.

Técnico retira essas orientações introdutórias e permite consulta direta aos mesmos resultados. Equações, dados intermediários, métodos, resíduos, avisos e hipóteses continuam nos painéis existentes e ficam disponíveis nos dois modos. Os avisos e limitações existentes não foram ocultados nem seus critérios modificados.

O formulário tem três grupos recolhíveis, inicialmente abertos:

1. Condições de operação: entrada de ar, razão de pressão, TIT, vazão e combustível.
2. Escolhas de projeto: eixo único, compressor, turbina e discretização radial.
3. Hipóteses e parâmetros do modelo: eficiências, limite de temperatura adotado, Mach prescrito e perda de pressão do combustor, com indicação das hipóteses fixas.

Campos usam a largura da barra lateral e nomes por extenso junto aos símbolos. Os rótulos são os mesmos nos dois modos para manter a identificação consistente; o Técnico remove a orientação extra, não abrevia os nomes novamente. Tooltips, limites, passos, valores de referência e condições dos campos foram preservados. Foram acrescentadas chaves explícitas aos campos que ainda dependiam de identidade automática.

## Verificação reproduzível

Da pasta `NEW`:

```powershell
python -X utf8 ../checkpoints/modos_leitura_2026-11-12/verificar.py
```

A comparação por AST confere os argumentos de 38 campos da interface, excluindo apenas rótulos e chaves. Confere também igualdade das definições do pipeline e da inicialização dos estados de execução.

AppTest verifica o caso manual de referência e seus avisos contra a evidência anterior; os seis guias no Guiado e sua ausência no Técnico; preservação de entradas modificadas e do caso calculado ao alternar modos; aplicação das entradas somente na submissão; igualdade da seleção automática com a evidência anterior; eixo comum e ausência de falha na sensibilidade. Evidências finais em `resultado.json` e `interface.log` no checkpoint.

A verificação de entradas ainda não submetidas refere-se ao comportamento no AppTest. A organização visual completa deve ser conferida na largura do navegador do usuário; não foi feita uma captura do navegador nesta tarefa. Os testes são de regressão e apresentação, sem constituir validação física ou experimental do modelo.

## Arquivos e reversão

- Alterado: `NEW/engine/webapp/streamlit_app.py`.
- Novo: `NEW/engine/webapp/reading_mode.py`.
- Checkpoint: `checkpoints/modos_leitura_2026-11-12/manifesto.json`, com cópia anterior e SHA256.

Para reverter esta tarefa, restaurar o Streamlit dessa cópia e remover o novo módulo de leitura e este relatório, comparando eventuais alterações posteriores antes de restaurar. Nenhum arquivo de cálculo ou critério físico foi modificado. A prioridade de candidatos continua aguardando a decisão com o professor.
