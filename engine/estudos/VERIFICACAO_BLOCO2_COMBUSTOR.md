# Bloco 2 — comprimento do combustor e fontes dos combustíveis

Implementado e conferido em 05/11/2026, com autorização do autor.

## Alteração física

A Eq. 10-34 de Mattingly usa a pressão total na **entrada** da câmara. A notação do livro é Pt3; a notação do ciclo deste projeto é P02. A temperatura Tt4 do livro corresponde à TIT do projeto.

```text
L = L_ref * (P02/Pt3_ref)^(-r) * sqrt(Tt4_ref/TIT)
```

O código usava P03, pressão de saída após a perda do combustor. Agora usa P02. Foram mantidos os valores convertidos/arredondados da referência JT9D: L_ref=0,4394 m, Pt3_ref=2179 kPa, Tt4_ref=1592 K e r=0,714.

Fonte realmente conferida: Mattingly, *Elements of Gas Turbine Propulsion*, p. 821, Eq. 10-34; p. 822, tabela 10-5 e exemplo de escala JT9D. No PDF local `ELEMENTS OF GAS TURBINE PROPULTION2.pdf`, páginas 886–887, contadas a partir de 1. Equação, tabela e correspondência de estações foram conferidas também nas imagens das páginas.

| Caso | Antes | Depois |
|---|---:|---:|
| Referência do projeto, P02=800 kPa, TIT=1200 K, perda=5% | 107,363267 cm | 103,502389 cm |
| Exemplo do livro, pressão de entrada=350 psia e temperatura de saída=2900 °R | A aplicação anterior com perda de 5% dava aproximadamente 16,584 in | 15,987614 in; livro publica 16,0 in |

A expressão calculada diretamente nas unidades publicadas, antes dos arredondamentos de conversão usados pelo projeto, dá 15,985323 in. A diferença de aproximadamente 0,0023 in entre as duas versões decorre dos arredondamentos da referência. O teste aceita diferença inferior a 0,025 in em relação aos 16,0 in impressos.

O exemplo foi executado com uma fixture de condições de entrada do combustor, isolando a escala. Não foi reproduzido o ciclo completo ou o desempenho real do JT9D.

## Hipóteses preservadas e explicitadas

A lei de comprimento continua sendo uma escala entre projetos semelhantes, não dimensionamento por primeiros princípios. A derivação pressupõe, entre outras condições, razão A4/Aref constante e escoamento estrangulado na entrada da turbina. O programa não verifica essas duas condições. Vazão e Mach entram no cálculo da área, mas não diretamente nesta escala de comprimento.

Não foram incluídos difusor, cinética, atomização, zona primária, recirculação, perfil de temperatura, correlação preditiva de perda de pressão ou teste de estabilidade da chama.

O balanço que calcula f continua incluindo a massa de combustível nos gases. Somente Q_total conserva a aproximação de aumento de entalpia do ar. Essa distinção foi corrigida no cabeçalho do módulo e no nome impresso pela execução de terminal, preservando a variável e seu valor para compatibilidade.

## Rastreabilidade por propriedade

Os números de COMBUSTIVEIS e F_STOICH foram preservados. A atribuição incorreta de todo o catálogo à tabela 2-4 foi removida. Na cópia local, a tabela 2-4, p. 106 (PDF 171), contém constantes de propriedades termodinâmicas de ar e produtos de combustão, não os PCI do catálogo.

| Combustível | PCI usado | Situação do PCI | f_stoich usado | Situação de f_stoich |
|---|---:|---|---:|---|
| JP-4 | 42,8 MJ/kg | Mattingly, exemplo p. 816 (PDF 881), informa 42.800 kJ/kg | 0,0667 | Informado no mesmo exemplo para JP-4 |
| JP-8 | 43,2 MJ/kg | Nominal compatível com a tabela 10-6, p. 826 (PDF 891): 10.333 cal/g = 43,233272 MJ/kg usando 1 cal=4,184 J | 0,0667 | Hipótese de usar o mesmo valor de JP-4; não confirmado como dado específico de JP-8 nessa tabela |
| Gás natural | 50,0 MJ/kg | Valor nominal adotado, sem fonte específica confirmada nesta revisão; depende de composição | 0,0580 | Hipótese de metano: 4 kg O2/kg CH4, com fração mássica de O2 no ar assumida como 0,232; 0,232/4=0,0580 |
| Diesel | 42,5 MJ/kg | Valor nominal adotado, sem fonte específica confirmada nesta revisão | 0,0664 | Valor nominal adotado, sem composição química definida ou fonte específica confirmada |

No JP-8, foi consultada a coluna de valor típico, não o mínimo de especificação. Não se afirma que o PCI escolhido caracterize todo lote de combustível. Os dados do exemplo de JP-4 e os dados típicos da tabela 10-6 são conjuntos distintos; não precisam ter o mesmo número.

