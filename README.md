# Projeto preliminar de turbina a gás axial

Ferramenta didática em Python e Streamlit que conecta ciclo Brayton, compressor, combustor 1D, turbina, distribuição radial, perfis e geometria paramétrica. O projeto permite estudar resultados e hipóteses, comparar casos e exportar tabelas e curvas CAD.

## Ambiente de referência

- Windows de 64 bits e **CPython 3.10**. A verificação de instalação usa Python **3.10.8**; isso identifica o ambiente testado, não exige instalar especificamente esse patch antigo.
- Navegador com JavaScript e WebGL para a montagem 3D.
- Internet para obter o Python e instalar as dependências. O cálculo local não depende de uma conta Streamlit, GitHub ou serviço de nuvem.
- Outros sistemas e versões de Python ainda não foram verificados nesta entrega.

Os sete pacotes diretos e suas versões estão em [requirements.txt](requirements.txt). [requirements-lock-windows-py310.txt](requirements-lock-windows-py310.txt) registra também as dependências transitivas do ambiente limpo de referência. O lock não inclui o instalador Python, o navegador ou o FreeCAD.

As regras de colaboração locais ficam no README da pasta superior, quando esta acompanha a cópia do projeto. Para versionar e atualizar este repositório, consulte [CONTRIBUTING.md](CONTRIBUTING.md). A preparação e as decisões ainda pendentes estão em [PREPARACAO_GITHUB.md](PREPARACAO_GITHUB.md).

## Propriedades do ar e dos gases

O caso atual calcula produtos de combustão completa a partir de combustíveis representativos e ar seco. A integral dos coeficientes NASA Glenn entre 298,15 K e TIT fornece um **cp equivalente constante** dos gases; a composição fornece R e `k=cp/(cp−R)`. O ar mantém cp prescrito (padrão 1005 J/(kg·K)) e R calculado pela composição seca. A turbina não integra cp variável durante a expansão. O formulário permite desativar esse modo e prescrever cp/R, inclusive para reproduzir exercícios antigos; arquivos de casos antigos preservam o modo prescrito. A escolha manual de ψ e número de estágios pode divergir dos alvos do ciclo.

JP-8 e diesel mineral usam aqui o mesmo substituto elementar C12H23, com PCI distintos. Nas condições de referência, esses PCI produzem f, composição e propriedades diferentes; à mesma temperatura e f, o substituto comum produz propriedades iguais. Isso é uma limitação explícita, sem representar diferenças detalhadas entre lotes ou aditivos. Gás natural é aproximado por metano puro e JP-4 por CH1,94. Não há equilíbrio, dissociação, cinética, emissões ou biodiesel. Fontes, resultados e verificações: [mistura dos combustíveis](engine/estudos/VERIFICACAO_MISTURA_COMBUSTIVEIS.md).

Consulte [hipóteses, resultados e verificações das propriedades](engine/estudos/VERIFICACAO_PROPRIEDADES_AR_GASES.md). Arquivos antigos de entradas restauram a hipótese de cp único explicitamente; os novos arquivos preservam as quatro propriedades submetidas.

## Instalar e executar no Windows

Baixe a pasta do projeto ou extraia o ZIP do repositório. **Mantenha toda a pasta `engine` e sua estrutura.** Abra o PowerShell na pasta que contém `engine`, `README.md` e `requirements.txt`. Na cópia completa do TCC, essa pasta se chama `NEW`; por exemplo, se o terminal está na pasta `TCC`:

```powershell
cd .\NEW
```

Se você baixou somente o repositório de `NEW`, a pasta extraída pode ter outro nome. Entre nela diretamente; não é necessário haver outra subpasta `NEW`. Os demais comandos abaixo são executados nessa raiz.

Confira o Python e crie um ambiente virtual:

```powershell
py -3.10 --version
py -3.10 -m venv .venv
```

Se o comando `py` não existir, use `python --version` e, tendo selecionado o Python 3.10, `python -m venv .venv`.

Instale os pacotes e confira as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Para repetir as versões diretas **e transitivas** do teste Windows/Python 3.10, use o lock no lugar de `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock-windows-py310.txt
```

Inicie a interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run engine/webapp/streamlit_app.py
```

Abra no navegador o endereço local mostrado no terminal, normalmente `http://localhost:8501`. Mantenha o terminal aberto enquanto usar a interface; **Ctrl+C** encerra o servidor. Para abrir novamente, repita o último comando, dentro de `NEW`.

Não é necessário ativar o ambiente virtual: os comandos usam diretamente seu Python. Isso também evita depender da política de execução de scripts do PowerShell. Instale os pacotes com o mesmo executável usado para iniciar o Streamlit.

Nenhum destes comandos configura hospedagem pública ou publicação no GitHub. A instalação local permite executar o código baixado; disponibilizar um endereço público é uma etapa separada.

## Conferir a instalação

Teste do cálculo de referência, geração de perfis, CSV/DXF, tabela formatada, figura e montagem 3D:

```powershell
.\.venv\Scripts\python.exe -m engine.estudos.verificar_instalacao
```

Para também abrir a aplicação em teste automatizado, acionar o cálculo, verificar a sensibilidade e preparar a montagem:

```powershell
.\.venv\Scripts\python.exe -m engine.estudos.verificar_instalacao --interface
```

O segundo comando pode demorar mais. Ele usa AppTest, sem abrir uma janela de navegador. Para salvar o resumo da conferência:

