# Bloco 5 — definições dos indicadores e alcance dos critérios

Implementação autorizada em 06/11/2026. O bloco acrescenta indicadores derivados e explicações; preserva os solvers, suas entradas, as perdas prescritas e os limites de aviso.

## Definições implementadas

```text
Energia química pelo PCI: E_PCI = m_f * h_PR                  [W]
Calor útil:              Q_util = eta_b * E_PCI             [W]
Eficiência calor útil:   eta_util = W_liq / Q_util
Eficiência sobre PCI:    eta_PCI = W_liq / E_PCI = eta_b * eta_util
Potência líquida:        W_liq = m_g * w_t − m_a * w_c       [W]
Trabalho por kg de ar:   w_liq,a = (1+f) * w_t − w_c        [J/kg de ar]
BWR:                    m_a * w_c / (m_g * w_t)
SFC:                    3,6e6 * m_f / W_liq                [kg/kWh]
```

m_g = m_a + m_f. O trabalho específico da turbina é por kg de gás, enquanto o do compressor é por kg de ar. BWR usa potências para compatibilizar as bases mássicas.

O indicador `eta_ciclo` existente continua com o mesmo valor e significado matemático: eficiência sobre o calor útil transferido aos gases. A nova eficiência sobre PCI incorpora a fração não aproveitada representada por eta_b. `Q_total` do combustor, que representa o aumento aproximado de entalpia do ar, não foi usado como denominador.

Aplicam-se o balanço de energia em regime permanente e as definições de desempenho discutidas em Saravanamuttoo et al., Gas Turbine Theory (análise de ciclos), e Mattingly, Elements of Gas Turbine Propulsion (análise de desempenho). A aplicação mantém as hipóteses do código: gás ideal, propriedades constantes e mesmo cp para ar e gases; sem termo explícito de entalpia sensível do combustível. As identidades acima também são conferidas diretamente por unidades e pelo balanço já implementado. Este bloco não constitui nova validação integral dos livros.

Não há rendimento mecânico, gerador ou consumo auxiliar no modelo. A eficiência sobre PCI aqui apresentada não deve ser chamada de eficiência elétrica. A potência dos indicadores é a do ciclo; o fechamento com os meanlines permanece em painel separado.

## Referência manual

| Indicador | Valor |
| --- | ---: |
| Energia química pelo PCI | 9349,086664 kW |
| Calor útil transferido | 9255,595797 kW |
| Potência líquida do ciclo | 2233,239640 kW |
| Eficiência sobre calor útil | 24,128535% |
| Eficiência sobre PCI | 23,887249% |
| Eficiência de combustão | 99% |
| BWR | 0,671996 |
| SFC | 0,352122 kg/kWh |

## Apresentação e compatibilidade

- O cartão principal foi renomeado para explicitar o denominador; os valores anteriores foram preservados.
- Um expander reúne as duas eficiências, SFC, potências de entrada/saída, equações e hipóteses.
- O glossário distingue as duas eficiências.
- Os eixos de sensibilidade, na interface e no script de gráficos, identificam a eficiência sobre calor útil e a base kg de ar do trabalho líquido.
- A sensibilidade conserva `eta_ciclo_pct` e acrescenta `eta_calor_util_pct` e `eta_PCI_pct`. Os dados antigos não são renomeados nem recalculados retroativamente; execute novamente a sensibilidade para gerar os campos novos.
- Download JSON específico com unidades nos nomes dos campos e identificação da base de potência/trabalho.
- O expander de critérios distingue a definição sônica, o critério empírico de difusão, faixas comparativas de reação, limiares de aviso de Mach/swirl/fechamento e alertas geométricos. As faixas adotadas não são apresentadas como exigências universais dos livros.

O resumo de critérios não substitui todas as verificações nem certifica o projeto. Não foram alterados os avisos ou seus limites.

## Verificações

`verificar_indicadores.py` verifica 12 casos: vazões de 15 e 16 kg/s, eta_b de 0,95/0,99/1 e combustíveis JP-4/gás natural. Conferências: igualdade com eta_ciclo e BWR existentes; eta_PCI = eta_b × eta_util; compatibilidade SFC–PCI; balanço Q_util = m_a × q_ent; mesmos valores nas varreduras; ausência de mutação dos objetos serializados.

Regressão de oito casos pelo verificador de acoplamento, comparada ao resultado do bloco 4: aprovada, sem alteração dos estados ou da geometria existente.

Streamlit AppTest aprovado: execução de referência com os dois avisos anteriores, exibição dos novos indicadores/expansores/download, alteração de eta_b para 0,95, ambos os componentes automáticos com vazão de 16 kg/s e consistência das novas eficiências nas varreduras. Análise sintática de todos os arquivos Python do engine aprovada. Os testes foram programáticos; a apresentação visual final ainda deve ser conferida no navegador. Evidências em `interface.json` e `stdout_interface.txt` no checkpoint.

Comandos a partir de `NEW`:

```powershell
python -X utf8 -m engine.estudos.verificar_indicadores --saida ../checkpoints/bloco5_indicadores_2026-11-06/indicadores_depois.json
python -X utf8 -m engine.estudos.verificar_acoplamento --antes ../checkpoints/bloco4_fechamento_2026-11-06/regressao_depois.json --saida ../checkpoints/bloco5_indicadores_2026-11-06/regressao_depois.json
```

Os testes não constituem validação experimental e não tratam estol, durabilidade, emissões, resfriamento ou desempenho de gerador.

## Checkpoint

`checkpoints/bloco5_indicadores_2026-11-06/manifesto.json` identifica as cópias anteriores e seus SHA256 de:

- `NEW/engine/webapp/streamlit_app.py`
- `NEW/engine/estudos/sensibilidade.py`
- `NEW/engine/estudos/plot_sensibilidade.py`

Para reverter, restaure essas três cópias nos respectivos caminhos. Os novos módulos de indicadores/apresentação e o verificador podem permanecer sem uso.
