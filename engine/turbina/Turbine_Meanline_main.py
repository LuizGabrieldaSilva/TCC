from engine import design_criteria as dc
from engine.aero.constraints import checar_estagio_turbina_meanline
from engine.aero.annulus_geometry import raios_anular
from engine.aero.reacao_turbina import reacao_estatica
from engine.input_validation import validar_maquina, verificar_ciclo_resolvido, positivo, erros_numericos
#______________________________________________________________________________________________________________
# Projeto Meanline 1D da Turbina Axial Multiestágio.
# Recebe um objeto CicloBrayton já resolvido e os parâmetros geométricos/aerodinâmicos
# da turbina para calcular os triângulos de velocidade, grandezas termodinâmicas
# e critérios aerodinâmicos de cada estágio.
#
# Hipóteses:
#   - Gás caloricamente perfeito (cp, k constantes)
#   - Velocidade axial constante entre estágios (u_ax = φ·U = cte)
#   - Raio médio ARITMÉTICO constante: (r_tip + r_hub)/2 (meanline fixo)
#   - HTR é condição de entrada; cubo e ponta variam com a área por estágio
#   - Eficiência politrópica constante e igual à do ciclo
#   - Estágios com parâmetros uniformemente distribuídos (φ, ψ iguais em todos)
#   - Só o primeiro bocal recebe entrada axial; depois v1[i]=v3[i-1]
#   - Sem trabalho, calor ou perda adicional no plano entre estágios
#   - Reação = queda de entalpia estática no rotor / queda estática no estágio
#
# Notação de estações por estágio (Mattingly, Cap. 9):
#   Estação 1 → entrada do bocal (estator)
#   Estação 2 → saída do bocal / entrada do rotor
#   Estação 3 → saída do rotor (= entrada do próximo estágio)
#
# Diferenças em relação ao compressor:
#   - O escoamento expande: Tt e Pt caem a cada estágio
#   - A área do anular cresce a cada estágio (densidade cai)
#   - Faixa comparativa de ψ adotada: dc.PSI_TURB (distinta do compressor)
#   - α₂ é o ângulo de saída do bocal (estator), parâmetro de entrada
#   - Não há critério de DF como no compressor
#______________________________________________________________________________________________________________

import math

