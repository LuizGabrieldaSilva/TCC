import math
from dataclasses import dataclass, field
from typing import List, Optional

#______________________________________________________________________________________________________________
# Empilhamento radial de perfis 2D (PerfilPa) em geometria 3D de pá, e
# montagem sequencial de TODAS as peças (rotor/estator do compressor,
# bocal/rotor da turbina) em todos os estágios, com acúmulo de z_offset
# axial ao longo da máquina.
#
# Convenção de eixos: z = axial, r = radial, θ = circunferencial.
#
# Construção por peça (loftar_pa): para cada seção radial (raio r_j), o
# perfil 2D local (x ao longo da corda, y perpendicular) é rotacionado
# pelo stagger (ζ) e "desenrolado" no plano axial-tangencial daquele raio:
#   x_axial      = x_local·cos(ζ) - y_local·sin(ζ)
#   desloc_tang  = x_local·sin(ζ) + y_local·cos(ζ)
#   θ            = desloc_tang / r_j          (aproximação de arco pequeno)
#   z            = z_offset_peça + x_axial
# Empilhando as N seções (cada uma no seu raio real), forma-se a pá 3D.
#
# Construção da máquina (loftar_compressor / loftar_turbina): as peças são
# concatenadas na ordem física (rotor→estator→rotor→... ou bocal→rotor→
# bocal→...), cada uma iniciando no z_offset onde a anterior "terminou"
# mais uma folga de convenção (calcular_espacamento_axial).
#
# IMPORTANTE — Espaçamento axial entre peças é FIXO e arbitrário (fator ×
# corda média) —> convenção de VISUALIZAÇÃO, não resultado de engenharia.
# Nenhum módulo deste projeto calcula folga axial real (rotor-estator gap,
# tip clearance axial etc.) — ver nota de escopo já registrada para
# airfoil.py/loft.py. z_final de cada peça também é uma estimativa
# conservadora (usa a corda cheia, não a projeção axial reduzida pelo
# stagger — ver docstring de PecaLoftada).
#______________________________________________________________________________________________________________


@dataclass
class PaLofted:
    """Uma pá 3D completa (uma fileira, N seções empilhadas)."""
    r_secoes: List[float]       = field(default_factory=list)
    camber_cil: List[list]      = field(default_factory=list)  # cada item: lista de (r,θ,z)
    extradorso_cil: List[list]  = field(default_factory=list)
    intradorso_cil: List[list]  = field(default_factory=list)
    camber_cart: List[list]     = field(default_factory=list)  # cada item: lista de (x,y,z)
    extradorso_cart: List[list] = field(default_factory=list)
    intradorso_cart: List[list] = field(default_factory=list)


@dataclass
class PecaLoftada:
    """
    Uma peça completa (rotor OU estator OU bocal) de um estágio, já
    lofted (N seções empilhadas) e posicionada axialmente na máquina.

    z_final é uma estimativa CONSERVADORA (z_offset + corda cheia), não a
    projeção axial real da pá (que seria corda·cos(stagger), sempre menor
    devido ao ângulo de instalação). Suficiente para a convenção de
    espaçamento de visualização adotada neste projeto — não usar para
    dimensionamento mecânico real do envelope axial.
    """
    tipo: str                # 'rotor', 'estator' ou 'bocal'
    estagio: int             # 1-indexado, mesma convenção de gerar_perfis_*
    pa: PaLofted
    z_offset: float          # (m) — início axial desta peça
    z_final: float           # (m) — estimativa conservadora do fim axial
    corda: float             # (m)
    Z_pas: int               # número de pás da fileira
    anel: Optional[list] = None   # pás replicadas (extradorso), se replicar=True


@dataclass
class MaquinaLofted:
    """Conjunto sequencial de peças lofted formando compressor OU turbina completos."""
    pecas: List[PecaLoftada] = field(default_factory=list)
    z_total: float = 0.0     # (m) — comprimento axial total (convenção de visualização)


def cil_para_cart(r: float, theta: float, z: float) -> tuple:
    return (r * math.cos(theta), r * math.sin(theta), z)