Para gás natural, a hipótese equivalente reconstruída para f_stoich não transforma o PCI de 50 MJ/kg em um valor validado por fonte, nem representa uma mistura real de gás natural. Para diesel, a ausência de composição impede reconstituir de forma única f_stoich. Esses limites permanecem visíveis em vez de se inventar uma referência ou alterar os números para aparentar concordância.

Assim, foi implementada **rastreabilidade explícita**, incluindo lacunas. A confirmação bibliográfica de todas as propriedades de todos os combustíveis continua pendente; não se declara o catálogo inteiro validado.

O novo método `Combustor1D.fontes_combustivel()` retorna valores, unidades, situação da origem, referência e hipótese de cada propriedade. O retorno é uma cópia. Se h_PR for passado explicitamente ao construtor, sua origem é identificada como fornecida pelo chamador, sem atribuí-la à referência do catálogo.

## Interface

Na aba Combustor foram acrescentados dois painéis recolhíveis:

- **Fontes e hipóteses do combustível:** dados do combustível da execução calculada, com origem separada para PCI e f_stoich.
- **Como o comprimento é estimado — referência JT9D:** equação, correspondência das estações, pressão atual usada e valores da referência, com hipóteses de semelhança.

Os tooltips de combustível, PCI e comprimento foram atualizados. Os painéis acompanham o caso submetido; mudar o formulário exige recalcular, como os demais resultados. A documentação não acrescenta avisos físicos artificiais à contagem global.

## Verificações executadas

1. Snapshot anterior dos quatro combustíveis e dos três dicionários de constantes.
2. Comparação campo a campo dos resultados antes/depois: **somente L_comb mudou**. PCI, f_stoich, razão combustível/ar, equivalência, vazões, pressões, temperaturas, área, diâmetro e Q_total foram preservados.
3. Fechamento de energia com a massa de combustível, nos quatro combustíveis, usando tolerâncias relativa 1e-12 e absoluta 1e-7 W.
4. Exemplo JT9D de Mattingly, recuperação exata de L_ref quando as condições coincidem com as da referência e invariância de L com perdas de 0%, 5% e 20% quando P02 e TIT são mantidos. O último teste detectaria a reutilização indevida de P03.
5. Metadados de todos os combustíveis, cópias independentes e origem correta para PCI personalizado de 44 MJ/kg.
6. Reconstrução da hipótese de f_stoich do metano e conversão explícita do valor típico da tabela de JP-8.
7. Verificador de acoplamento: oito casos anteriores passaram; estados, áreas, U, triângulos e número de estágios preservados, com Euler consistente.
8. AppTest do Streamlit com JP-4, JP-8 e diesel: execução sem exceções, comprimento de 103,50 cm e painéis de fontes atualizados conforme o combustível. As 56 avaliações de sensibilidade de cada execução concluíram sem casos computacionalmente inválidos, totalizando 168 avaliações. Isso não certifica viabilidade física.
9. Análise sintática dos arquivos Python de engine sem erros.

Os três casos de interface conservaram dois avisos: Mach relativo na ponta do primeiro estágio do compressor e câmber do rotor da turbina no terceiro estágio/hub. A alteração do comprimento não elimina essas pendências.

Não houve inspeção visual em navegador nesta etapa: AppTest verifica a execução e os valores, não a aparência final. Não foram refeitas exportações CAD, pois a escala L_comb não alimenta a geração dos perfis ou o loft das turbomáquinas nesta cadeia.

## Reprodução

Na pasta NEW:

```powershell
python -m engine.estudos.verificar_combustor --antes ../checkpoints/bloco2_combustor_2026-11-05/antes.json --saida ../checkpoints/bloco2_combustor_2026-11-05/depois.json
python -m engine.estudos.verificar_acoplamento --antes ../checkpoints/bloco1_geometria_2026-11-05/depois.json --saida ../checkpoints/bloco2_combustor_2026-11-05/acoplamento_depois.json
streamlit run engine/webapp/streamlit_app.py
```

Reiniciar o processo Streamlit e recalcular o caso para carregar a classe corrigida e os novos painéis.

## Checkpoint e recuperação

Pasta na raiz do TCC: `checkpoints/bloco2_combustor_2026-11-05/`.

`manifesto.json` e as cópias preservam o estado anterior de:

- `NEW/engine/combustor/Combustor_1D_2_main.py`.
- `NEW/engine/webapp/streamlit_app.py` — inclui o bloco 1 já concluído.

Para voltar apenas ao estado anterior ao bloco 2, restaurar essas duas cópias aos respectivos caminhos e reiniciar o Streamlit. Os novos arquivos `estudos/verificar_combustor.py` e este relatório podem permanecer sem uso; o novo verificador depende do método de rastreabilidade da versão corrigida.

Os JSONs `antes.json`, `depois.json`, `acoplamento_depois.json` e `interface_depois.json` registram os resultados. Nenhum dado antigo em saida_dxf foi sobrescrito. Não restaurar o repositório inteiro, que abrange alterações preexistentes de outros trabalhos.

Próximo bloco recomendado: continuidade de swirl entre estágios da turbina e definição de reação. Essas equações não foram modificadas neste bloco.
