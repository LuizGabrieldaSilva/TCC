# Correção do acoplamento meanline–radial: implementação e verificações

Implementação autorizada pelo autor, iniciada em 04/11/2026 e conferida em 05/11/2026.

## 1. Resultado e alcance

Compressor e turbina agora constroem seus anulares por estágio mantendo o raio médio **aritmético** usado pelos triângulos meanline. O radial verifica essa compatibilidade e usa a mesma referência para a constante de vórtice livre.

O trabalho radial recuperou o trabalho meanline e `cp*Delta_Tt_estagio` nos oito casos executados. O maior resíduo absoluto de Euler foi `2,9103830456733704e-11 J/kg`.

Isso resolve a discrepância de referência identificada. **Não significa que o projeto inteiro esteja validado, que todos os critérios aerodinâmicos tenham sido atendidos ou que a geometria seja um sólido CAD aprovado.**

## 2. Formulação implementada

```text
r_ref = (r_tip_entrada + r_hub_entrada)/2
U_meanline = omega*r_ref
h_i = A_i/(2*pi*r_ref)
r_hub_i = r_ref - h_i/2
r_tip_i = r_ref + h_i/2
HTR_i = r_hub_i/r_tip_i
```

As áreas continuam sendo as calculadas pelo escoamento meanline. `HTR` continua sendo a entrada da API e dos estudos, agora explicitamente uma condição de entrada; `HTR_estagio` armazena os resultados locais. A ponta da turbina deixa de ser fixa.

O raio adotado não é o raio que divide o anular em áreas iguais, `sqrt((r_tip**2+r_hub**2)/2)`. Os valores recebidos pelos radiais não são reinterpretados silenciosamente em outro raio. Se a geometria não recuperar a referência, é emitida uma exceção com identificação do componente/estágio.

Área/raio não finitos ou não positivos e construção com `r_hub <= 0` ou `r_tip <= r_hub` são rejeitados.

## 3. Arquivos

- `engine/aero/annulus_geometry.py`: construção comum do anular e verificação da referência.
- Dois módulos meanline: geometria por estágio e armazenamento de `HTR_estagio`.
- Dois módulos radiais: referência explícita e verificada do meanline; a lei free vortex foi preservada.
- `engine/webapp/streamlit_app.py`: HTR de entrada, painel geométrico por estágio e explicação da definição de raio.
- `engine/webapp/velocity_triangles.py`: mantém a comparação dos três trabalhos e identifica discrepâncias como falhas a investigar.
- `engine/estudos/plot_sensibilidade.py`: rótulos de HTR de entrada.
- `engine/estudos/export_csv.py`: acrescenta ao final dos CSVs `r_mean_aritmetico_cm`, `HTR_entrada` e `HTR_estagio`, preservando os nomes das colunas anteriores.
- `engine/estudos/verificar_acoplamento.py`: verificações e comparação bibliográfica reproduzíveis.

O comentário da tendência radial de reação da turbina também foi corrigido: para soma positiva das componentes tangenciais de referência, a expressão já utilizada faz a reação aumentar em direção à ponta. Nenhuma equação de reação foi alterada.

Não foram modificados os parâmetros do caso de referência, as equações do ciclo ou combustor, nem a forma de cálculo de U, phi, psi e ajuste automático de estágios. A orientação histórica do Claude sobre preservar a geometria foi reavaliada e substituída pela autorização atual do autor; seu documento foi conservado como registro histórico.

## 4. Oito casos e comparação antes/depois

Todos usam os parâmetros atuais de `engine/reference_case.py`, com razão de pressão, modo de estágios e discretização indicados abaixo. No modo automático, `n_estagios=None` é enviado aos dois componentes.

| Razão de pressão | Modo | Seções | Estágios compressor | Estágios turbina | Maior resíduo Euler compressor (J/kg) | Maior resíduo Euler turbina (J/kg) |
|---|---|---:|---:|---:|---:|---:|
| 8 | Manual | 3 | 8 | 3 | 7,28e-12 | 2,91e-11 |
| 8 | Manual | 7 | 8 | 3 | 7,28e-12 | 2,91e-11 |
| 6 | Automático | 3 | 7 | 3 | 1,46e-11 | 0 |
| 6 | Automático | 7 | 7 | 3 | 1,46e-11 | 2,91e-11 |
| 8 | Automático | 3 | 8 | 4 | 1,46e-11 | 2,91e-11 |
| 8 | Automático | 7 | 8 | 4 | 1,46e-11 | 2,91e-11 |
| 12 | Automático | 3 | 11 | 5 | 7,28e-12 | 2,91e-11 |
| 12 | Automático | 7 | 11 | 5 | 7,28e-12 | 2,91e-11 |

A comparação dos snapshots confirmou igualdade dos estados termodinâmicos e campos de triângulos meanline registrados, áreas, raio de referência, U, velocidade axial, psi efetivo e número de estágios. A alteração pretendida está na geometria e nos resultados que dela dependem, inclusive no arredondamento do número de pás e solidez.

As identidades internas usam tolerâncias relativa de `1e-10` e absoluta de `1e-9` nas unidades verificadas. A comparação com saídas do ciclo no modo automático usa tolerâncias relativa de `1e-9` e absoluta de `1e-7`. São tolerâncias de verificação numérica, não critérios de concordância experimental.

Foram verificados:

