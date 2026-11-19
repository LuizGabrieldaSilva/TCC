# Apresentação da prévia CAD — 12/11/2026

Refinamento autorizado após os prints da aba Downloads: reduzir espaço em branco/altura, eliminar rótulos cortados/sobrepostos e oferecer detalhe de estágio sem deformar a geometria.

## Mudanças

- Título e explicações saíram do bitmap e ficam em texto normal do Streamlit.
- Imagens com largura limitada, tamanhos distintos para uma fileira, estágio e componente completo. As alturas nominais na largura escolhida são até 378 px, evitando o crescimento anterior pela largura total da página.
- Projeção ortográfica, zoom uniforme calculado a partir dos pontos projetados e mesma razão entre escalas dos três eixos. Não muda a geometria ou a exportação.
- Removidos grade, números e rótulos internos que se sobrepunham. Uma pequena tríade X/Y/Z indica a orientação. Os limites cartesianos das curvas são apresentados logo abaixo, em metros e com vírgula decimal.
- No componente completo, a opção **Mostrar detalhe de um estágio** permite ampliar o estágio escolhido. Esse seletor é próprio da vista e não muda a seleção ou o arquivo preparado para download.

O componente completo continua alongado conforme as proporções calculadas e os espaçamentos do modelo. A ampliação mostra um subconjunto em maior tamanho sem comprimir o eixo axial nem exagerar a altura das pás. A imagem continua sendo uma projeção estática das curvas 3D, sem superfície ou sólido.

## Conferência

Da pasta `NEW`:

```powershell
python -X utf8 ../checkpoints/layout_previa_cad_2026-11-12/verificar.py
```

Seis seleções: fileira, estágio e componente completo do compressor e da turbina. O verificador confere coordenadas das curvas, ausência de mutação, limites XYZ e enquadramento dos pontos dentro do quadro. Compara por AST as funções de seleção, preparação do arquivo, fechamento de curvas e empacotamento com a cópia anterior: permanecem iguais.

As imagens de fileira, estágio e componente completo foram renderizadas e inspecionadas. AppTest exercita o detalhe, sua independência do arquivo preparado e a revalidação do seletor ao trocar para um componente com menos estágios. Evidências em `resultado.json`, `interface.log` e seis PNGs no checkpoint.

A inspeção é de imagens e teste automatizado do Streamlit, não captura do navegador completo. Não acrescenta validação de CAD, de sólido ou física.

## Checkpoint e reversão

`checkpoints/layout_previa_cad_2026-11-12/manifesto.json` identifica a cópia anterior de `NEW/engine/webapp/download_guidance.py` e seu SHA256. Para reverter somente este refinamento, restaurar essa cópia e remover este relatório; conferir mudanças posteriores antes de sobrescrever. Os downloads guiados anteriores permanecem implementados. Nenhum exportador ou módulo físico foi alterado.
