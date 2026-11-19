# Comparação numérica com exemplos dos livros

Data: **18/11/2026**. Esta revisão usa o código atual e consulta direcionada dos PDFs locais. Não é leitura integral dos cinco livros, ensaio experimental ou certificação de um motor.

## Resultado e alcance

Foram executados **sete grupos bibliográficos, com 29 comparações escalares**. Destas, **28 ficaram nas tolerâncias estabelecidas** e uma ficou fora: β₂ no cubo do exemplo 6.1 de Dixon. A diferença foi investigada e registrada abaixo, sem ampliar a tolerância nem alterar o modelo. A comparação adicional do combustor com propriedades distintas é apresentada separadamente como diferença de hipótese, não como um teste que deveria coincidir.

As 29 linhas não são 29 validações independentes: incluem preparação analítica de entradas, pós-processamento e uma identidade de conversão de eficiência. A tabela numérica completa e o JSON distinguem esses alcances. Não se considera uma equação reescrita no verificador como prova de que o solver completo a implementa corretamente.

Nenhum código físico, parâmetro padrão, limite de aviso ou prioridade da seleção automática foi modificado. Foram acrescentados somente este relatório e o verificador bibliográfico. A matriz anterior continua sendo um registro histórico; suas evidências não se tornam atuais automaticamente.

## Referências e cobertura

Páginas PDF abaixo contadas a partir de 1.

| Livro | Trechos conferidos nesta tarefa | Tipo de evidência obtida |
| --- | --- | --- |
| Saravanamuttoo, Cohen e Rogers, *Gas Turbine Theory* | Exemplo 2.1, impressas 74–76 / PDF 91–93; anular, impressas 210–211 / PDF 227–228 | Números publicados comparados ao ciclo (compressão), diagnóstico de área e função de raios |
| Dixon & Hall, *Fluid Mechanics and Thermodynamics of Turbomachinery*, 7ª ed. | Exemplo 3.1, pp. 86–87 / PDF 97–98; Eq. 4.3a, p. 123 / PDF 133; continuidade, pp. 134–135 / PDF 144–145; exemplo 4.2, pp. 138–139 / PDF 148–149; exemplo 5.1(a), p. 178 / PDF 187; exemplo 6.1, pp. 219–221 / PDF 228–230 | Carter, helpers de Mach, solver radial do compressor, reação estática e área da turbina |
| Mattingly, *Elements of Gas Turbine Propulsion* | Exemplo de mistura, p. 816 / PDF 881; Eq. 10-34 e tabela 10-5/exemplo JT9D, pp. 821–822 / PDF 886–887 | Escala de comprimento reproduzida no combustor; diferença de propriedades quantificada |
| Boyce, *Gas Turbine Engineering Handbook*, 2ª ed. | p. 125 / PDF 141 | Suporte conceitual à distinção entre eficiência politrópica e isentrópica; sem novo benchmark numérico independente |
| Lakshminarayana, *Fluid Dynamics and Heat Transfer of Turbomachinery* | p. 49 / PDF 78, Eqs. 2.4–2.7; p. 63 / PDF 92, Eq. 2.26 | Conferência visual das definições de torque, Euler, carga e vazão; sem novo exemplo numérico independente |

Boyce e Lakshminarayana têm camadas textuais insuficientes para esses trechos; as páginas foram renderizadas e consultadas visualmente. Também foram inspecionadas visualmente páginas dos exemplos de Dixon, Mattingly e Saravanamuttoo para confirmar equações, unidades e diagramas. As páginas renderizadas e os hashes dos cinco PDFs estão na pasta de evidências.

## 1. Ciclo: Saravanamuttoo, exemplo 2.1

Entradas publicadas usadas: T₀₁=288 K, razão de pressão 4, k=1,4 e eficiência **isentrópica** do compressor 0,85. A API recebe eficiência **politrópica**. Faz-se explicitamente a conversão:

`τ = 1 + (π^((k−1)/k) − 1)/η_s`

`η_p = ((k−1)/k) ln(π)/ln(τ) = 0,8759149032`.

`CicloBrayton.resolver()` fornece T₀₂=**452,666300 K**, contra **452,7 K** publicado. Diferença: **−0,033700 K**, tolerância de reprodução 0,1 K.

