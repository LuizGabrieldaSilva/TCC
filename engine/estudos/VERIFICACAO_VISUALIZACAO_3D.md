# Visualização 3D na interface

Data: 16/11/2026.

## Funcionalidade

Nova aba **Geometria 3D**, com compressor ou turbina; uma pá como padrão, um estágio ou componente completo. Inclui repetição circunferencial, setores de 90° a 360°, vista leve de até 24 pás por fileira, detalhe dos contornos, seções da pá de referência, eixos, vistas iniciais e rotação/zoom com o mouse.

O botão **Gerar ou atualizar montagem 3D** prepara somente a visualização. Não executa os cálculos físicos. Alterar a seleção ou calcular uma nova execução invalida a apresentação preparada. O uso do botão evita gerar malhas grandes em todas as atualizações das outras abas.

## Geometria e alcance

- Coordenadas originais de `extradorso_cart` e `intradorso_cart`, dos objetos calculados pelo pipeline.
- Triângulos ligam pontos correspondentes entre seções radiais. Todas as seções calculadas são mantidas; apenas os pontos ao longo dos contornos são subamostrados para apresentação.
- Rotação rígida em torno do Z original, com passo `2π/Z_pas`, igual ao escritor DXF completo e ao macro FreeCAD. A vista apenas permuta os eixos para colocar Z axial na horizontal; mantém as proporções físicas.
- A vista leve desenha índices inteiros de pás nas posições reais, sem alterar o passo angular. A tabela informa a quantidade real e a desenhada. Desativá-la permite desenhar todas as pás do setor escolhido.
- Malha aberta no cubo e na ponta: não é um sólido nem reproduz o algoritmo de loft do FreeCAD. Não fornece verificação de colisões ou fabricação.
- Espaçamentos axiais e alinhamento angular seguem a montagem existente. Não representam dimensionamento mecânico ou análise de interação entre fileiras.
- Compressor e turbina são exibidos separadamente. Não foi inventada uma conexão geométrica entre eles: combustor 1D e difusor não fornecem a geometria necessária.
- Nenhuma alteração em fórmulas, parâmetros, critérios, prioridades automáticas ou exportações CAD.

## Dependência

Plotly 6.9.0 instalado no Python usado nos testes. Para outro ambiente, além das dependências já usadas pelo projeto, executar de `NEW`:

```powershell
python -m pip install -r engine/webapp/requirements-3d.txt
```

O gráfico é gerado localmente, sem serviço externo de visualização. Arquivos HTML de inspeção incluem a biblioteca JavaScript para abertura local.

## Verificação

De `NEW`:

```powershell
python ../checkpoints/visualizacao_3d_2026-11-16/verificar.py
python ../checkpoints/visualizacao_3d_2026-11-16/inspecionar_malha.py
```

Foram reutilizados resultados reais já calculados, incluindo a turbina automática de quatro estágios. Conferidos: rotação contra `_rotacionar_curva`, preservação de raios e coordenadas axiais, índices de triângulos, ausência de triângulos degenerados no caso testado, repetição completa e amostragem explícita.

AppTest verificou os controles, geração sob demanda, mudança de componente, invalidação por nova execução e presença da nova aba na aplicação completa, sem exceções. Os objetos de resultados não foram modificados. As funções existentes de cálculo da aplicação foram comparadas por AST com o checkpoint e permaneceram idênticas.

O acesso ao navegador pela ferramenta de controle estava indisponível. Portanto, AppTest confirma a preparação do gráfico, mas a renderização WebGL, os gestos do mouse e o layout final no navegador ainda precisam de conferência visual na interface do usuário. As imagens Matplotlib auxiliares representam as mesmas malhas e não substituem essa conferência.

## Checkpoint

`checkpoints/visualizacao_3d_2026-11-16/` contém cópias de `streamlit_app.py` e `reading_mode.py`, manifesto SHA256, verificadores, resultados e arquivos locais de inspeção. Integridade dos backups conferida.

Para voltar, restaurar essas duas cópias sobre os caminhos correspondentes em `NEW/engine/webapp/`. Os novos arquivos `assembly_3d.py` e `requirements-3d.txt` deixam de ser utilizados ao restaurar o aplicativo; podem ser preservados para consulta.