def _curva_local_para_cilindrica(x_lista, y_lista, r, zeta_rad, z_offset):
    pontos_cil = []
    cos_z, sin_z = math.cos(zeta_rad), math.sin(zeta_rad)
    
    for x_local, y_local in zip(x_lista, y_lista):
        x_axial = x_local * cos_z - y_local * sin_z
        desloc_tang = x_local * sin_z + y_local * cos_z
        theta = desloc_tang / r
        z = z_offset + x_axial
        pontos_cil.append((r, theta, z))
    return pontos_cil


def calcular_espacamento_axial(corda_media: float, fator: float = 3.0) -> float:
    """
    Espaçamento axial fixo entre peças consecutivas (convenção
    de visualização, não física). fator=3.0 é um valor de projeto usual
    para dar folga visual entre fileiras sem sobreposição.
    """
    return fator * corda_media


def loftar_pa(perfis: List, raios: List[float], z_offset: float = 0.0) -> PaLofted:
    """
    Empilha N PerfilPa (mesma peça, mesmo estágio, ordenados hub->tip) nos
    seus raios reais, formando uma pá 3D completa.

    perfis: lista de objetos PerfilPa (de geometry.airfoil), ordem hub->tip
    raios:  lista de raios (m), mesma ordem e mesmo comprimento de perfis
    z_offset: posição axial de início desta peça (m) — ver
              calcular_espacamento_axial()
    """
    if len(perfis) != len(raios):
        raise ValueError("perfis e raios devem ter o mesmo comprimento (A quantidade de valores das listas diferem).")

    pa = PaLofted(r_secoes=list(raios))

    for perfil, r in zip(perfis, raios):
        zeta_rad = math.radians(perfil.stagger)

        cam_cil = _curva_local_para_cilindrica(
            perfil.x_camber, perfil.y_camber, r, zeta_rad, z_offset)
        ext_cil = _curva_local_para_cilindrica(
            perfil.x_extradorso, perfil.y_extradorso, r, zeta_rad, z_offset)
        intr_cil = _curva_local_para_cilindrica(
            perfil.x_intradorso, perfil.y_intradorso, r, zeta_rad, z_offset)

        pa.camber_cil.append(cam_cil)
        pa.extradorso_cil.append(ext_cil)
        pa.intradorso_cil.append(intr_cil)

        pa.camber_cart.append([cil_para_cart(*p) for p in cam_cil])
        pa.extradorso_cart.append([cil_para_cart(*p) for p in ext_cil])
        pa.intradorso_cart.append([cil_para_cart(*p) for p in intr_cil])

    return pa


def replicar_circular(pa: PaLofted, n_pas: int) -> List[List[list]]:
    """
    Replica a pá única (extradorso, referência mais visível) Z vezes em
    torno do eixo, formando a fileira completa (rotor OU estator/bocal de
    um estágio). Retorna lista de Z pás, cada uma como lista de curvas 3D
    cartesianas (extradorso).

    Nota: replica só o extradorso por padrão (suficiente para conferência
    visual/contagem). Para exportação completa (extradorso+intradorso de
    todas as Z pás), aplique a mesma rotação também a extradorso_cart e
    intradorso_cart — ver comentário no export_dxf.py.
    """
    dtheta = 2 * math.pi / n_pas
    fileira = []
    for k in range(n_pas):
        ang = k * dtheta
        pa_rotacionada = []
        for secao_cart in pa.extradorso_cart:
            secao_rot = [
                (x * math.cos(ang) - y * math.sin(ang),
                 x * math.sin(ang) + y * math.cos(ang),
                 z)
                for (x, y, z) in secao_cart
            ]
            pa_rotacionada.append(secao_rot)
        fileira.append(pa_rotacionada)
    return fileira