O teste adicional de recuperar η_s=0,85 é uma identidade de conversão, não uma segunda evidência bibliográfica. Não se compara a eficiência global desse motor com o livro: o exemplo possui recuperador, propriedades distintas para gases, perda no escape e rendimento mecânico, características que não compõem nosso ciclo simplificado.

## 2. Compressor: área e anular de Saravanamuttoo

Com T₀₂=452,5 K, P₀₂=419 kPa, velocidade axial 150 m/s, swirl zero e vazão 20 kg/s, o diagnóstico `_plano` fornece **0,044018807 m²**, contra cerca de **0,0440 m²** publicado. A diferença é 0,000018807 m², dentro de 0,0001 m².

Usando separadamente a área publicada 0,0440 m² e raio médio aritmético 0,1697 m, `raios_anular` fornece:

| Grandeza | Código (m) | Livro (m) | Tolerância (m) |
| --- | ---: | ---: | ---: |
| Raio do cubo | 0,149067067 | 0,1491 | 0,00005 |
| Raio da ponta | 0,190332933 | 0,1903 | 0,00005 |
| Altura | 0,041265866 | 0,0413 | 0,00005 |

Isto confere duas partes isoladas; não reproduz a máquina inteira do livro. O R derivado de cp/k no projeto difere ligeiramente do 287 J/(kg·K) empregado nos números arredondados do livro.

## 3. Perfis: Dixon, exemplo 3.1

O livro fornece ângulos do escoamento de 50° e 30°, incidência 3° e passo/corda 0,85. O verificador transforma a entrada em **ângulo metálico de 47°**, antes de chamar `gerar_perfil_pa(47, 30, 1/0.85, 0.05)`.

Resultados: desvio **6,203971°** e câmber **23,203971°**, contra **6,2°** e **23,2°** publicados. Tolerância: 0,05°.

Esta preparação não significa que o solver passe a calcular incidência diferente de zero. São conferidas a correlação de Carter e sua solução algébrica; perdas, separação e desempenho de cascata não foram reproduzidos.

## 4. Mach: Dixon, exemplo 5.1(a)

Usam-se T₀₁=288 K, Mach relativo 0,9, ângulo relativo 45°, entrada absoluta axial, k=1,4 e R=287,15 J/(kg·K). A preparação analítica fornece U=**208,271256 m/s**, próximo dos **208,3 m/s** do livro. O cp é compatibilizado com R e k para este teste, sem mudar o padrão do projeto.

Com essas velocidades, os helpers reais `_mach` e `_mach_relativo` retornam **0,636396103** e **0,900000000**. A velocidade absoluta determina a temperatura estática usada no Mach relativo. O cálculo externo de U prepara o teste; não é um resultado obtido pelo solver meanline.

As perdas e pressões das demais partes desse exemplo transônico não são cobertas. A concordância de Mach não valida um modelo de choque.

## 5. Distribuição radial: Dixon, exemplo 6.1

Entradas: raio de ponta 0,50 m, cubo 0,45 m, rotação 6000 rpm, densidade constante 1,5 kg/m³ e ângulos na ponta α₁=30°, β₁=60°, α₂=60°, β₂=30°. A preparação dos triângulos fornece Cx=**136,034952 m/s**. Os valores no raio médio aritmético são preparados pela própria hipótese de vórtice livre e entregues a `RadialCompressor.resolver()` com três seções.

A vazão, calculada externamente com a densidade publicada, é **30,449856 kg/s**, contra **30,4 kg/s**. Euler aplicado às velocidades produzidas pelo solver radial fornece **1,502640 MW**, contra **1,5 MW**.

| Grandeza no cubo | Código | Livro | Diferença | Tolerância |
| --- | ---: | ---: | ---: | ---: |
| α₁ (°) | 32,680184 | 32,75 | −0,069816 | 0,1 |
| β₁ (°) | 55,165431 | 55,15 | +0,015431 | 0,1 |
| α₂ (°) | 62,542924 | 62,6 | −0,057076 | 0,1 |
| β₂ (°) | 8,752538 | 8,64 | +0,112538 | 0,1: **fora** |
| Reação | 0,382716 | 0,382 | +0,000716 | 0,001 |

