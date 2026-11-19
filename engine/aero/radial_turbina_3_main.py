from engine.aero.constraints import checar_secao_turbina_radial
from engine.input_validation import inteiro, positivo
from engine.aero.annulus_geometry import referencia_radial
from engine.aero.cascade_geometry import solidez_local
from engine.aero.reacao_turbina import reacao_estatica
import math

#______________________________________________________________________________________________________________
# Distribuição Radial da Turbina Axial — Lei Free Vortex.
# Recebe um objeto TurbinaAxialMeanline já resolvido e calcula, para cada
# estágio, as grandezas aerodinâmicas em N seções radiais igualmente
# espaçadas entre hub (cubo) e tip (ponta).
#
# ══════════════════════════════════════════════════════════════════════════
# MUDANÇA ESTRUTURAL (generalização de 3 para N seções radiais):
#   Mesma lógica aplicada em radial_compressor.py — 
#   Resumo: 
#   gerar_secoes(n_secoes) substitui a
#   lista fixa ["hub","mid","tip"], reproduzindo-a exatamente quando
#   n_secoes=3 (compatibilidade retroativa total). A lógica de cálculo
#   dentro do loop radial (free vortex, triângulos, Mach, R_c, stagger,
#   avisos) não muda.
# ══════════════════════════════════════════════════════════════════════════
# Teoria — Free Vortex (Mattingly, Eq. 9-45):
#   v(r) = v_m · r_m / r
#   Componente tangencial varia inversamente com o raio.
#   Velocidade axial e trabalho constantes com o raio.
#
# Reação radial estática (Dixon & Hall, Eq. 4.3a):
#   R_c(r)=[w+(V3²-V2²)/2]/[w+(V3²-V1²)/2].
#   1-(v2+v3)/(2U) é apenas queda estática do rotor/trabalho de eixo;
#   coincide com R_c quando V1²=V3². Não impor repetição no primeiro bocal.
#
# Notação de estações (mesma do meanline da turbina):
#   Estação 1 → entrada do bocal (axial só no primeiro estágio)
#   Estação 2 → saída do bocal / entrada do rotor (α2 definido)
#   Estação 3 → saída do rotor
#__________________________________________________________________________________________________________


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


# Compatibilidade: mantém o nome SECOES no nível do módulo. Padrão N=7.
SECOES, _FRACOES_PADRAO = gerar_secoes()


