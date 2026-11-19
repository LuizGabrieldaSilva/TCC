# Bloco 3 — continuidade entre estágios e reação da turbina

Implementação autorizada pelo autor, iniciada em 05/11/2026 e conferida em 06/11/2026.

## Resultado

Só o primeiro bocal conserva entrada axial. Os demais recebem o swirl de saída do rotor anterior. A reação meanline e radial agora usa a queda de entalpia estática do estágio no denominador, sem impor igualdade entre as energias cinéticas de entrada e saída.

Os oito casos de regressão preservaram exatamente os resultados do ciclo e do compressor, os estados totais da turbina, o trabalho por estágio, o raio médio, U, Cx, o número de estágios e os triângulos de entrada/saída dos rotores no raio médio. As mudanças esperadas são a entrada dos bocais posteriores, a reação estática e a geometria dimensionada com essa entrada.

Não foram ajustados os parâmetros de referência ou limites de Mach/reação para eliminar avisos. A validação global do TCC continua aberta: o fechamento manual ciclo–meanline e a representação das áreas dentro das fileiras são assuntos do próximo bloco.

## 1. Continuidade meanline

O plano de saída do estágio i alimenta diretamente o plano de entrada do estágio i+1:

```text
Ctheta1[i+1] = Ctheta3[i]
Cx1[i+1] = Cx3[i] = Cx
Tt1[i+1] = Tt3[i]
Pt1[i+1] = Pt3[i]
alpha1[i+1] = atan2(Ctheta1[i+1], Cx)
```

O plano intermediário não introduz trabalho, calor ou perda adicional de pressão. A perda politrópica prescrita continua representando cada estágio. Não se criou um retificador ou outra fileira intermediária.

A área de entrada passa a usar o módulo e o ângulo reais da estação 1:

```text
A1 = m_dot*sqrt(Tt1)/(Pt1*cos(alpha1)*MFP(M1))
```

Também foi acrescentada `A_saida_estagio`, calculada pelas condições da estação 3. Ela serve para conferir que a área exigida na saída anterior coincide com a área de entrada seguinte. O cálculo usa propriedades meanline; não integra densidade radial.

As temperaturas estáticas T1, T2 e T3 são armazenadas, com Tt2=Tt1 no bocal adiabático sem trabalho. Isso não supõe uma pressão total específica na estação 2: a repartição de perdas bocal/rotor continua não modelada.

## 2. Reação estática geral

Definição: Dixon & Hall, *Fluid Mechanics and Thermodynamics of Turbomachinery*, 7ª edição, Eq. 4.3a, página impressa 123 (PDF local 133):

```text
R = (h2-h3)/(h1-h3)
w = h01-h03 = cp*DeltaTt
h = h0-C²/2

dh_rotor = w + (C3²-C2²)/2
dh_estagio = w + (C3²-C1²)/2
R = dh_rotor/dh_estagio
```

Referência para a condição de repetição: mesmo livro, pp. 125–127, PDF 135–137. O primeiro estágio não precisa satisfazer essa condição. Todas as velocidades C dessas expressões são absolutas; a convenção de sinais tangenciais foi preservada.

A forma anterior `1-(Ctheta2+Ctheta3)/(2U)` continua sendo uma identidade útil no modelo de raio/Cx constantes, mas representa **queda estática no rotor dividida pelo trabalho de eixo**. Ela só coincide com a reação estática quando C1²=C3².

Essa razão alternativa foi conservada como diagnóstico, com nome explícito `reacao_rotor_por_trabalho`. O campo `grau_reacao` do meanline e `R_c` do radial agora representam a razão estática geral. No radial, C1, C2 e C3 são os valores locais da mesma seção.

O helper comum rejeita trabalho/velocidades não admissíveis e denominador de reação não positivo ou numericamente nulo. Ele não trunca reações negativas ou maiores que 1: esses valores continuam sendo sinalizados pelos verificadores, com interpretação de aumento estático na fileira correspondente.

## 3. Continuidade radial e limite geométrico

Cada distribuição livre de vórtice usa `K = r_m*Ctheta_m`. Como o raio médio permanece constante e Ctheta1 do estágio seguinte recebe Ctheta3 anterior, a mesma constante é preservada:

```text
K1[i+1] = K3[i]
Ctheta1[i+1](r) = Ctheta3[i](r), no mesmo raio físico r
```