**Investigação da diferença de β₂:** a página 220 publica uma tangente intermediária de 0,152; `atan(0,152)` dá aproximadamente 8,643°, compatível com o 8,64° publicado. Usando os dados geométricos e angulares originais, sem os arredondamentos intermediários, a tangente é aproximadamente 0,153960, correspondente a 8,752538°. A diferença é compatível com a aproximação numérica da resolução impressa, e não evidencia por si um erro no solver radial. Mantém-se o teste fora da tolerância original de 0,1°, visível no JSON e no código de saída.

A fixture inclui valores auxiliares de temperatura, corda e Z para satisfazer a estrutura do objeto. Esses valores não são fornecidos pelo livro nem são evidência de reprodução de Mach, DF, termodinâmica ou geometria dessa máquina. O solver compressível completo não foi forçado a usar a densidade constante do exemplo.

## 6. Turbina: Dixon, exemplo 4.2

Entradas: cinco estágios repetitivos, vazão 15 kg/s, potência 6,64 MW, raio médio 0,46 m, rotação 5600 rpm, T₀₁=1200 K, P₀₁=213 kPa, cp=1150 J/(kg·K), k=1,333. Os módulos dos ângulos são 15° na entrada e 70° na saída do bocal.

O diagrama do livro coloca o swirl de entrada e saída do estágio em sentido oposto ao da saída do bocal. Na convenção assinada do projeto, usam-se **Cθ₁=Cθ₃<0 e Cθ₂>0**. Assim se evita somar ou subtrair módulos com sinais incompatíveis.

| Grandeza | Calculado | Publicado | Tolerância absoluta |
| --- | ---: | ---: | ---: |
| U, preparação (m/s) | 269,758089 | 269,8 | 0,1 |
| ψ, preparação | 1,216628 | 1,217 | 0,001 |
| φ, preparação | 0,403468 | 0,403 | 0,001 |
| Reação estática | 0,499795 | 0,5 | 0,002 |
| Mach de entrada | 0,166602 | 0,166 | 0,001 |
| Área de entrada (m²) | 0,226170 | 0,227 | 0,001 |
| Altura (m) | 0,078252 | 0,0785 | 0,0005 |
| HTR | 0,843221 | 0,843 | 0,002 |

O teste aciona `reacao_estatica`, `_plano` e `raios_anular`. U, ψ, φ e triângulos são preparação analítica. Não se afirma reprodução de `TurbinaAxialMeanline` inteira: nosso primeiro bocal recebe entrada axial, enquanto o exemplo adota cinco estágios repetitivos com swirl de entrada.

O exemplo usa tabelas compressíveis e valores arredondados. Nosso diagnóstico deriva R=287,284321 J/(kg·K) de cp/k, ligeiramente diferente de R=287,2 publicado. A página 139 apresenta H=0,0785 m e a conversão seguinte como 78,2 mm, valores inconsistentes entre si. Registra-se H=0,0785 m como alvo da equação; o resultado contínuo do diagnóstico fica próximo de 78,25 mm. Não se alterou código para imitar a contradição editorial.

## 7. Combustor: escala de Mattingly

A referência JT9D possui comprimento 17,3 in, pressão 316 psia e temperatura de saída 2865 °R. O exemplo pede 350 psia e 2900 °R, com expoente r=0,714. Convertem-se pressões para Pa e temperaturas **absolutas** para K, usando K=°R×5/9.

`Combustor1D.resolver()` retorna **15,987614 in**, contra **16,0 in** publicado, diferença −0,012386 in; tolerância 0,025 in. O próprio módulo usa referências convertidas e arredondadas. Esta é uma escala para projetos semelhantes, não reprodução de combustão, dimensionamento detalhado ou desempenho do JT9D.

Um ciclo auxiliar resolvido prepara as condições de entrada exigidas pela API. Seus demais estados não representam o motor do livro e não são comparados.

## 8. Combustor: diferença de hipótese quantificada

O exemplo da p. 816 de Mattingly usa Tentrada=653 K, TIT=1670 K, eficiência de combustão 1, PCI=42,8 MJ/kg, cp do ar=1004 e cp dos gases=1235 J/(kg·K). O modelo atual conserva um único cp; nesta comparação usa-se o padrão 1005 J/(kg·K).

