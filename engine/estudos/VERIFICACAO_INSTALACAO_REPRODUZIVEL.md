# Instalação reproduzível e portabilidade

Data: 18/11/2026.

## Entrega

- [Guia de instalação e execução](../../README.md), separado do README raiz de regras de colaboração.
- [Dependências diretas](../../requirements.txt), com versões explícitas.
- [Lock Windows/Python 3.10](../../requirements-lock-windows-py310.txt), com as 46 dependências diretas e transitivas do ambiente limpo.
- `.gitignore` em `NEW`, para ambientes virtuais usuais, caches Python e segredos locais Streamlit.
- `python -m engine.estudos.verificar_instalacao`, com opção `--interface` e resumo JSON opcional `--saida`.
- Cabeçalho de execução da interface atualizado. `requirements-3d.txt` agora usa a mesma versão Plotly do ambiente de referência, sem ser apresentado como lista completa do projeto.

Somente comentários de `streamlit_app.py` e a declaração da dependência Plotly foram alterados entre os arquivos preexistentes. As funções da aplicação foram comparadas por AST com o checkpoint e permaneceram idênticas. Nenhum módulo físico foi modificado.

## Dependências e ambiente

| Pacote direto | Versão |
|---|---|
| Streamlit | 1.64.0 |
| Pandas | 2.2.3 |
| NumPy | 2.1.2 |
| Matplotlib | 3.10.0 |
| Altair | 6.2.2 |
| Plotly | 6.9.0 |
| Jinja2 | 3.1.6 |

Ambiente verificado: Windows x64, CPython 3.10.8. O ambiente virtual novo foi criado sem `--system-site-packages`; seu `pyvenv.cfg` contém `include-system-site-packages = false`. A instalação usou `NEW/requirements.txt`, com pacotes baixados e instalados somente no ambiente do checkpoint. `pip check` terminou com **No broken requirements found**.

Jinja2 é declarada explicitamente porque a aplicação usa tabelas `pandas.Styler`, embora o código não a importe nominalmente. `mpl_toolkits` pertence ao Matplotlib. Os demais imports da biblioteca padrão não exigem pacotes adicionais.

O lock foi obtido desse ambiente, sem referências a diretórios locais ou instalações editáveis. Registra o conjunto instalado; não inclui o runtime Python. Não houve uma segunda instalação independente a partir do lock nem teste em Linux/macOS ou outro Python; a instalação limpa executada partiu do arquivo de dependências diretas. O lock permite solicitar as mesmas versões transitivas no ambiente Windows/Python 3.10 descrito.

O auxiliar antigo `NEW/diagnostico_dxf.py` usa `ezdxf` e dados já existentes; é opcional e não integra o fluxo da interface. FreeCAD é um aplicativo externo opcional, com seu próprio interpretador, e não uma dependência pip da aplicação. Seu uso não foi testado novamente nesta tarefa.

## Auditoria de caminhos e arquivos necessários

Foi feita uma inspeção AST dos arquivos `.py` de `NEW/engine`: nenhum erro de sintaxe. Os únicos imports externos encontrados foram Altair, Matplotlib/mpl_toolkits, NumPy, Pandas, Plotly e Streamlit; Jinja2 foi acrescentada pela dependência funcional das tabelas.

A busca por texto de caminhos absolutos encontrou um exemplo de comando FreeCAD no gerador de macros. Trata-se de documentação, não de caminho executado pelo fluxo da aplicação. A interface resolve `engine` relativamente a `__file__`; não depende do nome de usuário ou diretório do autor. A identificação do modelo lê fontes Python relativas à instalação.

Os scripts auxiliares que geram `saida_dxf/...` usam caminhos relativos ao diretório de execução. Essa convenção foi mantida e documentada: executar de `NEW` via `python -m engine...`. A interface prepara seus downloads em diretórios temporários.

## Teste de portabilidade executado

Foi preparada `checkpoints/instalacao_reproduzivel_2026-11-18/Cópia portátil/NEW`, contendo somente os arquivos Python de `engine`, os arquivos de instalação e o README. Não foram copiados livros, feedback, checkpoints históricos, resultados antigos ou a pasta `.git`. O caminho tem espaços e acentos.

O Python do ambiente isolado executou, a partir dessa cópia:

```powershell
python -m engine.estudos.verificar_instalacao --interface
```

Conferências concluídas:

1. Imports e versões das sete dependências.
2. Caso de referência manual e identidades numéricas dos componentes.
3. Perfis e loft de compressor/turbina.
4. CSVs, DXF de uma pá e tabela formatada com Jinja2.
5. Figura Matplotlib e montagem Plotly com cubo simplificado.
6. Aplicação Streamlit via AppTest: abertura, botão de cálculo, nove abas principais, sensibilidade sem erro e preparação do 3D.

Resultados de referência: **2.233.239,6399407783 W**, compressor de **8 estágios**, turbina de **3 estágios** e **2 avisos**. São consistentes com o registro de referência anterior; não foram ajustados parâmetros ou limites para remover avisos.

O AppTest emitiu avisos de depreciação referentes a chamadas preexistentes de `use_container_width`; eles não impediram as verificações. Esta tarefa não revisou essas chamadas, pois a instalação funcionou com a versão fixada. Esses avisos de API são distintos dos dois avisos do modelo físico.

## Servidor real

Também foi executado `python -m streamlit run engine/webapp/streamlit_app.py` na cópia portátil, com modo headless, estatísticas desativadas e uma porta temporária livre ligada a `127.0.0.1` apenas para o teste. O endpoint de saúde respondeu **ok**, e a página inicial respondeu HTTP **200**. O processo criado pelo verificador foi encerrado ao final.

Essas opções locais de teste não alteraram configurações permanentes, o endereço padrão da aplicação ou a possibilidade de configurá-la futuramente para outra rede/hospedagem. A abertura HTTP e o AppTest não substituem a conferência visual do WebGL no navegador; a apresentação 3D já havia sido aprovada pelo autor antes desta tarefa.

## Reprodução e limites

O guia usa diretamente `.venv/Scripts/python.exe`, dispensando alterações na política de scripts PowerShell. A primeira instalação exige acesso aos pacotes; a execução de cálculos não exige GitHub, conta Streamlit, PDFs ou FreeCAD.

Esta entrega prepara a execução local do código baixado. Não houve publicação no GitHub, criação de hospedagem, envio dos arquivos do projeto a terceiros ou alteração no ambiente Python originalmente usado pelo autor. A instalação em outro sistema ainda deve ser testada antes de se afirmar compatibilidade.

## Checkpoint e evidências

Pasta: `checkpoints/instalacao_reproduzivel_2026-11-18/`.

- `manifesto.json`: cópias anteriores e relação de arquivos novos.
- `auditoria_imports.json`: imports, versões e busca de caminhos.
- `portabilidade.json`: fontes da cópia, hashes e comparação das funções da aplicação.
- `resultado_portatil.json`: resultado completo da instalação e AppTest.
- `resultado_servidor.json` e `servidor.log`: abertura HTTP e encerramento do servidor de teste.
- `.venv-limpa/`: ambiente isolado utilizado; não é parte da distribuição em `NEW`.
- `Cópia portátil/NEW/`: cópia usada no teste, sem dados e referências externas ao código.

Para voltar aos arquivos anteriores, restaurar as cópias de `streamlit_app.py` e `requirements-3d.txt` do checkpoint. Os arquivos novos de instalação/documentação são independentes e estão relacionados no manifesto; não é necessário alterar os cálculos para deixá-los de usar. O README raiz de regras foi preservado.
