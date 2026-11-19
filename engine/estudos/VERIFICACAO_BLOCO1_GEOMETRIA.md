# Bloco 1 — Carter, orientação e solidez dos perfis

Implementação autorizada pelo autor e verificada em 05/11/2026.

## Resultado

O bloco 1 foi concluído. Os perfis usam Carter fechado no câmber metálico final, o rotor do compressor é convertido para a convenção tangencial global e a solidez de cada seção corresponde à corda, ao raio e ao número inteiro de pás realmente usados na geometria.

Os cálculos termodinâmicos, parâmetros de referência, triângulos de velocidade, áreas, carregamento meanline e número de estágios foram preservados nos oito casos comparados. As mudanças esperadas estão nos DF radiais, nos perfis e no loft do compressor e nos dados de solidez dos dois componentes.

Esta verificação não encerra a validação global do TCC. Combustor, continuidade de swirl entre estágios da turbina, definição de reação, fechamento manual ciclo–meanline e indicadores de eficiência continuam nos blocos seguintes.

## Formulação

### Carter

Referência conferida na revisão: Dixon & Hall, 7ª edição, Eqs. 3.34–3.35 e exemplo 3.1, páginas impressas 86–87 (PDF local 97–98).

Para o arco circular com a/c = 0,5 e os ângulos em graus:

```text
m = 0,23 + 0,002*abs(angulo_saida_escoamento)
a_C = m*sqrt(s/c)
theta_final = (angulo_entrada_metal - angulo_saida_escoamento)/(1-a_C)
delta = a_C*theta_final
angulo_saida_metal = angulo_saida_escoamento - delta
```

O código anterior aplicava delta à deflexão de escoamento, sem fechar a relação com o câmber final. Agora ela é resolvida algebricamente. Entradas não finitas/não positivas, denominador não admissível e câmber com módulo >=180° são rejeitados com mensagem explícita. O limite de 180° diz respeito ao ramo de arco circular representado como função de x neste gerador; não é critério de separação aerodinâmica.

O teste do exemplo 3.1 fornece diretamente a entrada metálica de 47° = 50°−3°, porque a API do projeto adota incidência zero. Assim ele testa o núcleo de Carter, sem afirmar que reproduziu a incidência não nula do exemplo.

| Grandeza | Antes | Agora | Publicado no livro |
|---|---:|---:|---:|
| Desvio | 4,545235° | 6,203971° | 6,2° |
| Câmber | 21,545235° | 23,203971° | 23,2° |

A correlação continua sendo empírica e restrita ao contexto de cascatas de compressor. Não foi aplicada à turbina, onde o desvio continua imposto como zero.

### Orientação

Os perfis e o loft usam o eixo axial positivo no sentido do escoamento e o tangencial positivo no sentido de U. O compressor armazena `beta_modelo = atan2(U-Ctheta, Cx)`, portanto o ângulo geométrico de W é `-beta_modelo`.

A conversão é feita ao fornecer os ângulos ao gerador de perfis do rotor do compressor. Câmber, desvio e stagger mantêm seus sinais de forma coerente; os estatores e a turbina preservam sua convenção. A transformação do loft não foi alterada. Os beta armazenados no meanline/radial e exibidos nas tabelas anteriores continuam na convenção do modelo.

As médias `gamma_*` dos radiais são médias de ângulos de escoamento, com a convenção de cada componente. Elas não substituem o stagger metálico de `PerfilPa`, que é o efetivamente usado no loft.

### Solidez

```text
s(r) = 2*pi*r/Z
sigma_local(r) = Z*c/(2*pi*r)
```

Mantiveram-se a corda verdadeira e Z constantes em cada fileira. A solidez local diminui com r. O compressor usa esse valor em rotor e estator, tanto no DF quanto em Carter. Na turbina, os perfis também recebem a solidez local obtida do Z arredondado, substituindo o valor 1,0 fixo no gerador.

As listas antigas `RadialCompressor.sigma_rotor` e `.sigma_estator` continuam sendo as referências meanline para compatibilidade. Os novos campos `sigma_rotor_local`, `sigma_estator_local` e `sigma_bocal_local`, conforme o componente, são listas de dicionários por estágio/seção.

O parâmetro opcional sigma de RadialTurbina não pode divergir do alvo meanline: para mudar o alvo é necessário recalcular a turbina, incluindo Z. Não se modifica a solidez construída apenas sobrescrevendo um número no radial.

Caso de referência, estágio 1 do compressor:

| Seção | Sigma meanline | Sigma local usada agora | DF rotor anterior | DF rotor atual |
|---|---:|---:|---:|---:|
| Hub | 1,273240 | 1,485446 | 0,512165 | 0,480421 |
| Tip | 1,273240 | 1,114085 | 0,364830 | 0,381656 |

O máximo de DF rotor entre todas as seções/estágios passou de **0,512164842 para 0,482072365**. Isso decorre da solidez local; os triângulos e critérios de aviso não foram ajustados.

## Interface e exportações

Compressor e turbina têm um painel recolhível: **Do escoamento ao perfil — ângulos metálicos e solidez local**. O usuário escolhe estágio, seção e fileira para consultar:

- Escoamento, metal e diferença na entrada/saída.
- Z, corda, passo e solidez local.
- Câmber e stagger metálicos entregues ao loft.
- Equação e referência de Carter ou hipótese de desvio zero da turbina.

Os valores vêm dos perfis da execução calculada, não de números independentes. Alterações no formulário entram após recalcular o caso. O campo da turbina agora é identificado como alvo de solidez no raio médio; o valor construído depende do arredondamento de Z e do raio local.

