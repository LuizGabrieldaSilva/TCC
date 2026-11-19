# Aba consolidada de verificações e referências

Implementação de apresentação em 12/11/2026. A nova aba **Verificações** reúne registros da execução e documentação dos critérios; preserva os painéis locais e não executa novas análises físicas.

## Conteúdo

- Resumo de mensagens por componente, separado do estado das etapas registradas.
- Filtro por componente, seleção de aviso e mensagem completa. A identificação usa execução, ID original e ocorrência, independentemente da posição da linha ou da formatação decimal.
- Associação conservadora da mensagem à família do critério. Mensagens desconhecidas permanecem explicitamente sem associação bibliográfica automática.
- Catálogo de 22 itens: natureza, valor/faixa padrão, origem, localização, interpretação e próxima análise útil. Limites compartilhados são lidos de `design_criteria.py`.
- Interfaces termodinâmicas lidas dos diagnósticos existentes, com resíduos e coincidência numérica.
- Alcance e limitações por área, além das cinco referências com localizadores registrados no projeto.
- Orientação no modo Guiado; conteúdo completo acessível também no modo Técnico.

O catálogo distingue definição física, correlação empírica, faixa/escolha do projeto, hipótese geométrica e comparação numérica. Não apresenta todos os itens como verificações aprovadas da execução. A contagem de mensagens não é um índice de gravidade.

## Verificação reproduzível

Da pasta `NEW`, executar:

```powershell
python ../checkpoints/verificacoes_consolidadas_2026-11-12/verificar.py
```

O verificador confere:

1. IDs únicos, associações conhecidas/desconhecidas, contagens e ausência de alteração dos registros originais.
2. Preservação por AST do pipeline e das funções preexistentes de extração/classificação de avisos e estado das etapas.
3. AppTest: cálculo manual, nova aba e sete guias, preservação dos painéis locais, troca de filtros, seleção de critérios, filtro sem avisos e modo Técnico.
4. Resultados, avisos e diagnósticos preservados durante as interações de apresentação.
5. Nova execução automática, renovação do contexto do seletor e comparação integral das escolhas dos candidatos com a referência de 08/11/2026.

Evidências: `checkpoints/verificacoes_consolidadas_2026-11-12/resultado.json` e `interface.log`. AppTest verifica a execução e as interações; não substitui avaliação visual no navegador nem validação física/experimental.

## Escopo e restauração

Não foram alterados fórmulas, parâmetros, limites, política de seleção ou arquivos de exportação. A prioridade dos candidatos continua aguardando discussão com o professor.

As referências transcrevem localizadores já registrados na matriz teórica. Esta implementação não constitui nova leitura dos cinco PDFs nem auditoria independente de todas as equações.

Checkpoint anterior: `checkpoints/verificacoes_consolidadas_2026-11-12/manifesto.json`. Para reverter esta implementação, restaurar `streamlit_app.py` e `reading_mode.py` a partir dos caminhos de backup indicados no manifesto e remover os dois módulos novos: `criteria_catalog.py` e `verification_overview.py`. Conferir antes se houve alterações posteriores que também devam ser preservadas. Os hashes finais ficam em `arquivos_depois.json`.
