# Matriz de rastreabilidade teórica e numérica

**Atualização em 19/11/2026 — propriedades por fluido:** ver [cp constantes distintos para ar e gases](VERIFICACAO_PROPRIEDADES_AR_GASES.md). A hipótese mudou no caso de referência; as evidências históricas abaixo conservam seus parâmetros e não são snapshots do novo modelo. O novo relatório identifica balanço, convenção de entalpia, compatibilidade legada e desvios do caso manual.

**Atualização em 11/11/2026 — perfil 2D:** acrescentada a [visualização didática dos perfis calculados](VERIFICACAO_PERFIL_2D_DIDATICO.md), com camadas, orientação pelo stagger, distribuição de espessura e comparação radial. Apenas apresentação de coordenadas existentes; modelos e prioridade de seleção preservados. Evidências em `checkpoints/perfil_2d_didatico_2026-11-11/`.

Consolidada em **06/11/2026**, após os cinco blocos de correção e os refinamentos de apresentação. Escopo: versão dos arquivos identificada pelos hashes da pasta de evidências. Os parâmetros do caso de referência e os modelos físicos não foram modificados nesta consolidação.

**Atualização posterior em 06/11/2026:** foi implementada a [seleção automática entre estágios vizinhos](VERIFICACAO_SELECAO_ESTAGIOS.md). Ela substitui o antigo arredondamento sempre para cima e pode alterar os casos automáticos. As evidências E1–E7 abaixo continuam identificando a versão da consolidação original; não são snapshots da nova política. A nova bateria e as decisões estão em `checkpoints/selecao_estagios_2026-11-06/`. O caso manual foi preservado. As prioridades da seleção são escolhas explícitas do projeto, não uma certificação física.

**Atualização em 09/11/2026:** foi concluída a [validação de entradas e fronteiras numéricas](VERIFICACAO_ENTRADAS.md), iniciada em 08/11. π=1 é recusado explicitamente; razões próximas da unidade recebem avaliação estável das mesmas relações. Foram acrescentadas validações das APIs e de ordem de chamadas, preservando os resultados de regressão e a política de seleção. Evidências em `checkpoints/validacao_entradas_2026-11-08/`.

**Centralização em 09/11/2026:** os avisos, índices dos candidatos, metadados e apresentações principais passaram a consultar `design_criteria.py`, preservando os valores, alcances e prioridades. Ver [verificação dos critérios centralizados](VERIFICACAO_CRITERIOS_CENTRALIZADOS.md) e evidências em `checkpoints/criterios_centralizados_2026-11-09/`.

**Importações em 09/11/2026:** os exemplos passaram a exigir execução explícita, sem cálculos ou exportações durante importações. Foram preservados os estados dos exemplos, as definições físicas e a política de seleção. Ver [verificação das importações e execuções diretas](VERIFICACAO_IMPORTACOES.md).

**Apresentação em 09/11/2026:** foram revistas as legendas e explicações dos critérios e substituídas as contagens fixas dos scripts auxiliares pelos valores dos objetos executados. Foram corrigidas as falsas divergências do teste de loft com quatro estágios na turbina. Cálculos, limites e prioridades foram preservados. Ver [verificação das legendas, explicações e contagens](VERIFICACAO_LEGENDAS.md), com evidências em `checkpoints/revisao_legendas_2026-11-09/`.

**Didática em 10/11/2026:** implementada a comparação entre estágios, distinguindo meanline e extremos radiais, com seletor para consultar tabela e geometria de um estágio por vez. Dados, cálculos e escolhas foram preservados. Ver [verificação da comparação entre estágios](VERIFICACAO_COMPARACAO_ESTAGIOS.md). A prioridade da seleção automática permanece como está, aguardando discussão do autor com o professor.

**Distribuição radial didática em 10/11/2026:** acrescentados gráficos por raio, seleção de seção e conferência de `r·Cθ` contra o meanline, usando o estágio em foco. A relação de vórtice livre é identificada como hipótese imposta; a referência zero não produz percentual inválido. Modelos, critérios e prioridades foram preservados. Ver [verificação do painel radial](VERIFICACAO_DISTRIBUICAO_RADIAL_DIDATICA.md) e evidências em `checkpoints/distribuicao_radial_didatica_2026-11-10/`.

**Balanço visual em 11/11/2026:** acrescentado gráfico em cascata da produção da turbina, consumo do compressor e potência líquida do ciclo, com valores, vazões e bases de massa explícitos. Resultados e prioridades foram preservados. Ver [verificação do balanço energético visual](VERIFICACAO_BALANCO_ENERGETICO_VISUAL.md) e evidências em `checkpoints/balanco_energetico_visual_2026-11-11/`.

