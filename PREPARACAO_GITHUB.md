# Preparação para o GitHub — 19/11/2026

## Situação observada

- `NEW` já contém um repositório Git, separado do repositório da pasta superior `Codigos`.
- Branch local atual: `oficial`, ainda sem commits. O remoto `origin` aponta para `https://github.com/LuizGabrieldaSilva/TCC.git`, sem credenciais embutidas na URL.
- Uma consulta somente de leitura confirmou que o remoto já contém a branch `main`, no commit `5dc4fb7ae14f185363d988bf38b1945d2acb477b`. O conteúdo desse commit e a visibilidade do repositório não foram inspecionados. O histórico remoto precisa ser preservado e conciliado com esta cópia local antes do envio.
- Há quatro inclusões antigas no índice, três das quais correspondem a arquivos ausentes na pasta de trabalho. Esse estado foi preservado; não é uma base pronta para um primeiro commit.
- A aplicação atual e sua documentação ainda aparecem como conteúdo não rastreado. As exclusões novas não retiram do índice as inclusões antigas.

## Preparação aplicada

- Exclusões para livros locais, saídas CAD geradas, backups, ambientes, segredos locais e rascunhos.
- Preservação dos JSON de coeficientes NASA como candidatos ao versionamento.
- Regras de finais de linha em `.gitattributes`, sem renormalização em massa.
- README ajustado para execução a partir de um clone/ZIP cuja raiz já corresponde a `NEW`.
- Guia de atualizações, checkpoints e verificações em `CONTRIBUTING.md`.

Nenhuma licença de reutilização foi escolhida. A disponibilidade pública futura deverá acompanhar uma decisão explícita sobre licença e materiais distribuíveis.

## Antes do primeiro envio

1. Conferir o conteúdo da `main` remota, titularidade e visibilidade desejada. Usar uma cópia de trabalho isolada para comparar o histórico remoto com o projeto local antes de decidir como conciliá-los. Não forçar envio nem sobrescrever o histórico existente.
2. Revisar com o autor as quatro inclusões históricas e decidir o que deve compor o primeiro commit. Não limpar nem substituir o índice automaticamente.
3. Revisar a lista final de arquivos e materiais de terceiros. Referências bibliográficas devem acompanhar o projeto; os PDFs locais permanecem excluídos.
4. Executar as verificações adequadas na cópia que será distribuída. Os testes físicos e de interface não foram reexecutados nesta alteração de documentação e configuração Git.
5. Conciliar o histórico remoto existente, preparar um commit revisado com as mudanças locais e somente então enviar ao remoto autorizado. Não criar uma história independente e substituí-la sobre a `main` remota.
6. Escolher a licença antes de anunciar permissões de reutilização. Hospedagem pública e automação de testes podem ser configuradas depois de definido o repositório remoto.

## O que esta preparação não conclui

A configuração não publica arquivos, não cria histórico de commits e não altera os cálculos. A triagem de credenciais por padrões conhecidos é limitada: ausência de correspondência não garante ausência de informações privadas. A revisão do conteúdo continua necessária antes de enviar.

## Conferência desta preparação

- `git check-ignore`: exclusões confirmadas para livros, saídas, backups, `.env` e rascunhos.
- Dois JSON NASA e os documentos novos aparecem como candidatos ao versionamento.
- 123 arquivos novos candidatos, somando aproximadamente 1,04 MiB; nenhum PDF, backup `.bak` ou DXF nessa lista. Essa contagem não inclui os quatro arquivos históricos já preparados no índice.
- Conteúdo preparado no índice comparado com o registro anterior: preservado.
- Links locais dos documentos de preparação conferidos.
- Consulta `git ls-remote --heads --tags origin`: leitura bem-sucedida; confirmou a `main` existente, sem envio de arquivos.
