#______________________________________________________________________________________________________________
# Geração de perfil de pá 2D via câmber circular + Regra de Carter + 
# espessura parabólica simétrica.
#
# Decisões de projeto (fechadas em discussão prévia):
#   - Incidência i = 0            → β₁' = β₁ (ângulo metálico = ângulo de escoamento na entrada)
#   - Desvio via Regra de Carter  → β₂' = β₂ - δ, com δ = m·θ·√(s/c)
#   - Câmber circular puro        → a/c = 0,5 (máximo câmber no meio da corda)
#   - Carter fechado algebricamente no câmber METÁLICO final
#   - Espessura parabólica simétrica, parametrizada só por t/c
#
# Referência: Saravanamuttoo, Cohen & Rogers — Gas Turbine Theory, 5ª ed.
#   Cap. 5, seção "Compressor blade cascade tunnel..." (cascata, notação de
#   ângulos, Fig. 5.23) e seção "Construction of blade shape" (Fig. 5.27,
#   construção geométrica do perfil via linha de câmber + perfil base).
#   Eq. (5.29): regra de Carter para o ângulo de desvio δ.
#   Dixon & Hall, 7ª ed., Eqs. (3.34–3.35), exemplo 3.1, pp. 86–87:
#   θ_final = (β₁_metal - β₂_flow)/(1 - m·sqrt(s/c)).
#
# ══════════════════════════════════════════════════════════════════════════
# NOTA SOBRE ESCOPO:
#   Este módulo trabalha em um referencial LOCAL da corda (x de 0 a c,
#   y perpendicular). A rotação para o referencial global da máquina
#   usando o stagger METÁLICO calculado aqui fica a cargo do loft 3D.
#   Os gamma dos módulos radiais são médias de ângulos de ESCOAMENTO,
#   não substituem o stagger corrigido por Carter. Ângulos dos perfis
#   seguem o eixo tangencial global; no rotor do compressor, são -β_modelo.
# ══════════════════════════════════════════════════════════════════════════
#______________________________________________________________________________________________________________

import math
from dataclasses import dataclass, field
from typing import List
from engine import design_criteria as dc
from engine.aero.constraints import checar_camber_excessivo

# Seções radiais — mesma convenção usada em radial_compressor_2.py e
# radial_turbina_2.py (hub/mid/tip), repetida aqui para que este módulo
# não dependa de importar os módulos radiais só por essa constante.

# SECOES = ["hub", "mid", "tip"] Remanescente de versões anteriores

# ══════════════════════════════════════════════════════════════════════════
# CONTAINER DE RESULTADO
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class PerfilPa:
    """Resultado completo da geração de um perfil de pá 2D."""
    # Entradas
    beta1_graus: float
    beta2_graus: float
    sigma: float
    corda: float          # (m)
    t_sobre_c: float

    # Grandezas derivadas — ângulos metálicos e câmber
    beta1_linha: float = None     # ângulo metálico de entrada (°) — igual a beta1 (i=0)
    theta_raw: float = None       # câmber "cru", antes de Carter (°)
    m_carter: float = None        # coeficiente m da regra de Carter
    s_sobre_c: float = None       # razão pitch/chord (= 1/sigma)
    delta: float = None           # desvio de Carter (°)
    beta2_linha: float = None     # ângulo metálico de saída, corrigido (°)
    theta_final: float = None     # câmber final, usado no arco (°)
    stagger: float = None         # ângulo de stagger ζ (°)

    # Geometria do arco de câmber
    sagita: float = None          # h (m)
    raio_arco: float = None       # R (m)
    centro_arco: tuple = None     # (xc, yc) (m)

    # Coordenadas (listas de floats, mesmo comprimento)
    x_camber: List[float] = field(default_factory=list)
    y_camber: List[float] = field(default_factory=list)
    x_extradorso: List[float] = field(default_factory=list)
    y_extradorso: List[float] = field(default_factory=list)
    x_intradorso: List[float] = field(default_factory=list)
    y_intradorso: List[float] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES — PURAS