def plotar_pa_3d(pa: PaLofted, titulo: str = "Pá 3D") -> None:
    """Visualização rápida (extradorso+intradorso+câmber) de UMA peça via matplotlib 3D."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection='3d')

    for secao in pa.extradorso_cart:
        xs, ys, zs = zip(*secao)
        ax.plot(xs, ys, zs, color='C0', linewidth=0.8)
    for secao in pa.intradorso_cart:
        xs, ys, zs = zip(*secao)
        ax.plot(xs, ys, zs, color='C1', linewidth=0.8)

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_zlabel('z (m)')
    ax.set_title(titulo)
    plt.tight_layout()
    plt.show()


# ══════════════════════════════════════════════════════════════════════════
# GENERALIZAÇÃO — MÁQUINA COMPLETA (todos os estágios, todas as fileiras)
# ══════════════════════════════════════════════════════════════════════════

def loftar_compressor(rad_comp,
                      perfis: dict = None,
                      t_sobre_c: float = 0.10,
                      n_pontos: int = 50,
                      fator_espacamento: float = 3.0,
                      replicar: bool = True) -> MaquinaLofted:
    """
    Percorre TODOS os estágios do compressor e loft-a rotor+estator de
    cada um, na ordem física (rotor1 → estator1 → rotor2 → estator2 → ...),
    acumulando z_offset sequencialmente.

    PARÂMETROS:
        rad_comp    - Objeto RadialCompressor já resolvido (resolver()
                      chamado). Fornece raios por estágio/seção.
        perfis      - Dicionário de PerfilPa (saída de
                      geometry.airfoil4.gerar_perfis_compressor). Se None,
                      é gerado internamente com t_sobre_c e n_pontos dados.
        fator_espacamento - Repassado a calcular_espacamento_axial() para
                      a folga (convenção) entre peças consecutivas.
        replicar    - Se True, replica cada peça em Z pás (via
                      replicar_circular) e guarda em PecaLoftada.anel.
                      Se False, mantém anel=None (inspeção leve — só a pá
                      de referência de cada fileira, sem replicação).

    RETORNA: MaquinaLofted com uma PecaLoftada por (estágio, rotor/estator),
             na ordem em que aparecem axialmente, e z_total = comprimento
             axial total estimado (convenção de visualização).
    """
    if rad_comp.r[0]["hub"] is None:
        raise RuntimeError(
            "O objeto RadialCompressor deve ter resolver() chamado antes "
            "de ser passado a loftar_compressor()."
        )

    if perfis is None:
        from engine.geometry.airfoil4 import gerar_perfis_compressor
        perfis = gerar_perfis_compressor(rad_comp, t_sobre_c=t_sobre_c, n_pontos=n_pontos)

    comp = rad_comp.comp
    maquina = MaquinaLofted()
    z_offset = 0.0

    for i in range(rad_comp.n_est):
        estagio = i + 1
        raios_estagio = [rad_comp.r[i][s] for s in rad_comp.secoes]

        # ---------------------------- ROTOR ----------------------------
        perfis_rotor = [perfis[estagio][s]["rotor"] for s in rad_comp.secoes]
        corda_rotor = comp.corda_rotor[i]
        Z_rotor = comp.Z_rotor[i]

        pa_rotor = loftar_pa(perfis_rotor, raios_estagio, z_offset=z_offset)
        anel_rotor = replicar_circular(pa_rotor, Z_rotor) if replicar else None

        maquina.pecas.append(PecaLoftada(
            tipo="rotor", estagio=estagio, pa=pa_rotor,
            z_offset=z_offset, z_final=z_offset + corda_rotor,
            corda=corda_rotor, Z_pas=Z_rotor, anel=anel_rotor,
        ))
        z_offset += corda_rotor + calcular_espacamento_axial(corda_rotor, fator=fator_espacamento)

        # --------------------------- ESTATOR ---------------------------
        perfis_estator = [perfis[estagio][s]["estator"] for s in rad_comp.secoes]
        corda_estator = comp.corda_estator[i]
        Z_estator = comp.Z_estator[i]

        pa_estator = loftar_pa(perfis_estator, raios_estagio, z_offset=z_offset)
        anel_estator = replicar_circular(pa_estator, Z_estator) if replicar else None

        maquina.pecas.append(PecaLoftada(
            tipo="estator", estagio=estagio, pa=pa_estator,
            z_offset=z_offset, z_final=z_offset + corda_estator,
            corda=corda_estator, Z_pas=Z_estator, anel=anel_estator,
        ))
        z_offset += corda_estator + calcular_espacamento_axial(corda_estator, fator=fator_espacamento)

    maquina.z_total = z_offset
    return maquina


def loftar_turbina(rad_turb,
                   perfis: dict = None,
                   t_sobre_c: float = 0.10,
                   n_pontos: int = 50,
                   fator_espacamento: float = 3.0,
                   replicar: bool = True) -> MaquinaLofted:
    """
    Equivalente a loftar_compressor(), para a turbina: percorre todos os
    estágios e loft-a bocal+rotor de cada um, na ordem física
    (bocal1 → rotor1 → bocal2 → rotor2 → ...), acumulando z_offset.

    Ver docstring de loftar_compressor() para detalhes dos parâmetros —
    idênticos em espírito, trocando rotor/estator por bocal/rotor.
    """
    if rad_turb.r[0]["hub"] is None:
        raise RuntimeError(
            "O objeto RadialTurbina deve ter resolver() chamado antes "
            "de ser passado a loftar_turbina()."
        )

    if perfis is None:
        from engine.geometry.airfoil4 import gerar_perfis_turbina
        perfis = gerar_perfis_turbina(rad_turb, t_sobre_c=t_sobre_c, n_pontos=n_pontos)

    turb = rad_turb.turb
    maquina = MaquinaLofted()
    z_offset = 0.0

    for i in range(rad_turb.n_est):
        estagio = i + 1
        raios_estagio = [rad_turb.r[i][s] for s in rad_turb.secoes]

        # ---------------------------- BOCAL ----------------------------
        perfis_bocal = [perfis[estagio][s]["bocal"] for s in rad_turb.secoes]
        corda_bocal = turb.corda_bocal[i]
        Z_bocal = turb.Z_bocal[i]

        pa_bocal = loftar_pa(perfis_bocal, raios_estagio, z_offset=z_offset)
        anel_bocal = replicar_circular(pa_bocal, Z_bocal) if replicar else None

        maquina.pecas.append(PecaLoftada(
            tipo="bocal", estagio=estagio, pa=pa_bocal,
            z_offset=z_offset, z_final=z_offset + corda_bocal,
            corda=corda_bocal, Z_pas=Z_bocal, anel=anel_bocal,
        ))
        z_offset += corda_bocal + calcular_espacamento_axial(corda_bocal, fator=fator_espacamento)

        # ---------------------------- ROTOR ----------------------------
        perfis_rotor = [perfis[estagio][s]["rotor"] for s in rad_turb.secoes]
        corda_rotor = turb.corda_rotor[i]
        Z_rotor = turb.Z_rotor[i]

        pa_rotor = loftar_pa(perfis_rotor, raios_estagio, z_offset=z_offset)
        anel_rotor = replicar_circular(pa_rotor, Z_rotor) if replicar else None

        maquina.pecas.append(PecaLoftada(
            tipo="rotor", estagio=estagio, pa=pa_rotor,
            z_offset=z_offset, z_final=z_offset + corda_rotor,
            corda=corda_rotor, Z_pas=Z_rotor, anel=anel_rotor,
        ))
        z_offset += corda_rotor + calcular_espacamento_axial(corda_rotor, fator=fator_espacamento)

    maquina.z_total = z_offset
    return maquina


# ══════════════════════════════════════════════════════════════════════════
# EXIBIÇÃO — RESUMO TABULAR E PLOT DA MÁQUINA COMPLETA
# ══════════════════════════════════════════════════════════════════════════

def resumo_loft(maquina: MaquinaLofted, titulo: str = "Resumo do Loft") -> None:
    """Imprime tabela de conferência: uma linha por peça, na ordem axial."""
    def linha():
        print("─" * 92)

    linha()
    print(f"  {titulo}")
    linha()
    print(f"  {'Estágio':<9}{'Peça':<10}{'z_offset(cm)':>14}{'z_final(cm)':>13}"
          f"{'corda(cm)':>11}{'Z pás':>8}{'r_hub(cm)':>12}{'r_tip(cm)':>12}")
    print("  " + "─" * 88)
    for p in maquina.pecas:
        r_min = min(p.pa.r_secoes) * 100
        r_max = max(p.pa.r_secoes) * 100
        print(f"  {p.estagio:<9}{p.tipo:<10}{p.z_offset*100:>14.3f}{p.z_final*100:>13.3f}"
              f"{p.corda*100:>11.3f}{p.Z_pas:>8}{r_min:>12.3f}{r_max:>12.3f}")
    linha()
    print(f"  Comprimento axial total (convenção de visualização): {maquina.z_total*100:.3f} cm")
    print(f"  Total de peças (fileiras): {len(maquina.pecas)}")
    linha()


def plotar_maquina_3d(maquina: MaquinaLofted,
                       titulo: str = "Máquina 3D",
                       cores_por_tipo: dict = None) -> None:
    """
    Plota TODAS as peças da máquina em um único gráfico 3D.

    Se a peça tiver anel (replicar=True no loft), plota a fileira
    completa (Z pás, só extradorso — ver nota em replicar_circular()).
    Caso contrário, plota extradorso+intradorso da pá única de referência
    (modo leve, útil para conferência rápida de estagiamento e twist sem
    o custo de renderizar dezenas de pás por fileira).
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa

    fig = plt.figure(figsize=(11, 9))
    ax = fig.add_subplot(111, projection='3d')

    cores = cores_por_tipo or {"rotor": "C0", "estator": "C1", "bocal": "C2"}

    for peca in maquina.pecas:
        cor = cores.get(peca.tipo, "gray")

        if peca.anel is not None:
            for pa_rotacionada in peca.anel:
                for secao in pa_rotacionada:
                    xs, ys, zs = zip(*secao)
                    ax.plot(xs, ys, zs, color=cor, linewidth=0.4)
        else:
            for secao in peca.pa.extradorso_cart:
                xs, ys, zs = zip(*secao)
                ax.plot(xs, ys, zs, color=cor, linewidth=0.7)
            for secao in peca.pa.intradorso_cart:
                xs, ys, zs = zip(*secao)
                ax.plot(xs, ys, zs, color=cor, linewidth=0.7, linestyle='--')

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_zlabel('z (m) [axial]')
    ax.set_title(titulo)
    plt.tight_layout()
    plt.show()