Não é correto exigir igualdade entre valores identificados apenas pelo mesmo rótulo hub, mid ou tip, pois os raios desses rótulos mudam quando o anular varia. Os testes comparam a constante K e a velocidade em um raio comum às duas seções.

**Limitação preservada:** a geometria CAD ainda usa um anular representativo por estágio para as duas fileiras. A nova área de saída é um diagnóstico, não uma reconstrução da variação axial de altura das pás. Não foi implementado um mapeamento de tubos de corrente ou solução throughflow. Assim, o fechamento entre os planos meanline não equivale a uma solução geométrica/viscosa completa entre todas as estações.

## 4. Efeito no caso de referência manual

| Grandeza | Antes | Depois |
|---|---|---|
| alpha1 dos estágios 1/2/3 | 0 / 0 / 0° | 0 / -14,363441 / -14,363441° |
| Reação meanline dos estágios 1/2/3 | 0,536352 / 0,536352 / 0,536352 | 0,532263 / 0,536352 / 0,536352 |
| Área de entrada do estágio 1 | 0,038281112 m² | 0,038281112 m² |
| Área de entrada do estágio 2 | 0,060077738 m² | 0,060243625 m² |
| Área de entrada do estágio 3 | 0,101080911 m² | 0,101406876 m² |
| Z de bocal/rotor por estágio | 119 / 76 / 45 | 119 / 76 / 45 |

As cordas, alturas, raios de hub/tip e solidez locais posteriores acompanham as pequenas alterações de área. O número inteiro de pás permaneceu igual neste caso, mas não é garantido que permaneça em todas as entradas. Os bocais posteriores recebem ângulos de entrada diferentes; os perfis são regenerados com esses ângulos.

As duas interfaces da referência apresentaram resíduos nulos de Ctheta, Tt, Pt, área e K no registro da execução. A reação radial mínima passou para aproximadamente 0,373953.

Permanecem dois avisos de referência:

- Compressor, estágio 1, ponta: Mach relativo aproximadamente 1,001.
- Turbina, rotor do estágio 3, hub: câmber aproximadamente 97,76°, antes aproximadamente 97,69°. A pequena diferença decorre dos novos raios/triângulos locais.

O swirl de escape continua sendo verificado no último estágio. Os estágios intermediários passam seu swirl ao bocal seguinte, portanto não recebem mais repetidamente o aviso de swirl residual de escape. Os limites de Mach/reação não foram relaxados.

## 5. Interface e CSV

Novo painel recolhível na aba Turbina: **Continuidade entre estágios e reação estática da turbina**.

Ele apresenta os ângulos e as duas razões de reação por estágio, permite escolher a interface e compara velocidades, temperaturas total/estática, pressão total e área meanline. Um caso de um único estágio informa que não há interface intermediária a selecionar.

A tabela radial e a legenda da sensibilidade na interface identificam a reação como estática. O CSV da turbina conserva suas colunas anteriores e acrescenta reação estática meanline, razão rotor/trabalho local, quedas estáticas locais e área de saída meanline. A coluna anterior `grau_reacao_local` agora segue a definição estática corrigida; a antiga razão aparece separada como diagnóstico.

## 6. Verificações executadas

