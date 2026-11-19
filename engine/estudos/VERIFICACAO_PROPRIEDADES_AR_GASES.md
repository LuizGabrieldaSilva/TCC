# Propriedades constantes distintas para ar e gases

**Registro do modo prescrito.** O padrão da interface foi posteriormente ampliado para composição automática; consulte [Verificação da mistura](VERIFICACAO_MISTURA_COMBUSTIVEIS.md). Os números e hipóteses abaixo continuam aplicáveis ao modo prescrito.

Implementação e conferência: **19/11/2026**. Checkpoint anterior: `checkpoints/propriedades_ar_gases_2026-11-19/`, na raiz do projeto. As evidências e os roteiros adicionais estão nessa pasta. Esta mudança altera a hipótese de propriedades do fluido; os resultados históricos com cp único não são a referência numérica da versão nova.

## Modelo adotado

| Fluido | cp (J/(kg K)) | R (J/(kg K)) | k = cp/(cp − R) |
|---|---:|---:|---:|
| Ar, compressor e entrada do combustor | 1005 | 287,142857 | 1,4 |
| Gases, saída do combustor e turbina | 1148 | 287,142857 | 1,333554597 |

São gases ideais caloricamente perfeitos por região: **não foi implementado cp(T)**. cp dos gases = 1148 é um valor nominal contextual de Saravanamuttoo, Cohen e Rogers, *Gas Turbine Theory*, exemplo 2.1, p. 75; não é uma propriedade universal de todos os combustíveis ou temperaturas. R dos gases igual a R do ar é uma hipótese explícita, ajustável. Não há cálculo de composição dos produtos. Os campos exigem `0 < R < cp`; k é derivado, evitando entradas independentes contraditórias.

O balanço aproximado do combustor usa a convenção de entalpias `h_ar = cp_ar T` e `h_gases = cp_gases T`, com origem convencional comum e sem entalpia sensível do combustível:

```
ma cp_ar T02 + mf eta_b PCI = (ma + mf) cp_gases TIT
f = mf/ma = (cp_gases TIT − cp_ar T02)/(eta_b PCI − cp_gases TIT)
```

Esta é uma convenção do balanço simplificado; não é um cálculo de entalpias de formação, equilíbrio químico, dissociação ou combustão real. A aproximação com propriedades distintas aparece, por exemplo, no exercício de Mattingly, *Elements of Gas Turbine Propulsion*, p. 816 (PDF 881).

`Q_total` foi preservado por compatibilidade, mas identificado como **aquecimento virtual do ar**: `ma cp_ar (TIT − T02)`. Ele omite a mudança de propriedades e a massa de combustível; não fecha o balanço do combustor nem é o denominador das eficiências. O balanço efetivo compara `mf eta_b PCI` com `(ma + mf) cp_gases TIT − ma cp_ar T02`.

## Propagação e apresentação

- Compressor usa ar; combustor usa ar na entrada e gases na saída; turbina e seus cálculos radiais, Mach, áreas e geometria usam gases.
- Ciclo, indicadores e diagnósticos usam os trabalhos e vazões correspondentes. Sensibilidade recebe as propriedades da execução submetida; o baseline consulta o caso vigente.
- Formulário permite alterar cp e R de cada fluido. Tabelas, comparação de projetos, CSVs e relatório registram essas propriedades; os cálculos internos permanecem numéricos.
- Arquivo de entradas passa à versão 2. Importar versão 1 restaura explicitamente o cp único e R daquele arquivo, mantendo a hipótese antiga. A interface informa essa migração.
- Para compatibilidade da API, `CicloBrayton(cp=..., k=...)` continua descrevendo ar; omitir `cp_gases` mantém cp único. O caso de referência atual fornece os parâmetros dos gases explicitamente.
- T–s usa origens independentes: ar relativo a 01; gases relativo a 03. Não se traça uma conexão de entropia entre os dois fluidos, porque reação/mistura não são resolvidas. P–v continua sendo uma representação esquemática de estados totais equivalentes, sem interpretar sua área como trabalho líquido.

## Efeito no caso manual de referência

Mesmas entradas de operação, 8 estágios do compressor e 3 da turbina; ψ e a política de seleção automática não foram reajustados.

| Resultado do ciclo | cp único anterior | cp distintos |
|---|---:|---:|
| Potência líquida (kW) | 2.233,24 | 2.447,36 |
| Temperatura de saída da turbina (K) | 754,84 | 799,71 |
| Razão combustível/ar (kg/kg) | 0,01456244 | 0,01880934 |
| Eficiência sobre calor útil (%) | 24,13 | 20,47 |
| Eficiência sobre PCI (%) | 23,89 | 20,27 |
| SFC (kg/kWh) | 0,35212 | 0,41502 |

**O caso manual não fecha exatamente o ciclo.** Mantendo ψ = 1,198736 e 3 estágios, a turbina meanline passa a ter razão de expansão aproximadamente 7,187, frente ao alvo 7,6. A potência líquida da soma dos meanlines é aproximadamente **2.272,23 kW**, frente a **2.447,36 kW** no ciclo. A interface mostra os desvios; não foi feito ajuste silencioso de ψ ou de estágios. O modo automático redistribui a carga para atender ao alvo e mantém a prioridade de candidatos já existente, pendente de discussão com o professor.

Os novos resultados não são uma comprovação de maior precisão experimental. São resultados de outra hipótese de propriedades, cuja adequação ao escopo deve constar do TCC.

## Conferências

Executar em `NEW`, com o Python do ambiente do projeto:

```powershell
python -m engine.estudos.verificar_propriedades_ar_gases --saida propriedades.json
```

O roteiro verifica balanço de massa e energia, Euler nas seções radiais, relação entre eficiências, propriedades e entropias por fluido, preservação do caso legado, importação/exportação e rejeição de propriedades inválidas. O exemplo de Mattingly, com cp_ar = 1004 e cp_gases = 1235, retorna f = 0,03453418, cerca de 0,19% abaixo do valor impresso 0,0346, compatível com seu arredondamento.

Também foram executados os verificadores de acoplamento, combustor, estágios de turbina, diagnósticos, indicadores, geometria/perfis, entradas e importações. A conferência funcional Streamlit via AppTest abrange o caso padrão, propriedades personalizadas, diagramas, CSV, ZIP do relatório e recusa de entrada inválida. Isso não substitui inspeção visual no navegador nem validação física experimental.

**Pendência anterior preservada:** a bateria histórica de exemplos dos livros continua com 28 de 29 comparações aprovadas; β2 no cubo do exemplo Dixon 6.1 difere da tolerância adotada devido ao dado angular aproximado usado na comparação. A tolerância não foi relaxada. O [relatório dos exemplos](COMPARACAO_EXEMPLOS_LIVROS.md) conserva a identificação histórica de 18/11; os números antigos com cp único não devem ser apresentados como resultados atuais.
