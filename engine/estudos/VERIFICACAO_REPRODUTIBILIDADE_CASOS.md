# Salvar, recuperar e documentar casos

Implementação da camada de interface em **14/11/2026**. Nenhuma fórmula, limite de aviso, propriedade física ou política de seleção foi alterada.

## Uso

1. Em **Baixar entradas atuais**, na barra lateral, dê um nome ao caso e baixe o JSON. Esse arquivo guarda os valores dos campos, mesmo que ainda não tenham sido calculados.
2. Em **Salvar e recuperar casos**, selecione o JSON de entradas e clique em **Aplicar entradas do arquivo**. A aplicação preenche os campos; não executa o modelo nem substitui os resultados da última execução.
3. Confira os valores e clique em **Calcular e atualizar gráficos**. Modos automático e manual são preservados separadamente para compressor e turbina. No automático, o número manual fica desabilitado e não entra nos cálculos.
4. Em **Downloads → Salvar o caso calculado e seu relatório**, baixe as entradas usadas na execução ou prepare o relatório ZIP.

Os campos agora comunicam suas alterações ao servidor sem exigir a execução dos cálculos. O aviso de entradas ainda não calculadas compara os parâmetros atuais com a fotografia da última execução. Retornar aos mesmos valores remove o aviso. Alterar nome, modo de leitura ou controles de visualização não modifica as entradas físicas do caso calculado.

## Formato de entradas

- JSON UTF-8, versão 1, identificado como `tcc-turbina-axial/entradas`, até 64 KiB.
- Todas as entradas devem estar presentes; campos desconhecidos e chaves repetidas são rejeitados.
- Valores são números JSON, com ponto decimal. P01 é informado em **kPa**, conforme o campo da interface; rotações em rpm, temperaturas em K, ângulos em graus e vazão em kg/s.
- `n_estagios_comp` e `n_estagios_turb` são inteiros positivos no manual e `null` no automático. `n_secoes` admite 3, 5, 7, 9 ou 11.
- Validação de tipos, valores finitos, domínios e limites dos campos da interface; eixo único exige rotações iguais. A aplicação ocorre após a validação de todas as entradas.
- Não se executa a física na importação: uma combinação aceita no formulário pode continuar inviável no cálculo. Nesse caso, aplicam-se as validações físicas já existentes.
- A versão registra cp, k, catálogo de PCI, critérios e uma assinatura SHA-256 dos arquivos Python de `engine`, excluindo a apresentação web. cp/k diferentes impedem a importação; assinatura de códigos diferente gera aviso de conferência dos novos resultados.
- O arquivo não incorpora código executável nem modifica os padrões de `reference_case.py`. JSONs de resultados e diagnósticos não são aceitos como arquivos de entradas.

## Relatório

O ZIP contém:

| Arquivo | Conteúdo |
| --- | --- |
| `relatorio.md` | Nome/ID/início da execução, entradas, etapas, estados do ciclo, indicadores, combustor, estágios, avisos, hipóteses, critérios e referências. Números apresentados com vírgula decimal. |
| `entradas.json` | Caso reimportável correspondente à execução, com modos manual/automático e contexto do modelo. Disponível quando a execução registrou esse contexto. |
| `resultados.json` | Valores numéricos, bases, diagnósticos de integração, áreas, seleção de candidatos, combustível e suas fontes, avisos e dados de sensibilidade disponíveis. Valores ausentes nas curvas são `null`; erros dos pontos são preservados. |
| `parametros_compressor.csv` | Tabela radial produzida pelo exportador existente. |
| `parametros_turbina.csv` | Tabela radial produzida pelo exportador existente. |

O relatório é preparado a pedido e vinculado ao ID da execução. Editar um rascunho depois não altera o pacote dessa execução. Um novo cálculo invalida o pacote preparado anteriormente. Os CSVs e os números JSON preservam seus formatos técnicos; livros, código-fonte, imagens e sólidos CAD não são incluídos. Geometria continua disponível nos downloads DXF próprios.

Recuperar as entradas não garante repetir resultados em outra versão do código. A identificação do modelo permite comparar as versões, mas não substitui conservar o código e suas dependências junto ao estudo. O relatório documenta consistência e hipóteses do modelo preliminar; não constitui validação experimental nem documentação de fabricação.

## Verificação

Executar a partir de `NEW`:

```powershell
python ../checkpoints/reprodutibilidade_casos_2026-11-14/verificar.py
```

O verificador confere o ciclo de exportação/importação manual e automático, rejeição de arquivos inválidos, aplicação do upload sem recálculo, aviso de rascunho, preservação do caso manual, escolhas automáticas contra a referência histórica, conteúdo do ZIP e permanência do relatório da execução após edição das entradas. A importação é exercitada no AppTest com um upload simulado; isso não substitui a avaliação visual no navegador.

Evidências em `checkpoints/reprodutibilidade_casos_2026-11-14/`: `resultado.json`, `interface.log` e pacotes ZIP de conferência. A comparação por AST verifica que o pipeline e as funções preexistentes de avisos/estado das etapas foram preservados.

## Checkpoint e restauração

O `manifesto.json` do checkpoint relaciona os originais de `streamlit_app.py` e `reading_mode.py` aos respectivos backups e hashes SHA-256. Para reverter este bloco, restaurar esses dois arquivos e retirar os módulos novos `case_io.py` e `case_reproducibility.py`. Antes de restaurar, conferir se há alterações posteriores que precisem ser preservadas. `arquivos_depois.json` registra os hashes da implementação final.