class TurbinaAxialMeanline:
    """
    PARÂMETROS DE ENTRADA:

    ciclo           - Objeto CicloBrayton já resolvido (com m_dot definido)
    
    N               - Velocidade de rotação (mesmo eixo do compressor)     (rpm)
    
    HTR             - Razão de raios na entrada: r_hub/r_tip               (adimensional)
                      Intervalo de aviso adotado: consultar dc.HTR_TURB.
                      
    n_estagios      - Número de estágios manual; None aciona seleção automática
    
    phi             - Coeficiente de fluxo  φ = u_ax / U                  (adimensional)
    
    psi             - Coeficiente de carga  ψ = cp·ΔTt / U²               (adimensional)    
                      Faixa comparativa adotada: consultar dc.PSI_TURB.
                      
    alpha2_graus    - Ângulo absoluto de saída do bocal (entrada do rotor) (°)
                      Análogo ao α₁ do compressor com IGV.
    
    AR              - Razão de aspecto (aspect ratio) da pá: altura da pá dividida pela corda (h/c)
    m_dot_turbina   - Vazão mássica de gases à entrada da turbina (kg/s).
                      Se omitida, usa a vazão registrada no ciclo.

    Nota sobre a geometria:
        r_tip, r_hub e r_mean são calculados internamente a partir da área
        do escoamento (Eq. 9-8 — Mattingly) e do HTR, garantindo consistência
        geométrica com o escoamento.

    Critérios adotados na ferramenta, definidos em engine.design_criteria:
        PHI_MAQUINAS e HTR_TURB orientam entradas; PSI_TURB e REACAO_TURB
        são faixas comparativas. Mach do bocal e swirl de escape têm
        limiares próprios; não são limites físicos universais.
    Dixon & Hall e Mattingly fundamentam relações de turbomáquinas;
    isso não atribui automaticamente todos os intervalos do código aos livros.
        
    
    """

    @erros_numericos('TurbinaAxialMeanline')
    def __init__(self,
                 ciclo,
                 N: float,
                 HTR: float,
                 phi: float,
                 psi: float,
                 alpha2_graus: float,
                 n_estagios: int = None,
                 sigma: float = 1.0,
                 AR: float = 2.0,
                 m_dot_turbina: float = None,
                 n_secoes_avaliacao: int = 7,
                 ):

        validar_maquina(N, HTR, phi, psi, AR, n_estagios, n_secoes_avaliacao, alpha2_graus, 'alpha2_graus')
        positivo('sigma', sigma)
        verificar_ciclo_resolvido(ciclo)
        if m_dot_turbina is not None:
            positivo('m_dot_turbina', m_dot_turbina)
        for nome in ('TIT', 'P03', 'T04r', 'P04', 'w_turb'):
            positivo(nome+' do ciclo', getattr(ciclo, nome))
        self.n_secoes_avaliacao = n_secoes_avaliacao
        self._entrada_selecao = dict(ciclo=ciclo, N=N, HTR=HTR, phi=phi, psi=psi,
                                     alpha2_graus=alpha2_graus, sigma=sigma, AR=AR,
                                     m_dot_turbina=m_dot_turbina,
                                     n_secoes_avaliacao=n_secoes_avaliacao)

        # ------------------------------------------------------------------
        # VERIFICAÇÃO DO OBJETO CICLO
        # ------------------------------------------------------------------
        if ciclo.w_líq is None:
            raise RuntimeError(
                "O objeto CicloBrayton deve ter resolver() chamado antes "
                "de ser passado ao TurbinaAxialMeanline."
            )
        if ciclo.m_dot is None:
            raise RuntimeError(
                "A vazão mássica do ciclo não foi definida. "
                "Chame vazão_mássica_desejada() ou potência_líquida_desejada() "
                "antes de instanciar o TurbinaAxialMeanline."
            )

        # ------------------------------------------------------------------
        # PARÂMETROS HERDADOS DO CICLO
        # ------------------------------------------------------------------
        # Notação:
        # No CicloBrayton:
        #   Estado 3 (TIT, P03) → entrada da turbina
        #   Estado 4 (T04r, P04) → saída da turbina
        # No TurbinaAxialMeanline:
        #   Estação 1 → entrada do bocal do primeiro estágio (= TIT, P03)
        #   Estação 3 → saída do rotor do último estágio (≈ T04r, P04)

        self.T01_turb  = ciclo.TIT     # Temperatura total de entrada na turbina (K)
        self.P01_turb  = ciclo.P03     # Pressão total de entrada na turbina (Pa)
        self.T04r_alvo = ciclo.T04r    # Temperatura total alvo na saída (K)
        self.P04_alvo  = ciclo.P04     # Pressão total alvo na saída (Pa)
        self.r_turb    = ciclo.r_turb  # Razão de expansão P03/P04
        self.e_t       = ciclo.e_turb  # Eficiência politrópica da turbina
        vazao_ciclo = getattr(ciclo, "m_dot_turbina", None)
        self.m_dot = (
            m_dot_turbina if m_dot_turbina is not None
            else vazao_ciclo if vazao_ciclo is not None
            else ciclo.m_dot
        )
        if not math.isfinite(self.m_dot) or self.m_dot <= 0:
            raise ValueError(f"Vazão mássica da turbina inválida: {self.m_dot} kg/s.")
        self.cp        = ciclo.cp_gases  # Gases após combustão (J/kg·K)
        self.k         = ciclo.k_gases   # Coerente com cp_gases e R_gases
        self.R         = self.cp * (1 - 1/self.k)  # Constante do gás (J/kg·K)

        # ------------------------------------------------------------------
        # PARÂMETROS DE ENTRADA DA TURBINA
        # ------------------------------------------------------------------
        self.N            = N
        self.omega        = N * 2 * math.pi / 60
        self.HTR          = HTR
        self.n_estagios   = n_estagios
        self.phi          = phi
        self.psi          = psi
        self.alpha2_graus = alpha2_graus
        self.sigma        = sigma
        self.AR           = AR

        # ------------------------------------------------------------------
        # VERIFICAÇÕES DE ENTRADA
        # ------------------------------------------------------------------
        if not (dc.HTR_TURB[0] <= HTR <= dc.HTR_TURB[1]):
            print(f"AVISO: HTR = {HTR:.3f} está fora da faixa típica [{dc.HTR_TURB[0]}, {dc.HTR_TURB[1]}].")
        if not (dc.PHI_MAQUINAS[0] <= phi <= dc.PHI_MAQUINAS[1]):
            print(f"AVISO: φ = {phi:.3f} está fora da faixa típica [{dc.PHI_MAQUINAS[0]}, {dc.PHI_MAQUINAS[1]}].")
        

        # ------------------------------------------------------------------
        # GEOMETRIA DE ENTRADA — calculada a partir do escoamento e do HTR
        # Mesma lógica iterativa do compressor, usando TIT e P03 como
        # condições de entrada.
        # ------------------------------------------------------------------
        a2_rad = math.radians(alpha2_graus)

        r_tip_est = 0.30  # chute inicial

        for _ in range(50): # 50 iterações
            r_mean_est = r_tip_est * (1 + HTR) / 2  # raio médio estimado
            U_est = self.omega * r_mean_est
            u_ax_est = phi * U_est  # velocidade axial estimada

            # No PRIMEIRO bocal, o escoamento entra com velocidade axial
            # e sai com ângulo α2 — a velocidade de entrada no bocal (estação 1)
            # é aproximadamente axial: V1 ≈ u_ax, α1 ≈ 0
            V1_est = u_ax_est   # entrada do bocal ≈ axial

            denom = self.k * self.R * ciclo.TIT - (self.k - 1) / 2 * V1_est**2
            if denom <= 0:
                raise ValueError(
                    "Parâmetros levam a escoamento supersônico na entrada "
                    "da turbina. Reduza N ou φ."
                )
            M1_est = math.sqrt(V1_est**2 / denom)

            exp   = (self.k + 1) / (2 * (self.k - 1))
            MFP   = (M1_est * math.sqrt(self.k / self.R)) / ((1 + ((self.k - 1) / 2) * M1_est**2) ** exp)

            # α1 ≈ 0 na entrada do bocal
            A_est = (self.m_dot * math.sqrt(ciclo.TIT) / (ciclo.P03 * math.cos(math.radians(0.0)) * MFP))

            r_tip_novo = math.sqrt(A_est / (math.pi * (1 - HTR**2)))

            if abs(r_tip_novo - r_tip_est) < 1e-8:
                break
            r_tip_est = r_tip_novo
        else:
            raise RuntimeError(
                f"Dimensionamento da turbina não convergiu em 50 iterações "
                f"(N={self.n_estagios}, phi={phi:.3f}, alpha2={alpha2_graus:.1f}°, HTR={HTR:.3f})."
            )

        self.r_tip_entrada = r_tip_est
        self.r_hub_entrada = HTR * r_tip_est
        self.r_mean = r_tip_est * (1 + HTR) / 2
        self.A_entrada = A_est

        # ------------------------------------------------------------------
        # GRANDEZAS CINEMÁTICAS GLOBAIS
        # ------------------------------------------------------------------
        self.U = self.omega * self.r_mean
        self.u_ax = phi * self.U

        # Queda de temperatura por estágio — Eq. (9-20) adaptada para turbina
        # ψ = cp·ΔTt / U²  →  ΔTt = ψ·U² / cp
        self.delta_Tt_estagio = psi * self.U**2 / self.cp   # (K) — queda por estágio

        # ------------------------------------------------------------------
        # NÚMERO DE ESTÁGIOS ESTIMADO
        # ------------------------------------------------------------------
        # Queda total necessária: ΔTt_total = w_turb / cp
        self.delta_Tt_total = ciclo.w_turb / self.cp
        self.n_estagios_estimado = self.delta_Tt_total / self.delta_Tt_estagio
        
        # Vetores provisórios; resolver() seleciona entre os inteiros vizinhos.
        if n_estagios is None:
            n_estagios = max(1, math.ceil(self.n_estagios_estimado))
            self.delta_Tt_estagio = self.delta_Tt_total / n_estagios
            self.psi_efetivo = self.delta_Tt_estagio * self.cp / self.U**2
            self.calculo_automatico = True
        else:
            self.psi_efetivo = psi
            self.calculo_automatico = False
        
        psi_para_checar = self.psi_efetivo if self.calculo_automatico else psi
        if not self.calculo_automatico and not (dc.PSI_TURB[0] <= psi_para_checar <= dc.PSI_TURB[1]):
            print(f"AVISO: ψ = {psi_para_checar:.3f} está fora da faixa típica [{dc.PSI_TURB[0]}, {dc.PSI_TURB[1]}].")
        

        self.n_estagios = n_estagios

        # ------------------------------------------------------------------
        # INICIALIZAÇÃO DOS RESULTADOS POR ESTÁGIO
        # ------------------------------------------------------------------
        n = n_estagios

        # Condições termodinâmicas
        self.Tt_entrada  = [None] * n
        self.Pt_entrada  = [None] * n
        self.Tt_saida    = [None] * n
        self.Pt_saida    = [None] * n
        self.pi_estagio  = [None] * n   # razão de expansão por estágio

        # Triângulos de velocidade
        # Estação 1: primeiro bocal axial; demais herdam a saída anterior
        # Estação 2: saída bocal / entrada rotor (α2 = alpha2_graus)
        # Estação 3: saída rotor
        self.alpha1      = [None] * n   # Ângulo absoluto entrada bocal (°)
        self.alpha2      = [None] * n   # Ângulo absoluto saída bocal (°)
        self.alpha3      = [None] * n   # Ângulo absoluto saída rotor (°)
        self.beta2       = [None] * n   # Ângulo relativo entrada rotor (°)
        self.beta3       = [None] * n   # Ângulo relativo saída rotor (°)

        # Módulos das velocidades
        self.V1          = [None] * n   # Velocidade absoluta entrada bocal (m/s)
        self.V2          = [None] * n   # Velocidade absoluta saída bocal (m/s)
        self.V3          = [None] * n   # Velocidade absoluta saída rotor (m/s)
        self.W2          = [None] * n   # Velocidade relativa entrada rotor (m/s)
        self.W3          = [None] * n   # Velocidade relativa saída rotor (m/s)

        # Componentes tangenciais
        self.v1          = [None] * n
        self.v2          = [None] * n
        self.v3          = [None] * n

        # Critérios aerodinâmicos
        self.M1          = [None] * n   # Mach entrada bocal
        self.M2          = [None] * n   # Mach saída bocal / entrada rotor
        self.M3          = [None] * n   # Mach saída rotor
        self.M2R         = [None] * n   # Mach relativo entrada rotor
        self.M3R         = [None] * n   # Mach relativo saída rotor
        self.grau_reacao = [None] * n
        self.reacao_rotor_por_trabalho = [None] * n  # diagnóstico, não R estática geral
        self.queda_h_estatica_rotor = [None] * n
        self.queda_h_estatica_estagio = [None] * n
        self.T1_est = [None] * n
        self.T2_est = [None] * n
        self.T3_est = [None] * n

        # Geometria do anular por estágio
        self.A_estagio   = [None] * n
        self.A_saida_estagio = [None] * n  # área exigida na estação 3, diagnóstico meanline
        self.r_hub_est   = [None] * n
        self.r_tip_est   = [None] * n
        self.h_pa        = [None] * n
        self.HTR_estagio = [None] * n

        # Número de pás
        self.corda_bocal   = [None] * n
        self.corda_rotor   = [None] * n
        self.Z_bocal       = [None] * n
        self.Z_rotor       = [None] * n

        # Resultado global
        self.pi_total_calc = None

    #___________________________________________________________________________
    # FUNÇÕES AUXILIARES
    #___________________________________________________________________________

    def _MFP(self, M: float) -> float:
        """Mass Flow Parameter — Eq. (9-8) Mattingly."""
        k, R = self.k, self.R
        exp = (k + 1) / (2 * (k - 1))
        return (M * math.sqrt(k / R)) / ((1 + ((k - 1) / 2) * M**2) ** exp)
    
    def _mach_de_velocidade(self, V: float, Tt: float) -> float:
        """
        Calcula M a partir de V e Tt.
        M² = V² / (k·R·Tt - (k-1)/2·V²)
        """
        k, R = self.k, self.R
        denominador = k * R * Tt - (k - 1) / 2 * V**2
        if denominador <= 0:
            raise ValueError(
                f"V={V:.1f} m/s incompatível com Tt={Tt:.1f} K."
            )
        return math.sqrt(V**2 / denominador)
    
    def _mach_relativo(self, W: float, V: float, Tt: float) -> float:
        """W: velocidade relativa; V: velocidade ABSOLUTA da mesma estação;
        Tt: temperatura total absoluta."""
        T = Tt - V**2 / (2 * self.cp)          # temperatura estática
        if T <= 0:
            raise ValueError(
                f"V={V:.1f} m/s incompatível com Tt={Tt:.1f} K "
                "(temperatura estática não positiva)."
            )
        return W / math.sqrt(self.k * self.R * T)

    #___________________________________________________________________________
    # MÉTODO PRINCIPAL
    #___________________________________________________________________________

    @erros_numericos('TurbinaAxialMeanline.resolver')
    def resolver(self) -> None:
        """
        Resolve o meanline 1D da turbina axial multiestágio.

        Para cada estágio, na sequência:
          1. Condições de entrada (Tt, Pt)
          2. Estação 1: axial só no primeiro bocal; saída do rotor anterior depois
          3. Estação 2: saída do bocal — α2 definido pelo usuário
             v2 = u_ax · tan(α2)  →  V2, W2, β2
          4. Equação de Euler → ΔTt, v3
             cp·ΔTt = U·(v2 - v3)  →  v3 = v2 - ψ·U
          5. Estação 3: saída do rotor → V3, W3, α3, β3
          6. Razão de expansão do estágio via eficiência politrópica
          7. Números de Mach (M1, M2, M2R, M3, M3R)
          8. Área do anular e geometria — raio médio aritmético fixo
          9. Número de pás
         10. Grau de reação
         11. Verificações de viabilidade
        """
        validar_maquina(self.N, self.HTR, self.phi, self.psi, self.AR,
                        self.n_estagios, self.n_secoes_avaliacao, self.alpha2_graus, 'alpha2_graus')
        positivo('sigma', self.sigma)
        if self.calculo_automatico:
            from engine.stage_selection import selecionar_estagios
            selecionar_estagios(self, "Turbina")
            return
        cp, k = self.cp, self.k
        U    = self.U
        u_ax = self.u_ax
        a2_rad = math.radians(self.alpha2_graus)
        sigma  = self.sigma

        # Expoente para razão de pressão via eficiência politrópica da turbina
        # τ_t = (P_saida/P_entrada)^((k-1)*e_t/k)  →  invertendo:
        # π_s = (Tt_in/Tt_out)^(k/((k-1)*e_t))
        exp_politropico = k / ((k - 1) * self.e_t)

        Tt_in = self.T01_turb
        Pt_in = self.P01_turb
        v1 = 0.0  # reiniciado em cada chamada, para resolver() ser idempotente
        avisos = []

        for i in range(self.n_estagios):

            # ==================================================================
            # ESTAÇÃO 1 — ENTRADA DO BOCAL
            # ==================================================================
            self.Tt_entrada[i] = Tt_in
            self.Pt_entrada[i] = Pt_in

            # Saída anterior alimenta este bocal, sem zerar o swirl.
            V1 = math.hypot(u_ax, v1)
            alpha1_rad = math.atan2(v1, u_ax)

            # ==================================================================
            # ESTAÇÃO 2 — SAÍDA DO BOCAL / ENTRADA DO ROTOR
            # O bocal acelera e deflete o escoamento para α2
            # ==================================================================
            v2 = u_ax * math.tan(a2_rad)        # componente tangencial (m/s)
            V2 = math.sqrt(u_ax**2 + v2**2)     # velocidade absoluta (m/s)

            # Velocidade relativa de entrada no rotor
            w2_tang = v2 - U                     # componente tangencial relativa
            W2 = math.sqrt(u_ax**2 + w2_tang**2)
            beta2_rad = math.atan2(w2_tang, u_ax)

            # ==================================================================
            # EQUAÇÃO DE EULER — Eq. (9-7a) adaptada para turbina
            # cp·ΔTt = U·(v2 - v3)  →  v3 = v2 - ψ·U
            # Na turbina, v2 > v3 (o rotor extrai trabalho reduzindo o swirl)
            # ==================================================================
            delta_Tt = self.delta_Tt_estagio     # queda de temperatura (K)
            v3 = v2 - delta_Tt * cp / U    # componente tangencial saída (m/s)

            # ==================================================================
            # ESTAÇÃO 3 — SAÍDA DO ROTOR
            # ==================================================================
            Tt_out = Tt_in - delta_Tt            # temperatura cai na turbina

            V3 = math.sqrt(u_ax**2 + v3**2)
            alpha3_rad = math.atan2(v3, u_ax)

            w3_tang = v3 - U
            W3 = math.sqrt(u_ax**2 + w3_tang**2)
            beta3_rad = math.atan2(w3_tang, u_ax)

            # ==================================================================
            # RAZÃO DE EXPANSÃO DO ESTÁGIO
            # Via eficiência politrópica da turbina:
            # τ_t = Tt_out/Tt_in = (1/π_s)^((k-1)*e_t/k)
            # π_s = (Tt_in/Tt_out)^(k/((k-1)*e_t))
            # ==================================================================
            tau_s = Tt_out / Tt_in
            pi_s = (1 / tau_s) ** exp_politropico   # razão de expansão > 1
            Pt_out = Pt_in / pi_s                   # pressão cai

            # ==================================================================
            # NÚMEROS DE MACH
            # ==================================================================
            M1 = self._mach_de_velocidade(V1, Tt_in)
            M2 = self._mach_de_velocidade(V2, Tt_in)
            M2R = self._mach_relativo(W2, V2, Tt_in)
            M3 = self._mach_de_velocidade(V3, Tt_out)
            M3R = self._mach_relativo(W3, V3, Tt_out)

            # ==================================================================
            # ÁREA DO ANULAR — Eq. (9-8) Mattingly
            # Usa condições e ângulo na entrada do bocal (estação 1)
            # ==================================================================
            # Área do anular — Eq. (9-8) Mattingly
            # Hipótese: raio médio aritmético CONSTANTE.
            # A = 2π·r_mean·h; a expansão muda cubo e ponta, sem ponta fixa.
            
            A_i = (self.m_dot * math.sqrt(Tt_in) / (Pt_in * math.cos(alpha1_rad) * self._MFP(M1)))
            A_saida_i = self.m_dot * math.sqrt(Tt_out) / (Pt_out * math.cos(alpha3_rad) * self._MFP(M3))
            r_hub_i, r_tip_i, h_i = raios_anular(
                A_i, self.r_mean, contexto=f"Turbina estágio {i + 1}",
            )
            r_mean_i = self.r_mean

            # ==================================================================
            # NÚMERO DE PÁS
            # c = h / AR  →  Z = 2π·r_mean·σ / c
            # ==================================================================
            c_bocal = h_i / self.AR
            c_rotor = h_i / self.AR
            Z_bocal_i = max(1, round(2 * math.pi * r_mean_i * sigma / c_bocal))
            Z_rotor_i = max(1, round(2 * math.pi * r_mean_i * sigma / c_rotor))

            # ==================================================================
            # GRAU DE REAÇÃO
            # R=(h2-h3)/(h1-h3), com h=h0-C²/2 (Dixon, Eq. 4.3a).
            # 1-(v2+v3)/(2U) é queda estática no rotor / trabalho de
            # eixo. Só coincide com R geral quando C1²=C3².
            # ==================================================================
            trabalho = cp * delta_Tt
            grau_reacao, queda_rotor, queda_estagio = reacao_estatica(
                trabalho, V1, V2, V3, contexto=f"Turbina estágio {i + 1}",
            )

            # ==================================================================
            # VERIFICAÇÕES DE VIABILIDADE
            # ==================================================================
            avisos.extend(
                checar_estagio_turbina_meanline(
                    grau_reacao=grau_reacao, M2=M2, M3R=M3R,
                    v3=v3, U=U, estagio=i + 1,
                    verificar_swirl=(i == self.n_estagios - 1),
                )
            )

            # ==================================================================
            # ARMAZENAMENTO
            # ==================================================================
            self.Tt_entrada[i]  = Tt_in
            self.Pt_entrada[i]  = Pt_in
            self.Tt_saida[i]    = Tt_out
            self.Pt_saida[i]    = Pt_out
            self.pi_estagio[i]  = pi_s
            self.v1[i]          = v1
            self.v2[i]          = v2
            self.v3[i]          = v3
            self.V1[i]          = V1
            self.V2[i]          = V2
            self.V3[i]          = V3
            self.W2[i]          = W2
            self.W3[i]          = W3
            self.alpha1[i]      = math.degrees(alpha1_rad)
            self.alpha2[i]      = self.alpha2_graus
            self.alpha3[i]      = math.degrees(alpha3_rad)
            self.beta2[i]       = math.degrees(beta2_rad)
            self.beta3[i]       = math.degrees(beta3_rad)
            self.M1[i]          = M1
            self.M2[i]          = M2
            self.M2R[i]         = M2R
            self.M3[i]          = M3
            self.M3R[i]         = M3R
            self.grau_reacao[i] = grau_reacao
            self.reacao_rotor_por_trabalho[i] = queda_rotor / trabalho
            self.queda_h_estatica_rotor[i] = queda_rotor
            self.queda_h_estatica_estagio[i] = queda_estagio
            self.T1_est[i] = Tt_in - V1 ** 2 / (2 * cp)
            self.T2_est[i] = Tt_in - V2 ** 2 / (2 * cp)
            self.T3_est[i] = Tt_out - V3 ** 2 / (2 * cp)
            self.A_estagio[i]   = A_i
            self.A_saida_estagio[i] = A_saida_i
            self.r_hub_est[i]   = r_hub_i
            self.r_tip_est[i]   = r_tip_i
            self.h_pa[i]        = h_i
            self.HTR_estagio[i] = r_hub_i / r_tip_i
            self.corda_bocal[i] = c_bocal
            self.corda_rotor[i] = c_rotor
            self.Z_bocal[i]     = Z_bocal_i
            self.Z_rotor[i]     = Z_rotor_i

            Tt_in = Tt_out
            Pt_in = Pt_out
            v1 = v3

        # Razão de expansão total calculada
        self.pi_total_calc = 1.0
        for pi in self.pi_estagio:
            self.pi_total_calc *= pi

        # Exibe avisos
        if avisos:
            print("\n  ⚠  AVISOS DE VIABILIDADE AERODINÂMICA:")
            for av in avisos:
                print(f"     • {av}")

        # ==================================================================
        # VERIFICAÇÃO DE CONSISTÊNCIA GLOBAL
        # ==================================================================
        erro_T = abs(self.Tt_saida[-1] - self.T04r_alvo) / self.T04r_alvo * 100
        erro_P = abs(self.pi_total_calc - self.r_turb) / self.r_turb * 100

        if erro_T > dc.FECHAMENTO_AVISO_PCT:
            print(
                f"\n  AVISO: Tt saída calculada ({self.Tt_saida[-1]:.1f} K) "
                f"difere {erro_T:.1f}% do alvo do ciclo ({self.T04r_alvo:.1f} K)."
            )
        if erro_P > dc.FECHAMENTO_AVISO_PCT:
            print(
                f"\n  AVISO: π_total calculado ({self.pi_total_calc:.3f}) "
                f"difere {erro_P:.1f}% da razão de expansão do ciclo "
                f"({self.r_turb:.3f}). Revise n_estagios, φ ou ψ."
            )

    #___________________________________________________________________________
    # EXIBIÇÃO DE RESULTADOS
    #___________________________________________________________________________

    def mostrar_resultados(self) -> None:
        """Imprime os resultados de cada estágio de forma organizada."""
        self._verif_resolução()

        def linha():
            print("─" * 76)

        linha()
        print("  TURBINA AXIAL — RESULTADOS MEANLINE")
        linha()
        print(f"  N = {self.N:.0f} rpm  │  HTR entrada = {self.HTR:.3f}  │  "
              f"r_mean = {self.r_mean*100:.2f} cm")
        print(f"  r_hub = {self.r_hub_entrada*100:.2f} cm  │  "
              f"r_tip = {self.r_tip_entrada*100:.2f} cm  │  "
              f"A_entrada = {self.A_entrada*1e4:.2f} cm²")
        print(f"  U = {self.U:.2f} m/s  │  u_ax = {self.u_ax:.2f} m/s  │  "
              f"φ = {self.phi:.3f}  │  ψ = {self.psi:.3f}")
        print(f"  π_total calculado = {self.pi_total_calc:.4f}  │  "
              f"π_expansão ciclo = {self.r_turb:.4f}")
        linha()
        print(f"  n_estagios: {self.n_estagios} "
              f"({'calculado automaticamente' if self.calculo_automatico else 'definido manualmente'}, "
              f"estimativa bruta: {self.n_estagios_estimado:.2f})")
        print(f"  ψ efetivo: {self.psi_efetivo:.4f}")
        linha()
        for i in range(self.n_estagios):
            print(f"\n  ESTÁGIO {i+1}")
            print(f"    Tt entrada = {self.Tt_entrada[i]:8.2f} K  │  "
                  f"Pt entrada = {self.Pt_entrada[i]/1e3:8.2f} kPa")
            print(f"    Tt saída   = {self.Tt_saida[i]:8.2f} K  │  "
                  f"Pt saída   = {self.Pt_saida[i]/1e3:8.2f} kPa  │  "
                  f"π = {self.pi_estagio[i]:.4f}")
            print(f"    α₁ = {self.alpha1[i]:6.2f}°  │  "
                  f"α₂ = {self.alpha2[i]:6.2f}°  │  "
                  f"α₃ = {self.alpha3[i]:6.2f}°")
            print(f"    β₂ = {self.beta2[i]:6.2f}°  │  "
                  f"β₃ = {self.beta3[i]:6.2f}°")
            print(f"    V1 = {self.V1[i]:7.2f} m/s  │  "
                  f"V2 = {self.V2[i]:7.2f} m/s  │  "
                  f"V3 = {self.V3[i]:7.2f} m/s")
            print(f"    W2 = {self.W2[i]:7.2f} m/s  │  "
                  f"W3 = {self.W3[i]:7.2f} m/s")
            print(f"    M1 = {self.M1[i]:.4f}  │  M2 = {self.M2[i]:.4f}  │  "
                  f"M2R = {self.M2R[i]:.4f}  │  M3 = {self.M3[i]:.4f}  │  "
                  f"M3R = {self.M3R[i]:.4f}")
            print(f"    Reação estática = {self.grau_reacao[i]:.4f}  │  "
                  f"queda rotor/trabalho = {self.reacao_rotor_por_trabalho[i]:.4f}")
            htr_i = self.r_hub_est[i] / self.r_tip_est[i]
            print(f"    A = {self.A_estagio[i]*1e4:7.2f} cm²  │  "
                  f"h_pá = {self.h_pa[i]*100:6.3f} cm  │  "
                  f"r_hub = {self.r_hub_est[i]*100:6.3f} cm  │  "
                  f"r_tip = {self.r_tip_est[i]*100:6.3f} cm  │  "
                  f"HTR = {htr_i:.3f}")
            print(f"    Bocal: c = {self.corda_bocal[i]*100:5.3f} cm  │  "
                  f"Z = {self.Z_bocal[i]:3d} pás")
            print(f"    Rotor: c = {self.corda_rotor[i]*100:5.3f} cm  │  "
                  f"Z = {self.Z_rotor[i]:3d} pás")
        linha()

    #___________________________________________________________________________
    # MÉTODOS AUXILIARES PÚBLICOS
    #___________________________________________________________________________

    def _verif_resolução(self) -> None:
        if self.Tt_saida[0] is None:
            raise RuntimeError(
                "Execute resolver() antes de acessar os resultados."
            )

    def n_estagios_estimado_info(self) -> None:
        print(f"  Número de estágios estimado : {self.n_estagios_estimado:.2f}")
        print(f"  Número de estágios adotado  : {self.n_estagios} "
            f"({'automático' if self.calculo_automatico else 'manual'})")
        if not self.calculo_automatico:
            diff = abs(self.n_estagios - self.n_estagios_estimado)
            if diff > 1.0:
                print(f"  AVISO: diferença de {diff:.1f} estágio(s) entre o valor "
                    f"adotado e o estimado. Revise φ, ψ ou N.")
            