# ══════════════════════════════════════════════════════════════════════════

def _coeficiente_m_carter(beta2_graus: float) -> float:
    """
    Coeficiente m da regra de Carter (Eq. 5.29, Saravanamuttoo), na forma
    simplificada para câmber circular puro (a/c = 0,5):

        m = 0,23·(2a/c)² + 0,1·(β₂/50) , com a/c=0,5 → (2a/c)²=1

        m = 0,23 + 0,002·β₂    (β₂ em graus, valor absoluto)
    """
    return 0.23 + 0.002 * abs(beta2_graus)


def _espessura_parabolica(x: float, c: float, t_sobre_c: float) -> float:
    """
    Distribuição de espessura parabólica simétrica:
        t(x) = t_max · 4·(x/c)·(1 - x/c)
    Zero nos bordos (x=0 e x=c), máxima em x=c/2, igual a t_max = (t/c)·c.
    """
    t_max = t_sobre_c * c
    xi = x / c
    return t_max * 4 * xi * (1 - xi)


def _ponto_camber_e_derivada(x: float, c: float, h: float, R: float,
                             y_centro: float) -> tuple:
    """
    Retorna (y_camber, dy/dx) no ponto x, para um arco circular de corda c,
    sagita h e raio R (já calculados), centrado em (c/2, y_centro).

    Equação do arco:  y = y_centro + sign(h)·sqrt(R² - (x - c/2)²)
    Derivada:          dy/dx = -sign(h)·(x - c/2) / sqrt(R² - (x - c/2)²)
    """
    if abs(h) < 1e-9:
        # Câmber nulo — pá reta (caso degenerado, não deve ocorrer na prática)
        return 0.0, 0.0

    sinal_h = 1.0 if h >= 0 else -1.0
    u = x - c / 2
    raiz = math.sqrt(max(R**2 - u**2, 0.0))  # max() evita erro numérico de arredondamento

    y = y_centro + sinal_h * raiz
    if raiz < 1e-9:
        dydx = 0.0  # ponto próximo ao vértice do arco perpendicular à corda
    else:
        dydx = -sinal_h * u / raiz
    return y, dydx


