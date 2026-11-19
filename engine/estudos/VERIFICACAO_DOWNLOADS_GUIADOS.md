# Downloads e exportação CAD guiada — 12/11/2026

Implementação do bloco 8 da ordem aprovada, correspondente à documentação e prévia de exportações da seção 14 de `Ideias_Interface_Didatica.md`. Não altera cálculos ou exportadores.

## Uso

Na aba Downloads, o painel **Qual arquivo baixar e como utilizá-lo?** descreve CSV, JSON, DXF/ZIP e a indisponibilidade de STEP. Distingue tabelas, diagnósticos, curvas e sólidos. Explica a convenção decimal técnica dos arquivos, mantida apesar da vírgula decimal na interface.

Em **Prévia e exportação CAD por seleção**:

1. Escolher Compressor ou Turbina.
2. Escolher uma fileira, um estágio ou o componente completo; selecionar estágio/fileira quando aplicável.
3. Conferir a tabela de peças, Z, seções e raios e a prévia opcional de curvas.
4. Clicar em **Preparar arquivo desta seleção** e depois baixar o DXF ou ZIP preparado.

Uma fileira corresponde à sua pá de referência, não ao anel completo. Um estágio inclui as duas pás de referência das fileiras. O componente completo inclui uma pá por fileira/estágio. O combustor 1D não tem geometria CAD de pás neste fluxo.

A seleção preparada é associada à identificação da execução e aos seletores. Uma mudança de conteúdo ou uma nova execução oculta o download anterior até nova preparação. Seletores são revalidados se o número de estágios diminuir ou se a troca de componente invalidar o tipo de fileira.

Os botões completos anteriores continuam disponíveis. Seu ZIP passou a usar a lista de arquivos retornada pela exportação atual, evitando incluir arquivos antigos de estágios adicionais que permaneçam na pasta temporária.

## Geometria e limitações

`download_guidance.curvas_perfil` usa a função existente `_fechar_perfil` do escritor DXF para formar os mesmos laços fechados. A prévia mostra contornos e câmber dos pontos calculados, sem gerar novo loft ou superfície. Para leitura do componente completo, o Z axial do CAD é desenhado na horizontal; X e Y continuam identificados como coordenadas cartesianas transversais. A tabela e os eixos usam metros. As coordenadas exportadas não são permutadas.

O DXF por seleção reutiliza `exportar_peca_dxf` com os nomes reais das seções, gerando camadas `HUB_PERFIL`/`TIP_PERFIL` e `CAMBER`. Os pacotes completos anteriores continuam com os nomes de seção por índice. O escritor mantém seis casas decimais em metros; a prévia usa os pontos anteriores a esse arredondamento.

A ajuda orienta conferir unidades/dimensões na importação e ordenar as seções do cubo para a ponta. O arquivo fornece curvas 3D para construir e conferir um loft; não contém um sólido pronto. Câmber aberto não é contorno de sólido. Não há curvas-guia, validação de colisões, folgas, estrutura ou fabricação. Os espaçamentos axiais são convenções do modelo. Não foi executada importação, construção de sólido ou exportação STEP no FreeCAD nesta tarefa; essa verificação é uma etapa própria.

## Verificação

Da pasta `NEW`:

```powershell
python -X utf8 ../checkpoints/downloads_guiados_2026-11-12/verificar.py
```

Seis seleções de referência: os três alcances em cada componente. Confere número de arquivos, nomes de camadas/unidades, igualdade byte a byte com chamadas diretas ao escritor existente e ausência de mutação dos objetos. Compara os pontos da prévia com os laços do loft, considerando somente a permutação dos eixos de visualização. Salva seis imagens; prévias de uma fileira e de componente completo foram inspecionadas.

Teste adicional verifica que empacotar os caminhos atuais não inclui um arquivo antigo presente na mesma pasta. AppTest exercita preparação, mudança de alcance, troca de fileira/componente, invalidação por nova execução e redução de estágios. Confere a referência manual, os avisos e as escolhas automáticas contra a evidência anterior. Os resultados finais ficam em `resultado.json` e `interface.log` no checkpoint.

Essas verificações conferem seleção e escrita de curvas; não comprovam importação CAD nem validade de sólido. A inspeção de figuras não substitui a avaliação do layout no navegador do usuário.

## Checkpoint e reversão

`checkpoints/downloads_guiados_2026-11-12/manifesto.json` identifica a cópia anterior do Streamlit e seu SHA256. Para reverter esta tarefa, restaurar essa cópia e remover o novo módulo `NEW/engine/webapp/download_guidance.py` e este relatório, comparando mudanças posteriores antes de restaurar. `arquivos_depois.json` identifica os fontes finais. Os módulos de cálculo e os escritores CAD/CSV permaneceram inalterados.