## 1. Como interpretar esta matriz

Esta matriz relaciona implementação, fundamento, hipótese, evidência e limitação. **Uma identidade numérica satisfeita não prova desempenho real, estabilidade ou adequação para fabricação.** A conformidade é parcial e delimitada pelas hipóteses de cada linha.

- **N:** verificação numérica reexecutada nesta consolidação.
- **H:** comparação ou consulta bibliográfica histórica, registrada na revisão anterior; não significa nova leitura do PDF nesta tarefa.
- **A:** escolha/hipótese adotada no projeto, explicitamente identificada; não é exigência universal do livro.
- **P:** evidência, decisão ou validação ainda pendente.

As referências e páginas abaixo foram consolidadas dos relatórios anteriores. A revisão dos cinco livros foi de trechos pertinentes, não uma leitura integral dos volumes. Onde não existe localizador preciso confirmado, a lacuna foi mantida. Não se inventou equação, página ou tolerância atribuída à literatura.

O parecer de 05/11 foi preservado como [registro histórico](../../../checkpoints/matriz_rastreabilidade_2026-11-06/REVISAO_HISTORICA_2026-11-05.md). Ele contém problemas que já foram corrigidos: **não deve ser usado isoladamente como diagnóstico do código atual**. O estado atual é descrito nesta matriz e nos relatórios dos blocos.

## 2. Referências disponíveis e localizadores

Páginas PDF contadas a partir de 1; a numeração impressa pode ser diferente.

| ID | Livro local | Localizadores registrados na revisão anterior | Uso nesta matriz |
| --- | --- | --- | --- |
| S | [Saravanamuttoo, Cohen e Rogers — Gas Turbine Theory](<../../../GAS TURBINE THEORY BY HIH SARAVANAMUTTOO, H. COHEN & GFC ROGERS.pdf>) | Impressas 58/60/68 → PDF 75/77/85; exemplo 2.1, 74–76 → 91–93; 191–193 → 208–210; 201 → 218; 210–211 → 227–228; 265/273/275 → 282/290/292 | Ciclo, hipóteses de propriedades, difusão, área/anular, equilíbrio radial e combustão |
| D | [Dixon & Hall — Fluid Mechanics and Thermodynamics of Turbomachinery, 7ª ed.](../../../dokumen.pub_fluid-mechanics-and-thermodynamics-of-turbomachinery-7nbsped-9780124159549.pdf) | Carter, Eqs. 3.34–3.35/exemplo 3.1, impressas 86–87 → PDF 97–98; reação, Eq. 4.3a, 123 → 133; repetição, 125–127 → 135–137; exemplo 4.2, 134–139 → 144–149; exemplo 5.1, 178 → 187; exemplo 6.1, 218–221 → 227–230 | Carter, reação, triângulos, definições de raio, continuidade e vórtice livre |
| M | [Mattingly — Elements of Gas Turbine Propulsion](<../../../ELEMENTS OF GAS TURBINE PROPULTION2.pdf>) | Impressa 106/tabela 2-4 → PDF 171; 374–375 → 439–440; 632–633 → 697–698; 816/818 → 881/883; Eq. 10-34, 821 → 886; tabela 10-5, 822 → 887; tabela 10-6, 826 → 891 | Balanço com combustível, equivalência, difusão, escala do combustor e propriedades dos combustíveis |
| B | [Boyce — Gas Turbine Engineering Handbook, 2ª ed.](<../../../GAS TURBINE ENGINEERING HAND BOOK BY MEHERWAN P. BOYCE (2nd Edtion).pdf>) | Impressa 125 → PDF 141; 291–299 → 307–315; 371/373 → 387/389 | Eficiências, distribuição de trabalho, reação, equilíbrio radial e balanço do combustor |
| L | [Lakshminarayana — Fluid Dynamics and Heat Transfer of Turbomachinery](../../../pdfcoffee.com_fluid-dynamics-and-heat-transfer-of-turbo-machinery-pdf-free.pdf) | Impressas 49–50/Eqs. 2.4–2.12 → PDF 78–79; 63/Eq. 2.26 → 92; 79/82 → 108/111; 147–148 → 176–177; 300–304/Eqs. 4.97–4.100 → 329–333 | Euler, coeficientes, referenciais de velocidade, repetição e limites do equilíbrio radial simplificado |

Na revisão anterior, Lakshminarayana e partes de Boyce exigiram consulta por imagens; a camada textual não era suficiente. A consulta visual também foi registrada para Carter e a escala de Mattingly. Não se afirma que cada cálculo tenha sido comparado independentemente com todos os cinco livros.

## 3. Evidências numéricas atuais

