# Centralização dos critérios de verificação

Implementada em **09/11/2026**, com autorização do autor. Esta revisão organiza
os critérios existentes; não altera modelos físicos, valores dos limites,
parâmetros do caso de referência ou prioridades da seleção automática.

## Fonte comum

[`engine/design_criteria.py`](../design_criteria.py) reúne as constantes usadas
nos avisos, nos índices da seleção, nos metadados dos candidatos, nos limites
dos gráficos de sensibilidade e nas explicações principais da interface.

| Critério | Valor preservado | Alcance preservado |
|---|---|---|
| Mach relativo | 1 | Entrada do rotor do compressor; saída do rotor da turbina |
| Mach do bocal da turbina | 1,3 | Meanline e distribuição radial |
| DF rotor/estator | 0,6 | Compressor, meanline e radial |
| Reação negativa | 0 | Verificador radial; seleção compara também valores meanline |
| Reação acima de um | 1 | Turbina radial e índice comparativo da seleção |
| Reação comparativa do compressor | 0,4–0,6 | Meanline; não foi acrescentado aviso de faixa na distribuição radial |
| Reação comparativa da turbina | 0,3–0,7 | Meanline e radial |
| ψ comparativo | 0,3–0,6 / 1–2,5 | Compressor / turbina |
| Câmber metálico em módulo | 60° / 90° | Perfil do compressor / turbina |
| Swirl residual em módulo | 0,15 | Somente escape do último estágio meanline da turbina |
| Aviso de fechamento | Desvio acima de 2% | Temperatura/pressão nos meanlines |
| Coincidência numérica | relativa 1e-9; absoluta 1e-7 | Diagnóstico e elegibilidade dos candidatos; unidades SI |

Também foram reunidos os intervalos já usados nos avisos de entrada de HTR,
φ, DF alvo, eficiência/Mach do combustor, razão combustível/ar, equivalência
da mistura e espessura relativa do perfil. Esses avisos não foram incluídos
como novos critérios de classificação.

Os limites personalizados das funções genéricas (`limite`, `faixa`,
`limite_camber`) continuam aceitos. Domínios matemáticos obrigatórios
permanecem separados em `input_validation.py`. Valores de entrada padrão,
intervalos de varredura e todos os limites de widgets não foram transformados
em critérios de aprovação física.

## Verificações

Evidências em `checkpoints/criterios_centralizados_2026-11-09/`, com os comandos
e códigos de saída em `execucoes.json`. Executar os scripts dessa pasta a partir
de `NEW` com o Python do ambiente do projeto.

- **612 comparações de mensagens**, cobrindo 18 funções: resultados idênticos
  às funções copiadas antes da mudança, incluindo fronteiras e valores vizinhos.
  Assinaturas e limites padrão preservados; parâmetros personalizados aceitos.
- **90 valores, limites e localizações dos candidatos** conferidos; escores,
  justificativas e escolhas preservados em razões de pressão 6, 8 e 12.
- Regressão de acoplamento em oito casos, diagnósticos, combustor, indicadores,
  continuidade da turbina e geometria dos perfis aprovados.
- As **155 recusas de entradas inválidas**, quatro fronteiras válidas e ordem
  de chamadas da API continuam aprovadas.
- Análise sintática dos arquivos Python aprovada.

O teste de interface também foi aprovado: avisos e potência do caso manual
idênticos ao checkpoint; seleção automática completa idêntica; tabela de
origens e sensibilidade sem erros. Resultados em `interface.json` e
`interface.log`, gerados por `verificar_interface.py`.
Esse teste usa AppTest local; não equivale a inspeção visual no navegador.

## Limitações e próximos itens

Esta centralização evita divergência de valores entre consumidores; não
certifica a viabilidade física dos limites adotados. A política continua
`vizinhos_criterios_v1`: o câmber ainda precede as faixas comparativas na
classificação, aguardando decisão do autor.

A revisão editorial completa das legendas permanece separada. Por exemplo,
o aviso de espessura já era acionado acima de 0,25, embora seu texto mencione
0,05–0,15: ambos foram preservados nesta refatoração. Os comentários históricos
e as citações numéricas dos livros também não são definições executáveis de
limites e não foram reescritos como se fossem.

A separação dos exemplos executados ao importar os módulos é o próximo item
técnico pendente; não foi incorporada a esta tarefa.

## Checkpoint e retorno

As cópias anteriores de 11 arquivos estão na mesma pasta de checkpoint,
mantendo o caminho relativo `NEW/engine/...`. O arquivo `manifesto.json`
registra seus hashes SHA-256.

Para retornar: encerrar a execução do Streamlit, copiar esses 11 arquivos
de volta aos caminhos correspondentes, substituindo somente os arquivos
desta revisão. Depois disso, os novos `design_criteria.py`,
`estudos/verificar_criterios_centralizados.py` e este relatório podem ser
removidos se o autor desejar. Não é necessário resetar o repositório nem
alterar outros arquivos do projeto.
