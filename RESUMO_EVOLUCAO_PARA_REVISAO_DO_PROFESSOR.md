# Evolução do projeto — resumo para revisão do professor

**Projeto:** ferramenta didática para projeto preliminar de turbina a gás axial.  
**Responsável pelo TCC:** Luiz Gabriel da Silva.  
**Período resumido:** recebimento das orientações de 26/10/2026 até 19/11/2026.

Este documento reúne as implementações, correções e verificações realizadas nesse período. As alterações pequenas de apresentação foram agrupadas por finalidade. Os relatórios técnicos ligados ao final conservam equações, arquivos e evidências de cada etapa.

**Situação atual:** existe um fluxo integrado de ciclo, compressor, combustor, turbina, distribuição radial, perfis e geometria, acompanhado de recursos didáticos, comparação e exportação. Há verificações numéricas e comparações parciais com livros. **Isso não equivale à validação integral de um motor real ou de uma geometria pronta para fabricação.** As decisões ainda abertas estão na seção 9.

## 1. Ponto de partida e direção do trabalho

Os documentos de referência recebidos foram as orientações de projeto, o feedback de avaliação e as ideias de interface didática da pasta `Feedback TCC 2026-10-26`. Também foi utilizado o roteiro `INSTRUCOES_CORRECOES_CODEX.md`, elaborado posteriormente com auxílio do Claude a partir das irregularidades identificadas.

Na situação inicial já existiam os principais módulos de cálculo, estudos de sensibilidade e geração geométrica. As prioridades foram integrar o combustor à interface, tornar os resultados rastreáveis, investigar inconsistências entre etapas e explicar as hipóteses ao usuário.

Algumas decisões posteriores, autorizadas pelo autor, **substituíram hipóteses conservadas no roteiro inicial**: a massa de combustível passou a entrar na vazão da turbina, a construção do anular foi corrigida para recuperar o raio meanline, e as propriedades do ar e dos produtos passaram a ser diferenciadas. Portanto, o roteiro inicial é um registro histórico, não a descrição completa da versão atual.

## 2. Correções e mudanças nos cálculos

Para leitura desta seção: *meanline* é o cálculo em um raio de referência; distribuição radial é a avaliação em várias alturas da pá; *swirl* é a componente tangencial da velocidade. ψ representa a carga por estágio, φ relaciona velocidade axial e periférica, e HTR é a razão entre raio do cubo e da ponta.