1. Snapshot anterior dos oito casos: razão de pressão 8 manual e 6/8/12 automático, cada um com 3 e 7 seções.
2. Regressão dos estados e grandezas preservados citados no início. O compressor completo registrado e os resultados do ciclo permaneceram iguais.
3. Continuidade de Ctheta, V, alfa, Tt, Pt e temperatura estática entre estágios; continuidade de K e velocidade no mesmo raio físico.
4. Continuidade de massa pelas condições estáticas meanline nas áreas de entrada e saída de cada estágio. As áreas nos dois lados de cada interface coincidiram.
5. Reação recuperada independentemente pelas temperaturas estáticas: `(T2-T3)/(T1-T3)`, no meanline e em todas as seções radiais.
6. Euler radial/meanline e energia nos oito casos, com resíduo máximo de aproximadamente **2,91e-11 J/kg**. Identidades usam tolerâncias relativa 1e-10 e absoluta 1e-8 nas unidades verificadas.
7. Triângulo sintético U=300 m/s, Cx=100 m/s, Ctheta2=250 m/s e Ctheta3=50 m/s: w=60 kJ/kg, queda estática no rotor=30 kJ/kg, queda estática do estágio=61,25 kJ/kg e R=0,489795918. Quando C1=C3, a razão volta a 0,5. É um teste analítico, não um exemplo numérico atribuído ao livro.
8. Rejeição de denominadores/entradas inválidos e preservação de uma reação negativa sem truncamento. Testado aviso de swirl habilitado/desabilitado conforme posição de escape.
9. Idempotência: executar resolver() novamente não altera os resultados nem reutiliza o swirl final como entrada do primeiro estágio.
10. Casos adicionais de um estágio e de saída axial sem swirl. O primeiro não exige interface intermediária; no segundo, as duas definições de reação coincidem.
11. **980 perfis** reconferidos nos oito casos: Carter, orientação, solidez, coordenadas e tangentes 3D. Maior erro angular de discretização aproximadamente 0,011589°, abaixo da tolerância de 0,02° com 200 subdivisões.
12. AppTest do Streamlit nos modos manual, um estágio e automático, sem exceções. Seleção da interface 2→3 e conferência da tabela de resíduos. O automático adotou quatro estágios e herdou swirl positivo, mostrando que o código não impõe sinal negativo ao escoamento.
13. As 56 avaliações de sensibilidade do caso de referência concluíram sem casos computacionalmente inválidos. Avisos e recomendações físicas continuam sendo registrados.
14. CSV da referência com 21 linhas e campos de reação/área conferidos; seis DXFs da turbina gerados e conferidos quanto a entidades e terminador. Saídas foram gravadas somente no checkpoint.
15. Arquivos Python de engine passaram por análise sintática.

AppTest não é conferência visual do navegador. Não foi realizada abertura dos DXFs em aplicativo CAD, verificação de sólido STEP, ensaio de turbina ou validação experimental. Não foram ajustadas as entradas para obter a contagem de dois avisos.

## 7. Reprodução

Na pasta NEW:

```powershell
python -m engine.estudos.verificar_estagios_turbina --antes ../checkpoints/bloco3_turbina_2026-11-05/antes.json --saida ../checkpoints/bloco3_turbina_2026-11-05/depois.json
python -m engine.estudos.verificar_geometria_perfis --saida ../checkpoints/bloco3_turbina_2026-11-05/perfis_depois.json
streamlit run engine/webapp/streamlit_app.py
```

Reiniciar o processo Streamlit e recalcular o caso para carregar as classes e os campos novos. O comparador antigo de snapshots de `verificar_acoplamento --antes` exige áreas/entradas invariantes e não deve ser usado para aprovar este bloco, que altera essas grandezas intencionalmente. As identidades desse verificador foram reutilizadas, e o novo comparador separa campos preservados de mudanças previstas.

## 8. Checkpoint e recuperação

Pasta: `checkpoints/bloco3_turbina_2026-11-05/`. A data do nome corresponde ao início do trabalho; a conferência final foi em 06/11.

O manifesto e as cópias preservam seis arquivos anteriores ao bloco 3:

- `NEW/engine/turbina/Turbine_Meanline_main.py`.
- `NEW/engine/aero/radial_turbina_3_main.py`.
- `NEW/engine/aero/constraints.py`.
- `NEW/engine/geometry/airfoil4.py`.
- `NEW/engine/webapp/streamlit_app.py`.
- `NEW/engine/estudos/export_csv.py`.

Para voltar, restaurar somente essas seis cópias aos respectivos caminhos e reiniciar o Streamlit. Elas incluem os blocos 1 e 2 anteriores. Os novos arquivos `aero/reacao_turbina.py`, `estudos/verificar_estagios_turbina.py` e este relatório podem permanecer sem uso pela versão restaurada; o novo verificador depende dos campos da versão corrigida.

Os resultados ficam em `antes.json`, `depois.json`, `perfis_depois.json`, `interface_exportacoes.json`, `stdout_interface.txt` e `exportacoes/`, todos dentro do checkpoint. Não foram sobrescritos os CSVs/DXFs antigos do usuário. Não restaurar o repositório inteiro: há arquivos e mudanças preexistentes de outros projetos no Git pai.

Próximo bloco: explicitar e conciliar os resíduos ciclo–meanline no modo manual e as áreas necessárias nas diferentes estações. A correção atual fecha os planos entre estágios no modelo adotado, sem declarar resolvidas essas outras limitações.
