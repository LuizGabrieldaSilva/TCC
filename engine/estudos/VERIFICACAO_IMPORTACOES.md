# Exemplos separados das importações

Implementado em **09/11/2026**, com autorização do autor. Checkpoint:
`checkpoints/importacoes_sem_execucao_2026-11-09/`.

## Alteração

Os módulos de ciclo, compressor e turbina criavam e resolviam `ciclo1`,
`compr1` e `turb1` durante a importação. Isso executava exemplos mesmo quando
o objetivo era apenas importar uma classe para a interface, uma verificação
ou outro cálculo.

Esses objetos globais foram substituídos por funções explícitas:

```python
from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo

ciclo = criar_ciclo_exemplo()          # Exemplo com 15 kg/s
comp = criar_compressor_exemplo()      # Exemplo automático
turb = criar_turbina_exemplo()         # Exemplo automático
```

Cada chamada cria e resolve um objeto novo. Não há cache nem objeto de exemplo
compartilhado. São exemplos independentes: as três chamadas acima **não**
constroem um novo pipeline acoplado entre si. A interface continua montando
seu próprio pipeline com as entradas submetidas e a massa de combustível.

Os parâmetros dos antigos exemplos automáticos foram mantidos, inclusive o
fato de a turbina desses exemplos históricos usar o ciclo sem registrar o
acréscimo de combustível. A refatoração não converte esses exemplos em uma
nova referência integrada.

Os exemplos de combustor, distribuição radial, perfis e loft agora chamam as
funções explicitamente dentro de seus pontos de entrada. Os scripts de CSV,
regressão, teste de loft e geração de macros foram protegidos por `main()` e
`if __name__ == "__main__"`. Importá-los não gera resultados ou arquivos.

Classes e funções físicas preexistentes não foram alteradas. Também foram
preservados os parâmetros próprios dos exemplos executados diretamente:
por exemplo, o ciclo direto usa 3,085 kg/s e os meanlines diretos usam os
casos manuais de 8 e 3 estágios. O `baseline_regressao.py` mantém seu caso
histórico, inclusive ψ da turbina igual a 1,21.

## Como executar

A partir de `NEW`, continuam disponíveis os pontos de entrada por módulo:

```powershell
python -m engine.ciclo.CicloBrayton
python -m engine.compressor.Compressor_Meanline_main
python -m engine.turbina.Turbine_Meanline_main
python -m engine.combustor.Combustor_1D_2_main
python -m engine.aero.radial_compressor_4_main
python -m engine.aero.radial_turbina_3_main
python -m engine.geometry.airfoil4
python -m engine.geometry.loft2
python -m engine.estudos.baseline_regressao DEPOIS
python -m engine.estudos.csv_test
```

Scripts de exportação geram saídas somente quando executados explicitamente.
As demonstrações de geometria continuam podendo abrir figuras no ambiente
normal do usuário. O aplicativo continua sendo iniciado por `streamlit run`.

## Verificações e evidências

- **60 arquivos importados** sem chamadas aos construtores/resolvedores físicos,
  sem mensagens em stdout/stderr e sem arquivos de saída no diretório isolado.
  O aplicativo Streamlit, que é um ponto de entrada, foi verificado separadamente.
- Estados completos das três funções de exemplo iguais aos estados dos antigos
  objetos globais, capturados antes da refatoração em `exemplos_antes.json`.
- Chamadas repetidas da função de compressor produzem objetos e ciclos
  independentes; modificar um não modifica o outro.
- Comparação sintática das definições preexistentes de classes e funções,
  incluindo o auxiliar do teste de loft que passou a ficar dentro de `main()`.
- Nove verificadores de regressão aprovados: acoplamento, seleção, detalhes dos
  critérios, combustor, indicadores, diagnósticos, continuidade da turbina,
  perfis e entradas. Resultados e prioridades preservados.
- **18 execuções diretas sem exceções**, incluindo geração de CSV e macros.
  As saídas de teste estão exclusivamente no checkpoint, em `exemplos_diretos/`.
  Os gráficos foram executados com backend Agg, sem abrir janelas.
- AppTest da interface aprovado: avisos e potência manuais, seleção automática
  completa e 56 pontos de sensibilidade preservados, sem erro computacional.

Comandos, códigos de saída e logs estão em `execucoes.json`,
`exemplos_diretos.json`, `importacoes.json`, `interface.json` e arquivos `.log`.
O verificador reproduzível é `engine.estudos.verificar_importacoes`.

Não foi executado o FreeCAD: foi testada a **geração** das macros `.FCMacro`,
não sua abertura, execução ou exportação STEP dentro do programa. AppTest não
é inspeção visual no navegador. Nenhum desses testes certifica desempenho
físico, resistência ou fabricabilidade.

## Pendências antigas observadas

`Temporários/teste_loft_completo.py` ainda espera seis fileiras na turbina e
a sequência `['bocal', 'rotor'] * 3`. O antigo objeto automático já tinha
quatro estágios, como consta no snapshot anterior; o exemplo explícito
preservado gera oito fileiras. Por isso o script termina com código zero,
mas imprime **duas divergências de expectativa**, registradas no log da
execução direta 11. Não são falhas novas dos cálculos ou dos gaps axiais.

Há rótulos históricos relacionados em `estudos/csv_test.py` (21 linhas
esperadas para a turbina) e na demonstração de `geometry/loft2.py` (título
de três estágios). Eles foram preservados, não tratados como testes aprovados
de contagem. A atualização dessas expectativas/rótulos para os objetos
realmente executados é uma pendência identificada para a próxima revisão.

Os antigos imports de objetos de exemplo (`from ... import compr1`, por
exemplo) deixam de ser uma API disponível. Os 13 consumidores encontrados em
`NEW/engine` foram migrados. Cópias históricas em `NEW/Arquivos de apoio` e os
materiais de feedback foram preservados; caso se queira reexecutá-los, pode
ser necessária uma adaptação explícita. Eles não fazem parte do pipeline atual.

## Retorno ao checkpoint

Foram preservados 19 arquivos antes da edição, com caminhos relativos e hashes
SHA-256 no `manifesto.json`. Para voltar, encerrar o Streamlit e copiar apenas
esses arquivos de `checkpoints/importacoes_sem_execucao_2026-11-09/NEW/engine/`
para os caminhos correspondentes em `NEW/engine/`.

Após restaurar, os novos `estudos/verificar_importacoes.py` e este relatório
podem ser removidos se desejado. Não é necessário resetar o Git ou substituir
outros arquivos do projeto.