| Tema | O que mudou | Por que isso importa |
|---|---|---|
| **Mach relativo** | A temperatura estática passou a ser obtida pela velocidade **absoluta** da mesma estação; a velocidade relativa é dividida pela velocidade do som assim obtida. Correção aplicada a compressor/turbina, meanline/radial. | Evita misturar referenciais e distorcer os avisos de Mach relativo. |
| **Entradas e robustez numérica** | Validações de valores finitos, eficiências, temperaturas, vazões, ângulos, HTR e contagens inteiras; rejeição de estados impossíveis e falhas de convergência com mensagens mais claras. Valores indefinidos deixaram de escapar silenciosamente das comparações. | Um cálculo que não pode ser feito deixa de parecer um caso aprovado ou de terminar apenas com um erro genérico. Faixas orientativas continuam distintas de proibições matemáticas. |
| **Avisos do combustor** | Avisos passaram a ser conservados e apresentados; Mach de entrada é validado antes do cálculo de área. | Evita perder diagnósticos ou dividir por uma função de vazão nula. |
| **Vazão da turbina** | O combustor fornece a vazão de combustível e a turbina recebe **ar + combustível**. O ciclo usa essas vazões nas potências e indicadores. | Compressor e turbina têm bases mássicas diferentes; não se deve subtrair diretamente seus trabalhos específicos como se fossem por kg do mesmo fluido. |
| **Raio médio e trabalho de Euler** | Anulares de cada estágio passaram a respeitar o raio médio **aritmético** usado no meanline. Cubo e ponta variam ao redor dessa referência; HTR informado caracteriza a entrada. | A distribuição radial recupera o trabalho do meanline no raio de referência. A turbina deixou de impor ponta fixa nessa construção. |
| **Perfis do compressor** | A correlação de Carter passou a ser fechada no câmber metálico final. Corrigiu-se a conversão entre o sinal de β armazenado no modelo e o ângulo geométrico da velocidade relativa. | Os ângulos metálicos, o stagger e a orientação entregue ao loft ficam coerentes com o escoamento e a convenção de sinais adotada. |
| **Solidez local** | A relação corda/passo passou a considerar raio local e número inteiro de pás realmente construído. Essa solidez alimenta DF/Carter no compressor e os perfis da turbina. | A solidez varia ao longo da altura; o valor-alvo do meanline não é automaticamente o valor de todas as seções. |
| **Continuidade entre estágios da turbina** | Só o primeiro bocal tem entrada axial. Os seguintes recebem a componente tangencial de saída do rotor anterior, além dos estados totais correspondentes. | Evita reiniciar artificialmente o escoamento como axial a cada estágio. |
| **Reação da turbina** | A reação passou a usar a queda de entalpia estática no rotor dividida pela queda estática no estágio. A razão alternativa baseada no trabalho de eixo permanece identificada como diagnóstico diferente. | As duas definições só coincidem em condições específicas de velocidade; a distinção afeta interpretação e geometria. |
| **Comprimento do combustor** | A escala de Mattingly/JT9D passou a usar a pressão de **entrada** da câmara, e não a pressão depois da perda. Fontes e correspondências entre estações foram explicitadas. | Corrige a aplicação da escala; o comprimento continua uma estimativa por semelhança, não um dimensionamento detalhado da combustão. |
| **Energia do combustor** | Separaram-se o calor útil do combustível, o aumento de entalpia dos produtos e o indicador auxiliar `Q_total`. | `Q_total` representa aquecimento virtual de ar; não é uma segunda fonte de energia e não deve ser somado ao calor do combustível. |
| **Indicadores do ciclo** | Foram explicitadas eficiência sobre calor útil, eficiência sobre PCI, BWR e consumo específico, com unidades e bases mássicas. | O usuário distingue fração da potência consumida pelo compressor, eficiência térmica e consumo; a potência não é apresentada como potência elétrica. |
| **Referência manual da turbina** | Houve revisão autorizada de ψ, com adoção de **1,198736** no caso manual após experimentações anteriores. | Esse valor pertence ao histórico de escolha do caso; não garante fechamento exato após mudanças posteriores nas propriedades. |

### 2.1 Fechamento entre ciclo, estágios e áreas

Foram acrescentados diagnósticos que comparam temperaturas, pressões, trabalhos, potências e interfaces. Diferenças pequenas continuam visíveis mesmo quando não ultrapassam o limiar de emissão de aviso.

- **Modo manual:** conserva N e ψ fornecidos; pode divergir dos alvos do ciclo. O combustor recebe as condições definidas pelo ciclo, sem substituição silenciosa pela saída manual do compressor.
- **Modo automático:** redistribui o trabalho entre os estágios escolhidos e recalcula ψ efetivo para atender aos alvos nos casos calculáveis.
- **Áreas:** entrada e saída dos estágios são avaliadas por continuidade em condições meanline. Na estação entre fileiras, pressão, densidade e área podem permanecer **não determinadas**, pois o modelo não reparte as perdas de pressão entre rotor e estator/bocal.
- **CAD:** usa uma área representativa por estágio. Isso não resolve a forma exata do anular ao longo de cada fileira nem a continuidade de linhas de corrente.

Igualdade dentro de tolerância numérica não é tolerância de fabricação ou comprovação experimental. A interface apresenta essa distinção.

## 3. Propriedades do ar e dos produtos: ampliação mais recente

O projeto passou primeiro do cp único para **propriedades constantes distintas por região**. Em seguida, foi acrescentado o modo automático por composição, com base nos coeficientes NASA Glenn. O modo prescrito permanece disponível para exercícios, comparações históricas e hipóteses escolhidas pelo usuário.

No automático:

1. O combustível é representado por uma composição elementar simplificada e queima com ar seco contendo N₂, O₂ e argônio.
2. São calculados CO₂, vapor de água, N₂, O₂ excedente e argônio, para combustão completa pobre ou estequiométrica. Misturas ricas são recusadas nesse modelo.
3. A razão combustível/ar e a composição são resolvidas conjuntamente pelo balanço de energia.
4. A integração de cp(T) das espécies, de **298,15 K até TIT**, fornece um **cp equivalente constante** da mistura. R vem da massa molar e k é derivado de cp e R.
5. Esse cp permanece constante durante a expansão: **não foi implementada uma turbina que integra cp variável ao longo do processo**.

As entalpias sensíveis têm referência em 298,15 K, sem somar novamente a energia química já representada pelo PCI. O ar mantém cp prescrito; no automático, seu R deriva da composição seca adotada. No prescrito, conserva-se a convenção legada para reprodução dos casos antigos.

| Combustível | Representação atual | Observação essencial |
|---|---|---|
| JP-4 | CH₁,₉₄ | Média elementar documentada na fonte NASA. |
| JP-8 | C₁₂H₂₃ | Substituto elementar baseado em Jet-A; não representa todos os aditivos/lotes de JP-8. |
| Gás natural | CH₄ | Aproximação por metano puro, não uma análise de uma mistura comercial. |
| Diesel | C₁₂H₂₃ | Diesel mineral representativo; sem biodiesel, impurezas ou composição específica de lote. |

**JP-8 e diesel:** o mesmo substituto produz propriedades iguais à mesma temperatura e razão combustível/ar. Os PCI distintos adotados exigem diferentes quantidades de combustível e, no caso resolvido, geram composições e propriedades diferentes. Não foram criadas diferenças artificiais apenas pelo nome do combustível. Os PCI nominais de gás natural e diesel continuam com fonte específica pendente, explicitada na interface.

Essa ampliação afeta combustor, ciclo, turbina, radial, geometria, sensibilidades, comparações e exportações; o cálculo de R/k do ar também pode alterar ligeiramente o compressor. Ela vai além de uma mudança de apresentação e merece apreciação do professor quanto à adequação ao recorte do TCC.

### Exemplo da versão atual — não confundir com resultados históricos

Condições: T01=300 K; P01=100 kPa; razão de pressão=8; TIT=1200 K; vazão de ar=15 kg/s; cp_ar=1005 J/(kg·K); η_b=0,99; eficiências politrópicas do compressor/turbina=0,85/0,80; perda no combustor=5%; propriedades automáticas.

| Combustível | Razão combustível/ar (kg/kg de ar) | cp dos produtos (J/(kg·K)) | Potência líquida do ciclo (kW) |
|---|---:|---:|---:|
| JP-4 | 0,016837847 | 1.112,558579 | 2.392,370325 |
| JP-8 | 0,016667502 | 1.112,071503 | 2.389,645837 |
| Metano | 0,014582265 | 1.124,178257 | 2.455,300566 |
| Diesel | 0,016958663 | 1.112,516358 | 2.392,175509 |

São resultados do modelo, não medições. Relatórios anteriores com cerca de **2.233,24 kW** referem-se ao caso com cp único; a alteração desses valores era esperada com a mudança de hipóteses. Não se deve combinar tabelas de versões distintas como se fossem uma única execução.

## 4. Estágios automáticos, critérios e sensibilidade

### Seleção do número de estágios

A seleção deixou de depender apenas de arredondamento. O programa compara os inteiros imediatamente abaixo/acima da estimativa, sem duplicatas, executando meanline, radial e perfis de cada candidato.

A prioridade atual é: candidato calculável e com fechamento dos alvos; menor excesso aerodinâmico máximo; menor soma dos excessos aerodinâmicos; menor excesso de câmber; menores excessos nas faixas comparativas; menor afastamento de ψ solicitado; menor número de estágios no desempate.

Essa é uma **política de comparação do projeto**, não uma regra universal da literatura nem uma busca global pelo melhor motor. Ela não usa a contagem bruta de avisos. A interface mostra candidatos, valores, limites, locais críticos, índices normalizados e o motivo da preferência. **A prioridade entre câmber e faixas comparativas está pendente de discussão com o professor.**

### Critérios e varreduras