1. Positividade dos raios, área recuperada e raio médio constante.
2. `U(r) = omega*r`, módulos C/W e recuperação do meanline na seção central das malhas ímpares.
3. Constância de `r*Ctheta` e trabalho de Euler em todas as seções.
4. Igualdade Euler radial = Euler meanline = `cp*Delta_Tt_estagio`.
5. Continuidade na estação usada para dimensionar a área, pelas condições meanline. Não é integração radial de densidade.
6. Finitude dos Mach, DF e reação radiais disponibilizados pelo modelo.
7. Fechamento das temperaturas e pressões de saída com o ciclo no modo automático.
8. Rejeição de geometria inválida e de referência radial incompatível.

O desvio de pressão do compressor manual, cerca de `0,57176%`, foi preservado. Não é a discrepância radial corrigida. O comportamento de arredondamento dos estágios automáticos também foi preservado: a turbina adota quatro estágios no caso automático de razão 8.

## 5. Caso de referência manual, sete seções

| Grandeza | Compressor | Turbina |
|---|---:|---:|
| HTR no último estágio | 0,9272094 | 0,7559676 |
| Mach relativo máximo disponível | M1R = 1,0011895 | M3R = 0,8849121 |
| Reação radial mínima | 0,3688866 | 0,3746047 |
| Reação radial máxima | 0,6449987 | 0,6425947 |
| DF máximo do rotor | 0,5121648 | Não calculado por esse critério |
| DF máximo do estator | 0,4977897 | Não calculado por esse critério |

Permanecem avisos no fluxo de referência:

- Compressor, estágio 1, tip: `M1R ≈ 1,001 > 1`.
- Perfil do rotor da turbina, estágio 3, hub: câmber aproximado de `97,69°`, acima do critério de `90°` para um único arco circular.

Não foram ajustadas entradas ou correlações para remover esses avisos. Eles exigem discussão e decisão próprias. A ausência de reação negativa nos resultados atuais não prova que todos os requisitos físicos estejam atendidos.

## 6. Primeira comparação com exemplo bibliográfico

Fonte: Saravanamuttoo, Cohen e Rogers, *Gas Turbine Theory*, seção 5.7, páginas impressas 210–211; páginas 227–228 do PDF local.

Escopo da comparação: **somente a construção geométrica do anular**, não o desempenho completo do compressor do livro.

Entradas publicadas usadas: área de saída `0,0440 m²` e raio médio `0,1697 m`. Comparam-se cubo, ponta e altura aos valores publicados `0,1491 m`, `0,1903 m` e `0,0413 m`.

O cálculo recuperou os valores dentro de `5e-5 m`, tolerância associada às quatro casas decimais dos valores publicados. Esse teste chama a mesma função usada nos dois meanlines.

As cinco referências não estão integralmente validadas por esse teste. O trabalho seguinte é selecionar outros exemplos comparáveis e registrar, para cada um, hipóteses, entradas, resultados esperados e desvios. Dixon & Hall, Mattingly, Boyce e Lakshminarayana continuam como referências para fundamentos, convenções, critérios e limites, conforme o conteúdo pertinente ao modelo preliminar.

## 7. Integração, interface e exportações

O caso de referência gerou os perfis e lofts dos dois componentes. Conferiram-se a correspondência dos raios das seções e a finitude das coordenadas cartesianas. Foram gerados 22 DXFs, um por fileira, e dois CSVs de verificação, com número esperado de linhas e as novas colunas geométricas.

Os DXFs foram conferidos quanto à geração e presença das entidades e terminador esperados. Isso não substitui a abertura no aplicativo CAD de destino, nem demonstra sólido STEP válido.

O mecanismo AppTest do Streamlit executou a interface completa, o formulário, os painéis geométricos e a seleção dos triângulos interativos sem exceções. Essa execução não substitui a conferência visual da página no navegador.

As oito séries da sensibilidade totalizaram 56 execuções, todas concluídas sem exceções tratadas como falha: três séries do compressor (21 pontos), três da turbina (22 pontos) e duas do ciclo (13 pontos). Foram preservados os avisos físicos; conclusão computacional não é aprovação aerodinâmica. O resumo está em `sensibilidade_depois.json` no checkpoint. Não foram sobrescritas as imagens antigas salvas dos estudos.

## 8. Reprodução

Na pasta `NEW`:

```powershell
python -m engine.estudos.verificar_acoplamento --saida verificacao_raio_medio.json
```

Para repetir a comparação com o estado anterior preservado:

```powershell
python -m engine.estudos.verificar_acoplamento --antes ../checkpoints/raio_medio_constante_2026-11-04/antes.json --saida verificacao_raio_medio.json
```

`--snapshot caminho.json` registra o estado que estiver instalado naquele momento sem exigir as novas identidades. Não recria automaticamente a versão anterior.

## 9. Checkpoint e recuperação

Pasta, a partir da raiz do TCC: `checkpoints/raio_medio_constante_2026-11-04/`.

- `manifesto.json`: arquivos anteriores e hashes SHA-256.
- `NEW/engine/...`: cópias anteriores com a mesma estrutura de caminhos.
- `antes.json` e `depois.json`: resultados numéricos.
- `interface_depois.json`: execução e avisos da interface.
- `sensibilidade_depois.json`: conclusão e falhas das varreduras de sensibilidade.
- `exportacoes_depois/`: CSVs e DXFs desta conferência, sem sobrescrever saídas antigas.
- `avisos_geometria_depois.txt`: mensagens da execução de conferência; o início também pode conter mensagens de exemplos antigos executados nas importações.

Para voltar à versão anterior, restaurar as oito cópias listadas no manifesto aos respectivos caminhos do projeto e reiniciar o Streamlit. Os três arquivos novos (helper de anular, verificador e este relatório) podem permanecer sem uso pela versão restaurada; sua remoção é opcional. Não restaurar o repositório inteiro, pois há alterações preexistentes fora deste trabalho.
