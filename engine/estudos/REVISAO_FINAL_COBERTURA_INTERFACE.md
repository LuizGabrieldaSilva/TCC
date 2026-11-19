# Revisão de cobertura da interface e refinamento 3D

Data: 17/11/2026.

## Conclusão da revisão

Os oito grupos de trabalho organizados na conversa possuem implementações na interface: leitura guiada/técnica, balanço energético visual, perfil 2D, geometria 3D, verificações, comparação de casos, reprodução dos casos e orientação CAD. **Isso encerra a primeira passagem pelos oito grupos, mas não significa que todas as sugestões detalhadas dos documentos estejam implementadas ou que o TCC esteja integralmente validado.**

O núcleo didático está disponível. Permanecem complementos de interação, apresentação da validação bibliográfica, exportação e documentação de entrega. A prioridade de seleção dos candidatos automáticos continua aguardando discussão com o professor; esta revisão não a altera.

## Fontes e alcance

Documentos locais consultados:

- [Orientações do projeto — Luiz Gabriel Da Silva.md](<../../../Feedback TCC 2026-10-26/Feedback 2026-10-26/Luiz Gabriel Da Silva.md>).
- [Feedback_Luiz_Gabriel.md](<../../../Feedback TCC 2026-10-26/Feedback 2026-10-26/Feedback_Luiz_Gabriel.md>), registro de 26/10/2026. As observações sobre o código daquela data não foram tratadas automaticamente como problemas atuais.
- [Ideias_Interface_Didatica.md](<../../../Feedback TCC 2026-10-26/Feedback 2026-10-26/Ideias_Interface_Didatica.md>), propostas incrementais, e não uma lista de exigências físicas adicionais.
- [Matriz de rastreabilidade](MATRIZ_RASTREABILIDADE_TEORICA.md) e relatórios posteriores de importações, perfis, reprodução, comparação e geometria 3D.

Conferência por leitura do código atual e registros de verificação, complementada pelos prints fornecidos pelo autor. Não houve nesta tarefa nova auditoria dos cinco PDFs, reexecução de toda a validação física, execução FreeCAD ou avaliação externa de aprendizagem. O texto das orientações foi consultado em Markdown; a figura embutida de entradas globais não foi objeto de nova auditoria.

## Cobertura das propostas didáticas

**Atendido**: recurso funcional identificado no escopo indicado. **Parcial**: há uma implementação útil, com complemento específico ainda ausente. **Orientação**: sequência de trabalho ou aceitação, sem ser um recurso isolado.

