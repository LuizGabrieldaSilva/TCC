# Validação dos domínios de entrada dos cálculos

Implementação autorizada pelo autor, iniciada em **08/11/2026** e concluída em **09/11/2026**. Escopo: item 1 da revisão de robustez, antes de novas funcionalidades de interface.

## Resultado

Entradas inadmissíveis são verificadas nas APIs dos cálculos, sem depender exclusivamente dos widgets do Streamlit. Números não finitos, tipos incompatíveis, contagens fracionárias e divisores degenerados passam a gerar erros claros. Faixas de recomendação continuam sendo avisos: não foram convertidas em proibições.

Os resultados, geometrias e números de estágios dos oito casos de regressão foram preservados exatamente nos campos comparados. Escores, justificativas e escolhas dos candidatos também foram preservados. A política de prioridade `vizinhos_criterios_v1` não foi alterada.

Não foram centralizados ou modificados os critérios aerodinâmicos de recomendação, nem separados os exemplos ainda executados durante importação: esses são os itens posteriores da revisão, fora desta implementação.

## 1. Domínios implementados

Validações comuns estão em `engine/input_validation.py`. Elas verificam o domínio matemático e físico adotado pelas APIs, não certificam viabilidade aerodinâmica.

| Entrada/modelo | Domínio aceito |
| --- | --- |
| Valores numéricos das APIs cobertas | Reais finitos; bool, texto, None indevido, NaN e infinito são recusados |
| Ciclo: T01, P01, TIT, limite prescrito de TIT e cp | Positivos |
| Ciclo: k | Maior que 1 |
| Eficiências politrópicas e eficiência de combustão | Maiores que zero e menores ou iguais a 1; eficiência 1 continua aceita |
| Razão de compressão do motor | Maior que 1; a API não representa o caso degenerado sem compressão |
| Perda relativa do combustor | No ciclo, 0 ≤ Delta_P_cc < 1, com r_compr·(1−Delta_P_cc)>1 para permitir expansão até P01 |
| Calor do combustor | TIT maior que a temperatura total de saída do compressor; adição positiva de calor |
| Vazão de ar e potência desejada | Positivas e finitas, com resultado dimensional finito; dimensionar vazão por potência requer trabalho líquido-base positivo |
| Vazão de gases registrada no ciclo | Positiva, finita e maior ou igual à vazão de ar já definida |
| Meanlines: rotação, φ, ψ, AR, DF alvo do compressor e solidez da turbina | Positivos e finitos |
| HTR | Estritamente entre 0 e 1 |
| Ângulos de entrada usados nas relações axiais | Estritamente entre −90° e 90°, coerentes com velocidade axial positiva e sem a singularidade da tangente |
| Número manual de estágios | Inteiro ≥1; None conserva a seleção automática |
| Número de seções radiais | Inteiro ≥2, preservando o suporte existente a hub/tip; não se impôs arbitrariamente o mínimo de três |
| Combustor: PCI e razão estequiométrica | Positivos e finitos; denominador do balanço de combustível deve ser positivo e finito |
| Mach de entrada do combustor | Estritamente entre 0 e 1, preservando a hipótese subsônica já existente |

O tipo inteiro é exigido para contagens: `3.0` não é convertido silenciosamente em `3`. O catálogo de combustíveis e seus valores não foram modificados.

São exemplos de valores que continuam gerando apenas avisos, quando matematicamente calculáveis: DF alvo de 0,65 e eficiência de combustão de 0,89. O domínio de uma entrada não garante que os demais cálculos daquele projeto conseguirão convergir ou construir um perfil admissível.

## 2. Fronteiras numéricas do ciclo

Para π=1, a antiga conversão de eficiência encontrava 0/0. Agora essa razão é recusada explicitamente pelo domínio do modelo de motor. Para razões maiores que 1, mas próximas da unidade, as mesmas relações politrópicas são avaliadas de maneira mais estável quando `abs(log(razão))<1e-6`:

```text
a = (k−1)/k
eta_compressor = expm1(a·ln(pi_c)) / expm1((a/e_compressor)·ln(pi_c))
eta_turbina = expm1(−a·e_turbina·ln(pi_t)) / expm1(−a·ln(pi_t))
```

Usa-se a identidade x^b=exp(b·ln(x)); não foi introduzida nova equação física. `expm1` evita a subtração de números quase iguais nas diferenças exp(x)−1. As temperaturas reais também usam a forma exponencial equivalente nessa região. Fora dela, o caminho de cálculo anterior foi preservado para manter os resultados existentes.

Se a elevação/queda de temperatura não puder ser distinguida de zero na precisão disponível, a API informa essa limitação em vez de continuar para divisões degeneradas. Casos extremos com overflow ou divisão por zero nas rotinas protegidas são convertidos em ValueError com contexto do cálculo.