- Os limites e faixas foram centralizados, evitando divergência entre verificadores, seleção, gráficos e explicações. Foram diferenciados definição física, correlação empírica, escolha do projeto e domínio matemático.
- Mach=1 indica condição sônica; DF é uma triagem empírica de difusão; faixas de reação, carga e swirl não são apresentadas como aprovações universais.
- O caso de referência da sensibilidade vem das **entradas efetivamente calculadas na execução**. Estrelas e curvas acompanham mudanças depois de recalcular, sem gravar valores da sessão nos padrões do arquivo.
- CLI e interface só devem produzir a mesma curva quando usam as mesmas entradas, hipóteses e modos de estágios. No automático, cada ponto pode escolher outro N e gerar saltos ou patamares.
- Pontos que falham são registrados com motivo e lacuna na curva, sem inventar resultados ou ligar o traço por cima da falha.
- Reação é uma saída dependente dos ângulos e coeficientes. Sua relação com a torção é explorada por comparação de casos; não foi criada uma entrada independente de reação incompatível com o restante do modelo.

## 5. Implementações didáticas na interface

Os recursos usam os resultados identificados de uma execução. A organização atual inclui **Ciclo, Combustor, Compressor, Turbina, Sensibilidade, Comparar projetos, Geometria 3D, Verificações e Downloads**.

| Grupo | Implementações e refinamentos |
|---|---|
| **Formulário e leitura** | Entradas agrupadas em condições de operação, escolhas de projeto e hipóteses; rotação única para o eixo; unidades e tooltips; glossário com símbolos, subscritos e equações; modos Guiado/Técnico. O nível de leitura não muda os cálculos. |
| **Identificação do caso** | ID e horário da execução; fotografia das entradas submetidas; estado de cada etapa; indicação de resultados com avisos e de etapas não executadas; aviso quando há entradas alteradas ainda não calculadas. Corrigida a apresentação inicial que mostrava etapas como não registradas. |
| **Combustor** | Integração ao pipeline e aba própria; controles de combustível, eficiência, Mach prescrito e perda; tabelas de mistura, estados, vazões, energia e dimensões; hipóteses, fontes e limitações em painéis expansíveis. |
| **Ciclo e energia** | Percurso funcional do fluido; estados globais; balanço visual de produção da turbina, consumo do compressor e saldo; eficiências sobre calor útil/PCI, BWR, SFC e bases de massa; diagnósticos de fechamento. |
| **P–v e T–s** | Diagramas dinâmicos em imagem/interativo, hover e zoom opcional. O T–s tem opção inicial equivalente, com quatro etapas conectadas e fluido de referência único, e opção por componente, com propriedades e zeros independentes. Incluem explicação detalhada da diferença, tabelas e referências isentrópicas coerentes com cada desenho. Nenhum é chamado de T–s real da combustão. |
| **Triângulos de velocidade** | Seleção de estágio/seção; entrada e saída do rotor; vetores absoluto, relativo e periférico; componentes, módulos, ângulos, sinais, normalização por U, equação de Euler e comparação dos trabalhos. Opções imagem/interativo. |
| **Anular e estágios** | Tabelas de área, cubo, ponta, altura, raio médio e HTR por estágio; comparação de temperaturas, pressões, razões de pressão, reação, Mach, DF e número de pás; estágio em foco para tabela radial e geometria. |
| **Distribuição radial** | Gráficos do cubo à ponta, seção em foco, localização dos extremos e conferência de r·Cθ para a hipótese de vórtice livre. Distingue valores meanline e extremos nas seções calculadas. |
| **Do escoamento ao perfil** | Distinção entre ângulos do escoamento e do metal, incidência, desvio, câmber, stagger, corda, passo e solidez local; desenho 2D em camadas; orientação pelo stagger; normalização e sobreposição cubo/meio/ponta. |
| **Avisos** | Painéis por componente e avisos gerais no local correspondente; tabela principal e detalhes do aviso selecionado; mensagem completa, tipo de critério, origem, interpretação e próxima análise. Aba consolidada de Verificações, filtros por componente e catálogo de critérios/fontes. Associação por identificação para evitar trocar a interpretação depois de filtros/seleções. |
| **Comparação de projetos** | Fixação de uma execução como referência; entradas alteradas, diferenças globais, dimensões, avisos e localização dos extremos; comparação radial em altura relativa; reação e torção por seção. Referência e caso atual têm estilos distinguíveis mesmo quando coincidem. |
| **Discretização radial** | Estudo que varia somente o número de seções, preservando as demais entradas calculadas; tabelas, gráficos, estados de falha e diferenças em relação à menor discretização. No automático, uma mudança de N é identificada como mudança de projeto, não apenas de amostragem. |
| **Legibilidade e estabilidade** | Tabelas reorganizadas, detalhes condicionais, leitura de mensagens longas, explicação para expandir células, correção de erro de container, rolagem e enquadramento; legendas e contagens dependentes do caso; vírgula decimal na apresentação e contagens inteiras onde aplicável. |