# ══════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def gerar_perfil_pa(beta1_graus: float,
                    beta2_graus: float,
                    sigma: float,
                    corda: float,
                    t_sobre_c: float = 0.10,
                    n_pontos: int = 50,
                    aplicar_carter: bool = True,
                    limite_camber: float = dc.CAMBER_COMP_GRAUS,
                    estagio: int = None,
                    secao: str = None,
                    fileira: str = None) -> PerfilPa:
    """
    Gera um perfil de pá 2D completo a partir do triângulo de velocidades
    local (β₁, β₂), da solidez (σ) e da corda (c) — todos já calculados
    pelos módulos meanline/radial existentes.

    PARÂMETROS:
        beta1_graus  - Ângulo de escoamento de entrada (°), tangencial global
        
        beta2_graus  - Ângulo de escoamento de saída (°), mesma convenção
        
        sigma        - Solidez da fileira (rotor ou estator/bocal)
        
        corda        - Corda da pá (m)
        
        t_sobre_c    - Razão espessura máxima/corda (adimensional)
                       Faixa típica: 0.08-0.12 (Saravanamuttoo usa 0.10
                       no perfil-base T6, Fig. 5.11)
                       
        aplicar_carter - Se True, aplica a Regra de Carter (δ = m·θ·√(s/c))
                       para corrigir o ângulo metálico de saída. Válida
                       para cascatas de COMPRESSOR (escoamento em difusão,
                       Cap. 5). Se False, assume δ=0 (β₂'=β₂), apropriado
                       para cascatas de TURBINA (escoamento acelerado),
                       cuja regra de desvio própria (cos⁻¹(o/s), Cap. 7,
                       Fig. 7.13) não foi implementada neste trabalho —
                       ver nota de escopo abaixo.
                       
        limite_camber - Limite de aviso para θ_final (°), acima do qual um
                       único arco circular é considerado geometricamente
                       pouco representativo (ver checar_camber_excessivo).
                       O projeto adota 60° no compressor e 90° na turbina.
                       São limiares de triagem da aproximação geométrica,
                       não limites universais de separação ou aprovação
                       aerodinâmica/estrutural das pás.
                       
        n_pontos     - Número de pontos ao longo da corda (resolução)
        
        estagio, secao, fileira - Metadados apenas para identificação em
                                  avisos (não afetam o cálculo)

    RETORNA: objeto PerfilPa com todas as grandezas derivadas e as
             coordenadas (x, y) da linha de câmber, extradorso e intradorso.

    SEQUÊNCIA DE CÁLCULO:
      1. β₁' = β₁                                    (incidência zero)
      2. θ_raw = β₁' - β₂
      3. m (Carter, a/c=0,5) e s/c = 1/σ
      4. θ_final = θ_raw / (1 - m·√(s/c)); δ = m·θ_final·√(s/c)
      5. β₂' = β₂ - δ
      6. θ_final = β₁' - β₂'
      7. ζ (stagger) = β₁' - θ_final/2
      8. Sagita h e raio R do arco de câmber
      9. Linha de câmber (x, y) via equação do arco
     10. Espessura parabólica t(x)
     11. Extradorso/intradorso via offset perpendicular à linha de câmber
     12. Verificação de câmber excessivo (aero/constraints.py)
    """
    if not all(math.isfinite(v) for v in (beta1_graus, beta2_graus, sigma, corda, t_sobre_c)):
        raise ValueError("Ângulos, solidez, corda e espessura devem ser finitos.")
    if sigma <= 0 or corda <= 0 or t_sobre_c <= 0:
        raise ValueError("Solidez, corda e espessura relativa devem ser positivas.")
    if isinstance(n_pontos, bool) or not isinstance(n_pontos, int) or n_pontos < 2:
        raise ValueError("n_pontos deve ser inteiro e >= 2.")
    if t_sobre_c > dc.ESPESSURA_RELATIVA_AVISO:
        print(f"AVISO: t/c = {t_sobre_c} > {dc.ESPESSURA_RELATIVA_AVISO:g} — espessura acima do limiar de aviso adotado para a aproximação geométrica; não é um limite universal de projeto.")

    # ----------------------------------------------------------------------
    # 1-2. INCIDÊNCIA ZERO E CÂMBER CRU
    # ----------------------------------------------------------------------
    beta1_linha = beta1_graus
    theta_raw = beta1_linha - beta2_graus

    # ----------------------------------------------------------------------
    # 3-6. DESVIO DE SAÍDA — Regra de Carter (compressor) ou δ=0 (turbina)
    #
    # A Regra de Carter (m = 0,23+0,002·|β₂|; δ = m·θ_final·√(s/c)) foi derivada
    # para cascatas de COMPRESSOR (escoamento em difusão, Saravanamuttoo
    # Cap. 5). Testada em lote neste projeto, ela produz θ_final > 90° em
    # TODAS as seções da turbina (18/18 casos), pois amplifica em vez de
    # corrigir o ângulo quando aplicada a deflexões grandes em escoamento
    # acelerado — fora do regime em que foi calibrada.
    #
    # A regra de desvio própria para turbinas (cos⁻¹(o/s), Cap. 7, Fig. 7.13,
    # com interpolação por Mach e dependência de um parâmetro geométrico de
    # bordo de fuga ainda não modelado neste projeto) NÃO foi implementada, 
    # dado a discussão de escopo. Para a turbina, assume-se aqui δ=0
    # (β₂'=β₂), aproximação sustentada pelo próprio livro, que indica que a
    # correlação de desvio de turbina converge para valores pequenos à
    # medida que M→1 — faixa em que boa parte das seções deste projeto
    # efetivamente opera (M2 e M3R predominantemente altos subsônicos).
    # ----------------------------------------------------------------------
    if aplicar_carter:
        m = _coeficiente_m_carter(beta2_graus)
        s_sobre_c = 1.0 / sigma
        fator_carter = m * math.sqrt(s_sobre_c)
        denominador = 1.0 - fator_carter
        if denominador <= 1e-12:
            raise ValueError(
                f"Carter sem solução admissível: 1 - m·sqrt(s/c) = {denominador:.6g}. "
                "Revise a solidez e a aplicabilidade da correlação."
            )
        # A relação usa o câmber metálico, não a deflexão de escoamento.
        # A forma assinada também preserva o espelhamento do rotor.
        delta = fator_carter * theta_raw / denominador
    else:
        m = 0.0
        s_sobre_c = 1.0 / sigma   # mantido no resultado por completude/rastreabilidade
        delta = 0.0

    beta2_linha = beta2_graus - delta
    theta_final = beta1_linha - beta2_linha
    if not math.isfinite(theta_final) or abs(theta_final) >= 180.0:
        raise ValueError("Câmber deve ter módulo < 180° para este arco circular em função de x.")

    # ----------------------------------------------------------------------
    # 7. STAGGER
    # ----------------------------------------------------------------------
    stagger = beta1_linha - theta_final / 2

    # ----------------------------------------------------------------------
    # 8. GEOMETRIA DO ARCO — SAGITA E RAIO
    # h = (c/2)·tan(θ_final/4)
    # R = [(c/2)² + h²] / (2|h|)
    # ----------------------------------------------------------------------
    theta_final_rad = math.radians(theta_final)
    h = (corda / 2) * math.tan(theta_final_rad / 4)

    if abs(h) < 1e-9:
        R = float('inf')
        y_centro = 0.0
    else:
        R = ((corda / 2) ** 2 + h ** 2) / (2 * abs(h))
        sinal_h = 1.0 if h >= 0 else -1.0
        y_centro = h - R * sinal_h

    centro_arco = (corda / 2, y_centro)

    # ----------------------------------------------------------------------
    # 9-11. COORDENADAS — LINHA DE CÂMBER, EXTRADORSO, INTRADORSO
    # ----------------------------------------------------------------------
    x_camber, y_camber = [], []
    x_extra, y_extra = [], []
    x_intra, y_intra = [], []

    for j in range(n_pontos + 1):
        x = corda * j / n_pontos

        y_c, dydx = _ponto_camber_e_derivada(x, corda, h, R, y_centro)

        t_local = _espessura_parabolica(x, corda, t_sobre_c)

        # Vetor normal unitário à linha de câmber: (-dy/dx, 1) normalizado
        norma = math.sqrt(1 + dydx ** 2)
        nx, ny = -dydx / norma, 1.0 / norma

        # Dois candidatos de superfície (offset ±t/2 na direção normal)
        xa, ya = x + (t_local / 2) * nx, y_c + (t_local / 2) * ny
        xb, yb = x - (t_local / 2) * nx, y_c - (t_local / 2) * ny

        # Classificação robusta: extradorso = lado mais distante do centro
        # do arco (convexo); intradorso = lado mais próximo (côncavo).
        if math.isinf(R):
            # Pá reta (câmber nulo) — não há "lado convexo"; usa convenção y>0
            extra, intra = (xa, ya), (xb, yb)
        else:
            dist_a = math.hypot(xa - centro_arco[0], ya - centro_arco[1])
            dist_b = math.hypot(xb - centro_arco[0], yb - centro_arco[1])
            extra, intra = ((xa, ya), (xb, yb)) if dist_a > dist_b else ((xb, yb), (xa, ya))

        x_camber.append(x); y_camber.append(y_c)
        x_extra.append(extra[0]); y_extra.append(extra[1])
        x_intra.append(intra[0]); y_intra.append(intra[1])
        
        

    # ----------------------------------------------------------------------
    # 12. VERIFICAÇÃO DE VIABILIDADE GEOMÉTRICA
    # ----------------------------------------------------------------------
    aviso = checar_camber_excessivo(
        abs(theta_final), estagio=estagio, limite = limite_camber, secao=secao, fileira=fileira,
    )
    if aviso:
        print(f"  ⚠  {aviso}")

    return PerfilPa(
        beta1_graus=beta1_graus, 
        beta2_graus=beta2_graus,
        sigma=sigma, 
        corda=corda, 
        t_sobre_c=t_sobre_c,
        beta1_linha=beta1_linha, 
        theta_raw=theta_raw, 
        m_carter=m,
        s_sobre_c=s_sobre_c, 
        delta=delta, 
        beta2_linha=beta2_linha,
        theta_final=theta_final, 
        stagger=stagger,
        sagita=h, 
        raio_arco=R, 
        centro_arco=centro_arco,
        x_camber=x_camber, 
        y_camber=y_camber,
        x_extradorso=x_extra, 
        y_extradorso=y_extra,
        x_intradorso=x_intra, 
        y_intradorso=y_intra,
    )