Pasta: [checkpoints/matriz_rastreabilidade_2026-11-06](../../../checkpoints/matriz_rastreabilidade_2026-11-06/). Resultados JSON e logs conservam os valores em unidades numéricas; a formatação brasileira da interface não altera esses arquivos.

| ID | Verificador/evidência | O que demonstra | O que não demonstra |
| --- | --- | --- | --- |
| E1 | [Acoplamento](../../../checkpoints/matriz_rastreabilidade_2026-11-06/acoplamento.json), `verificar_acoplamento.py` | Oito casos: razão de pressão 8 manual e 6/8/12 automática, com 3 e 7 seções; Euler, raio, velocidades, áreas e comparação com a regressão do bloco 5 | Erro contra ensaio experimental ou estabilidade física |
| E2 | [Perfis](../../../checkpoints/matriz_rastreabilidade_2026-11-06/perfis.json), `verificar_geometria_perfis.py` | Exemplo de Carter, entradas inválidas, solidez e tangentes das curvas construídas em oito casos; alvos adicionais de solidez | Desvio aerodinâmico medido, ausência de colisões ou fabricação |
| E3 | [Combustor](../../../checkpoints/matriz_rastreabilidade_2026-11-06/combustor.json), `verificar_combustor.py` | Quatro combustíveis, balanço, escala JT9D, metadados de origem e PCI personalizado | Fonte bibliográfica confirmada de todas as constantes ou estabilidade da chama |
| E4 | [Estágios da turbina](../../../checkpoints/matriz_rastreabilidade_2026-11-06/estagios_turbina.json), `verificar_estagios_turbina.py` | Oito casos e dois adicionais: swirl herdado, reação geral, energia e Euler | Distribuição preditiva de perdas entre bocal e rotor |
| E5 | [Diagnósticos](../../../checkpoints/matriz_rastreabilidade_2026-11-06/diagnosticos.json), `verificar_diagnosticos.py` | Resíduos, áreas por estação, interfaces e valores ausentes; objetos não modificados pelos diagnósticos | Integração geométrica/quantidade de movimento do difusor ou throughflow |
| E6 | [Indicadores](../../../checkpoints/matriz_rastreabilidade_2026-11-06/indicadores.json), `verificar_indicadores.py` | 12 casos: duas vazões, três eficiências de combustão e dois combustíveis; bases energéticas e SFC | Eficiência elétrica, rendimento mecânico ou validação de uma instalação |
| E7 | [Sensibilidade](../../../checkpoints/matriz_rastreabilidade_2026-11-06/sensibilidade.json) e gráficos na mesma pasta | Varreduras de projeto nos modos manual/automático, inclusão do ponto de referência e compatibilidade dos indicadores | Mapa off-design de uma geometria fixa ou margem de surge |
| E8 | Relatórios dos blocos e prints fornecidos pelo autor | Evidência histórica de execução Streamlit, atualização dinâmica e apresentação dos painéis mostrados | Nova inspeção visual de todas as abas ou importação dos DXFs em CAD nesta consolidação |

As tolerâncias numéricas estão nos verificadores. Para igualdade dos diagnósticos, por exemplo, usam-se tolerâncias relativa de 1e-9 e absoluta de 1e-7 nas unidades SI; **não são tolerâncias de aceitação de projeto**. Comparações com números arredondados dos livros têm tolerâncias próprias, indicadas abaixo.

Resultado desta consolidação: os seis verificadores concluíram sem falhas. E2 conferiu 980 perfis nos oito casos, com erro máximo de tangente de aproximadamente 0,011589°, inferior ao limite de discretização de 0,02° adotado no teste. E7 executou 56 pontos em cada modo (112 avaliações) e gerou 12 gráficos por modo, totalizando 24. Não houve casos computacionalmente inválidos nessas varreduras; avisos e limitações físicas continuam aplicáveis. A comparação de hashes confirmou que os 53 arquivos Python de `engine` foram preservados.

## 4. Ciclo e indicadores globais

Implementação: [CicloBrayton.py](../ciclo/CicloBrayton.py), métodos `resolver` e `registrar_vazao_turbina`; [indicadores.py](../indicadores.py).

