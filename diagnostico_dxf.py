import ezdxf, os
from collections import Counter

pasta_script = os.path.dirname(os.path.abspath(__file__))
caminho = os.path.join(pasta_script, "saida_dxf", "teste_rotor_e1.dxf")

doc = ezdxf.readfile(caminho)
msp = doc.modelspace()
entidades = list(msp)
print(f"Total de entidades: {len(entidades)}")

contagem = Counter(e.dxf.layer for e in entidades)
for layer, qtd in sorted(contagem.items()):
    print(f"  {layer}: {qtd}")

try:
    doc = ezdxf.readfile(caminho)
    print("✓ Arquivo lido com sucesso pelo ezdxf (formato válido).")
    msp = doc.modelspace()
    entidades = list(msp)
    print(f"Total de entidades no modelspace: {len(entidades)}")
    tipos = {}
    for e in entidades:
        tipos[e.dxftype()] = tipos.get(e.dxftype(), 0) + 1
    print("Contagem por tipo:", tipos)
except Exception as e:
    print(f"✗ ezdxf REJEITOU o arquivo:")
    print(f"  {type(e).__name__}: {e}")
    

from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt

fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1])
ctx = RenderContext(doc)
backend = MatplotlibBackend(ax)
Frontend(ctx, backend).draw_layout(msp, finalize=True)
ax.set_aspect('equal')
ax.set_xlim(0.19, 0.20)   # ajuste conforme o raio real da seção hub, se souber
ax.set_ylim(-0.005, 0.025)
fig.savefig("saida_dxf/preview_zoom_hub.png", dpi=200)
print("Preview salvo em saida_dxf/preview_rotor_e1.png")


import ezdxf
import os
import matplotlib.pyplot as plt

segmentos = [e for e in msp if e.dxftype() == "LINE" and e.dxf.layer == "HUB_PERFIL"]
print(f"Segmentos em HUB_PERFIL: {len(segmentos)}")  # esperado 100

xs, ys, zs = [], [], []
for seg in segmentos:
    xs += [seg.dxf.start.x, seg.dxf.end.x]
    ys += [seg.dxf.start.y, seg.dxf.end.y]
    zs += [seg.dxf.start.z, seg.dxf.end.z]

print(f"x: [{min(xs):.5f}, {max(xs):.5f}]  (variação={(max(xs)-min(xs))*1000:.3f} mm)")
print(f"y: [{min(ys):.5f}, {max(ys):.5f}]  (variação={(max(ys)-min(ys))*1000:.3f} mm)")
print(f"z: [{min(zs):.5f}, {max(zs):.5f}]  (variação={(max(zs)-min(zs))*1000:.3f} mm)")

fig, ax = plt.subplots(figsize=(10, 4))
for seg in segmentos:
    ax.plot([seg.dxf.start.z, seg.dxf.end.z],
            [seg.dxf.start.y, seg.dxf.end.y],
            color='white', linewidth=1)
ax.set_facecolor('#1e2530')
fig.patch.set_facecolor('#1e2530')
ax.set_aspect('equal')
ax.set_xlabel('z (m) [axial]')
ax.set_ylabel('y (m) [tangencial]')
ax.set_title('HUB_PERFIL isolado — projeção z × y')
saida = os.path.join(pasta_script, "saida_dxf", "hub_perfil_isolado.png")
fig.savefig(saida, dpi=200)
print(f"Salvo: {saida}")