O P–v e o T–s mostram estados totais equivalentes e ligações esquemáticas. A área desses desenhos não é apresentada como o trabalho líquido do motor. O retorno tracejado fecha uma representação equivalente; não é uma tubulação física de retorno dos gases ao compressor.

## 6. Geometria 3D, CAD e arquivos de saída

- **Montagem na interface:** uma pá, um estágio ou um componente completo, com rotação, zoom, vistas iniciais, seções, eixos, setor angular e repetição circunferencial segundo Z calculado.
- **Leve versus detalhado:** redução de pontos do contorno para apresentação; a vista leve de montagem também pode omitir pás, mantendo suas posições angulares reais. As contagens real/desenhada são informadas. Não muda o projeto calculado.
- **Cubo simplificado opcional:** superfície interna esquemática seguindo os raios calculados, com transparência ajustável. Não representa um único corpo girante ou solução de fixação de estatores/bocais. Houve refinamentos de câmera, opacidade, margens e escala para melhorar a leitura.
- **Natureza da visualização:** a malha triangular da interface não é o sólido FreeCAD. As vistas de curvas/CAD foram distinguidas de superfícies, lofts e sólidos, com eixos e unidades explícitos.
- **Downloads guiados:** seleção por fileira, estágio ou componente; prévia e tabela de peças; orientações de unidade, camadas, ordem das seções e reconstrução do loft. Uma fileira exportada corresponde à sua pá de referência, não a todas as pás da circunferência.
- **Correções de exportação/apresentação:** contagens seguem o número efetivo de estágios/seções; os ZIPs usam os arquivos da seleção atual para evitar incluir resultados antigos de estágios adicionais. Os CSVs receberam informações de geometria, áreas, propriedades e diagnósticos pertinentes.
- **FreeCAD e STEP:** há registros visuais fornecidos pelo autor de reconstruções no FreeCAD, incluindo montagem da turbina. Isso não substitui uma demonstração dimensional reproduzível. O STEP continua fora da saída validada da interface, com limitação documentada.

Compressor e turbina são mostrados separadamente. Não se inventou uma ligação geométrica entre eles: o combustor 1D e o difusor não fornecem uma geometria resolvida para montar o motor inteiro.

## 7. Reprodução, organização e entrega do código

| Recurso | Mudança realizada |
|---|---|
| **Importações** | Exemplos que calculavam automaticamente ao importar módulos foram separados em funções/chamadas explícitas. Instâncias de exemplos são independentes; importar uma classe não deve executar um caso oculto. |
| **Referência comum** | `reference_case.py` reúne padrões e monta cópias do caso de cada execução, usadas pelos estudos e interface. |
| **Salvar/recuperar** | JSON de entradas, com validação antes de preencher campos; importação não executa o modelo. Versão atual registra o modo de propriedades; casos antigos preservam a hipótese prescrita em vez de ativar silenciosamente a composição automática. |
| **Relatório da execução** | ZIP com relatório Markdown, entradas, resultados/diagnósticos e tabelas CSV, incluindo dados de sensibilidade. A preparação do pacote é separada do download. Livros, imagens e CAD não estão incorporados nesse ZIP. |
| **Instalação** | README de execução em `NEW`, dependências diretas e lock de referência Windows/Python 3.10; teste de instalação em ambiente isolado e cópia portátil. Não requer conta GitHub ou Streamlit para calcular localmente. |
| **Checkpoints** | Cópias anteriores, manifestos e evidências por etapa permitem retornar a versões anteriores. Os relatórios históricos conservam o contexto e as hipóteses daquela data. |

