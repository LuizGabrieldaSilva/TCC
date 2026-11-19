from engine.aero.constraints import checar_secao_compressor_radial
from engine.input_validation import inteiro
from engine.aero.annulus_geometry import referencia_radial
from engine.aero.cascade_geometry import solidez_local
import math

#______________________________________________________________________________________________________________
# Distribuição Radial do Compressor Axial — Lei Free Vortex.
# Recebe um objeto CompressorMeanline já resolvido e calcula, para cada
# estágio, as grandezas aerodinâmicas em N seções radiais igualmente
# espaçadas entre hub (cubo) e tip (ponta).
#
# ══════════════════════════════════════════════════════════════════════════
# A função gerar_secoes(n_secoes) gera N rótulos e frações radiais
# igualmente espaçadas entre hub (fração=0) e tip (fração=1).
# Para n_secoes=3, reproduz EXATAMENTE ["hub","mid","tip"] —
# compatibilidade retroativa total com todos os casos de
# referência já validados neste projeto.
#
# Motivação: mais seções radiais produzem uma malha mais fina
# para a geometria de pá (geometry/airfoil.py e, posteriormente,
# geometry/loft.py), suavizando a aparência da pá lofted sem
# exigir interpolação spline (que, com poucos pontos de
# controle, arriscaria oscilação não-física de Runge).
#
# A lógica de cálculo dentro do loop radial (free vortex,
# triângulos, Mach, DF, grau de reação, stagger, avisos) NÃO
# muda — já trabalhava genericamente com "o raio r desta seção
# s", independente de quantas seções existem.
# ══════════════════════════════════════════════════════════════════════════
#
# MUDANÇA ESTRUTURAL ANTERIOR (acompanha a refatoração de Compressor_Meanline_main.py):
#
#   ANTES:  σ era um escalar único (self.sigma), herdado de comp.sigma ou
#           passado como argumento opcional ao construtor de RadialCompressor.
#
#   AGORA:  σ é uma SAÍDA do meanline, calculada por estágio e por fileira
#           (rotor/estator) via inversão do critério de Lieblein — não existe
#           mais comp.sigma (escalar). RadialCompressor agora lê
#           comp.sigma_rotor[i] e comp.sigma_estator[i] (listas por estágio,
#           valores as-built pós-arredondamento de Z).
#
#           comp.sigma_* é a referência no raio médio. Na geometria de
#           corda e Z constantes, a solidez LOCAL varia: σ(r)=Z*c/(2πr).
#           DF e perfis usam sigma_rotor_local / sigma_estator_local.
# ══════════════════════════════════════════════════════════════════════════
#
# Teoria — Free Vortex (Mattingly, Eq. 9-45):
#   A hipótese free vortex assume:
#     - Velocidade axial constante com o raio: u(r) = u_ax
#     - Trabalho constante com o raio: Δh_t = cte
#   Isso implica que a componente tangencial varia inversamente com r:
#     v(r) = v_m · r_m / r      (Eq. 9-45)
#   onde v_m é o valor no raio médio (meanline) e r_m é o raio médio.
#
# Teoria — Grau de reação radial (Mattingly, Eq. 9-47):
#   Para free vortex com estágios repetitivos (v1 = v3):
#     R_c(r) = 1 - (v1_m + v2_m)·r_m² / (2·U_m·r²)
#            = 1 - const / (r/r_m)²
#   O grau de reação cresce com r — no hub é menor, no tip é maior.
#
# Notação de estações (mesma do meanline):
#   Estação 1 → entrada do rotor
#   Estação 2 → saída do rotor / entrada do estator
#______________________________________________________________________________________________________________


def gerar_secoes(n_secoes: int = 7) -> tuple:
    """
    Gera n_secoes rótulos e frações radiais (0=hub, 1=tip), igualmente
    espaçados entre hub e tip.

    RETORNA: (lista_rotulos, lista_fracoes)
        Para n_secoes=3: (["hub","mid","tip"], [0.0, 0.5, 1.0])
        Para n_secoes=7: (["hub","r1","r2","r3","r4","r5","tip"],
                          [0.0, 0.1667, 0.3333, 0.5, 0.6667, 0.8333, 1.0])
    """
    inteiro('n_secoes', n_secoes, minimo=2)

    fracoes = [i / (n_secoes - 1) for i in range(n_secoes)]

    if n_secoes == 3:
        rotulos = ["hub", "mid", "tip"]
    else:
        rotulos = ["hub"] + [f"r{i}" for i in range(1, n_secoes - 1)] + ["tip"]

    return rotulos, fracoes