| Resultado | Livro publicado | Equação externa com cp distintos | Modelo com cp único |
| --- | ---: | ---: | ---: |
| f (kg combustível/kg ar) | 0,0346 | 0,034534183 | 0,024855155 |
| Razão de equivalência | 0,519 | aproximadamente 0,5178 | 0,372641 |

A diferença de f do modelo em relação ao valor publicado é **−28,1643%**. A equação externa reproduz o balanço com cp distintos; não é apresentada como resultado do código do combustor. A pequena diferença entre essa equação e o valor impresso também é conservada, sem ajustar entradas para coincidir.

Isso não indica automaticamente erro algébrico no balanço com cp único: indica que essa hipótese não reproduz quantitativamente o exemplo com propriedades distintas. Fechar o balanço interno não elimina esse erro de representação. A magnitude encontrada pertence a essas temperaturas e propriedades; não pode ser transferida diretamente ao caso de referência do TCC.

**Possível melhoria futura, sujeita a autorização:** separar cp do ar e dos gases de forma consistente no combustor, no ciclo, na turbina e nos indicadores. Alterar somente a fórmula de f deixaria a integração com hipóteses incompatíveis. Nenhuma dessas alterações foi aplicada nesta tarefa.

## Reprodução, integridade e interpretação dos resultados

Da pasta `NEW`, usando o ambiente do projeto:

```powershell
python -X utf8 -m engine.estudos.verificar_exemplos_livros --saida resultados_livros.json
```

O comando preserva os modelos. Escreve apenas o JSON solicitado, além dos caches normais de importação. O código de saída é **1 quando alguma comparação excede a tolerância**. Nesta versão isso ocorre em β₂ do exemplo 6.1; não é um erro de inicialização nem deve ser ocultado para tornar a bateria verde. Leia as entradas, o escopo e a explicação junto ao resultado.

Evidências da execução desta tarefa: `checkpoints/exemplos_livros_2026-11-18/`, na raiz do TCC:

- `manifesto.json`: os dois arquivos acrescentados não existiam; reversão não requer restaurar modelos.
- `fontes_antes.json` e `integridade.json`: hashes dos arquivos preexistentes e dos cinco PDFs.
- `resultados.json` e `tabela_resultados.md`: as 29 comparações e suas tolerâncias.
- `referencia.json` e `referencia.log`: nova conferência do caso manual e das identidades de acoplamento.
- Páginas renderizadas e transcrições locais para auditoria dos dados bibliográficos.

A ferramenta de PDF foi instalada somente em `pdf_tools` dentro do checkpoint; não entrou nas dependências da plataforma. O verificador usa a biblioteca padrão e os módulos já existentes do projeto, sem precisar ler PDFs durante a execução.

Para reverter apenas esta entrega, remova os dois arquivos novos listados no manifesto após conferir seus nomes. Preserve a pasta de evidências se desejar manter o histórico. Nenhum arquivo preexistente do motor foi editado.

## Pendências após esta revisão

| Tema | Situação e próxima ação |
| --- | --- |
| Exemplos numéricos completos dos cinco livros | Ainda não existem. Boyce e Lakshminarayana permanecem apoio conceitual nesta rodada; selecionar exercícios numéricos adicionais, se necessários à avaliação acadêmica |
| Ciclo completo do livro | Recuperador, escape, propriedades distintas e rendimentos mecânicos impedem exigir igualdade do motor inteiro com as hipóteses atuais |
| Turbina completa do exemplo 4.2 | Helpers conferidos; entrada com swirl do estágio repetitivo não coincide com a condição axial do primeiro bocal da interface |
| Combustor com cp distintos | Diferença quantificada; decidir com o autor/professor se a hipótese única permanece ou se a integração será ampliada |
| Política de escolha de estágios | Preservada; decisão continua reservada à reunião com o professor |
| Validação real | Ensaios, mapas, estabilidade, estrutura, resfriamento e fabricação não são demonstrados por estes exemplos |

O resultado fortalece a verificação de partes implementadas e torna explícitas as diferenças de hipótese. Não autoriza declarar que todos os cálculos foram validados integralmente pelos cinco livros.