**Ao enviar esta versão:** preservar toda a pasta `NEW/engine`, inclusive os **dois JSON de coeficientes NASA** em `engine/combustor`. Eles são dados de execução. Os PDFs e checkpoints não são dependências para abrir a interface, mas podem acompanhar a entrega como referências/evidências. O teste portátil de 18/11 é anterior à inclusão desses JSON; não significa que uma cópia atual contendo apenas arquivos `.py` seja suficiente.

Execução, após instalar as dependências conforme [README](README.md), a partir de `NEW`:

```powershell
python -m streamlit run engine/webapp/streamlit_app.py
```

A preparação para publicação foi melhorada, mas não houve publicação no GitHub ou contratação/configuração de hospedagem pública nesta etapa.

## 8. Verificações realizadas e o que elas demonstram

| Tipo de evidência | O que foi conferido | Limite da conclusão |
|---|---|---|
| **Regressões antes/depois** | Estados, triângulos, áreas, raios, trabalhos e exportações conforme o escopo de cada correção. | Uma mudança de hipótese pode alterar legitimamente resultados; não se exige reproduzir números de outra versão física. |
| **Identidades e acoplamento** | Energia, vazões, Euler, recuperação do meanline no radial, r·Cθ, geometria, continuidade e interfaces; casos manuais/automáticos e diferentes discretizações. | Consistência matemática interna, sem prova experimental de desempenho. |
| **Domínios e falhas** | Entradas inválidas, valores indefinidos, fronteiras numéricas, convergência e mensagens de erro. | Recusa de entradas impróprias não garante que todas as entradas aceitas produzam uma máquina viável. |
| **Mistura NASA** | Integral conferida por integração numérica, continuidade entre intervalos, conservação de massa/elementos, frações, energia e oito pipelines dos quatro combustíveis em modos manual/automático. | Verifica a implementação das hipóteses; não certifica a composição de combustíveis reais, chama ou dissociação. |
| **Interface e reprodução** | AppTest para cálculos, sensibilidade, seletores, arquivos antigos/atuais, relatórios e 3D; inspeção de figuras e prints do autor. A troca de visão T–s foi conferida sem alterar a execução. | Teste funcional e inspeção visual não substituem avaliação de aprendizagem ou testes completos em todos os navegadores. |
| **Livros** | Sete grupos bibliográficos, com 29 comparações escalares: **28 dentro das tolerâncias**. | Não são 29 validações independentes nem reprodução de um motor completo de cada livro. |

**Ressalva bibliográfica:** permanece fora da tolerância a comparação de β₂ no cubo do exemplo 6.1 de Dixon, com discrepância investigada e registrada no contexto de arredondamentos. A tolerância não foi ampliada para aprovar o teste. A reprodução do exemplo de combustor de Mattingly com propriedades distintas passa no modo prescrito apropriado; isso não exige que o modo NASA produza o mesmo resultado sob outras hipóteses.

As referências de base são Saravanamuttoo/Cohen/Rogers, Dixon & Hall, Mattingly, Boyce e Lakshminarayana, acrescidas da fonte NASA Glenn para propriedades. Houve consulta direcionada de trechos, equações e exemplos; **não se declara leitura integral ou validação independente de todas as equações pelos cinco livros**. Boyce e Lakshminarayana também fornecem apoio conceitual, sem um benchmark completo independente de cada obra.

## 9. Pontos para a próxima reunião e limites atuais