Os CSVs conservam as colunas anteriores e acrescentam colunas explícitas de solidez local; na turbina também registram o alvo meanline. As antigas sigma_rotor/sigma_estator do CSV do compressor continuam sendo valores meanline, para preservar compatibilidade. As coordenadas DXF passam a refletir os perfis corrigidos por utilizarem o mesmo loft.

Os gráficos de sensibilidade atuais continuam apresentando suas métricas meanline, como já faziam antes; não se trocou silenciosamente uma métrica meanline pelo máximo radial. Portanto um gráfico de DF meanline não precisa mudar em função desta correção de solidez radial.

## Verificações executadas

1. Exemplo de Carter, simetria entre perfil original/espelhado e rejeição de dez conjuntos de entradas inválidas de Carter/geometria.
2. Oito casos: razão de pressão 8 manual e 6/8/12 automático, cada um com 3 e 7 seções.
3. Total de **980 perfis**: fechamento de Carter, incidência zero imposta, desvio, solidez geométrica e orientação correta dos ângulos de entrada e saída.
4. Tangentes recuperadas das curvas 3D realmente geradas, por derivadas unilaterais de três pontos em coordenadas desenroladas rθ,z, com 200 subdivisões de corda. Maior erro angular **0,011587131°**, abaixo da tolerância de discretização adotada de 0,02°. Isso é uma verificação numérica da geometria; não mede desvio aerodinâmico real.
5. Raios e coordenadas das superfícies loftadas: finitude e correspondência com os raios prescritos.
6. Alvos adicionais de solidez da turbina 0,7 e 1,4: Z/c/raio locais recuperados pelos perfis.
7. Comparação antes/depois: estados, triângulos meanline, áreas, U, velocidade axial e estágios iguais nos oito casos. Euler continua fechando, com resíduo máximo da ordem de 2,91e-11 J/kg.
8. AppTest do Streamlit: cálculo completo, dois novos painéis, troca para compressor estágio 8/tip/estator e correspondência do valor exibido com o perfil selecionado.
9. Formulário com solidez da turbina alterada para 1,4 e recálculo: a solidez dos perfis acompanhou Z/c/raio do novo caso. Nenhuma exceção de interface.
10. As 56 avaliações de sensibilidade da execução com sigma da turbina 1,4 concluíram sem casos computacionalmente inválidos. Avisos físicos continuam sendo registrados; execução não é aprovação de viabilidade.
11. Dois CSVs e 22 DXFs do caso de referência foram gerados dentro do checkpoint. Conferidos número de linhas, valores de solidez local, entidades POLYLINE e terminador EOF.
12. Todos os arquivos Python de engine passaram por análise sintática.

O teste de perfis também executou os casos de referência da turbina com sigma=1. Os alvos adicionais do verificador usam o ciclo do último caso de razão de pressão 12; seus avisos de acoplamento manual são preservados e não são confundidos com os avisos da referência de razão 8.

Permanecem os dois avisos da referência manual: Mach relativo de aproximadamente 1,001 na ponta do primeiro estágio do compressor e câmber de aproximadamente 97,69° no rotor do terceiro estágio da turbina, no hub. Nenhuma entrada foi ajustada para eliminá-los.

Não foi realizada inspeção visual em navegador ou importação dos DXFs no aplicativo CAD. AppTest não comprova aparência visual; geração de DXF não comprova sólido STEP, ausência de colisões ou aptidão para fabricação.

## Reprodução

Na pasta NEW:

```powershell
python -m engine.estudos.verificar_geometria_perfis --saida ../checkpoints/bloco1_geometria_2026-11-05/verificacao_perfis.json
python -m engine.estudos.verificar_acoplamento --antes ../checkpoints/bloco1_geometria_2026-11-05/antes.json --saida ../checkpoints/bloco1_geometria_2026-11-05/depois.json
streamlit run engine/webapp/streamlit_app.py
```

Para ver as alterações na interface, reiniciar o processo Streamlit e recalcular o caso. Na conferência de processos ao final desta tarefa, não havia servidor Streamlit deste projeto em execução; não foi encerrado nenhum processo do usuário.

## Checkpoint e recuperação

Pasta: `checkpoints/bloco1_geometria_2026-11-05/`, a partir da raiz do TCC.

`manifesto.json` contém os hashes anteriores e as cópias preservam os mesmos caminhos relativos. Para voltar, restaurar somente os cinco arquivos do manifesto:

- `NEW/engine/geometry/airfoil4.py`.
- `NEW/engine/aero/radial_compressor_4_main.py`.
- `NEW/engine/aero/radial_turbina_3_main.py`.
- `NEW/engine/estudos/export_csv.py`.
- `NEW/engine/webapp/streamlit_app.py`.

Depois, reiniciar o Streamlit. Os novos arquivos `aero/cascade_geometry.py`, `estudos/verificar_geometria_perfis.py` e este relatório podem permanecer sem uso pela versão restaurada. O verificador novo depende dos campos locais da versão corrigida e não deve ser usado como teste da versão anterior. Não restaurar o repositório inteiro: existem alterações preexistentes e arquivos de outros projetos no Git pai.

Os resultados desta tarefa estão em `antes.json`, `depois.json`, `verificacao_perfis.json`, `interface_exportacoes.json`, `stdout_interface.txt` e `exportacoes/`, todos dentro do checkpoint. Não foram sobrescritos os CSVs/DXFs antigos do usuário.
