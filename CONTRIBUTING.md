# Versionamento e atualizações

## Raiz do repositório

Execute os comandos Git na pasta que contém `engine` e `requirements.txt` (na cópia do autor, `NEW`). A pasta superior do TCC pode pertencer a outro repositório. Confira antes de trabalhar:

```powershell
git rev-parse --show-toplevel
git status
```

## Conteúdo versionado

Inclua código, dependências, documentação e verificadores pertinentes. Preserve também `engine/combustor/glenn_200_1000.json` e `engine/combustor/glenn_1000_6000.json`: são dados de execução, não resultados descartáveis. Os livros locais, ambientes virtuais, backups, saídas em `saida_dxf` e rascunhos estão no `.gitignore`; ignorar não apaga arquivos.

Não inclua segredos, dados pessoais ou materiais de terceiros sem autorização de distribuição. O `.gitignore` é uma primeira barreira, não uma auditoria de todo o conteúdo. Arquivos já preparados ou rastreados não deixam de sê-lo ao adicionar uma regra de exclusão.

## Fluxo de uma alteração

1. Registre um checkpoint recuperável antes de editar, conforme as regras do autor. Depois que houver histórico Git, um commit dos arquivos pertinentes pode cumprir esse papel. Arquivos não versionados continuam precisando de backup próprio.
2. Parta de uma versão funcional e crie uma branch para a alteração, por exemplo `melhoria/diagramas-ts`. O nome da branch estável será definido na organização inicial do repositório.
3. Faça uma mudança de escopo claro. Alterações nas fórmulas, hipóteses e parâmetros exigem autorização do autor e justificativa teórica.
4. Execute as verificações pertinentes, atualize a documentação e revise a diferença. Mudanças da interface também requerem conferência visual no navegador.
5. Prepare somente os arquivos revisados e confira o conteúdo antes de fazer o commit:

```powershell
git diff
git add -- caminho/do/arquivo.py caminho/do/relatorio.md
git diff --cached --stat
git diff --cached
git commit -m "Descreve a alteração e seu propósito"
```

Os caminhos são exemplos e devem ser substituídos. Não use inclusão indiscriminada na organização inicial: pode haver arquivos antigos já preparados. A revisão do diff preparado deve abranger todos os arquivos que entrarão no commit.

6. Incorpore à branch estável apenas após a conferência. Envio remoto, visibilidade pública e publicação de releases dependem da autorização correspondente.

## Verificações existentes

Na raiz do projeto, usando o ambiente descrito no README:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m engine.estudos.verificar_instalacao
.\.venv\Scripts\python.exe -m engine.estudos.verificar_instalacao --interface
```

Escolha verificadores adicionais em `engine/estudos` conforme o módulo alterado; o teste de instalação não substitui as verificações teóricas. A comparação bibliográfica registra uma divergência conhecida no exemplo de Dixon: consulte `engine/estudos/COMPARACAO_EXEMPLOS_LIVROS.md`. Não afrouxe critérios nem omita divergências para obter um resultado de testes aparentemente aprovado.

## Entregas e resultados acadêmicos

Depois de um commit revisado, uma tag pode identificar a versão entregue ao professor. Guarde junto aos resultados o identificador do commit/tag, o JSON de entradas calculadas e as versões das dependências. Uma nova hipótese de propriedades pode mudar resultados mesmo com entradas parecidas.

Registre nas descrições: o problema, o comportamento resultante, as verificações executadas e as limitações restantes. Separe alterações de apresentação de mudanças físicas sempre que isso facilitar a revisão.

## Execução e hospedagem

O GitHub armazena o código. A execução local segue o README e não requer os PDFs. Hospedagem da interface é uma etapa separada: o ambiente verificado é Windows/Python 3.10; Linux, limites de memória e desempenho da montagem 3D precisam de conferência antes de anunciar uma implantação em nuvem como funcional.