#_______________________________________________________________________________
def criar_turbina_exemplo():
    """Cria e resolve o exemplo automático, sem estado global compartilhado."""
    from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
    ciclo1 = criar_ciclo_exemplo()
    turb1 = TurbinaAxialMeanline(
            ciclo        = ciclo1,
            N            = 14000,
            HTR          = 0.90, 
            n_estagios   = None,
            phi          = 0.53, 
            psi          = 1.198736, # 1.21 
            alpha2_graus = 63.5,
            sigma        = 1.0,
            AR           = 2.0,
        )
    turb1.resolver()
    return turb1


if __name__ == "__main__":
    from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
    ciclo1 = criar_ciclo_exemplo()

    class _CicloMock:
        TIT    = 1200.0
        P03    = 760e3
        T04r   = 800.8
        P04    = 100e3
        r_turb = 7.6
        e_turb = 0.80
        m_dot  = 15.0
        cp     = 1005.0
        k      = 1.4
        w_turb = 474.61e3
        w_líq  = 1.0

    ciclo_teste = ciclo1

    turb = TurbinaAxialMeanline(
        ciclo        = ciclo1,
        N            = 14000,
        HTR          = 0.90, 
        n_estagios   = 3,
        phi          = 0.53, 
        psi          = 1.198736, # 1.21
        alpha2_graus = 63.5,
        sigma        = 1.0,
        AR           = 2.0,
    )

    print(f"r_tip entrada  = {turb.r_tip_entrada*100:.3f} cm")
    print(f"r_hub entrada  = {turb.r_hub_entrada*100:.3f} cm")
    print(f"r_mean         = {turb.r_mean*100:.3f} cm")
    print(f"A_entrada      = {turb.A_entrada*1e4:.2f} cm²")
    print(f"U              = {turb.U:.2f} m/s")
    print(f"u_ax           = {turb.u_ax:.2f} m/s")
    print(f"ΔTt/estágio    = {turb.delta_Tt_estagio:.2f} K")
    print(f"ΔTt total      = {turb.delta_Tt_total:.2f} K")
    turb.n_estagios_estimado_info()
    print()
    turb.resolver()
    turb.mostrar_resultados()

# CASOS DE ESTABILIDADE E USO

# turb1 = TurbinaAxialMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.89,
#         n_estagios   = 3,
#         phi          = 0.47,
#         psi          = 1.00,
#         alpha2_graus = 65.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# turb1 = TurbinaAxialMeanline(
#         ciclo        = ciclo1,
#         N            = 14000,
#         HTR          = 0.90,
#         n_estagios   = 3,
#         phi          = 0.42,
#         psi          = 1.05,
#         alpha2_graus = 65.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# turb1 = TurbinaAxialMeanline(
#         ciclo        = ciclo1,
#         N            = 14000,
#         HTR          = 0.898, 
#         n_estagios   = 3,
#         phi          = 0.451, 
#         psi          = 1.10, 
#         alpha2_graus = 65.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# Exemplo automático atual: criar_turbina_exemplo(), definido acima.