| Item em Ideias_Interface_Didatica.md | Estado | Implementação identificada | Complemento ou limite |
|---|---|---|---|
| 1. Percurso do projeto e estado das etapas | Parcial | Identificação da execução, tabela de etapas, abas, guias e resultados por componente em `streamlit_app.py` e `reading_mode.py`. Combustor integrado. | Não há um navegador único de todo o pipeline que selecione uma etapa e sincronize os demais painéis. |
| 2. Leitura guiada e técnica | Atendido | `reading_mode.py`; ambos usam os mesmos resultados e preservam avisos/limitações. | Avaliação de compreensão por outro usuário ainda não realizada. |
| 3. Entradas autoexplicativas | Atendido | Formulário em três grupos, nomes, unidades, tooltips e glossário. | Faixas e propriedades nominais continuam sujeitas às ressalvas bibliográficas documentadas. |
| 4. Escolhas automáticas e entradas dependentes | Atendido | ψ solicitado/efetivo, estimativa e N adotado, comparação de candidatos e índices detalhados. Modo manual mostra desvios ciclo–meanline. | Política de preferência pendente de discussão com o professor. |
| 5. Visão geral da máquina | Parcial | Cartões dos componentes com estados globais; distinção das estações locais nos painéis de triângulos. | O esquema não abre automaticamente abas/resultados; não é um corte longitudinal integrado do motor. |
| 6. Ciclo com gráficos e balanços | Atendido | Estados, diagramas, balanço de potências, bases de massa, eficiências e equações em `cycle_diagrams.py`, `energy_balance.py` e `energy_indicators.py`. | Ligações entre estados são esquemáticas, conforme indicado. |
| 7. Dimensionamento visível dos estágios | Parcial | Comparação entre estágios, estágio em foco, tabelas, geometria, áreas e triângulos. | Os seletores dos triângulos/perfis permanecem independentes do estágio em foco, explicitamente informados. Não há seleção única para todos os painéis. |
| 8. Distribuição radial | Parcial | Gráficos por raio, seção em foco, tabela destacada, conferência de r·Cθ e estudo de discretização. | Seção selecionada no painel radial não destaca simultaneamente a mesma seção na malha 3D. |
| 9. Ângulos e forma do perfil | Atendido | Camadas de contorno, câmber, corda, espessura, ângulos e stagger; orientação e comparação hub/meio/ponta em `blade_profile.py`. | Geometria paramétrica, sem previsão de pressão na pá ou validação estrutural. |
| 10. Geometria 3D em níveis | Atendido | Uma pá como padrão, estágio/componente, rotação, zoom, seções, eixos, replicação e setor em `assembly_3d.py`. Seção 2D disponível no painel de perfis. | Malha de visualização, distinta do sólido FreeCAD. Cubo é esquemático. |
| 11. Localização e significado dos avisos | Parcial | Painéis locais e aba Verificações; IDs, mensagem completa, critério, origem, interpretação e próxima análise. | Filtro consolidado é por componente; filtros específicos de estágio/seção ainda não estão disponíveis nessa aba. Nem todo aviso é um registro estruturado de grandeza/valor/unidade separado do texto. |
| 12. Verificação e comparação com referência | Parcial | Aba Verificações, resíduos de interfaces, critérios/fontes, limitações; matriz e verificadores no projeto. | Resultados dos exemplos bibliográficos não estão reunidos em uma tabela consultável na interface com referência, hipóteses, desvios e tolerâncias. |
| 13. Causa e efeito/comparar projetos | Atendido | Referência preservada, entradas alteradas, diferenças, avisos, distribuições radiais, reação × torção, sensibilidade com falhas/lacunas e discretização. | Não é uma varredura independente de reação, pois ela é uma saída dependente do modelo. |
| 14. Rastreabilidade e reprodução | Parcial | ID, fotografia das entradas, aviso de alterações pendentes, JSON de entrada, relatório Markdown/JSON/CSV em ZIP. | O ZIP não inclui figuras nem um manifesto que associe cada geometria exportada ao relatório; DXFs são baixados separadamente. |
| 15. Explicar e selecionar arquivos CAD | Parcial | Guia de formatos, prévia, seleção por fileira/estágio/componente, DXF e orientação para loft. | Macros continuam externas a esse fluxo; não há entrega STEP validada. Demonstração CAD reproduzível precisa ser consolidada. |
| 16. Ordem sugerida | Orientação | Os oito grupos de trabalho possuem implementações correspondentes. | A conclusão dos grupos não substitui os critérios de aceitação detalhados. |
| 17. Diagramas P–v e T–s dinâmicos | Parcial | Estados equivalentes calculados, ideais opcionais, imagem/interativo, valores e zoom. | Não há seleção bidirecional de estados/processos entre os dois diagramas e esquema; comparação de casos não sobrepõe esses diagramas. |
| 18. Vista longitudinal de compressor, câmara e turbina | Parcial | Esquema funcional na aba Ciclo, dimensões do combustor em tabela e geometria calculada de cada turbomáquina. | Não há uma vista longitudinal integrada dos três componentes nem seleção de fileira no desenho que abra os resultados. Não foi inventada a geometria do difusor. |
| 19. Triângulos dinâmicos e sincronizados | Parcial | Vetores calculados, entrada/saída, sinais, normalização, hover, ângulos e comparação de Euler em `velocity_triangles.py`. | Seletores próprios; não sincronizam com seção destacada na pá 3D, nem mostram automaticamente a diferença vetorial contra o caso anterior ou sobreposição simultânea hub/meio/ponta. |
| 20. Recursos dinâmicos usando a mesma execução | Parcial | As vistas consomem os resultados calculados; montagens são preparadas sob demanda e invalidadas por mudança de seleção/execução. | Integração bidirecional entre vistas e montagem longitudinal completa permanecem complementos. |
| 21. Avaliação da interface revisada | Parcial | As informações essenciais têm pontos de consulta identificados nos painéis. | Fazer uma passagem de aceitação com outro usuário, cobrindo os sete questionamentos do documento e larguras de tela diferentes. |

## Exigências centrais e entrega acadêmica