Mantém-se a regra existente que recusa trabalho líquido-base negativo antes do acoplamento de combustível. Não foi ampliado o modelo para motores acionados externamente, ciclo reverso ou análise de casos que só adquiram saldo positivo após a massa de combustível. Saldo-base zero não pode ser usado para dimensionar vazão por uma potência positiva; esse caminho é recusado antes da divisão.

## 3. Ordem de chamadas e integridade dos resultados

- Resolver o ciclo novamente invalida vazões, potência e acoplamento da solução anterior. Após sucesso, é necessário definir novamente vazão ou potência antes de instanciar os componentes.
- Se a nova solução falhar, o estado não é considerado resolvido e os métodos públicos de resultados recusam sua utilização. Não se apresenta uma combinação parcial de cálculos novos e resultados antigos como solução válida.
- Entradas inválidas nos métodos de vazão/potência são recusadas antes de substituir uma execução válida.
- No registro de gases, vazões e energias derivadas são conferidas antes de atualizar os atributos.
- O combustor só é considerado resolvido após o balanço e as dimensões resultarem em valores admissíveis.
- Os componentes verificam que o ciclo foi resolvido e que existe vazão positiva. As fixtures numéricas com atributos continuam disponíveis nos verificadores, sem exigir uma classe concreta de ciclo.

As validações não tornam suportada a alteração arbitrária de atributos de dimensionamento de um meanline já construído. Para mudar suas entradas de projeto, deve-se construir/resolver o modelo correspondente, como já ocorre no pipeline da interface.

## 4. Testes executados

Evidências em `checkpoints/validacao_entradas_2026-11-08/` — o nome conserva a data de início.

| Evidência | Resultado |
| --- | --- |
| `entradas.json`, novo verificador `verificar_entradas.py` | 155 recusas esperadas, com tipo/mensagem de erro conferidos; tipos inválidos, NaN/infinito, geometrias degeneradas, eficiências inválidas, contagens e singularidades |
| Fronteiras válidas no mesmo arquivo | Razões de compressão 1+1e-10, 1+1e-8, 1+1e-5 e 8; eficiências ideais iguais a 1 e perda de pressão zero; temperaturas conferidas contra relações analíticas |
| Ordem de chamadas | Vazão antes de resolver, gases antes de definir ar, nova solução invalidando vazão anterior e acesso aos resultados após falha recusados de forma controlada |
| Potência/vazão | Divisão por trabalho zero recusada; potência-alvo de 2000 kW preservada após registrar a massa de combustível |
| `acoplamento.json` | Oito casos: estados, triângulos, áreas, U, velocidade axial e estágios preservados em relação ao snapshot de 06/11 |
| `selecao_estagios.json` e `detalhes_selecao.json` | Política/seleção preservadas; 90 valores/limites/locais conferidos contra os objetos e o snapshot anterior |
| `combustor.json`, `indicadores.json`, `diagnosticos.json`, `estagios_turbina.json`, `geometria_perfis.json` | Verificadores anteriores aprovados, incluindo os exemplos parciais já existentes e os perfis do conjunto atual |
| `interface.json` e `interface.log` | AppTest aprovado: manual de referência com 8/3 estágios e dois avisos; TIT de 400 K recusada com mensagem de adição de calor; resultados/sensibilidades antigos limpos; retorno a 1200 K e modo automático com 8/4 estágios e fechamento; sensibilidades executadas sem erro de pipeline |
| Sintaxe | Todos os arquivos Python do engine passaram pela análise sintática no teste da interface |

Os oito verificadores existentes da bateria terminaram com código de saída zero, registrado em `execucoes.json`. Além deles foi executado o novo verificador de entradas. O teste anterior de seleção com grade inadmissível foi atualizado para esperar a rejeição já no construtor, antes de avaliar candidatos.

Não houve inspeção visual em navegador nem validação experimental nesta etapa. Testes de domínio e regressão não demonstram estabilidade da chama, margens de estol, vida de pá ou aptidão para fabricação.

## 5. Reprodução

A partir de `NEW`, com o ambiente Python/dependências do projeto:

```powershell
python -X utf8 -m engine.estudos.verificar_entradas --saida ../checkpoints/validacao_entradas_2026-11-08/entradas.json
python -X utf8 ../checkpoints/validacao_entradas_2026-11-08/reexecutar_verificacoes.py
```

Os comandos repetem as verificações e sobrescrevem apenas suas respectivas evidências na pasta indicada. Use outra pasta/caminhos se desejar preservar um novo histórico de execução.

## 6. Checkpoint e recuperação

`checkpoints/validacao_entradas_2026-11-08/manifesto.json` registra as oito cópias anteriores e seus hashes: ciclo, dois meanlines, combustor, dois radiais, verificador da seleção e matriz de rastreabilidade.

Para reverter, restaure somente esses arquivos nos mesmos caminhos relativos. Os arquivos novos `input_validation.py`, `verificar_entradas.py` e este relatório podem permanecer sem uso após a restauração. Não se deve reverter todo o repositório. Nenhum padrão de referência, critério aerodinâmico ou arquivo da interface foi alterado nesta implementação.