| Assunto | Situação e decisão desejada |
|---|---|
| **Propriedades automáticas** | Avaliar a adequação do cp equivalente constante, das composições representativas e do modo padrão ao escopo acadêmico. Completar fontes dos PCI nominais pendentes se necessário. |
| **Escolha automática de estágios** | Discutir a prioridade atual entre aerodinâmica, câmber e faixas comparativas. Menos avisos não significa candidato fisicamente superior. |
| **Caso principal do TCC** | Escolher como apresentar manual/automático e reavaliar os parâmetros manuais após a alteração de propriedades. Divergências ciclo–meanline continuam expostas; não foram eliminadas por ajuste recente de ψ/N. |
| **Comparações bibliográficas** | Resolver/discutir a comparação pendente de Dixon e consolidar as hipóteses equivalentes de cada exercício. A tabela de benchmarks ainda não está reunida em um painel próprio na interface. |
| **Casos e redação** | Organizar as demonstrações acadêmicas, incluindo razões de pressão 6 e 12, arquivos de entradas, avisos, reação/torção e discussão com a versão atual. A infraestrutura existe; isso não substitui resultados e discussão escritos do TCC. |
| **CAD** | Consolidar abertura dimensional de uma pá e um estágio, loft e procedimento reproduzível. A visualização e os DXFs não comprovam sólido válido, ausência de colisões, resistência ou fabricabilidade. |
| **Complementos de interface** | Sincronização entre todos os seletores/diagramas/3D, filtros adicionais de estágio/seção, figuras no relatório e vista longitudinal integrada continuam parciais ou ausentes. Não são apresentados como concluídos. |
| **Aceitação e distribuição** | Avaliar uso por terceiros, diferentes telas/navegadores e o pacote final completo. A instalação documentada foi verificada em Windows/Python 3.10; outros ambientes e hospedagem ainda exigem conferência. |

Continuam fora do modelo: difusor compressor–combustor, previsão de incidência/desvio reais de todas as fileiras, repartição detalhada de perdas, choques/CFD, mapas experimentais e margem de estol/surge, química/cinética e estabilidade de chama, emissões, resfriamento, estrutura, vibração, materiais, fixações e fabricação. O Mach do combustor é prescrito, não derivado da descarga do compressor. A eficiência de combustão e a perda de pressão são entradas, não previsões desses fenômenos.

O recorte permanece o de **projeto preliminar e ferramenta didática**. Ausência de avisos, fechamento numérico, figura 3D ou arquivo exportado não certificam funcionamento de uma turbina real.

## 10. Onde consultar detalhes

Os documentos abaixo são históricos de etapas; valores antigos devem ser lidos com suas respectivas hipóteses e datas.

| Tema | Documento |
|---|---|
| Instalação e primeiro uso | [README da implementação](README.md) |
| Raio médio, anular e Euler | [Verificação do acoplamento](engine/estudos/VERIFICACAO_RAIO_MEDIO.md) |
| Carter, sinais e solidez | [Bloco 1 — geometria](engine/estudos/VERIFICACAO_BLOCO1_GEOMETRIA.md) |
| Comprimento e fontes do combustor | [Bloco 2 — combustor](engine/estudos/VERIFICACAO_BLOCO2_COMBUSTOR.md) |
| Continuidade e reação da turbina | [Bloco 3 — turbina](engine/estudos/VERIFICACAO_BLOCO3_TURBINA.md) |
| Fechamento e áreas | [Bloco 4 — integração](engine/estudos/VERIFICACAO_BLOCO4_FECHAMENTO.md) |
| Indicadores energéticos | [Bloco 5 — indicadores](engine/estudos/VERIFICACAO_BLOCO5_INDICADORES.md) |
| Estágios automáticos | [Política de seleção](engine/estudos/VERIFICACAO_SELECAO_ESTAGIOS.md) |
| Referências e exemplos | [Matriz teórica](engine/estudos/MATRIZ_RASTREABILIDADE_TEORICA.md) · [Comparações com livros](engine/estudos/COMPARACAO_EXEMPLOS_LIVROS.md) |
| Propriedades atuais | [Mistura dos combustíveis](engine/estudos/VERIFICACAO_MISTURA_COMBUSTIVEIS.md) |
| Comparação e discretização | [Comparação de casos](engine/estudos/VERIFICACAO_COMPARACAO_CASOS.md) |
| Geometria na interface | [Visualização 3D](engine/estudos/VERIFICACAO_VISUALIZACAO_3D.md) |
| Cobertura e complementos didáticos | [Revisão de cobertura](engine/estudos/REVISAO_FINAL_COBERTURA_INTERFACE.md), atualizada neste resumo pelas etapas posteriores de instalação, propriedades e T–s |

**Escopo desta preparação:** consolidação documental a partir das orientações, código consultado, relatórios e evidências existentes. Não foram alterados cálculos nem reexecutada toda a bateria de testes para produzir este resumo.