| ID / cálculo | Equação ou vínculo implementado | Referência | Hipóteses e evidência | Situação/limite |
| --- | --- | --- | --- | --- |
| C1 — compressão politrópica | T02/T01 = πc^[(k−1)/(k·ec)]; wc = cp·(T02−T01) | S, pp. 58–68 e exemplo 2.1; B, p. 125 | Gás ideal, cp/k e eficiência prescritos constantes. E1; H: T02=452,6663 K contra 452,7 K do exemplo parcial, tolerância 0,1 K | N/H. Não reproduz o recuperador ou todas as propriedades do exemplo |
| C2 — expansão politrópica | T04/T03 = (P04/P03)^[(k−1)·et/k]; wt = cp·(T03−T04) | S, pp. 58–68; B, p. 125 | Mesmo cp/k do ar e dos gases. E1/E4 | N/H. Não incorpora resfriamento, composição variável ou perdas de eixo |
| C3 — pressão e TIT | P02=πc·P01; P03=(1−ΔPcc)·P02; P04=P01; T03=TIT | S, p. 58 para a idealização de escape; restrições de entrada do projeto | Perda relativa e TIT prescritas; saída total equivalente à ambiente | A. Não representa um plano real com pressões estática e total ambas ambientes e velocidade finita; TIT não é limite universal de material |
| C4 — massa e potência | mg=ma+mf; Wlíq=mg·wt−ma·wc; wlíq,ar=(1+f)·wt−wc | Balanço de energia; S, análise de ciclos; M, balanço com massa adicionada | Transmissão ideal, sem sangria/acessórios. E1/E5/E6 | N/H. Bases específicas de ar e gás não podem ser subtraídas sem compatibilização |
| C5 — duas eficiências | ηútil=Wlíq/(mf·ηb·PCI); ηPCI=Wlíq/(mf·PCI)=ηb·ηútil | S, análise de ciclos; M, desempenho. Localizador específico das duas formas em uma mesma apresentação: P | Definições pelo balanço; denominadores explícitos. E6 | N/A/P bibliográfico. Não são duas previsões físicas diferentes; ηPCI não é eficiência elétrica |
| C6 — BWR e SFC | BWR=ma·wc/(mg·wt); SFC=3,6e6·mf/Wlíq, com W em watts | S, análise de desempenho; definição dimensional | E6 confere ηPCI=3,6e6/(SFC·PCI), PCI em J/kg | N. Identidade dimensional não valida o combustível real |

## 5. Meanline, velocidades e distribuição radial

Implementação: [compressor](../compressor/Compressor_Meanline_main.py), [turbina](../turbina/Turbine_Meanline_main.py), [radial do compressor](../aero/radial_compressor_4_main.py), [radial da turbina](../aero/radial_turbina_3_main.py), [anular](../aero/annulus_geometry.py) e [reação](../aero/reacao_turbina.py).

| ID / cálculo | Equação ou vínculo implementado | Referência | Hipóteses e teste | Situação/limite |
| --- | --- | --- | --- | --- |
| T1 — Euler | Compressor: w=U·(Cθ2−Cθ1); turbina: w=U·(Cθ2−Cθ3) no rotor | L, pp. 49–50, Eqs. 2.4–2.12; D, capítulos de máquinas axiais | Mesmo raio na entrada/saída do rotor simplificado. E1/E4 comparam com cp·ΔTt | N/H. Sem torque/perdas mecânicas medidos |
| T2 — coeficientes e estágios | φ=Cx/U; ψ=w_estágio/U²; ΔTt,estágio=ψ·U²/cp | L, p. 63, Eq. 2.26; B, pp. 291–292 | Trabalho uniforme por estágio, Cx e raio de referência constantes; modo automático redistribui carga após escolher N inteiro. E1 | N/A. Algoritmo de arredondamento é escolha do projeto, não equação universal de otimização |
| T3 — total/estático e Mach | T=Tt−C²/(2cp); a=√(kRT); M=C/a; Mrel=W/a | L, pp. 79/82; D, exemplo 5.1, p. 178 | Temperatura estática obtida com C absoluto, não substituindo C por W. E1/E5; H: U=208,2713 contra 208,3 m/s, tolerância 0,1 m/s | N/H. Choques e perdas transônicas não são resolvidos |
| T4 — triângulos e sinais | C=U+W; Wθ=Cθ−U; no compressor βmodelo=atan2(U−Cθ,Cx) | Euler/cinemática; L, pp. 49–50 e 79–82 | E1/E2 verificam componentes, módulos e conversão do ângulo geométrico do rotor para −βmodelo | N. Não confundir β armazenado com sinal geométrico global de W |
| T5 — vórtice livre | r·Cθ=rm·Cθm; U(r)=ωr | S, p. 201; D, pp. 218–221/exemplo 6.1; L, pp. 300–304, Eqs. 4.97–4.100 | Lei de projeto; Cx uniforme, simplificações de entalpia/entropia e curvatura. E1; H: comparação parcial do exemplo 6.1 | N/H/A. Não é solução geral de equilíbrio radial/throughflow |
| T6 — raio de referência | rm=(rt+rh)/2; h=A/(2πrm); rh=rm−h/2; rt=rm+h/2 | D, definições de raio nos trechos de máquinas axiais; S, exemplo de anular pp. 210–211 | rm aritmético constante por componente; HTR de entrada, demais HTR calculados. E1 | N. Distinguir do raio de áreas iguais √[(rt²+rh²)/2]; não impõe continuidade de linhas de corrente |
| T7 — repetição do compressor | Estator devolve o ângulo/velocidade tangencial de referência de entrada; carga uniforme | B, pp. 291–299; hipótese de estágio normal do projeto | E1/E5 recuperam interfaces meanline | N/A. Não há cálculo preditivo de incidência/perdas de cada estator ou IGV detalhado |
| T8 — encadeamento da turbina | Cθ1[i+1]=Cθ3[i]; Tt1[i+1]=Tt3[i]; Pt1[i+1]=Pt3[i] | D, pp. 125–127; L, pp. 147–148 | Primeiro bocal axial; demais recebem swirl anterior. E4/E5 | N/H. Transferência radial comparada no mesmo raio físico; hub/tip de anulares distintos não são a mesma linha de corrente |
| T9 — reação estática da turbina | R=(h2−h3)/(h1−h3)=[w+(C3²−C2²)/2]/[w+(C3²−C1²)/2] | D, Eq. 4.3a, p. 123/PDF 133 | Velocidades absolutas e reação local; E4 por temperaturas estáticas e Euler | N/H. A razão antiga queda estática do rotor/trabalho de eixo permanece diagnóstico distinto; coincide com R quando C1²=C3² |
| T10 — área por plano | P=Pt·(T/Tt)^[k/(k−1)]; ρ=P/(RT); A=m/(ρCx) | Continuidade e gás ideal; D, Eq. 4.23 (página exata a confirmar); S, pp. 210–211 | Condições meanline, sem integração radial. E1/E5 e equivalência à função de vazão compressível | N/H/P localizador. Pt e área da estação 2 não determinados: perdas entre fileiras não repartidas |
| T11 — anular usado no CAD | Área representativa de entrada de cada estágio | Escolha geométrica do projeto, explicitada no bloco 4 | E2 verifica raios efetivamente construídos; E5 compara área requerida na saída | A/N/P. Não é anular exato em todos os planos. Impor a mesma área na saída é apenas diagnóstico condicional |

