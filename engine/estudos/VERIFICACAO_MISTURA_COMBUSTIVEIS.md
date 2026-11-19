# Mistura dos produtos de combustão e propriedades constantes equivalentes

Implementação: 19/11/2026. Checkpoint anterior: `checkpoints/mistura_combustiveis_2026-11-19/`, na raiz TCC. Nenhum valor de ψ, número manual de estágios ou prioridade de seleção foi ajustado nesta tarefa.

## Modelo e alcance

O modo automático é o padrão da interface e do caso de referência. A API `CicloBrayton` conserva `mistura_automatica=False` como padrão para não mudar silenciosamente exercícios e chamadas antigas. A interface permite desativar o automático; arquivos de entradas v1/v2 são migrados para **propriedades prescritas**, e v3 registra explicitamente a escolha.

Ar seco em frações molares: N₂=0,78084; O₂=0,209795; Ar=0,009365. CO₂-traço e umidade são omitidos. O cp do ar permanece prescrito; R do ar deriva dessa composição, e k=cp/(cp−R).

Para CₓHᵧ, a=x+y/4. Os produtos por mol de combustível são:

```
x CO2 + (y/2) H2O + a(λ−1) O2
       + aλ(zN2/zO2) N2 + aλ(zAr/zO2) Ar
```

λ resulta da vazão de ar efetiva: λ=f_stoich/f. A razão estequiométrica usa a mesma composição e massas molares dos balanços. As frações molares são convertidas em **frações mássicas** antes de ponderar propriedades por kg. Água permanece vapor, em base úmida. Misturas ricas são recusadas: combustão incompleta não é resolvida.

| Combustível selecionado | Representação elementar | PCI mantido (MJ/kg) | Alcance |
|---|---|---:|---|
| JP-4 | CH₁,₉₄ | 42,8 | Média elementar da fonte NASA; não resolve lote real |
| JP-8 | C₁₂H₂₃ | 43,2 | Substituto elementar baseado em Jet-A; aditivos omitidos |
| Gás natural | CH₄ | 50,0 | Metano puro; composição real de gás natural não resolvida |
| Diesel | C₁₂H₂₃ | 42,5 | Diesel mineral representativo; sem biodiesel/impurezas |

**JP-8 e diesel:** o substituto comum não permite atribuir diferenças intrínsecas fictícias. Para o mesmo f e temperatura, as propriedades calculadas são iguais. No caso resolvido, PCI distintos exigem f distintos, mudam produtos/excesso de ar e produzem propriedades diferentes. Modelar diferenças adicionais exigiria composições elementares ou substitutos específicos documentados. Não se adotou C₁₂H₂₆ só para separar números.

Os PCI foram preservados do catálogo anterior. JP-4 e JP-8 têm registros bibliográficos no projeto; os PCI nominais de gás natural e diesel continuam identificados como fonte específica pendente na interface. O novo cálculo de composição não transforma esses PCI em dados certificados de um combustível real.

## Propriedades e energia

São usados todos os sete termos NASA Glenn:

```
cp_molar/Ru = a1/T² + a2/T + a3 + a4 T + a5 T² + a6 T³ + a7 T⁴
```

Intervalos 200–1000 K e 1000–6000 K, com integração separada em 1000 K. Ar monoatômico: cp_molar=2,5Ru. Ru=8,31446261815324 J/(mol K). As constantes de integração/entalpias de formação da NASA **não são somadas ao PCI**, para evitar dupla contagem da energia química.

Para cada composição:

```
h_g(TIT) = soma Y_i integral[298,15→TIT] cp_i(T) dT
cp_g_equivalente = h_g(TIT)/(TIT−298,15)
R_g = Ru/M_mistura; k_g = cp_g/(cp_g−R_g)
h_ar(T02) = cp_ar (T02−298,15)
f η_b PCI = (1+f) h_g(TIT) − h_ar(T02)
```

A composição e f são resolvidos conjuntamente por bisseção no intervalo pobre/estequiométrico. η_b é a fração da energia do PCI aproveitada; os produtos continuam sendo de combustão completa, sem calcular uma fração não queimada.

**cp equivalente permanece constante durante toda a expansão.** A integral NASA reproduz a entalpia sensível dos produtos até TIT, mas não torna exata a queda de entalpia na turbina em outras temperaturas. Não é um ciclo com cp(T) integrado, nem uma solução de equilíbrio/dissociação ou validação experimental. Essa escolha mantém o modelo de gás ideal com propriedades constantes por região.

No modo prescrito, mantém-se a convenção algébrica legada h=cp·T para reprodução dos exercícios. A interface e os relatórios distinguem os dois modos e suas referências de entalpia. `Q_total` continua apenas aquecimento virtual de ar: ma cp_ar(TIT−T02). O balanço útil usa h dos produtos e inclui a massa de combustível.