#_______________________________________________________________________________
if __name__ == "__main__":
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()
    from engine.aero.radial_turbina_3_main import RadialTurbina

    # ══════════════════════════════════════════════════════════════════
    # CASO ÚNICO (mantido para conferência pontual — rotor, estágio 1,
    # compressor, 7 seções)
    # ══════════════════════════════════════════════════════════════════
    from engine.geometry.airfoil4 import gerar_perfis_compressor

    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()
    perfis_compressor = gerar_perfis_compressor(rad_comp, t_sobre_c=0.10)

    perfis_rotor_e1 = [perfis_compressor[1][s]["rotor"] for s in rad_comp.secoes]
    raios_e1 = [rad_comp.r[0][s] for s in rad_comp.secoes]

    pa_e1_rotor = loftar_pa(perfis_rotor_e1, raios_e1, z_offset=0.0)
    plotar_pa_3d(pa_e1_rotor, titulo="Rotor — Estágio 1 (7 seções)")

    Z_rotor_e1 = rad_comp.comp.Z_rotor[0]
    anel = replicar_circular(pa_e1_rotor, Z_rotor_e1)
    print(f"Rotor estágio 1: {len(anel)} pás replicadas (Z={Z_rotor_e1})")

    # ══════════════════════════════════════════════════════════════════
    # MÁQUINA COMPLETA — COMPRESSOR (rotor+estator por estágio calculado)
    # ══════════════════════════════════════════════════════════════════
    maquina_comp = loftar_compressor(rad_comp, perfis=perfis_compressor, replicar=True)
    resumo_loft(maquina_comp, titulo=f"COMPRESSOR — {compr1.n_estagios} estágios")
    plotar_maquina_3d(maquina_comp, titulo=f"Compressor completo ({compr1.n_estagios} estágios)")

    # ══════════════════════════════════════════════════════════════════
    # MÁQUINA COMPLETA — TURBINA (bocal+rotor por estágio calculado)
    # ══════════════════════════════════════════════════════════════════
    rad_turb = RadialTurbina(turb=turb1, n_secoes=7)
    rad_turb.resolver()

    maquina_turb = loftar_turbina(rad_turb, replicar=True)
    resumo_loft(maquina_turb, titulo=f"TURBINA — {turb1.n_estagios} estágios")
    plotar_maquina_3d(maquina_turb, titulo=f"Turbina completa ({turb1.n_estagios} estágios)")
    