## 6. Combustor e constantes

Implementação: [Combustor_1D_2_main.py](../combustor/Combustor_1D_2_main.py), métodos `resolver` e `fontes_combustivel`.

| ID / cálculo | Equação ou vínculo implementado | Referência | Hipóteses e teste | Situação/limite |
| --- | --- | --- | --- | --- |
| B1 — combustível/ar | f=cp·(TIT−T02)/(ηb·PCI−cp·TIT) | M, Eq. 7-9 e exemplo p. 816; B, Eq. 10-1, trechos pp. 371/373 | Balanço global com combustível na massa de saída, cp único e sem termo sensível explícito do combustível. E3/E6 | N/H. Exemplo original com cp_ar diferente de cp_gás não pode ser reproduzido integralmente com cp único |
| B2 — equivalência | φeq=f/festeq; mg=ma+mf | M, pp. 816/818; B, balanço de combustão | Composição representada pelo catálogo. E3 | N/A. Equivalência global não é equivalência da zona primária nem critério completo de estabilidade |
| B3 — calor e aproximação do ar | Qútil=mf·ηb·PCI; Q_ar,aprox=ma·cp·(TIT−T02) | Especialização do balanço B1 | E3/E6 conferem energia com massa adicionada e distinguem as duas grandezas | N. Não somar Q_ar,aprox a Qútil nem interpretar sua diferença como nova fonte de calor |
| B4 — entrada e seção | A pela função de vazão compressível com Mach prescrito; D_eq=√(4A/π) | Relações de gás ideal/continuidade; M, capítulo de combustores | Entrada aproximadamente axial; Mach padrão 0,05. E3/E5 | A/N/P. Área circular equivalente, sem projeto de difusor, recirculação ou passagem anular real |
| B5 — comprimento | L=Lref·(P02/Pref)^−0,714·√(Tref/TIT) | M, Eq. 10-34 p. 821/PDF 886; tabela 10-5 p. 822/PDF 887 | Escala JT9D: Lref=0,4394 m, Pref=2179 kPa, Tref=1592 K. E3 | N/H/A. Usa pressão de entrada da câmara; assume semelhança e condições de garganta/área que o programa não comprova |

Rastreabilidade das constantes, sem atribuição genérica de todo o catálogo a uma tabela:

| Propriedade | Valor atual | Origem/hipótese | Situação |
| --- | --- | --- | --- |
| JP-4, PCI/festeq | 42,8 MJ/kg; 0,0667 | M, exemplo p. 816/PDF 881 | H/N, conferidos em E3 |
| JP-8, PCI | 43,2 MJ/kg | Nominal próximo do típico de M, tabela 10-6 p. 826/PDF 891: 10.333 cal/g → 43,233272 MJ/kg | H/N. Não caracteriza todo lote |
| JP-8, festeq | 0,0667 | Adotado por aproximação ao JP-4 | A/P, sem confirmação específica nessa tabela |
| Gás natural, PCI | 50,0 MJ/kg | Nominal adotado, sem fonte específica confirmada | A/P; depende da composição |
| Gás natural, festeq | 0,0580 | Metano equivalente; 4 kg O₂/kg CH₄ e fração mássica de O₂ no ar de 0,232 | A/N; não prova composição de gás natural real |
| Diesel, PCI/festeq | 42,5 MJ/kg; 0,0664 | Nominais adotados, composição/fonte específica não confirmadas | A/P |

## 7. Perfis, geometria e exportações

Implementação: [airfoil4.py](../geometry/airfoil4.py), [cascade_geometry.py](../aero/cascade_geometry.py), [loft2.py](../geometry/loft2.py), [export_dxf.py](../cad/export_dxf.py) e [export_csv.py](export_csv.py).

| ID / cálculo | Relação implementada | Referência | Hipóteses e teste | Situação/limite |
| --- | --- | --- | --- | --- |
| G1 — Lieblein e Z | Solidez invertida do DF alvo; arredondamento para número inteiro de pás; DF recalculado | S, pp. 191–193; M, pp. 374–375; D, exemplo 3.1 | Cascata de compressor. E1/E2; H: DF=0,4040689 contra 0,404 no exemplo | N/H. Limite 0,6 é triagem empírica; efeitos de ponta/choques não estão modelados |
| G2 — solidez local | s=2πr/Z; σlocal=c/s | Definição geométrica de cascata, D/S | Z e corda constantes em cada fileira. E2 nos perfis efetivamente gerados | N. Valor alvo meanline e valor construído após arredondamento não são idênticos em todo raio |
| G3 — Carter fechado | aC=m·√(s/c); θ=(γ1,metal−γ2,escoamento)/(1−aC); δ=aC·θ | D, Eqs. 3.34–3.35 e exemplo 3.1, pp. 86–87 | Arco circular, a/c=0,5; m=0,23+0,002·|γ2|, ângulos em graus. E2 | N/H. Correlação de compressor; não transferida à turbina; a entrada metálica do exemplo é fornecida para isolar a incidência não nula do livro |
| G4 — incidência e desvio | Incidência imposta zero; turbina com desvio zero; compressor com Carter | Escolhas do projeto; D sustenta a distinção entre escoamento e metal | E2 confere sinais e tangentes no loft real | A/N. Não demonstra que escoamento real seguirá a linha metálica |
| G5 — câmber, espessura e loft | Arco circular, espessura parabólica, rotação pelo stagger e transformação cilíndrica/cartesiana | Construção paramétrica do projeto, sem reivindicar perfil ensaiado de um livro | E2 verifica finitude, raios, solidez e erro angular de discretização | A/N/P. Sem garganta/bloqueio preditivos, CFD, colisões completas, resistência ou bordos construtivos |
| G6 — AR e espaçamento | AR=h/c verdadeira; folga axial geométrica prescrita | Escolha do projeto. D, p. 135, usa discussão com corda axial: definições não intercambiáveis | E2 verifica coerência da geometria gerada | A/P. Não atribuir faixa baseada em corda axial à corda verdadeira sem conversão |
| G7 — CSV/DXF/STEP | CSV deriva dos objetos; DXF leva curvas do loft; STEP permanece limitado | Implementação de software, não equação física dos livros | H/E8: exportações e entidades conferidas nos blocos anteriores | P para importação CAD, sólido STEP e fabricação. Não foram repetidos esses testes de exportação nesta consolidação |

## 8. Sensibilidade, interface e critérios