# ══════════════════════════════════════════════════════════════════════════
# EXIBIÇÃO E PLOTAGEM (opcional — requer matplotlib)
# ══════════════════════════════════════════════════════════════════════════

def mostrar_resultado(perfil: PerfilPa) -> None:
    """Imprime as grandezas derivadas de forma organizada."""
    def linha():
        print("─" * 60)

    linha()
    print("  PERFIL DE PÁ — RESULTADOS")
    linha()
    print(f"  β₁ (escoamento)      = {perfil.beta1_graus:7.3f}°")
    print(f"  β₁' (metal, entrada) = {perfil.beta1_linha:7.3f}°   (i = 0)")
    print(f"  β₂ (escoamento)      = {perfil.beta2_graus:7.3f}°")
    print(f"  θ_raw                = {perfil.theta_raw:7.3f}°")
    linha()
    print(f"  σ (solidez)          = {perfil.sigma:7.4f}")
    print(f"  s/c                  = {perfil.s_sobre_c:7.4f}")
    print(f"  m (Carter)           = {perfil.m_carter:7.4f}")
    print(f"  δ (desvio)           = {perfil.delta:7.3f}°")
    print(f"  β₂' (metal, saída)   = {perfil.beta2_linha:7.3f}°")
    print(f"  θ_final              = {perfil.theta_final:7.3f}°")
    print(f"  ζ (stagger)          = {perfil.stagger:7.3f}°")
    linha()
    print(f"  corda (c)            = {perfil.corda*100:7.3f} cm")
    print(f"  t/c                  = {perfil.t_sobre_c:7.3f}")
    print(f"  sagita (h)           = {perfil.sagita*100:7.4f} cm")
    print(f"  raio do arco (R)     = {perfil.raio_arco*100:7.3f} cm")
    linha()