class RadialTurbina:
    """
    PARÂMETROS DE ENTRADA:

    turb       - Objeto TurbinaAxialMeanline já resolvido
    sigma      - Compatibilidade: deve coincidir com a entrada do meanline.
                 A solidez construída é calculada pelo Z inteiro, c e raio.
    n_secoes   - Número de seções radiais igualmente espaçadas entre hub
                 e tip (padrão: 7). Para n_secoes=3, reproduz exatamente
                 o comportamento original (hub/mid/tip).
    """

    def __init__(self, turb, sigma: float = None, n_secoes: int = 7):

        # ------------------------------------------------------------------
        # VERIFICAÇÃO
        # ------------------------------------------------------------------
        if turb.Tt_saida[0] is None:
            raise RuntimeError(
                "O objeto TurbinaAxialMeanline deve ter resolver() chamado "
                "antes de ser passado ao RadialTurbina."
            )

        # ------------------------------------------------------------------
        # REFERÊNCIAS DO MEANLINE
        # ------------------------------------------------------------------
        self.turb  = turb
        self.omega = turb.omega
        self.u_ax  = turb.u_ax
        self.cp    = turb.cp
        self.k     = turb.k
        self.R     = turb.R
        if sigma is not None:
            positivo('sigma', sigma)
        if sigma is not None and not math.isclose(sigma, turb.sigma, rel_tol=1e-12):
            raise ValueError("Altere a solidez na turbina meanline e recalcule Z antes do radial.")
        self.sigma = turb.sigma  # alvo de projeto; não é a solidez as-built local
        self.n_est = turb.n_estagios
        self.n_secoes = n_secoes    # seções radiais geradas dinamicamente (N=7 por padrão)
        self.secoes, self.fracoes_radiais = gerar_secoes(n_secoes)

        # ------------------------------------------------------------------
        # INICIALIZAÇÃO DOS RESULTADOS
        # ------------------------------------------------------------------
        def _novo():
            return [{s: None for s in self.secoes} for _ in range(self.n_est)]

        self.r             = _novo()
        self.U_r           = _novo()
        self.v1            = _novo()   # entrada bocal (≈ 0 axial)
        self.v2            = _novo()   # saída bocal / entrada rotor
        self.gamma_bocal   = _novo()  # ângulo de stagger do bocal (°)
        self.gamma_rotor   = _novo()  # ângulo de stagger do rotor (°)
        self.v3            = _novo()   # saída rotor
        self.V1            = _novo()
        self.V2            = _novo()
        self.V3            = _novo()
        self.W2            = _novo()
        self.W3            = _novo()
        self.alpha1        = _novo()
        self.alpha2        = _novo()
        self.alpha3        = _novo()
        self.beta2         = _novo()
        self.beta3         = _novo()
        self.R_c           = _novo()
        self.reacao_rotor_por_trabalho = _novo()
        self.queda_h_estatica_rotor = _novo()
        self.queda_h_estatica_estagio = _novo()
        self.M1            = _novo()
        self.M2            = _novo()
        self.M2R           = _novo()
        self.M3            = _novo()
        self.M3R           = _novo()
        self.sigma_bocal_local = _novo()
        self.sigma_rotor_local = _novo()

    #___________________________________________________________________________
    # FUNÇÕES AUXILIARES
    #___________________________________________________________________________

    def _free_vortex(self, v_m: float, r_m: float, r: float) -> float:
        """
        Lei free vortex — Eq. (9-45) Mattingly:
            v(r) = v_m · r_m / r
        """
        if abs(v_m) < 1e-10:
            return 0.0
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
        turb   = self.turb
        omega  = self.omega
        u_ax   = self.u_ax
        avisos = []

        for i in range(self.n_est):

            # Geometria e valores meanline do estágio i
            r_hub_i = turb.r_hub_est[i]
            r_tip_i = turb.r_tip_est[i]
            r_m = referencia_radial(
                r_hub_i, r_tip_i, turb.r_mean, contexto=f"Turbina estágio {i + 1}",
            )

            # Valores meanline das componentes tangenciais
            v1_m = turb.v1[i]    # zero só no primeiro; depois herda v3 anterior
            v2_m = turb.v2[i]    # saída bocal (alto swirl)
            v3_m = turb.v3[i]    # saída rotor (swirl reduzido)

            Tt_in  = turb.Tt_entrada[i]
            Tt_out = turb.Tt_saida[i]

            # ------------------------------------------------------------
            # Raios de cada seção — interpolação linear entre hub e tip,
            # para cada fração radial gerada por gerar_secoes(). Para
            # n_secoes=3 isso reproduz EXATAMENTE hub/mid/tip.
            # ------------------------------------------------------------
            raios = {
                s: r_hub_i + frac * (r_tip_i - r_hub_i)
                for s, frac in zip(self.secoes, self.fracoes_radiais)
            }

            for s in self.secoes:
                r = raios[s]

                # ==============================================================
                # 1. VELOCIDADE DE PONTA LOCAL
                # ==============================================================
                U_r = omega * r

                # ==============================================================
                # 2. COMPONENTES TANGENCIAIS VIA FREE VORTEX — Eq. (9-45)
                # Estação 1: v1_m*r_m/r; a constante de vórtice livre é
                # herdada da saída anterior. Comparar no MESMO raio físico,
                # não pelo rótulo hub/mid/tip de anulares diferentes.
                # Estação 2: saída do bocal — alto swirl
                # v2(r) = v2_m · r_m / r
                # Estação 3: saída do rotor
                # v3(r) = v3_m · r_m / r
                # ==============================================================
                v1_r = self._free_vortex(v1_m, r_m, r)
                v2_r = self._free_vortex(v2_m, r_m, r)
                v3_r = self._free_vortex(v3_m, r_m, r)

                # ==============================================================
                # 3. VELOCIDADES ABSOLUTAS E RELATIVAS
                # V = sqrt(u_ax² + v²)
                # w_tang = v - U  (componente tangencial relativa)
                # W = sqrt(u_ax² + w_tang²)
                # ==============================================================
                V1_r = math.sqrt(u_ax**2 + v1_r**2)
                V2_r = math.sqrt(u_ax**2 + v2_r**2)
                V3_r = math.sqrt(u_ax**2 + v3_r**2)

                w2_tang = v2_r - U_r
                w3_tang = v3_r - U_r
                W2_r    = math.sqrt(u_ax**2 + w2_tang**2)
                W3_r    = math.sqrt(u_ax**2 + w3_tang**2)

                # ==============================================================
                # 4. ÂNGULOS DE ESCOAMENTO
                # ==============================================================
                alpha1_r = math.degrees(math.atan2(v1_r,    u_ax))
                alpha2_r = math.degrees(math.atan2(v2_r,    u_ax))
                alpha3_r = math.degrees(math.atan2(v3_r,    u_ax))
                beta2_r  = math.degrees(math.atan2(w2_tang, u_ax))
                beta3_r  = math.degrees(math.atan2(w3_tang, u_ax))

                # ----------------------------------------------------------------
                # ÂNGULO DE STAGGER (γ) — aproximação de projeto preliminar
                # Bocal: média entre entrada (α1 herdado) e saída (α2)
                # Rotor: média entre entrada (β2) e saída (β3)
                # Corda e Z são constantes com o raio (herdados do meanline);
                # apenas o ângulo de instalação varia, gerando o twist da pá.
                # ----------------------------------------------------------------
                gamma_bocal_r = (alpha1_r + alpha2_r) / 2
                gamma_rotor_r = (beta2_r + beta3_r) / 2

                # ==============================================================
                # 5. REAÇÃO ESTÁTICA LOCAL, com V1,V2,V3 da mesma seção.
                # Não substituir a queda estática do estágio pelo trabalho
                # de eixo se V1² e V3² forem diferentes.
                # ==============================================================
                trabalho = turb.cp * turb.delta_Tt_estagio
                R_c_r, queda_rotor, queda_estagio = reacao_estatica(
                    trabalho, V1_r, V2_r, V3_r,
                    contexto=f"Turbina estágio {i + 1}, seção {s}",
                )

                # ==============================================================
                # 6. NÚMEROS DE MACH LOCAIS
                # Estação 1: usa Tt_in (antes do bocal)
                # Estações 2 e 2R: usa Tt_in (o bocal não faz trabalho)
                # Estações 3 e 3R: usa Tt_out (após o rotor)
                # ==============================================================
                M1_r  = self._mach(V1_r, Tt_in)
                M2_r  = self._mach(V2_r, Tt_in)
                M2R_r = self._mach_relativo(W2_r, V2_r, Tt_in)
                M3_r  = self._mach(V3_r, Tt_out)
                M3R_r = self._mach_relativo(W3_r, V3_r, Tt_out)

                # ==============================================================
                # 7. VERIFICAÇÕES DE VIABILIDADE
                # ==============================================================
                avisos.extend(
                    checar_secao_turbina_radial(
                        R_c=R_c_r, M2=M2_r, M3R=M3R_r,
                        estagio=i + 1, secao=s,
                    )
                )

                # ==============================================================
                # 8. ARMAZENAMENTO
                # ==============================================================
                self.r[i][s]      = r
                self.sigma_bocal_local[i][s] = solidez_local(turb.Z_bocal[i], turb.corda_bocal[i], r)
                self.sigma_rotor_local[i][s] = solidez_local(turb.Z_rotor[i], turb.corda_rotor[i], r)
                self.U_r[i][s]    = U_r
                self.v1[i][s]     = v1_r
                self.v2[i][s]     = v2_r
                self.v3[i][s]     = v3_r
                self.V1[i][s]     = V1_r
                self.V2[i][s]     = V2_r
                self.V3[i][s]     = V3_r
                self.W2[i][s]     = W2_r
                self.W3[i][s]     = W3_r
                self.alpha1[i][s] = alpha1_r
                self.alpha2[i][s] = alpha2_r
                self.alpha3[i][s] = alpha3_r
                self.beta2[i][s]  = beta2_r
                self.beta3[i][s]  = beta3_r
                self.gamma_bocal[i][s] = gamma_bocal_r
                self.gamma_rotor[i][s] = gamma_rotor_r
                self.R_c[i][s]    = R_c_r
                self.reacao_rotor_por_trabalho[i][s] = queda_rotor / trabalho
                self.queda_h_estatica_rotor[i][s] = queda_rotor
                self.queda_h_estatica_estagio[i][s] = queda_estagio
                self.M1[i][s]     = M1_r
                self.M2[i][s]     = M2_r
                self.M2R[i][s]    = M2R_r
                self.M3[i][s]     = M3_r
                self.M3R[i][s]    = M3R_r

        if avisos:
            print("\n  ⚠  AVISOS RADIAIS — TURBINA:")
            for av in avisos:
                print(f"     • {av}")

    #___________________________________________________________________________
    # EXIBIÇÃO DE RESULTADOS
    #___________________________________________________________________________

    def mostrar_resultados(self) -> None:
        """
        Imprime os resultados radiais por estágio e seção.

        Generalizado para N seções: o cabeçalho e as colunas da tabela
        são montados dinamicamente a partir de self.secoes.
        """
        self._verif_resolução()

        def linha():
            print("─" * (18 + 14 * self.n_secoes + self.n_secoes))

        linha()
        print("  TURBINA — DISTRIBUIÇÃO RADIAL (FREE VORTEX)")
        print(f"  N de seções radiais: {self.n_secoes}  │  {', '.join(self.secoes)}")
        linha()

        for i in range(self.n_est):
            print(f"\n  ESTÁGIO {i+1}")

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
            linha_dados("U (m/s)",   "U_r",    fmt=".2f")
            linha_dados("v1 (m/s)",  "v1",     fmt=".2f")
            linha_dados("v2 (m/s)",  "v2",     fmt=".2f")
            linha_dados("v3 (m/s)",  "v3",     fmt=".2f")
            linha_dados("V1 (m/s)",  "V1",     fmt=".2f")
            linha_dados("V2 (m/s)",  "V2",     fmt=".2f")
            linha_dados("V3 (m/s)",  "V3",     fmt=".2f")
            linha_dados("W2 (m/s)",  "W2",     fmt=".2f")
            linha_dados("W3 (m/s)",  "W3",     fmt=".2f")
            linha_dados("α₁ (°)",    "alpha1", fmt=".2f")
            linha_dados("α₂ (°)",    "alpha2", fmt=".2f")
            linha_dados("α₃ (°)",    "alpha3", fmt=".2f")
            linha_dados("β₂ (°)",    "beta2",  fmt=".2f")
            linha_dados("β₃ (°)",    "beta3",  fmt=".2f")
            linha_dados("R_c",       "R_c",    fmt=".4f")
            linha_dados("M1",        "M1",     fmt=".4f")
            linha_dados("M2",        "M2",     fmt=".4f")
            linha_dados("M2R",       "M2R",    fmt=".4f")
            linha_dados("M3",        "M3",     fmt=".4f")
            linha_dados("M3R",       "M3R",    fmt=".4f")
            linha_dados("σ bocal local", "sigma_bocal_local", fmt=".4f")
            linha_dados("σ rotor local", "sigma_rotor_local", fmt=".4f")
            linha_dados("γ_bocal(°)", "gamma_bocal", fmt=".2f")
            linha_dados("γ_rotor(°)", "gamma_rotor", fmt=".2f")

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
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()

    turb_mock = turb1

    rad = RadialTurbina(turb=turb_mock, n_secoes=7)   # n_secoes=7 (padrão)
    rad.resolver()
    rad.mostrar_resultados()
    
