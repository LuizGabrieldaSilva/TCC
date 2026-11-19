# Refinamentos de apresentação da comparação de casos

Data: 15/11/2026.

## Alterações

- Avisos sem estágio mostram **Geral**; sem seção, **Não se aplica**.
- Contagens de estágios e mensagens aparecem como inteiros, inclusive nas diferenças absolutas e nos estudos com casos não calculados. Percentuais e demais grandezas mantêm a precisão e a vírgula decimal.
- Referência usa linha tracejada e círculos vazados maiores; caso atual usa linha contínua e quadrados vazados menores. A referência é desenhada acima, permitindo identificar as duas séries quando se sobrepõem.
- Uma mensagem no título identifica coincidência numérica nas amostras comparadas: ambas as séries precisam ter o mesmo número de pontos, abscissas e ordenadas finitas coincidentes dentro de tolerância relativa de 1e-9 e absoluta de 1e-10. Não há interpolação; a indicação não comprova equivalência física nem convergência.

Somente `engine/webapp/case_comparison.py` foi modificado no código da aplicação. Modelos, cálculos, critérios, seleção automática e dados das exportações foram preservados.

## Verificação

Executado de `NEW`:

```powershell
python ../checkpoints/refinamentos_comparacao_2026-11-15/verificar.py
```

O teste reutiliza resultados reais previamente calculados. Foram conferidos contagens inteiras, percentuais preservados, dados ausentes, rótulos dos avisos, estilos dos gráficos e detecção de coincidência. Séries com amostragens diferentes ou valores ausentes não recebem indicação de coincidência. Os dois gráficos PNG foram inspecionados visualmente.

AppTest percorreu os componentes e uma métrica de contagem do estudo, incluindo falha sintética de apresentação. Não houve exceções nem recálculo dos modelos; resultados e referência permaneceram preservados. A verificação é de apresentação e comportamento da interface, sem validação física adicional.

## Checkpoint e restauração

Pasta: `checkpoints/refinamentos_comparacao_2026-11-15/` na raiz do projeto. O manifesto registra SHA256 e correspondência entre original e cópia; a integridade da cópia foi conferida.

Para restaurar o código anterior, copiar `NEW/engine/webapp/case_comparison.py` dessa pasta sobre o arquivo de mesmo caminho na raiz do projeto.

Evidências: `verificar.py`, `resultado.json`, `coincidentes.png` e `distintas.png`, na pasta do checkpoint.
