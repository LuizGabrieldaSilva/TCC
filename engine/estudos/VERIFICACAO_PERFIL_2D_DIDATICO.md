# Perfil 2D didático — 11/11/2026

Frente 3 do agrupamento aprovado, correspondente à seção 9 de `Ideias_Interface_Didatica.md`. Nenhuma mudança no núcleo físico ou na prioridade de escolha automática de estágios.

## Interface

Nas abas Compressor e Turbina, dentro de **Do escoamento ao perfil — ângulos metálicos e solidez local**, após as tabelas existentes. Os seletores de estágio, seção e fileira são compartilhados.

- Camadas independentes: extradorso, intradorso, câmber, corda, espessura, tangentes metálicas e stagger.
- Coordenadas normalizadas por c ou em cm; escala geométrica igual entre os eixos.
- Perfil alinhado à corda ou rotacionado pelo stagger no plano axial–tangencial.
- Sequência de construção ao lado do desenho; explicações de Carter no compressor e desvio zero prescrito na turbina.
- Distribuição de espessura obtida pela distância entre pares de pontos armazenados. A seta usa a amostra existente mais próxima de x/c = 0,5, sem apresentá-la como máximo exato se não coincide com o meio.
- Sobreposição opcional de cubo, seção disponível mais próxima de r_m e ponta, com tabela dos raios, cordas, staggers e câmbers. Sem interpolação de seção fictícia.
- Seletores reiniciados se uma nova execução eliminar o estágio ou a seção escolhidos.

## Referenciais e limites

`blade_profile.coordenadas` converte unidades/normaliza e aplica a mesma rotação plana de `geometry/loft2.py`: X=x cos ζ−y sen ζ, Y=x sen ζ+y cos ζ. Não modifica listas de `PerfilPa`. A sobreposição alinha bordos de entrada; não representa as posições finais da montagem 3D.

Os ângulos metálicos mostrados são referidos ao eixo axial da máquina. No desenho alinhado à corda, a tangente aponta em γ metal−ζ; com orientação, em γ metal. São tangentes à linha de câmber, não ao contorno espesso. O arco de stagger liga a direção axial à corda.

Arco circular e espessura parabólica são hipóteses geométricas existentes. O desenho não comprova pressão superficial, resistência, ausência de colisões ou desempenho aerodinâmico. Nenhum PDF foi novamente auditado nesta tarefa; as fontes e hipóteses anteriores do painel foram preservadas.

## Verificação

Da pasta `NEW`:

```powershell
python -X utf8 ../checkpoints/perfil_2d_didatico_2026-11-11/verificar.py
```

O verificador confere 306 perfis de seis combinações componente/caso: razão de pressão 8 manual com 7 seções, 8 automática com 3 e 6 automática com 4. Compara cada coordenada transformada nos dois referenciais e nas duas unidades; confere tangentes, espessura e ausência de mutação por serialização antes/depois. Salva oito imagens para inspeção visual.

AppTest exercita camadas, orientação, unidades dimensionais, comparação radial, fileiras e redução de seções/estágios. Compara referência manual e metadados automáticos com a evidência anterior. Resultados em `resultado.json`, logs em `interface.log` no checkpoint. As imagens são inspecionadas diretamente; AppTest não substitui a inspeção do layout no navegador do usuário. São verificações de apresentação/regressão, não validação experimental.

## Checkpoint e reversão

`checkpoints/perfil_2d_didatico_2026-11-11/manifesto.json` identifica cópias e SHA256 do Streamlit e da matriz anteriores. Para reverter esta tarefa, restaurar essas duas cópias nos caminhos originais e remover o novo módulo `NEW/engine/webapp/blade_profile.py` e este relatório. As evidências podem permanecer como histórico. Comparar eventuais alterações futuras antes de restaurar cópias antigas.