```powershell
.\.venv\Scripts\python.exe -m engine.estudos.verificar_instalacao --interface --saida verificacao_instalacao.json
```

Arquivos de teste intermediários usam uma pasta temporária. O teste não altera parâmetros ou resultados da interface aberta. Avisos físicos podem permanecer no caso de referência: sucesso de instalação não significa aprovação física. A inspeção de rotação/zoom WebGL deve ser feita no navegador.

## Primeiro uso e recuperação de casos

1. Confira as condições, escolhas e hipóteses no formulário. A rotação é comum ao compressor e à turbina.
2. Clique em **Calcular e atualizar gráficos**. Consulte o estado das etapas e os avisos.
3. Os resultados pertencem à execução identificada no topo. Alterar os campos sem calcular não altera o caso já calculado.
4. Em **Geometria 3D**, escolha a vista e clique em **Gerar ou atualizar montagem 3D**. A vista leve reduz apenas o desenho.
5. Em **Downloads**, guarde o JSON de entradas e, após preparar, o relatório ZIP. Para repetir o caso, importe o JSON em **Salvar e recuperar casos**, aplique as entradas e calcule novamente.

A comparação de casos e outras seleções ficam na sessão do navegador. Guarde as entradas e relatórios antes de encerrá-la. Para repetir resultados, preserve também a versão do código e das dependências. Não use os JSONs de diagnósticos/resultados como se fossem o JSON de entradas.

## Ferramentas e arquivos opcionais

| Recurso | Necessário para executar a interface? | Observação |
|---|---|---|
| PDFs dos livros e pasta de feedback | Não | Referências de estudo; não são arquivos de execução. |
| Diretório `checkpoints` e resultados antigos | Não | Evidências e cópias de segurança; o teste de instalação não depende deles. |
| Git | Não, ao baixar um ZIP | Útil para versionamento; não é usado pelo cálculo. |
| FreeCAD | Não | Necessário apenas para executar as macros e conferir a reconstrução CAD. Usa seu próprio Python. |
| STEP | Não disponível como entrega validada na interface | A existência de macro ou malha na tela não garante sólido STEP válido. |
| `diagnostico_dxf.py` na raiz de `NEW` | Não | Auxiliar antigo que depende de `ezdxf` e de DXFs preexistentes; não integra a interface nem o verificador de instalação. |

Os DXFs exportados contêm curvas 3D de seções, em **metros**. Importe-as em um aplicativo CAD e confira unidades, dimensões, fechamento e ordem das seções antes do loft. A montagem 3D da interface é uma malha visual; o cubo simplificado não é exportado e não é um projeto estrutural.

Exemplo opcional de geração de uma macro com a infraestrutura existente, a partir de `NEW`:

```powershell
.\.venv\Scripts\python.exe -m engine.cad.Export_Macro.Macros_Tests.Macro_Turbina_Completo
```

Esse exemplo independente usa suas próprias definições de referência; não exporta automaticamente o caso atualmente aberto no Streamlit. O arquivo é criado em `saida_dxf/macro_turbina_replicada.FCMacro`. Sua execução ocorre dentro do FreeCAD e requer conferência própria. Não instale um pacote chamado `FreeCAD` no ambiente virtual como substituto do aplicativo.

Os scripts de sensibilidade, plots, baseline e macros devem ser executados de `NEW`, usando `python -m engine...`. Seus caminhos `saida_dxf/...` são relativos à pasta de execução; a interface usa arquivos temporários para preparar downloads. Não há necessidade de criar uma pasta com o nome de usuário ou caminho do computador do autor.

## Problemas comuns

| Mensagem/sintoma | Como conferir |
|---|---|
| `No module named streamlit`, `plotly` ou outra biblioteca | Instale `requirements.txt` com `.\.venv\Scripts\python.exe`, e inicie a interface com o mesmo executável. |
| `No module named engine` ao executar um estudo | Abra o terminal em `NEW` e use `python -m engine.estudos.nome_do_script`. |
| Comando `streamlit` não encontrado | Use `python -m streamlit`, como nos exemplos acima. |
| Porta 8501 ocupada | Feche a outra execução ou acrescente `--server.port 8502` ao comando Streamlit. |
| Montagem 3D não aparece ou fica lenta | Gere a montagem, teste uma pá e a vista leve; confira WebGL/aceleração gráfica do navegador. |
| Resultados ainda mostram os valores anteriores | Clique em **Calcular e atualizar gráficos** após editar as entradas. |
| Erro de permissão ao gerar arquivos auxiliares | Extraia o projeto em uma pasta onde seu usuário possa gravar e execute os scripts de lá. |

## Organização e alcance

`engine/webapp/streamlit_app.py` é a entrada principal da interface. Os módulos de ciclo, combustor, compressor, turbina, aerodinâmica e geometria ficam em `engine/`; estudos/verificadores ficam em `engine/estudos/`. Arquivos antigos em pastas de apoio não são necessários para iniciar a aplicação atual.

O modelo é preliminar: propriedades constantes e perdas simplificadas; vórtice livre; perfis paramétricos. Não resolve CFD, projeto estrutural, resfriamento de turbina, química detalhada ou difusor compressor–combustor. Leia as limitações e os avisos na interface. As exportações não são documentação de fabricação.

A instalação limpa, as versões e o teste de portabilidade estão registrados em [VERIFICACAO_INSTALACAO_REPRODUZIVEL.md](engine/estudos/VERIFICACAO_INSTALACAO_REPRODUZIVEL.md).