| ID | Comportamento | Evidência/hipótese | Situação/limite |
| --- | --- | --- | --- |
| I1 | Referência da execução vem de `reference_case.py` e dos parâmetros submetidos | E7; testes de interface registrados nos blocos 4/5 | N/H. Alterar o formulário exige recalcular; não grava mudanças de sessão nos padrões do arquivo |
| I2 | Varredura muda um parâmetro de projeto e reconstrói a máquina | E7; carga/estágios podem mudar no automático | N/A. Não é off-design de uma máquina fixa; patamares/saltos podem decorrer de N ou Z inteiros |
| I3 | CLI e Streamlit precisam do mesmo modo e entradas para produzir a mesma curva | E7 executa ambos os modos separadamente; experiência documentada pelo autor | N/H. Não se exige igualdade de curvas manual versus automática |
| I4 | Gráficos de DF/Mach/reação usam métricas meanline especificadas pelo estudo | Código `sensibilidade.py`; E7 | A. Não interpretar máximo meanline como máximo de todas as seções radiais |
| I5 | Mach=1 define condição sônica; limites de 1,0/1,3 são avisos por contexto | L/D; `constraints.py`; relatório bibliográfico | H/A/P. Modelo não calcula choques; Mach pouco acima de 1 não prova impossibilidade da máquina |
| I6 | Faixas de reação, swirl, equivalência e diferença de 2% são triagens adotadas | `constraints.py` e verificações meanline; E1/E4/E5 | A. Sem aviso não significa fechamento exato, ausência de estol ou estabilidade da chama |
| I7 | Diagramas P–v/T–s usam estados totais equivalentes e segmentos esquemáticos | `webapp/cycle_diagrams.py`; prints do autor | A/H. Não representam trajetória interna real; área do P–v não é apresentada como trabalho do motor |

Pendência editorial: alguns gráficos genéricos ainda usam o texto **“Faixa recomendada (literatura)”** para bandas que precisam ser vinculadas ao critério/contexto específico. O novo painel de critérios esclarece o alcance, mas não substitui uma revisão de todas as legendas. Nenhuma legenda foi alterada nesta tarefa documental.

## 9. Comparações com números publicados

| Comparação | Valor calculado / publicado | Tolerância e alcance | Evidência |
| --- | --- | --- | --- |
| Carter, D exemplo 3.1 | δ=6,203971° / 6,2°; θ=23,203971° / 23,2° | Comparação parcial da correlação com entrada metálica fornecida; não reproduz incidência de 3° pelo solver | E2, atual |
| Escala JT9D, M pp. 821–822 | L=15,987614 in / 16,0 in | 0,025 in; escala isolada com referências convertidas/arredondadas | E3, atual |
| Anular, S pp. 210–211 | rh=0,1490671; rt=0,1903329; h=0,0412659 m / 0,1491; 0,1903; 0,0413 m | 0,00005 m; somente geometria com A=0,0440 m² e rm=0,1697 m | E1, atual |
| Área de saída, S pp. 210–211 | A=0,044018807 m² / aproximadamente 0,0440 m² | 0,0001 m²; condições meanline arredondadas, sem reproduzir compressor completo | E5, atual |
| Compressão, S exemplo 2.1 | T02=452,6663 K / 452,7 K | 0,1 K; somente compressor, eficiência convertida | H, não reexecutado nesta consolidação |
| Mach, D exemplo 5.1 | U=208,2713 m/s / 208,3 m/s | 0,1 m/s; helpers de Mach, sem perdas do exemplo completo | H, não reexecutado nesta consolidação |
| Vórtice livre, D exemplo 6.1 | Cx=136,03495 m/s; vazão=30,44986 kg/s; potência=1,50264 MW; R_hub=0,382716 | 0,1 m/s; 0,1 kg/s; 0,01 MW; 0,001 de reação. Fixture com densidade dada de 1,5 kg/m³ | H, não reexecutado nesta consolidação; não é ciclo compressível completo |

Não há exemplo completo de motor reproduzido para cada um dos cinco livros. Boyce e Lakshminarayana fornecem suporte teórico/contextual registrado; isso não equivale a benchmarks completos independentes desses livros.

## 10. Decisões e pendências que permanecem

| ID | Questão | Estado atual | Próxima decisão/evidência necessária |
| --- | --- | --- | --- |
| P1 | Caso de referência manual versus automático | Manual preservado: ciclo 2233,239640 kW; soma meanlines 2215,787186 kW; diferença −17,452454 kW (−0,781486%). Automático fecha os alvos nos casos testados | Autor escolher referência principal; esta matriz não muda parâmetros nem elimina o modo manual |
| P2 | Dois avisos da referência | M1R≈1,001 na ponta do compressor/estágio 1; câmber≈97,76° na turbina/rotor/estágio 3/hub, conforme bloco 3 | Documentar alcance do modelo; não ajustar limites ou parâmetros apenas para zerar avisos |
| P3 | Transição compressor–combustor | Sem difusor; combustor usa T02/P02 do ciclo, não substituídos pela saída manual divergente | Manter limitação explícita ou ampliar escopo apenas se solicitado pelo professor/autor |
| P4 | Área dentro de cada fileira | Entrada/saída calculáveis; estação 2 sem repartição de pressão; CAD representativo na entrada | Se for exigido anular físico contínuo, definir geometria e repartição de perdas; não inventar Pt2 |
| P5 | Combustíveis | Lacunas de PCI/estequiometria marcadas na seção 6 | Obter composição/fonte específica ou manter valores como hipóteses nominais |
| P6 | Localizadores bibliográficos | Eq. de área e apresentação das duas eficiências sem localizador exato completo na documentação atual | Completar páginas após consulta direcionada; não preencher por suposição |
| P7 | Verificação externa | Sem ensaio, mapa de desempenho, resistência, emissões ou margem dinâmica | Apresentar como ferramenta preliminar/didática dentro do recorte; evitar afirmação de projeto validado para operação |
| P8 | Entrega CAD | Curvas/loft/DXF computacionalmente verificados em etapas anteriores; limitação STEP conhecida | Importação em CAD e avaliação de sólido/colisões antes de afirmar CAD plenamente validado |
| P9 | Legendas e domínios de entrada | Rótulos genéricos de bandas; chamada direta com π=1 historicamente apresentou divisão por zero na conversão de eficiência | Revisão editorial e teste de domínio dedicado, com correção autorizada se necessária; π=1 não é caso coberto pelos testes atuais |

