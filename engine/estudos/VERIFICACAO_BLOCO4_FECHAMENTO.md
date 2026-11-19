# Bloco 4 — fechamento ciclo–meanline e áreas por estação

Implementação autorizada e verificada em 06/11/2026.

## Resultado e alcance

Foram acrescentados diagnósticos de leitura dos resultados, painéis condicionais na interface e exportação JSON. Não foram alterados os solvers, as entradas de referência, os critérios físicos, a geometria ou os resultados existentes. O modo manual continua respeitando número de estágios e coeficiente de carga informados pelo usuário.

Os painéis comparam temperaturas e pressões totais de saída, trabalhos específicos, potências e interfaces entre componentes. A convenção é calculado menos alvo. As tolerâncias `rel_tol=1e-9` e `abs_tol=1e-7` em unidades SI servem para reconhecer igualdade numérica; não representam tolerâncias de aceitação de projeto. Uma diferença inferior ao antigo limiar de aviso de 2% continua sendo uma diferença e agora fica visível.

## Caso de referência manual

| Grandeza | Ciclo | Meanline | Diferença |
| --- | ---: | ---: | ---: |
| Potência consumida pelo compressor | 4575,338748 kW | 4592,790695 kW | +17,451948 kW |
| Potência produzida pela turbina | 6808,578388 kW | 6808,577882 kW | −0,000506 kW |
| Potência líquida | 2233,239640 kW | 2215,787186 kW | −17,452454 kW (−0,781486%) |

No compressor, a temperatura total de saída excede o alvo em 1,157675 K e a pressão total em 4,574093 kPa (+0,571762%). A pequena diferença da turbina também aparece: o valor manual de psi tem precisão finita e não fecha exatamente o alvo.

O trabalho do compressor é referido a kg de ar; o da turbina, a kg de gases, incluindo combustível. As potências usam as vazões de cada componente antes da subtração. Não se subtraem diretamente trabalhos com bases mássicas distintas para calcular a potência líquida.

O combustor continua recebendo as condições de saída do compressor estabelecidas pelo ciclo. Não foi substituída silenciosamente essa entrada pelo resultado meanline manual. A discrepância é exposta na interface compressor–combustor. No modo automático, os alvos coincidiram dentro das tolerâncias numéricas nos casos verificados. Para fechar o caso manual será necessário escolher o modo automático ou autorizar um ajuste dos parâmetros manuais; este bloco não faz esse ajuste.

## Áreas e hipóteses

As áreas necessárias nas estações locais 1 (entrada) e 3 (saída) são calculadas por continuidade, com propriedades estáticas meanline:

```text
T = Tt − C²/(2 cp)
P = Pt (T/Tt)^[k/(k−1)]
rho = P/(R T)
A = m_dot/(rho Cx)
```

Mantêm-se gás ideal e propriedades constantes do modelo. O cálculo não integra a distribuição radial de densidade.

Na estação 2, a temperatura total é conhecida pelo trabalho do rotor ou pela ausência de trabalho no bocal. Entretanto, o modelo não reparte a perda total de pressão entre as fileiras. Por isso, Pt2, pressão estática, densidade e área não são determinadas. A interface mostra essa ausência, os CSVs deixam os campos correspondentes vazios e o JSON utiliza `null`. Nenhuma interpolação de pressão foi introduzida.

A geometria CAD continua usando a área representativa de entrada de cada estágio. A área exigida na saída é um diagnóstico, sem reconstrução do anular ao longo das fileiras. Uma opção adicional mostra o desvio de vazão que ocorreria **se** a área representativa fosse imposta também na saída: trata-se de uma hipótese geométrica condicional, não de um erro de conservação de massa observado no solver.

As interfaces consecutivas de cada máquina são comparadas em Tt, Pt, Cx, Ctheta e área. Coincidência entre os alvos termodinâmicos não valida uma transição física compressor–combustor: o difusor, a continuidade geométrica desse trecho e seu balanço de quantidade de movimento continuam fora do modelo.

## Interface e arquivos

- Aba Ciclo: expander de fechamento global e seleção da interface entre componentes.
- Abas Compressor e Turbina: comparação com o ciclo e áreas por estação, com seleção do estágio.
- Aba Downloads: `diagnosticos_integracao.json`.
- CSV do compressor: adicionados área de saída, Pt2, A2 e estado da determinação da estação 2.
- CSV da turbina: preservada a área de saída existente e adicionados Pt2, A2 e estado da estação 2.
- Implementação independente em `engine/diagnosticos.py`, sem modificar os objetos calculados.

## Verificações executadas

1. `verificar_diagnosticos`: oito casos, com razão de pressão 8 manual e 6/8/12 automática, em três e sete seções radiais. Foram conferidos os resíduos, as bases mássicas, a continuidade, os valores ausentes e a serialização JSON estrita. Comparações dos objetos serializados antes/depois confirmaram ausência de mutação pelos diagnósticos.
2. Regressão antes/depois com `verificar_acoplamento`: oito casos aprovados, preservando estados, áreas existentes, velocidades, triângulos e estágios.
3. Exemplo de saída do compressor de Saravanamuttoo, páginas impressas 210–211: Tt=452,5 K, Pt=419 kPa, Cx=150 m/s, sem swirl e vazão 20 kg/s. Área obtida de 0,044018807 m², compatível com aproximadamente 0,0440 m² do exemplo. A comparação de área admite 0,0001 m² devido aos dados arredondados; não constitui reprodução integral do projeto do livro.
4. Streamlit AppTest: referência manual, ambos os componentes automáticos, vazão alterada para 16 kg/s, seleção de estágio e diagnóstico geométrico condicional; sem exceções. Exportações CSV e JSON foram conferidas. As curvas de sensibilidade da execução com 16 kg/s não registraram casos inválidos.
5. Análise sintática dos arquivos Python do engine aprovada.

Os testes da interface foram programáticos; não houve inspeção visual em navegador nesta etapa. Não foram repetidas as verificações completas de perfis/DXF, pois o bloco não altera seus cálculos. Sucesso nos testes não equivale a validação experimental ou física completa.

Comandos executados a partir de `NEW`:

```powershell
python -X utf8 -m engine.estudos.verificar_diagnosticos --saida ../checkpoints/bloco4_fechamento_2026-11-06/diagnosticos_depois.json
python -X utf8 -m engine.estudos.verificar_acoplamento --antes ../checkpoints/bloco4_fechamento_2026-11-06/antes.json --saida ../checkpoints/bloco4_fechamento_2026-11-06/regressao_depois.json
```

## Checkpoint e reversão

Checkpoint: `checkpoints/bloco4_fechamento_2026-11-06/`. O manifesto registra SHA256 das cópias anteriores de `NEW/engine/webapp/streamlit_app.py` e `NEW/engine/estudos/export_csv.py`. Para reverter a integração deste bloco, copie esses dois arquivos do checkpoint para os mesmos caminhos no projeto. Os arquivos novos de diagnóstico, verificação e relatório podem permanecer sem uso; não são necessários à versão restaurada. Os resultados antes/depois e as exportações verificadas estão no checkpoint.

## Próxima etapa proposta

Bloco 5: esclarecer as definições dos indicadores, especialmente a eficiência referida ao calor útil transferido e a eficiência referida ao PCI, além das origens e interpretações dos critérios. Nenhuma mudança desses indicadores foi realizada neste bloco.