def plotar_perfil(perfil: PerfilPa, titulo: str = "Perfil de pá") -> None:
    """Plota o perfil (câmber + extradorso + intradorso). Requer matplotlib."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(perfil.x_camber, perfil.y_camber, '--', color='gray', label='Linha de câmber')
    ax.plot(perfil.x_extradorso, perfil.y_extradorso, '-', color='C0', label='Extradorso')
    ax.plot(perfil.x_intradorso, perfil.y_intradorso, '-', color='C1', label='Intradorso')
    ax.set_aspect('equal')
    ax.set_xlabel('x (m) — direção da corda')
    ax.set_ylabel('y (m)')
    ax.set_title(titulo)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()

# ___________________________________________________________________________________
# ══════════════════════════════════════════════════════════════════════════
# GERAÇÃO EM LOTE — todas as seções/estágios/fileiras
# ══════════════════════════════════════════════════════════════════════════

def gerar_perfis_compressor(radial_comp, t_sobre_c: float = 0.10,
                             n_pontos: int = 50) -> dict:
    """
    Gera perfis para TODAS as combinações de estágio × seção × fileira do
    compressor, a partir de um objeto RadialCompressor já resolvido.

    Fileiras do compressor: rotor (β₁, β₂) e estator (α₁, α₂ — usados no
    lugar de β porque o estator trabalha no referencial absoluto).

    RETORNA: dicionário aninhado
        resultado[estagio][secao]['rotor']   -> PerfilPa
        resultado[estagio][secao]['estator'] -> PerfilPa
    """
    if radial_comp.r[0]["hub"] is None:
        raise RuntimeError(
            "O objeto RadialCompressor deve ter resolver() chamado antes "
            "de gerar perfis em lote."
        )

    resultado = {}
    n_est = radial_comp.n_est

    for i in range(n_est):
        resultado[i + 1] = {}
        corda_rotor_i   = radial_comp.comp.corda_rotor[i]
        corda_estator_i = radial_comp.comp.corda_estator[i]

        for s in radial_comp.secoes:
            resultado[i + 1][s] = {}

            # β do compressor tem sinal oposto ao ângulo geométrico de W.
            # O loft usa tangencial positivo no sentido de U: espelhar aqui,
            # inclusive o câmber/desvio assinados, preserva incidência zero.
            resultado[i + 1][s]["rotor"] = gerar_perfil_pa(
                beta1_graus=-radial_comp.beta1[i][s],
                beta2_graus=-radial_comp.beta2[i][s],
                sigma=radial_comp.sigma_rotor_local[i][s],
                corda=corda_rotor_i,
                t_sobre_c=t_sobre_c,
                n_pontos=n_pontos,
                estagio=i + 1, secao=s, fileira="rotor",
            )

            # Estator — ângulos absolutos α₁, α₂ (estágio repetitivo: α₃=α₁)
            resultado[i + 1][s]["estator"] = gerar_perfil_pa(
                beta1_graus=radial_comp.alpha2[i][s],   # entrada do estator = saída do rotor
                beta2_graus=radial_comp.alpha1[i][s],   # saída do estator = entrada do próx. estágio
                sigma=radial_comp.sigma_estator_local[i][s],
                corda=corda_estator_i,
                t_sobre_c=t_sobre_c,
                n_pontos=n_pontos,
                estagio=i + 1, secao=s, fileira="estator",
            )

    return resultado


def gerar_perfis_turbina(radial_turb, t_sobre_c: float = 0.10,
                          n_pontos: int = 50) -> dict:
    """
    Gera perfis para TODAS as combinações de estágio × seção × fileira da
    turbina, a partir de um objeto RadialTurbina já resolvido.

    Fileiras da turbina: bocal (α₁, α₂ — nozzle, referencial absoluto) e
    rotor (β₂, β₃ — referencial relativo).

    RETORNA: dicionário aninhado
        resultado[estagio][secao]['bocal'] -> PerfilPa
        resultado[estagio][secao]['rotor'] -> PerfilPa
    """
    if radial_turb.r[0]["hub"] is None:
        raise RuntimeError(
            "O objeto RadialTurbina deve ter resolver() chamado antes "
            "de gerar perfis em lote."
        )

    resultado = {}
    n_est = radial_turb.n_est

    for i in range(n_est):
        resultado[i + 1] = {}
        corda_bocal_i = radial_turb.turb.corda_bocal[i]
        corda_rotor_i = radial_turb.turb.corda_rotor[i]

        for s in radial_turb.secoes:
            resultado[i + 1][s] = {}

            # Bocal — α₁ axial só no primeiro; depois herda swirl anterior.
            resultado[i + 1][s]["bocal"] = gerar_perfil_pa(
                beta1_graus=radial_turb.alpha1[i][s],
                beta2_graus=radial_turb.alpha2[i][s],
                sigma=radial_turb.sigma_bocal_local[i][s],
                corda=corda_bocal_i,
                t_sobre_c=t_sobre_c,
                n_pontos=n_pontos,
                aplicar_carter=False,   # ← regra de Carter não válida p/ turbina — ver nota de escopo
                limite_camber= dc.CAMBER_TURB_GRAUS,    # ← Turbina tolera um cambêr maior que o compressor (checar docstring)
                estagio=i + 1, secao=s, fileira="bocal",
            )

            # Rotor — ângulos relativos β₂ (entrada), β₃ (saída)
            resultado[i + 1][s]["rotor"] = gerar_perfil_pa(
                beta1_graus=radial_turb.beta2[i][s],
                beta2_graus=radial_turb.beta3[i][s],
                sigma=radial_turb.sigma_rotor_local[i][s],
                corda=corda_rotor_i,
                t_sobre_c=t_sobre_c,
                n_pontos=n_pontos,
                aplicar_carter=False,
                limite_camber= dc.CAMBER_TURB_GRAUS,
                estagio=i + 1, secao=s, fileira="rotor",
            )

    return resultado

#_______________________________________________________________________________
if __name__ == "__main__":

    # ══════════════════════════════════════════════════════════════════════
    # CASO DE TESTE ÚNICO — Rotor, Estágio 1, seção MID, do compressor de
    # referência (N=14000, HTR=0.75, φ=0.50, ψ=0.35, DF_alvo=0.45).
    #
    # Valores conferíveis à mão (ver cálculo no corpo da conversa):
    #   β₁ = 54.90°, β₂ = 35.85°, σ_rotor = 1.2732, corda = 3.222 cm
    #   θ_raw ≈ 19.05°, m ≈ 0.3017, s/c ≈ 0.7854, δ ≈ 5.10°
    #   β₂' ≈ 30.75°, θ_final ≈ 24.15°, ζ ≈ 42.83°
    # ══════════════════════════════════════════════════════════════════════

    perfil_teste = gerar_perfil_pa(
        beta1_graus = 54.90,
        beta2_graus = 35.85,
        sigma       = 1.2732,
        corda       = 0.03222,   # 3.222 cm em metros
        t_sobre_c   = 0.10,
        n_pontos    = 50,
        estagio=1, secao="mid", fileira="rotor",
    )

    mostrar_resultado(perfil_teste)

    # Descomente para visualizar (requer matplotlib instalado):
    plotar_perfil(perfil_teste, titulo="Rotor — Estágio 1 [mid]")
    
    
    # ____________________________________________________________________________________________________
    # ══════════════════════════════════════════════════════════════════════
    # GERAÇÃO EM LOTE — casos de referência (compressor + turbina)
    # ══════════════════════════════════════════════════════════════════════
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor 
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()
    from engine.aero.radial_turbina_3_main import RadialTurbina          
    
    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()
    perfis_compressor = gerar_perfis_compressor(rad_comp, t_sobre_c=0.10)

    rad_turb = RadialTurbina(turb=turb1, n_secoes=7)
    rad_turb.resolver()
    perfis_turbina = gerar_perfis_turbina(rad_turb, t_sobre_c=0.10)

    # ------------------------------------------------------------------
    # Checagem rápida: quantos perfis foram gerados, e algum theta_final
    # anormal (avisos já impressos automaticamente por checar_camber_excessivo)
    # ------------------------------------------------------------------
    n_perfis_comp = sum(
        1 for est in perfis_compressor.values()
          for sec in est.values()
          for _ in sec.values()
    )
    n_perfis_turb = sum(
        1 for est in perfis_turbina.values()
          for sec in est.values()
          for _ in sec.values()
    )
    print(f"\nPerfis gerados — Compressor: {n_perfis_comp} "
          f"({rad_comp.n_est} estágios)")
    print(f"Perfis gerados — Turbina:    {n_perfis_turb} "
          f"({rad_turb.n_est} estágios)")

    # Exemplo de acesso a um perfil específico do lote:
    # perfis_compressor[1]["hub"]["rotor"].theta_final
    # perfis_turbina[3]["tip"]["bocal"].beta2_linha