## 11. Relação com o recorte do professor

Fonte: [Luiz Gabriel Da Silva.md](<../../../Feedback TCC 2026-10-26/Feedback 2026-10-26/Luiz Gabriel Da Silva.md>).

| Exigência/recorte | Cobertura e ressalva |
| --- | --- |
| Brayton com perdas simplificadas; meanline 1D | C1–C6/T1–T4; hipóteses e perdas prescritas identificadas |
| Combustor 1D por balanço e ΔP | B1–B5; não se exige combustão reativa, difusor ou estabilidade detalhada no recorte transcrito |
| Free vortex; três seções; multiestágio | T5–T9; verificadores incluem três e sete seções, sem tornar sete uma exigência professoral |
| Geometria paramétrica e loft simples | G2–G6; distinção entre desenho paramétrico e perfil aerodinamicamente validado |
| Validação por coerência e literatura | E1–E7 e comparações parciais; rastreabilidade fornecida, validação integral não proclamada |
| CAD-ready/DXF/STEP | G7/P8: parte DXF disponível; STEP permanece limitação da entrega, não resolvida por concordância termodinâmica |
| Excluir CFD, estrutura, resfriamento e combustão reativa detalhada | Permanecem fora do escopo; sua ausência é limitação assumida, não motivo automático para implementar esses modelos |

O conjunto é compatível com uma investigação preliminar e didática sob hipóteses. A conclusão acadêmica deve delimitar resultados e pendências, em vez de declarar fidelidade irrestrita aos cinco livros.

## 12. Relatórios e reprodução

- [Raio médio e Euler](VERIFICACAO_RAIO_MEDIO.md).
- [Bloco 1 — Carter, orientação e solidez](VERIFICACAO_BLOCO1_GEOMETRIA.md).
- [Bloco 2 — combustor e fontes](VERIFICACAO_BLOCO2_COMBUSTOR.md).
- [Bloco 3 — continuidade e reação da turbina](VERIFICACAO_BLOCO3_TURBINA.md).
- [Bloco 4 — fechamento e áreas](VERIFICACAO_BLOCO4_FECHAMENTO.md).
- [Bloco 5 — indicadores](VERIFICACAO_BLOCO5_INDICADORES.md).

Os relatórios são históricos de cada bloco. Por exemplo, o bloco 1 registra o câmber anterior à continuidade corrigida no bloco 3; o relatório inicial de raio médio registra DF anterior à solidez local. Não combinar esses números de versões distintas como se fossem uma única execução.

Reprodução a partir da raiz do TCC, usando o Python/dependências do projeto:

```powershell
python -X utf8 checkpoints/matriz_rastreabilidade_2026-11-06/reexecutar_verificacoes.py
```

O script acima executa cinco verificadores e registra comandos/códigos de saída em `execucoes.json`. O teste de perfis foi executado separadamente, a partir de `NEW`:

```powershell
python -X utf8 -m engine.estudos.verificar_geometria_perfis --saida ../checkpoints/matriz_rastreabilidade_2026-11-06/perfis.json
python -X utf8 ../checkpoints/matriz_rastreabilidade_2026-11-06/reexecutar_sensibilidade.py
```

Uma repetição desses comandos sobrescreve apenas as respectivas evidências nessa pasta; para manter histórico de execuções futuras, use outra pasta e ajuste os caminhos. Os hashes em `fontes_antes.json` e a conferência final identificam o código efetivamente examinado nesta tarefa. Uma alteração posterior de fonte ou referência exige reavaliar as linhas afetadas da matriz.

Somente documentação e evidências foram criadas. O checkpoint identifica que esta matriz não existia antes; sua reversão não requer restaurar qualquer código físico. A referência manual continua vigente até decisão explícita do autor.