## Resultados no caso de referência

T01=300 K, P01=100 kPa, razão de pressão=8, TIT=1200 K, cp_ar=1005 J/(kg K), η_b=0,99, vazão de ar=15 kg/s. Os números abaixo são do ciclo, com os mesmos alvos e eficiências; diferenças manuais ciclo–meanline continuam expostas.

| Combustível | f (kg/kg de ar) | cp_g (J/(kg K)) | R_g (J/(kg K)) | k_g | Potência líquida do ciclo (kW) |
|---|---:|---:|---:|---:|---:|
| JP-4 | 0,016837847 | 1.112,558579 | 287,116148 | 1,347833 | 2.392,370325 |
| JP-8 | 0,016667502 | 1.112,071503 | 287,066832 | 1,347958 | 2.389,645837 |
| Metano | 0,014582265 | 1.124,178257 | 290,411691 | 1,348313 | 2.455,300566 |
| Diesel | 0,016958663 | 1.112,516358 | 287,066453 | 1,347770 | 2.392,175509 |

Não interpretar a pequena diferença JP-8/diesel como precisão experimental sobre combustíveis comerciais. Ela é consequência dos substitutos e PCI adotados.

## Fontes e rastreabilidade

- NASA/TP-2002-211556, *NASA Glenn Coefficients for Calculating Thermodynamic Properties of Individual Species*, arquivo local `20020085330 NASA Glenn Coefficients.pdf`. Equação 1, p.2 (PDF 10); CO₂ p.85 (PDF 93), H₂O p.131 (PDF 139), N₂ p.156 (PDF 164), O₂ p.166 (PDF 174). Os 56 coeficientes a1…a7 desses produtos, nos dois intervalos, foram conferidos contra as tabelas. Os JSON incluídos no módulo conservam esses valores.
- Mesmo relatório: CH₄ p.83 (PDF 91); JP-4 CH₁,₉₄ p.278 (PDF 286); Jet-A C₁₂H₂₃ p.279 (PDF 287). A entrada de JP-4 fornece composição elementar, não curva cp utilizável do combustível.
- [NIST, caracterização de combustíveis de aviação](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=920223): contexto da relação e distinções entre JP-8 e combustíveis Jet; não se afirma identidade exata.
- [NASA NTRS 20240010989](https://ntrs.nasa.gov/api/citations/20240010989/downloads/Thermal%20Management%20of%20Primary%20Fuel%20Cell%20System.pdf), p.31: representação de diesel por C₁₂H₂₃. Trata-se de substituto para balanços, não composição universal de diesel.

Os arquivos OLD foram apenas consultados. A implementação nova corrige os problemas identificados ali: uso indevido de frações molares na média de cp mássico/R e omissão dos termos inversos de temperatura. Não se alteraram os arquivos antigos.

## Verificações e limites das evidências

`verificar_mistura_gases.py` verifica a primitiva por integração numérica independente, inclusive cruzando 1000 K; continuidade dos ajustes; conservação de C/H/O/N/Ar e massa; frações e massas molares; energia, f e propriedades; recusas de domínio; oito pipelines dos quatro combustíveis em modos manual/automático; fechamento de Euler nos raios; preservação do modo de potência; ausência de diferenças artificiais para substitutos idênticos.

As suítes existentes verificam acoplamento, combustor, estágios de turbina, diagnósticos, indicadores, perfis, entradas, importações e reprodução do modo prescrito. As expectativas de k/cp prescritos foram explicitadas nas suítes correspondentes, sem relaxar tolerâncias físicas para aprovar o modo novo.

AppTest verifica cálculo e sensibilidade, troca de combustível, campos prescritos desativados no automático, JSON v1/v2/v3, relatório ZIP com composição/propriedades, retorno ao modo prescrito, diagramas e geração 3D. Trata-se de teste funcional; não substitui inspeção visual no navegador.

O conjunto histórico dos livros continua **28/29**: permanece a divergência anterior de arredondamento de β₂ no cubo do exemplo Dixon, sem ampliar tolerâncias ou ocultá-la. A reprodução específica Mattingly com cp_ar=1004 e cp_g=1235 continua passando no modo prescrito. Não se exige coincidência do novo modelo com exercícios que prescrevem propriedades diferentes. A revisão bibliográfica completa e o tratamento das discrepâncias ciclo–meanline permanecem tarefas separadas, conforme combinado.

Os logs, resultados JSON, relatórios gerados e manifesto dos arquivos estão no checkpoint desta tarefa. As verificações comprovam consistência no escopo testado; não validam chama, choque, estol/surge, materiais ou uma máquina fabricável.