# Compatibilidade: mantém o nome SECOES no nível do módulo para código
# externo que ainda o referencie diretamente. Valor padrão reflete N=7.
SECOES, _FRACOES_PADRAO = gerar_secoes()


class RadialCompressor:
    """
    PARÂMETROS DE ENTRADA:

    comp       - Objeto CompressorMeanline já resolvido
    n_secoes   - Número de seções radiais igualmente espaçadas entre hub
                 e tip (padrão: 7). Para n_secoes=3, reproduz exatamente
                 o comportamento original (hub/mid/tip).

    Nota sobre a solidez:
        σ_rotor e σ_estator NÃO são mais parâmetros de entrada opcionais
        desta classe. São herdados diretamente do meanline (comp.sigma_rotor
        e comp.sigma_estator, listas por estágio, valores as-built), pois é
        o meanline que os calcula via inversão do critério de Lieblein
        (ver Compressor_Meanline_main.py). Isso garante consistência: o DF
        verificado no radial recupera a solidez meanline no raio médio.
        Nas demais seções usa σ(r)=Z*c/(2πr), compatível com a geometria.

    Para cada estágio i e cada seção s, calcula:
      - r[i][s]         : raio da seção (m)
      - U[i][s]         : velocidade de ponta local U = ω·r (m/s)
      - v1[i][s]        : componente tangencial entrada rotor (m/s)
      - v2[i][s]        : componente tangencial saída rotor (m/s)
      - V1[i][s]        : velocidade absoluta entrada (m/s)
      - V2[i][s]        : velocidade absoluta saída (m/s)
      - W1[i][s]        : velocidade relativa entrada (m/s)
      - W2[i][s]        : velocidade relativa saída (m/s)
      - alpha1[i][s]    : ângulo absoluto entrada (°)
      - alpha2[i][s]    : ângulo absoluto saída (°)
      - beta1[i][s]     : ângulo relativo entrada (°)
      - beta2[i][s]     : ângulo relativo saída (°)
      - R_c[i][s]       : grau de reação local
      - M1[i][s]        : Mach absoluto entrada
      - M1R[i][s]       : Mach relativo entrada
      - DF_rotor[i][s]  : fator de difusão rotor
      - DF_estator[i][s]: fator de difusão estator
    """

    def __init__(self, comp, n_secoes: int = 7):

        # ------------------------------------------------------------------
        # VERIFICAÇÃO
        # ------------------------------------------------------------------
        if comp.Tt_saida[0] is None:
            raise RuntimeError(
                "O objeto CompressorMeanline deve ter resolver() chamado "
                "antes de ser passado ao RadialCompressor."
            )

        # ------------------------------------------------------------------
        # REFERÊNCIAS DO MEANLINE
        # ------------------------------------------------------------------
        self.comp    = comp
        self.omega   = comp.omega
        self.u_ax    = comp.u_ax
        self.cp      = comp.cp
        self.k       = comp.k
        self.R       = comp.R
        self.n_est   = comp.n_estagios
        self.n_secoes = n_secoes  # seções radiais geradas dinamicamente (N=7 por padrão)
        self.secoes, self.fracoes_radiais = gerar_secoes(n_secoes)

        # Solidez as-built por estágio e por fileira (rotor/estator),
        # calculada no meanline via inversão do critério de Lieblein.
        # Estas listas preservam a API dos valores de REFERÊNCIA meanline.
        # As solidez locais ficam em listas de dicionários separadas.
        self.sigma_rotor   = comp.sigma_rotor      # lista por estágio
        self.sigma_estator = comp.sigma_estator    # lista por estágio

        # ------------------------------------------------------------------
        # INICIALIZAÇÃO DOS RESULTADOS
        # Estrutura: lista de dicionários, um por estágio
        # Cada dicionário mapeia seção → valor
        # ------------------------------------------------------------------
        def _novo():
            return [{s: None for s in self.secoes} for _ in range(self.n_est)]

        self.r          = _novo()
        self.U_r        = _novo()
        self.v1         = _novo()
        self.v2         = _novo()
        self.gamma_rotor   = _novo()  # ângulo de stagger do rotor (°)
        self.gamma_estator = _novo()  # ângulo de stagger do estator (°)
        self.V1         = _novo()
        self.V2         = _novo()
        self.W1         = _novo()
        self.W2         = _novo()
        self.alpha1     = _novo()
        self.alpha2     = _novo()
        self.beta1      = _novo()
        self.beta2      = _novo()
        self.R_c        = _novo()
        self.M1         = _novo()
        self.M1R        = _novo()
        self.DF_rotor   = _novo()
        self.DF_estator = _novo()
        self.sigma_rotor_local = _novo()
        self.sigma_estator_local = _novo()

    #___________________________________________________________________________
    # FUNÇÕES AUXILIARES
    #___________________________________________________________________________

    def _free_vortex(self, v_m: float, r_m: float, r: float) -> float:
        """
        Lei free vortex — Eq. (9-45) Mattingly:
            v(r) = v_m · r_m / r
        Componente tangencial varia inversamente com o raio.
        """
        return v_m * r_m / r

    def _mach(self, V: float, Tt: float) -> float:
        """M² = V² / (k·R·Tt - (k-1)/2·V²)"""
        k, R = self.k, self.R
        denom = k * R * Tt - (k - 1) / 2 * V**2
        if denom <= 0:
            return float('nan')
        return math.sqrt(V**2 / denom)
    
    def _mach_relativo(self, W: float, V: float, Tt: float) -> float:
        """W: velocidade relativa; V: velocidade ABSOLUTA da mesma estação;
        Tt: temperatura total absoluta."""
        T = Tt - V**2 / (2 * self.cp)          # temperatura estática
        if T <= 0:
            return float('nan')
        return W / math.sqrt(self.k * self.R * T)
    #___________________________________________________________________________
    # MÉTODO PRINCIPAL
    #___________________________________________________________________________

    def resolver(self) -> None:
        """
        Aplica a lei free vortex em cada estágio e calcula todas as
        grandezas aerodinâmicas nas N seções radiais (hub, ..., tip).
        """
        comp   = self.comp
        omega  = self.omega
        u_ax   = self.u_ax
        avisos = []

        for i in range(self.n_est):

            # Raio médio e valores meanline do estágio i
            r_hub_i = comp.r_hub_est[i]
            r_tip_i = comp.r_tip_est[i]
            r_m = referencia_radial(
                r_hub_i, r_tip_i, comp.r_mean, contexto=f"Compressor estágio {i + 1}",
            )

            v1_m = comp.v1[i]    # componente tangencial entrada — meanline
            v2_m = comp.v2[i]    # componente tangencial saída — meanline
            Tt_i = comp.Tt_entrada[i]  # temperatura total de entrada do estágio

            # ------------------------------------------------------------
            # Raios de cada seção — interpolação linear entre hub e tip,
            # para cada fração radial gerada por gerar_secoes(). Para
            # n_secoes=3 isso reproduz EXATAMENTE hub/mid/tip (frações
            # 0, 0.5, 1.0), preservando compatibilidade com casos antigos.
            # ------------------------------------------------------------
            raios = {
                s: r_hub_i + frac * (r_tip_i - r_hub_i)
                for s, frac in zip(self.secoes, self.fracoes_radiais)
            }

            for s in self.secoes:
                r = raios[s]
                sigma_rotor_i = solidez_local(comp.Z_rotor[i], comp.corda_rotor[i], r)
                sigma_estator_i = solidez_local(comp.Z_estator[i], comp.corda_estator[i], r)

                # ==============================================================
                # 1. VELOCIDADE DE PONTA LOCAL
                # U(r) = ω · r
                # ==============================================================
                U_r = omega * r

                # ==============================================================
                # 2. COMPONENTES TANGENCIAIS VIA FREE VORTEX — Eq. (9-45)
                # v(r) = v_m · r_m / r
                # ==============================================================
                v1_r = self._free_vortex(v1_m, r_m, r)
                v2_r = self._free_vortex(v2_m, r_m, r)

                # ==============================================================
                # 3. TRIÂNGULOS DE VELOCIDADE
                # Velocidades absolutas:
                #   V = sqrt(u_ax² + v²)
                # Velocidades relativas (componente tangencial relativa = v - U):
                #   w_tang = v - U
                #   W = sqrt(u_ax² + w_tang²)
                # ==============================================================
                V1_r = math.sqrt(u_ax**2 + v1_r**2)
                V2_r = math.sqrt(u_ax**2 + v2_r**2)

                w1_tang = v1_r - U_r
                w2_tang = v2_r - U_r
                W1_r    = math.sqrt(u_ax**2 + w1_tang**2)
                W2_r    = math.sqrt(u_ax**2 + w2_tang**2)

                # ==============================================================
                # 4. ÂNGULOS DE ESCOAMENTO
                # α = atan(v / u_ax)       — ângulo absoluto
                # β = atan(-w_tang / u_ax) — ângulo relativo
                # ==============================================================
                alpha1_r = math.degrees(math.atan2(v1_r,   u_ax))
                alpha2_r = math.degrees(math.atan2(v2_r,   u_ax))
                beta1_r  = math.degrees(math.atan2(-w1_tang, u_ax))
                beta2_r  = math.degrees(math.atan2(-w2_tang, u_ax))

                # ----------------------------------------------------------------
                # MÉDIA DOS ÂNGULOS DE ESCOAMENTO (γ), na convenção do modelo.
                # Não é o stagger metálico do perfil corrigido por Carter.
                # No rotor, o sinal geométrico global de W é oposto ao β.
                # Como β1(r) e β2(r) variam com o raio (free vortex), γ(r)
                # também varia — isso é o que cria a torção (twist) da pá.
                # Corda (c) e número de pás (Z) são constantes com o raio
                # (herdados do meanline); o perfil usa a solidez local e Carter.
                # ----------------------------------------------------------------
                gamma_rotor_r   = (beta1_r + beta2_r) / 2
                gamma_estator_r = (alpha2_r + alpha1_r) / 2  # estágio repetitivo: α3=α1

                # ==============================================================
                # 5. GRAU DE REAÇÃO LOCAL — Eq. (9-47) Mattingly
                # R_c(r) = 1 - (v1 + v2) / (2·U(r))
                # Para free vortex:
                # R_c(r) = 1 - (v1_m + v2_m)·r_m² / (2·U_m·r²)
                # ==============================================================
                R_c_r = 1 - (v1_r + v2_r) / (2 * U_r)

                # ==============================================================
                # 6. NÚMEROS DE MACH LOCAIS
                # ==============================================================
                M1_r  = self._mach(V1_r, Tt_i)
                M1R_r = self._mach_relativo(W1_r, V1_r, Tt_i)

                # ==============================================================
                # 7. FATORES DE DIFUSÃO — Eqs. (9-17) e (9-18) Mattingly
                # DF_rotor  = 1 - W2/W1 + |w1_tang - w2_tang| / (2·σ_rotor·W1)
                # DF_estator = 1 - V3/V2 + |v2 - v3| / (2·σ_estator·V2)
                # Estágio repetitivo: V3 = V1, v3 = v1
                #
                # Usa a solidez AS-BUILT LOCAL da geometria de corda e Z
                # constantes. O passo cresce com r; σ diminui com r.
                # ==============================================================
                DF_rotor_r   = (1 - W2_r / W1_r
                                + abs(w1_tang - w2_tang) / (2 * sigma_rotor_i * W1_r))

                V3_r = V1_r
                v3_r = v1_r
                DF_est_r = (1 - V3_r / V2_r
                            + abs(v2_r - v3_r) / (2 * sigma_estator_i * V2_r))

                # ==============================================================
                # 8. VERIFICAÇÕES DE VIABILIDADE — via aero/constraints.py
                # ==============================================================
                avisos.extend(
                    checar_secao_compressor_radial(
                        DF_rotor=DF_rotor_r, DF_estator=DF_est_r,
                        R_c=R_c_r, M1R=M1R_r, estagio=i + 1, secao=s,
                    )
                )

                # ==============================================================
                # 9. ARMAZENAMENTO
                # ==============================================================
                self.r[i][s]          = r
                self.U_r[i][s]        = U_r
                self.v1[i][s]         = v1_r
                self.v2[i][s]         = v2_r
                self.V1[i][s]         = V1_r
                self.V2[i][s]         = V2_r
                self.W1[i][s]         = W1_r
                self.W2[i][s]         = W2_r
                self.alpha1[i][s]     = alpha1_r
                self.alpha2[i][s]     = alpha2_r
                self.beta1[i][s]      = beta1_r
                self.beta2[i][s]      = beta2_r
                self.gamma_rotor[i][s]   = gamma_rotor_r
                self.gamma_estator[i][s] = gamma_estator_r
                self.R_c[i][s]        = R_c_r
                self.M1[i][s]         = M1_r
                self.M1R[i][s]        = M1R_r
                self.DF_rotor[i][s]   = DF_rotor_r
                self.DF_estator[i][s] = DF_est_r
                self.sigma_rotor_local[i][s] = sigma_rotor_i
                self.sigma_estator_local[i][s] = sigma_estator_i

        if avisos:
            print("\n  ⚠  AVISOS RADIAIS — COMPRESSOR:")
            for av in avisos:
                print(f"     • {av}")

    #___________________________________________________________________________
    # EXIBIÇÃO DE RESULTADOS
    #___________________________________________________________________________

    def mostrar_resultados(self) -> None:
        """
        Imprime os resultados radiais por estágio e seção.

        Generalizado para N seções: o cabeçalho e as colunas da tabela
        são montados dinamicamente a partir de self.secoes, em vez de
        assumir fixamente HUB/MID/TIP (3 colunas).
        """
        self._verif_resolução()

        def linha():
            print("─" * (18 + 14 * self.n_secoes + self.n_secoes))

        linha()
        print("  COMPRESSOR — DISTRIBUIÇÃO RADIAL (FREE VORTEX)")
        print(f"  N de seções radiais: {self.n_secoes}  │  {', '.join(self.secoes)}")
        linha()

        for i in range(self.n_est):
            print(f"\n  ESTÁGIO {i+1}  │  σ_rotor no raio médio = {self.sigma_rotor[i]:.4f}  │  "
                  f"σ_estator no raio médio = {self.sigma_estator[i]:.4f}")

            cabecalho = "  " + f"{'Grandeza':<18}" + "".join(
                f"{s.upper():>14}" for s in self.secoes
            )
            print(cabecalho)
            print("  " + "─" * 18 + " " + " ".join("─" * 14 for _ in self.secoes))

            def linha_dados(nome, attr, fmt=".3f"):
                vals = [getattr(self, attr)[i][s] for s in self.secoes]
                linha_str = f"  {nome:<18} " + " ".join(
                    f"{v:>14{fmt}}" for v in vals
                )
                print(linha_str)

            print("  " + f"{'r (cm)':<18} " + " ".join(
                f"{self.r[i][s]*100:>14.3f}" for s in self.secoes
            ))
            linha_dados("U (m/s)",     "U_r",        fmt=".2f")
            linha_dados("v1 (m/s)",    "v1",         fmt=".2f")
            linha_dados("v2 (m/s)",    "v2",         fmt=".2f")
            linha_dados("V1 (m/s)",    "V1",         fmt=".2f")
            linha_dados("V2 (m/s)",    "V2",         fmt=".2f")
            linha_dados("W1 (m/s)",    "W1",         fmt=".2f")
            linha_dados("W2 (m/s)",    "W2",         fmt=".2f")
            linha_dados("α₁ (°)",      "alpha1",     fmt=".2f")
            linha_dados("α₂ (°)",      "alpha2",     fmt=".2f")
            linha_dados("β₁ (°)",      "beta1",      fmt=".2f")
            linha_dados("β₂ (°)",      "beta2",      fmt=".2f")
            linha_dados("R_c",         "R_c",        fmt=".4f")
            linha_dados("M1",          "M1",         fmt=".4f")
            linha_dados("M1R",         "M1R",        fmt=".4f")
            linha_dados("DF_rotor",    "DF_rotor",   fmt=".4f")
            linha_dados("DF_estator",  "DF_estator", fmt=".4f")
            linha_dados("σ rotor local", "sigma_rotor_local", fmt=".4f")
            linha_dados("σ estator local", "sigma_estator_local", fmt=".4f")
            linha_dados("γ_rotor (°)",  "gamma_rotor",   fmt=".2f")
            linha_dados("γ_estator(°)", "gamma_estator", fmt=".2f")

        linha()

    #___________________________________________________________________________
    # MÉTODO AUXILIAR
    #___________________________________________________________________________

    def _verif_resolução(self) -> None:
        if self.r[0]["hub"] is None:
            raise RuntimeError(
                "Execute resolver() antes de acessar os resultados."
            )


#_______________________________________________________________________________
if __name__ == "__main__":
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()

    comp_mock = compr1

    rad = RadialCompressor(comp=comp_mock, n_secoes=7)   
    rad.resolver()
    rad.mostrar_resultados()
    