| Tema das orientações/feedback | Estado observado | Próximo encaminhamento |
|---|---|---|
| Brayton, compressor/turbina multiestágio e combustor 1D | Implementados e apresentados no fluxo integrado; balanços e diferenças expostos. | Consolidar os casos usados na redação, com hipóteses e limites. Não presumir fechamento exato no modo manual. |
| Vórtice livre, três seções e refinamento | Implementados; três seções disponíveis e comparação de amostragens existente. | Justificar a discretização escolhida nos casos acadêmicos. |
| Perfis e loft simples, DXF/CSV | Implementados; visualização/curvas distinguidas de sólido CAD. | Consolidar uma pá e um estágio com unidades, dimensões e procedimento de abertura em CAD. Prints históricos do FreeCAD são evidência visual, não substituem esse procedimento. |
| Validação por coerência e literatura | Há verificadores, matriz e comparações parciais com números publicados. | Preservar condições/versões das evidências e completar os localizadores bibliográficos pendentes. Não concluir validação integral da máquina ou leitura integral dos cinco livros. |
| Casos π total 6 e 12, reação e torção | Há infraestrutura e registros de testes envolvendo essas razões; a relação reação/torção é explorável na comparação. | Organizar os casos como demonstrações acadêmicas, com arquivos de entradas, modo de estágios e discussão. Não é necessário criar novos modelos para isso. |
| Reprodução por terceiros | Entradas e relatório reproduzíveis na sessão; exemplos de importação refatorados conforme relatório de 09/11. | Falta documentação de instalação/execução voltada a terceiros e lista completa das dependências. `requirements-3d.txt` cobre somente o acréscimo Plotly. O README raiz registra regras de trabalho, não é um guia de instalação. |
| Avisos e prioridade de candidatos | Critérios e consequências documentados; a referência pode emitir avisos. | Discutir a prioridade com o professor e justificar as ocorrências remanescentes; não elevar limites para obter zero avisos. |
| STEP | Opcional nas orientações; limitação permanece exposta. | Manter fora da entrega validada enquanto não houver verificação própria. |
| CFD, estrutura, resfriamento e química detalhada | Excluídos do recorte. | Não são tarefas obrigatórias desta revisão. Difusor também continua fora do escopo acordado, com limitação explicada. |

O feedback de outubro contém estados históricos já superados, como combustor não integrado e efeitos de cálculo durante importações. A matriz também preserva pendências históricas: por exemplo, a linha P9 precisa ser lida junto às atualizações posteriores de validação de entradas/legendas. Esta revisão não as reintroduz como defeitos atuais.

## Pendências agrupadas para decisão

| Grupo | O que permanece | Natureza/prioridade |
|---|---|---|
| A. Aceitação da apresentação | Conferir opacidade e enquadramento no navegador, diferentes telas e leitura por outro usuário. | Próximo passo imediato. |
| B. Entrega reproduzível e discussão acadêmica | Guia de instalação, dependências completas, casos π=6/12, arquivos e discussão dos avisos; evidência de importação CAD. | Fechamento da entrega do projeto. |
| C. Evidências bibliográficas na interface | Tela/tabulação dos exemplos e desvios já registrados, distinguindo consultas históricas e testes reexecutados. | Complemento didático relevante; não confundir com novos cálculos físicos. |
| D. Navegação e sincronização | Estado/processo nos diagramas, estágio/seção entre painéis e destaque da seção na pá; filtros de avisos por estágio/seção. | Complemento de interação, pode ser incremental. |
| E. Relatório e visão longitudinal | Figuras no pacote, associação dos DXFs ao caso e esquema longitudinal integrado com partes ilustrativas identificadas. | Complemento de comunicação; não exige inventar um difusor físico. |
| F. Decisões do modelo | Prioridade entre candidatos, escolha/apresentação de referência manual/automática e lacunas bibliográficas/propriedades nominais. | Depende de discussão acadêmica; sem alteração nesta tarefa. |

Não foi iniciada implementação adicional dos grupos B–F nesta revisão.

## Refinamento visual aplicado nesta tarefa

Em `assembly_3d.py`:

- Transparência inicial do cubo passou a **0%**. O usuário continua podendo ajustá-la; o novo controle usa uma chave versionada para não herdar automaticamente os 35% do padrão anterior.
- Câmera inicial afastada em 25%, mantendo a direção de cada vista e a proporção geométrica entre eixos.
- Altura do gráfico de 620 para 680 px; margens laterais/inferior maiores e espaço superior dedicado à legenda.
- Identificação da vista versionada para invalidar montagens/câmeras preparadas antes deste ajuste.

Teste focal: `checkpoints/refinamento_final_3d_2026-11-17/verificar.py`, executado de `NEW`. Confere opacidade, preservação do ajuste do usuário, câmera, margens e identidade das coordenadas/triângulos contra o checkpoint, incluindo compressor e turbina e as três vistas iniciais. Usa resultados existentes, sem recalcular modelos. A conferência de cortes no navegador continua necessária; ampliar manualmente a imagem pode naturalmente aproximar objetos das bordas.

Checkpoint: `checkpoints/refinamento_final_3d_2026-11-17/`, com cópia anterior e manifesto SHA256. Para voltar ao código anterior, restaurar `NEW/engine/webapp/assembly_3d.py` dessa pasta e recarregar a interface. A revisão documental é um arquivo novo; os documentos históricos foram preservados.
