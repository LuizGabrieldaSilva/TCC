from engine import design_criteria as dc
from engine.aero.constraints import checar_estagio_compressor_meanline
from engine.aero.annulus_geometry import raios_anular
from engine.input_validation import validar_maquina, verificar_ciclo_resolvido, positivo, erros_numericos
#______________________________________________________________________________________________________________
# Projeto Meanline 1D do Compressor Axial Multiestágio.
# Recebe um objeto CicloBrayton já resolvido e os parâmetros geométricos/aerodinâmicos
# do compressor para calcular os triângulos de velocidade, grandezas termodinâmicas
# e critérios aerodinâmicos de cada estágio.
#
# ══════════════════════════════════════════════════════════════════════════
# MUDANÇA ESTRUTURAL (refatoração pós-constraints.py):
#
#   ANTES:  σ (solidez) era um parâmetro de ENTRADA fixo (padrão 1.0), igual
#           para rotor e estator em todos os estágios. O Fator de Difusão
#           (DF) de Lieblein era calculado A PARTIR de σ e apenas VERIFICADO
#           contra o limite de 0.6 (checagem a posteriori).
#
#   AGORA:  σ é uma SAÍDA calculada. O usuário define um DF_alvo de projeto
#           (recomendação de Saravanamuttoo, Cap. 5: manter D ~0.45-0.50,
#           com folga do limite de separação em D~0.6). A equação de
#           Lieblein é invertida para isolar σ_rotor e σ_estator
#           necessários para atingir DF_alvo em cada estágio.
#
#           Como Z (número de pás) deve ser inteiro, σ_teórico é arredondado
#           via Z, gerando uma σ "as-built" ligeiramente diferente. O DF
#           final armazenado e verificado é recalculado com σ_as-built —
#           portanto a checagem de DF em constraints.py continua com função
#           real (valida o projeto final, não um valor "cru").
#
#   Equação de Lieblein (forma usada, equivalente a Mattingly Eq. 9-17/9-18
#   e Saravanamuttoo Cap. 5, eq. de fator de difusão):
#
#       DF = 1 - (V2/V1) + ΔCw / (2·σ·V1)
#
#   Isolando σ:
#
#       σ = ΔCw / [2·V1·(DF_alvo - 1 + V2/V1)]
#
#   Válido apenas se (DF_alvo - 1 + V2/V1) > 0, i.e., se o próprio DF_alvo
#   for maior que a difusão mínima (V2/V1) que ocorreria com solidez
#   infinita. Caso contrário, o alvo é inatingível para aquele triângulo de
#   velocidades — ver tratamento de erro no resolver().
# ══════════════════════════════════════════════════════════════════════════
#
# Hipóteses:
#   - Gás caloricamente perfeito (cp, k constantes)
#   - Velocidade axial constante entre estágios (u_ax = φ·U = cte)
#   - Raio médio ARITMÉTICO constante: (r_tip + r_hub)/2 (meanline fixo)
#   - HTR é condição de entrada; cubo e ponta variam com a área por estágio
#   - Eficiência politrópica constante e igual à do ciclo
#   - Estágios com parâmetros uniformemente distribuídos (φ, ψ iguais em todos)
#   - Solidez derivada do critério de Lieblein — pode variar entre rotor e
#     estator, e entre estágios, conforme o triângulo de velocidades local
#
# Geometria de entrada:
#   O usuário fornece HTR (r_hub/r_tip) na entrada do compressor.
#   r_tip, r_hub e r_mean são calculados internamente a partir da área do
#   escoamento (Eq. 9-8) e do HTR, garantindo consistência geométrica.
#
# Notação de estações por estágio (Mattingly, Cap. 9):
#   Estação 1 → entrada do rotor
#   Estação 2 → saída do rotor / entrada do estator
#   Estação 3 → saída do estator (= entrada do próximo estágio)
#______________________________________________________________________________________________________________

import math

class CompressorMeanline:
    """
    PARÂMETROS DE ENTRADA:

    ciclo           - Objeto CicloBrayton já resolvido (com m_dot definido)
    
    N               - Velocidade de rotação                              (rpm)
    
    HTR             - Razão de raios na entrada: r_hub/r_tip             (adimensional)
                      Intervalo de aviso adotado: consultar dc.HTR_COMP.
                      
    n_estagios      - Número de estágios definido pelo usuário (ou calculado automaticamente)
    
    phi             - Coeficiente de fluxo  φ = u_ax / U                (adimensional)
    
    psi             - Coeficiente de carga  ψ = cp·ΔTt / U²             (adimensional)
    
    alpha1_graus    - Ângulo absoluto de entrada no rotor (IGV); 0 = sem IGV  (°)
    
    DF_alvo         - Fator de Difusão de Lieblein alvo de projeto      (adimensional)
                      Usado para DERIVAR a solidez de rotor e estator em
                      cada estágio (ver bloco de mudança estrutural acima).
                      Intervalo de orientação adotado: dc.DF_ALVO_COMP.
                      O fundamento empírico de difusão é discutido em
                      Saravanamuttoo, Cap. 5; o intervalo da ferramenta
                      não é uma exigência universal do livro.
                      
    AR              - Razão de aspecto (aspect ratio) da pá: altura da pá dividida pela corda (h/c)

    Nota sobre a geometria:
        r_tip, r_hub e r_mean NÃO são entradas — são calculados pelo código
        a partir da área do escoamento (Eq. 9-8 — Mattingly) e do HTR,
        garantindo consistência geométrica com o escoamento.

    Nota sobre a solidez:
        σ_rotor e σ_estator NÃO são entradas — são calculados por estágio
        a partir de DF_alvo, invertendo a equação de Lieblein. Isso permite
        que cada fileira de pás (rotor/estator, por estágio) tenha a
        solidez estritamente necessária para atingir o DF de projeto,
        em vez de uma solidez uniforme arbitrária.

    Critérios adotados na ferramenta, definidos em engine.design_criteria:
        PHI_MAQUINAS, PSI_COMP, DF_ALVO_COMP e HTR_COMP orientam entradas.
        DF_MAX é o limiar da triagem empírica de Lieblein.
        REACAO_COMP é uma faixa comparativa aplicada ao meanline.
    Os fundamentos das relações não tornam esses intervalos exigências
    universais de Dixon & Hall, Mattingly ou Saravanamuttoo. O cálculo sem
    avisos não comprova estabilidade ou fabricabilidade.
    """

    @erros_numericos('CompressorMeanline')
    def __init__(self,
                 ciclo,
                 N: float,
                 HTR: float,
                 phi: float,
                 psi: float,
                 n_estagios: int = None,
                 alpha1_graus: float = 0.0,
                 DF_alvo: float = 0.45,
                 AR: float = 2.0,
                 n_secoes_avaliacao: int = 7,
                 ):

        validar_maquina(N, HTR, phi, psi, AR, n_estagios, n_secoes_avaliacao, alpha1_graus, 'alpha1_graus')
        positivo('DF_alvo', DF_alvo)
        verificar_ciclo_resolvido(ciclo)
        for nome in ('T01', 'P01', 'T02r', 'P02', 'w_compr'):
            positivo(nome+' do ciclo', getattr(ciclo, nome))
        self.n_secoes_avaliacao = n_secoes_avaliacao
        self._entrada_selecao = dict(ciclo=ciclo, N=N, HTR=HTR, phi=phi, psi=psi,
                                     alpha1_graus=alpha1_graus, DF_alvo=DF_alvo, AR=AR,
                                     n_secoes_avaliacao=n_secoes_avaliacao)

        # ------------------------------------------------------------------
        # VERIFICAÇÃO DO OBJETO CICLO
        # ------------------------------------------------------------------
        if ciclo.w_líq is None:
            raise RuntimeError(
                "O objeto CicloBrayton deve ter resolver() chamado antes "
                "de ser passado ao CompressorMeanline."
            )
        if ciclo.m_dot is None:
            raise RuntimeError(
                "A vazão mássica do ciclo não foi definida. "
                "Chame vazão_mássica_desejada() ou potência_líquida_desejada() "
                "antes de instanciar o CompressorMeanline."
            )

        # ------------------------------------------------------------------
        # PARÂMETROS HERDADOS DO CICLO
        # ------------------------------------------------------------------
        # Atenção à nomenclatura:
        # No CicloBrayton, os estados seguem o ciclo completo:
        #   Estado 1 (T01, P01)   → entrada do compressor
        #   Estado 2 (T02r, P02)  → saída do compressor
        # No CompressorMeanline, a numeração segue as estações internas:
        #   Estação 1 → entrada do primeiro estágio (= estado 1 do ciclo)
        #   Estação 2 → saída do rotor
        #   Estação 3 → saída do estator
        # Portanto, a entrada do meanline é T01/P01 do ciclo.
        # T02r/P02 do ciclo são os valores ALVO de saída do compressor.

        self.T01_comp  = ciclo.T01     # Temperatura total de entrada no compressor (K)
        self.P01_comp  = ciclo.P01     # Pressão total de entrada no compressor (Pa)
        self.T02r_alvo = ciclo.T02r    # Temperatura total alvo na saída (K)
        self.P02_alvo  = ciclo.P02     # Pressão total alvo na saída (Pa)
        self.m_dot     = ciclo.m_dot   # Vazão mássica (kg/s)
        self.r_compr   = ciclo.r_compr # Razão de pressão total do compressor
        self.e_c       = ciclo.e_compr # Eficiência politrópica do compressor
        self.cp        = ciclo.cp      # Calor específico (J/kg·K)
        self.k         = ciclo.k       # Razão de calores específicos
        self.R         = self.cp * (1 - 1/self.k)  # Constante do gás (J/kg·K)

        # ------------------------------------------------------------------
        # PARÂMETROS DE ENTRADA DO COMPRESSOR
        # ------------------------------------------------------------------
        self.N            = N                         # Rotação (rpm)
        self.omega        = N * 2 * math.pi / 60     # Velocidade angular (rad/s)
        self.HTR          = HTR                       # Razão r_hub/r_tip somente na entrada
        self.n_estagios   = n_estagios               # Número de estágios
        self.phi          = phi                       # Coeficiente de fluxo φ
        self.psi          = psi                       # Coeficiente de carga ψ
        self.alpha1_graus = alpha1_graus              # Ângulo de entrada IGV (°)
        self.DF_alvo      = DF_alvo                   # Fator de Difusão alvo (Lieblein)
        self.AR           = AR                        # Razão de aspecto (h/c)

        # ------------------------------------------------------------------
        # VERIFICAÇÕES DE ENTRADA
        # ------------------------------------------------------------------
        if not (dc.HTR_COMP[0] <= HTR <= dc.HTR_COMP[1]):
            print(f"AVISO: HTR = {HTR:.3f} está fora da faixa típica [{dc.HTR_COMP[0]}, {dc.HTR_COMP[1]}].")
        if not (dc.PHI_MAQUINAS[0] <= phi <= dc.PHI_MAQUINAS[1]):
            print(f"AVISO: φ = {phi:.3f} está fora da faixa típica [{dc.PHI_MAQUINAS[0]}, {dc.PHI_MAQUINAS[1]}].")
        if not (dc.DF_ALVO_COMP[0] <= DF_alvo <= dc.DF_ALVO_COMP[1]):
            print(
                f"AVISO: DF_alvo = {DF_alvo:.3f} está fora da faixa de orientação adotada "
                f"[{dc.DF_ALVO_COMP[0]}, {dc.DF_ALVO_COMP[1]}]. A difusão é discutida em Saravanamuttoo, Cap. 5; "
                f"{dc.DF_MAX} é o critério empírico de triagem adotado, não previsão completa de separação."
            )

        # ------------------------------------------------------------------
        # GEOMETRIA DE ENTRADA — calculada a partir do escoamento e do HTR
        # ------------------------------------------------------------------
        # A área do anular na entrada é calculada pela Eq. (9-8) — Mattingly,
        # usando as condições do escoamento na entrada do compressor.
        # Para isso, precisamos de M1 na entrada — estimado iterativamente
        # a partir de u_ax e das condições termodinâmicas de entrada.
        #
        # Como U e u_ax dependem de r_mean, que depende da área, que depende
        # de M1, que depende de u_ax — resolvemos em duas etapas:
        #
        # Etapa 1: estimar M1 a partir de uma estimativa inicial de u_ax
        #          usando as condições T01, P01.
        # Etapa 2: calcular A, r_tip, r_hub, r_mean a partir de M1 e HTR.
        # Etapa 3: recalcular U e u_ax com o r_mean correto.
        #
        # Para o __init__, fazemos a estimativa de r_mean via área de escoamento.
        # O resolver() usa o r_mean calculado aqui como fixo.

        a1_rad = math.radians(alpha1_graus)
        
        # Estimativa inicial: assume u_ax inicial qualquer para obter M1_est
        # Usamos a relação: u_ax = phi * omega * r_mean
        # E A = pi*(r_tip² - r_hub²) com HTR = r_hub/r_tip
        # A = pi*r_tip²*(1 - HTR²)  →  r_tip = sqrt(A / (pi*(1-HTR²)))
        # r_mean = r_tip*(1+HTR)/2
        # Iteramos: começa com u_ax = phi * omega * r_mean_est

        # Chute inicial para r_tip baseado em dimensão típica
        r_tip_est = 0.30  # m — valor inicial qualquer para arrancar a iteração

        for _ in range(50):  # iterar até convergir
            r_mean_est = r_tip_est * (1 + HTR) / 2
            U_est      = self.omega * r_mean_est
            u_ax_est   = phi * U_est

            # V1 na entrada (considerando α1)
            v1_est = u_ax_est * math.tan(a1_rad)
            V1_est = math.sqrt(u_ax_est**2 + v1_est**2)

            # M1 estimado
            denom = self.k * self.R * ciclo.T01 - (self.k - 1) / 2 * V1_est**2
            if denom <= 0:
                raise ValueError(
                    "Parâmetros de entrada levam a escoamento supersônico "
                    "na entrada do compressor. Reduza N, φ ou α1."
                )
            M1_est = math.sqrt(V1_est**2 / denom)

            # Área pela Eq. (9-8)
            exp   = (self.k + 1) / (2 * (self.k - 1))
            MFP   = (M1_est * math.sqrt(self.k / self.R)) / ((1 + ((self.k - 1) / 2) * M1_est**2) ** exp)
            A_est = (ciclo.m_dot * math.sqrt(ciclo.T01) / (ciclo.P01 * math.cos(a1_rad) * MFP))

            # r_tip a partir da área e do HTR
            r_tip_novo = math.sqrt(A_est / (math.pi * (1 - HTR**2)))

            if abs(r_tip_novo - r_tip_est) < 1e-8:
                break
            r_tip_est = r_tip_novo
        else:
            raise RuntimeError(
                f"Dimensionamento do compressor não convergiu em 50 iterações "
                f"(N={self.n_estagios}, phi={phi:.3f}, alpha1={alpha1_graus:.1f}°, HTR={HTR:.3f})."
            )

        # Geometria de entrada consistente com o escoamento
        self.r_tip_entrada  = r_tip_est
        self.r_hub_entrada  = HTR * r_tip_est
        self.r_mean         = r_tip_est * (1 + HTR) / 2
        self.A_entrada      = A_est

        # ------------------------------------------------------------------
        # GRANDEZAS CINEMÁTICAS GLOBAIS
        # (baseadas no r_mean calculado acima)
        # ------------------------------------------------------------------

        # Velocidade periférica no raio médio aritmético
        self.U = self.omega * self.r_mean       # (m/s)

        # Velocidade axial constante: u_ax = φ·U
        self.u_ax = phi * self.U                   # (m/s)

        # Elevação de temperatura por estágio — Eq. (9-20) Mattingly
        # ψ = cp·ΔTt / U²  →  ΔTt = ψ·U² / cp
        self.delta_Tt_estagio = psi * self.U**2 / self.cp   # (K)

        # ------------------------------------------------------------------
        # NÚMERO DE ESTÁGIOS ESTIMADO
        # ------------------------------------------------------------------
        # Elevação total de temperatura no compressor: ΔTt_total = w_compr / cp
        self.delta_Tt_total = ciclo.w_compr / self.cp  # (K)

        # n_estimado = ΔTt_total / ΔTt_por_estágio
        self.n_estagios_estimado = self.delta_Tt_total / self.delta_Tt_estagio
        
        # ── Cálculo automático de n_estagios (caso não informado) ──
        # Inicialização provisória dos vetores; resolver() compara floor/ceil
        # com meanline, radial e perfis, redistribuindo o trabalho em cada caso.
        # O ψ solicitado é uma preferência, não um teto de carga garantido.
        
        if n_estagios is None:
            n_estagios = max(1, math.ceil(self.n_estagios_estimado))
            self.delta_Tt_estagio = self.delta_Tt_total / n_estagios  # divide exato
            self.psi_efetivo = self.delta_Tt_estagio * self.cp / self.U**2
            self.calculo_automatico = True
        else:
            self.psi_efetivo = psi
            self.calculo_automatico = False
            
        psi_para_checar = self.psi_efetivo if self.calculo_automatico else psi
        if not self.calculo_automatico and not (dc.PSI_COMP[0] <= psi_para_checar <= dc.PSI_COMP[1]):
            print(f"AVISO: ψ = {psi_para_checar:.3f} está fora da faixa típica [{dc.PSI_COMP[0]}, {dc.PSI_COMP[1]}].")

        self.n_estagios = n_estagios

        # ------------------------------------------------------------------
        # INICIALIZAÇÃO DOS RESULTADOS POR ESTÁGIO
        # ------------------------------------------------------------------
        n = n_estagios

        # Condições termodinâmicas
        self.Tt_entrada  = [None] * n   # Temperatura total de entrada (K)
        self.Pt_entrada  = [None] * n   # Pressão total de entrada (Pa)
        self.Tt_saida    = [None] * n   # Temperatura total de saída (K)
        self.Pt_saida    = [None] * n   # Pressão total de saída (Pa)
        self.pi_estagio  = [None] * n   # Razão de pressão por estágio

        # Triângulos de velocidade
        self.alpha1      = [None] * n   # Ângulo absoluto entrada rotor (°)
        self.alpha2      = [None] * n   # Ângulo absoluto saída rotor (°)
        self.beta1       = [None] * n   # Ângulo relativo entrada rotor (°)
        self.beta2       = [None] * n   # Ângulo relativo saída rotor (°)

        # Módulos das velocidades
        self.V1          = [None] * n   # Velocidade absoluta entrada rotor (m/s)
        self.V2          = [None] * n   # Velocidade absoluta saída rotor (m/s)
        self.W1          = [None] * n   # Velocidade relativa entrada rotor (m/s)
        self.W2          = [None] * n   # Velocidade relativa saída rotor (m/s)

        # Componentes tangenciais
        self.v1          = [None] * n
        self.v2          = [None] * n

        # Critérios aerodinâmicos
        self.M1          = [None] * n   # Mach absoluto entrada rotor
        self.M2          = [None] * n   # Mach absoluto saída rotor
        self.M1R         = [None] * n   # Mach relativo entrada rotor
        self.DF_rotor    = [None] * n   # Fator de difusão rotor   (as-built, Eq. 9-17)
        self.DF_estator  = [None] * n   # Fator de difusão estator (as-built, Eq. 9-18)
        self.grau_reacao = [None] * n   # Grau de reação por estágio

        # Geometria do anular por estágio
        self.A_estagio   = [None] * n   # Área do anular na entrada de cada estágio (m²)
        self.r_hub_est   = [None] * n   # Raio do cubo por estágio (m)
        self.r_tip_est   = [None] * n   # Raio da ponta por estágio (m)
        self.h_pa        = [None] * n   # Altura de pá por estágio (m)
        self.HTR_estagio = [None] * n   # HTR local; self.HTR continua sendo a entrada

        # Número de pás e corda por estágio
        self.corda_rotor   = [None] * n   # Corda do rotor por estágio (m)
        self.corda_estator = [None] * n   # Corda do estator por estágio (m)
        self.Z_rotor       = [None] * n   # Número de pás do rotor
        self.Z_estator     = [None] * n   # Número de pás do estator

        # Solidez — : alvo (teórico, via Lieblein) e as-built (pós-Z inteiro)
        self.sigma_rotor_alvo    = [None] * n
        self.sigma_estator_alvo  = [None] * n
        self.sigma_rotor         = [None] * n   # as-built — usada no DF final e no radial
        self.sigma_estator       = [None] * n   # as-built — usada no DF final e no radial

        # Resultado global
        self.pi_total_calc = None
    
    #___________________________________________________________________________
    # FUNÇÕES AUXILIARES
    #___________________________________________________________________________

    def _MFP(self, M: float) -> float:
        """
        Mass Flow Parameter — Eq. (9-8) Mattingly.
        MFP(M) = M · sqrt(k/R) · (1 + (k-1)/2 · M²)^(-(k+1)/(2(k-1)))
        Unidade: kg/(s·m²·Pa) · sqrt(K)  →  usado para calcular área do anular nas estações.
        """
        k, R = self.k, self.R
        exp = (k + 1) / (2 * (k - 1))
        return (M * math.sqrt(k / R)) / ((1 + ((k - 1) / 2) * M**2) ** exp)

    def _velocidade_som(self, Tt: float, M: float) -> float:
        """Velocidade do som estática a partir de Tt e M."""
        k, R = self.k, self.R
        T_est = Tt / (1 + (k - 1) / 2 * M**2)   # Temperatura Estática
        return math.sqrt(k * R * T_est)

    def _mach_de_velocidade(self, V: float, Tt: float) -> float:
        """
        Calcula M a partir de V e Tt.
        Encontrado fazendo a manipulação algébrica das seguintes fórmulas:
        V² = M²·k·R·T_est e T_est = Tt/(1+(k-1)/2·M²):
        M² = V² / (k·R·Tt - (k-1)/2·V²)
        """
        k, R = self.k, self.R
        denominador = k * R * Tt - (k - 1) / 2 * V**2
        if denominador <= 0:
            raise ValueError(
                f"V={V:.1f} m/s incompatível com Tt={Tt:.1f} K "
                f"(escoamento supersônico ou inválido)."
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

    def _solidez_de_lieblein(self,
                              DF_alvo: float,
                              V_entrada: float,
                              V_saida: float,
                              delta_C: float,
                              nome_fileira: str,
                              estagio: int) -> float:
        """
        Inverte a equação do Fator de Difusão de Lieblein para isolar a
        solidez (σ) necessária para atingir DF_alvo, dado o triângulo de
        velocidades já calculado da fileira (rotor ou estator).

        Equação direta (Mattingly Eq. 9-17/9-18; Saravanamuttoo Cap. 5):
            DF = 1 - V_saida/V_entrada + ΔC / (2·σ·V_entrada)

        Isolando σ:
            σ = ΔC / [2·V_entrada·(DF_alvo - 1 + V_saida/V_entrada)]
        
        delta_C é a variação da componente tangencial (swirl) da velocidade entre
        a entrada e a saída da fileira, ou seja, ΔC_θ. Ela mede quanto a pá desvia 
        o escoamento na direção circunferencial.

        Válido apenas se o denominador for positivo — caso contrário,
        DF_alvo é menor que a difusão mínima (V_saida/V_entrada) que
        ocorreria mesmo com solidez infinita, e o alvo é inatingível para
        aquele triângulo de velocidades.
        """
        razao_V = V_saida / V_entrada
        denom = DF_alvo - 1 + razao_V

        if denom <= 0:
            raise ValueError(
                f"Estágio {estagio} [{nome_fileira}]: DF_alvo = {DF_alvo:.3f} "
                f"é INATINGÍVEL para este triângulo de velocidades "
                f"(V_saida/V_entrada = {razao_V:.3f} já implica DF mínimo de "
                f"{1 - razao_V:.3f}, mesmo com solidez infinita). "
                f"Aumente DF_alvo ou revise φ/ψ para reduzir a difusão exigida."
            )

        return abs(delta_C) / (2 * V_entrada * denom)

    #___________________________________________________________________________
    # MÉTODO PRINCIPAL
    #___________________________________________________________________________

    @erros_numericos('CompressorMeanline.resolver')
    def resolver(self) -> None:
        """
        Resolve o meanline 1D do compressor axial multiestágio.

        Para cada estágio:
          1. Condições de entrada (Tt, Pt)
          2. Triângulo de velocidades na entrada do rotor (estação 1)
          3. Equação de Euler → ΔTt, v2
          4. Triângulo de velocidades na saída do rotor (estação 2)
          5. Razão de pressão via eficiência politrópica
          6. Números de Mach (M1, M1R, M2)
          7. Solidez alvo de rotor e estator via inversão do critério
             de Lieblein (DF_alvo especificado pelo usuário)
          8. Área do anular e geometria (r_hub, r_tip) — Eq. (9-8)
          9. Número de pás — usa a solidez alvo do passo 7
         10. Solidez as-built (pós-arredondamento de Z para inteiro)
         11. Fator de difusão as-built — recalculado com σ_as-built
         12. Grau de reação
         13. Verificações de viabilidade (via aero/constraints.py)
        """
        validar_maquina(self.N, self.HTR, self.phi, self.psi, self.AR,
                        self.n_estagios, self.n_secoes_avaliacao, self.alpha1_graus, 'alpha1_graus')
        positivo('DF_alvo', self.DF_alvo)
        if self.calculo_automatico:
            from engine.stage_selection import selecionar_estagios
            selecionar_estagios(self, "Compressor")
            return
        cp, k = self.cp, self.k
        U    = self.U
        u_ax = self.u_ax
        exp_politropico = (k - 1) / (k * self.e_c)
        a1_rad = math.radians(self.alpha1_graus)    # (Para estágios repetitivos, alpha1 é igual em todos os estágios)
        DF_alvo = self.DF_alvo

        Tt_in = self.T01_comp
        Pt_in = self.P01_comp

        avisos = [] # acumula avisos de viabilidade

        for i in range(self.n_estagios):

            # ==================================================================
            # ESTAÇÃO 1 — ENTRADA DO ROTOR
            # ==================================================================
            self.Tt_entrada[i] = Tt_in
            self.Pt_entrada[i] = Pt_in

            # Componente tangencial e velocidade absoluta de entrada
            v1 = u_ax * math.tan(a1_rad)    # v1 = u_ax · tan(α1)
            V1 = math.sqrt(u_ax**2 + v1**2)

            # Velocidade relativa de entrada: W1 = V1 - U (vetorial, tangencial)
            # Componente tangencial relativa: w1_tang = v1 - U
            w1_tang = v1 - U                        # (m/s)
            W1 = math.sqrt(u_ax**2 + w1_tang**2)    # (m/s)

            # Ângulo relativo de entrada
            # tan(β1) = w1_tang / u_ax  (convenção: positivo no sentido de U)
            beta1_rad = math.atan2(-w1_tang, u_ax)  # (rad)

            # ==================================================================
            # EQUAÇÃO DE EULER — Eq. (9-7a) Mattingly
            # cp·ΔTt = U·(v2 - v1)  →  v2 = ΔTt·cp/U + v1
            # ==================================================================
            delta_Tt = self.delta_Tt_estagio
            v2 = delta_Tt * cp / U + v1

            # ==================================================================
            # ESTAÇÃO 2 — SAÍDA DO ROTOR
            # ==================================================================
            Tt_out = Tt_in + delta_Tt                       # (K)

            # Velocidade absoluta de saída do rotor
            V2  = math.sqrt(u_ax**2 + v2**2)                # (m/s)

            # Ângulo absoluto de saída do rotor
            alpha2_rad = math.atan2(v2, u_ax)               # (rad)

            # Velocidade relativa de saída
            w2_tang = v2 - U                                # (m/s)
            W2 = math.sqrt(u_ax**2 + w2_tang**2)            # (m/s)

            # Ângulo relativo de saída
            beta2_rad = math.atan2(-w2_tang, u_ax)          # (rad)

            # ==================================================================
            # RAZÃO DE PRESSÃO DO ESTÁGIO
            # π_s = τ_s^(1/exp_politropico)   com   τ_s = Tt_out/Tt_in  (Eq. 6-14 — Mattingly)
            # ==================================================================
            tau_s  = Tt_out / Tt_in
            pi_s   = tau_s ** (1.0 / exp_politropico)
            Pt_out = Pt_in * pi_s

            # ==================================================================
            # NÚMEROS DE MACH
            # ==================================================================
            M1  = self._mach_de_velocidade(V1, Tt_in)   # Mach absoluto entrada do rotor
            M1R = self._mach_relativo(W1, V1, Tt_in)   # Mach relativo entrada do rotor
            M2  = self._mach_de_velocidade(V2, Tt_out)  # Mach absoluto saída do rotor = entrada do estator

            # ==================================================================
            # SOLIDEZ ALVO — INVERSÃO DO CRITÉRIO DE LIEBLEIN 
            #
            # Rotor:   ΔC = w1_tang - w2_tang   (variação da componente
            #          tangencial relativa através do rotor)
            # Estator: ΔC = v2 - v3, com v3 = v1 (estágio repetitivo)
            #
            # A solidez é calculada ANTES da geometria/número de pás porque
            # depende apenas do triângulo de velocidades (V1, V2, ΔC), não
            # da área do anular ou da corda.
            # ==================================================================
            sigma_rotor_alvo = self._solidez_de_lieblein(
                DF_alvo=DF_alvo,
                V_entrada=W1, V_saida=W2,
                delta_C=(w1_tang - w2_tang),
                nome_fileira="rotor", estagio=i + 1,
            )

            # Estator: estágio repetitivo → V3 = V1, v3 = v1
            V3 = V1
            v3 = v1
            sigma_estator_alvo = self._solidez_de_lieblein(
                DF_alvo=DF_alvo,
                V_entrada=V2, V_saida=V3,
                delta_C=(v2 - v3),
                nome_fileira="estator", estagio=i + 1,
            )

            # ==================================================================
            # ÁREA DO ANULAR — Eq. (9-8) Mattingly
            # A_i = ṁ·sqrt(Tt_in) / (Pt_in · cos(α1) · MFP(M1))
            # Raio médio aritmético fixo: A = 2π·r_mean·h.
            # HTR prescreve somente a geometria de entrada.
            #
            # (Independe da solidez — mantido na mesma posição do fluxo original)
            # ==================================================================
            A_i = (self.m_dot * math.sqrt(Tt_in) / (Pt_in * math.cos(a1_rad) * self._MFP(M1)))

            r_hub_i, r_tip_i, h_i = raios_anular(
                A_i, self.r_mean, contexto=f"Compressor estágio {i + 1}",
            )
            r_mean_i = self.r_mean

            # ==================================================================
            # NÚMERO DE PÁS — Z = 2π·r_mean·σ_alvo / c   com c = h_pá / AR
            # Usa a solidez ALVO (teórica) calculada acima.
            # ==================================================================
            c_rotor   = h_i / self.AR                            # corda rotor (m)
            c_estator = h_i / self.AR                            # corda estator (m)
            Z_rotor_i   = max(1, round(2 * math.pi * r_mean_i * sigma_rotor_alvo   / c_rotor))
            Z_estator_i = max(1, round(2 * math.pi * r_mean_i * sigma_estator_alvo / c_estator))

            # ==================================================================
            # SOLIDEZ AS-BUILT
            # Como Z precisa ser inteiro, a solidez real ("as-built") difere
            # ligeiramente da teórica. Recalculada a partir do Z arredondado:
            #   σ_as-built = Z·c / (2π·r_mean)
            # ==================================================================
            sigma_rotor_asbuilt   = Z_rotor_i   * c_rotor   / (2 * math.pi * r_mean_i)
            sigma_estator_asbuilt = Z_estator_i * c_estator / (2 * math.pi * r_mean_i)

            # ==================================================================
            # FATOR DE DIFUSÃO AS-BUILT
            # Recalculado com a solidez as-built — este é o DF real do
            # projeto final (pós-arredondamento de pás), e é o valor
            # armazenado e verificado por aero/constraints.py.
            # Eqs. (9-17) e (9-18) Mattingly:
            #   DF_rotor  = 1 - W2/W1 + |w1_tang - w2_tang| / (2·σ_rotor·W1)
            #   DF_estator = 1 - V3/V2 + |v2 - v3| / (2·σ_estator·V2)
            # ==================================================================
            DF_rotor   = (1 - W2/W1
                          + abs(w1_tang - w2_tang) / (2 * sigma_rotor_asbuilt * W1))

            DF_estator = (1 - V3/V2
                          + abs(v2 - v3) / (2 * sigma_estator_asbuilt * V2))

            # ==================================================================
            # GRAU DE REAÇÃO — Dixon & Hall
            # R = 1 - (v1 + v2) / (2·U)
            # ==================================================================
            grau_reacao = 1 - (v1 + v2) / (2 * U)

            # ==================================================================
            # VERIFICAÇÕES DE VIABILIDADE — via aero/constraints.py
            # ==================================================================
            avisos.extend(
                checar_estagio_compressor_meanline(
                    DF_rotor=DF_rotor, DF_estator=DF_estator,
                    grau_reacao=grau_reacao, M1R=M1R, estagio=i + 1,
                )
            )

            # ==================================================================
            # ARMAZENAMENTO
            # ==================================================================
            self.A_estagio[i]   = A_i
            self.r_hub_est[i]   = r_hub_i
            self.r_tip_est[i]   = r_tip_i
            self.h_pa[i]        = h_i
            self.HTR_estagio[i] = r_hub_i / r_tip_i
            self.corda_rotor[i]   = c_rotor
            self.corda_estator[i] = c_estator
            self.Z_rotor[i]       = Z_rotor_i
            self.Z_estator[i]     = Z_estator_i
            self.sigma_rotor_alvo[i]   = sigma_rotor_alvo
            self.sigma_estator_alvo[i] = sigma_estator_alvo
            self.sigma_rotor[i]        = sigma_rotor_asbuilt
            self.sigma_estator[i]      = sigma_estator_asbuilt
            self.v1[i]          = v1
            self.v2[i]          = v2
            self.V1[i]          = V1
            self.V2[i]          = V2
            self.W1[i]          = W1
            self.W2[i]          = W2
            self.alpha1[i]      = math.degrees(a1_rad)
            self.alpha2[i]      = math.degrees(alpha2_rad)
            self.beta1[i]       = math.degrees(beta1_rad)
            self.beta2[i]       = math.degrees(beta2_rad)
            self.Tt_saida[i]    = Tt_out
            self.Pt_saida[i]    = Pt_out
            self.pi_estagio[i]  = pi_s
            self.M1[i]          = M1
            self.M1R[i]         = M1R
            self.M2[i]          = M2
            self.DF_rotor[i]    = DF_rotor
            self.DF_estator[i]  = DF_estator
            self.grau_reacao[i] = grau_reacao

            Tt_in = Tt_out
            Pt_in = Pt_out

        # Razão de pressão total calculada (produto das razões por estágio)
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
        # Compara saída calculada com valores alvo do ciclo
        # ==================================================================
        erro_T = abs(self.Tt_saida[-1] - self.T02r_alvo) / self.T02r_alvo * 100
        erro_P = abs(self.pi_total_calc - self.r_compr) / self.r_compr * 100

        if erro_T > dc.FECHAMENTO_AVISO_PCT:
            print(
                f"\n  AVISO: Tt saída calculada ({self.Tt_saida[-1]:.1f} K) "
                f"difere {erro_T:.1f}% do alvo do ciclo ({self.T02r_alvo:.1f} K)."
            )
        if erro_P > dc.FECHAMENTO_AVISO_PCT:
            print(
                f"\n  AVISO: π_total calculado ({self.pi_total_calc:.3f}) "
                f"difere {erro_P:.1f}% do alvo do ciclo ({self.r_compr:.1f}). "
                f"Revise n_estagios, φ ou ψ."
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
        print("  COMPRESSOR AXIAL — RESULTADOS MEANLINE")
        linha()
        print(f"  N = {self.N:.0f} rpm  │  HTR entrada = {self.HTR:.3f}  │  "
              f"r_mean = {self.r_mean*100:.2f} cm")
        print(f"  r_hub = {self.r_hub_entrada*100:.2f} cm  │  "
              f"r_tip = {self.r_tip_entrada*100:.2f} cm  │  "
              f"A_entrada = {self.A_entrada*1e4:.2f} cm²")
        print(f"  U = {self.U:.2f} m/s  │  u_ax = {self.u_ax:.2f} m/s  │  "
              f"φ = {self.phi:.3f}  │  ψ = {self.psi:.3f}")
        print(f"  DF_alvo (Lieblein) = {self.DF_alvo:.3f}  │  "
              f"solidez DERIVADA do DF_alvo (ver σ por estágio abaixo)")
        print(f"  π_total calculado = {self.pi_total_calc:.4f}  │  "
              f"π_total ciclo = {self.r_compr:.1f}")
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
            print(f"    α₁ = {self.alpha1[i]:6.2f}°  │  β₁ = {self.beta1[i]:6.2f}°  │  "
                  f"V1 = {self.V1[i]:7.2f} m/s  │  W1 = {self.W1[i]:7.2f} m/s")
            print(f"    α₂ = {self.alpha2[i]:6.2f}°  │  β₂ = {self.beta2[i]:6.2f}°  │  "
                  f"V2 = {self.V2[i]:7.2f} m/s  │  W2 = {self.W2[i]:7.2f} m/s")
            print(f"    M1 = {self.M1[i]:.4f}  │  M1R = {self.M1R[i]:.4f}  │  "
                  f"M2 = {self.M2[i]:.4f}")
            print(f"    DF_rotor = {self.DF_rotor[i]:.4f}  │  "
                  f"DF_estator = {self.DF_estator[i]:.4f}  │  "
                  f"Grau reação = {self.grau_reacao[i]:.4f}")
            print(f"    A = {self.A_estagio[i]*1e4:7.2f} cm²  │  "
                  f"h_pá = {self.h_pa[i]*100:6.3f} cm  │  "
                  f"r_hub = {self.r_hub_est[i]*100:6.3f} cm  │  "
                  f"r_tip = {self.r_tip_est[i]*100:6.3f} cm")
            print(f"    Rotor:   c = {self.corda_rotor[i]*100:5.3f} cm  │  "
                  f"Z = {self.Z_rotor[i]:3d} pás  │  "
                  f"σ_alvo = {self.sigma_rotor_alvo[i]:.4f}  │  "
                  f"σ_as-built = {self.sigma_rotor[i]:.4f}")
            print(f"    Estator: c = {self.corda_estator[i]*100:5.3f} cm  │  "
                  f"Z = {self.Z_estator[i]:3d} pás  │  "
                  f"σ_alvo = {self.sigma_estator_alvo[i]:.4f}  │  "
                  f"σ_as-built = {self.sigma_estator[i]:.4f}")
        linha()

    #___________________________________________________________________________
    # MÉTODOS AUXILIARES
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
def criar_compressor_exemplo():
    """Cria e resolve o exemplo automático, sem estado global compartilhado."""
    from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
    ciclo1 = criar_ciclo_exemplo()
    compr1 = CompressorMeanline(
            ciclo        = ciclo1,
            N            = 14000,
            HTR          = 0.75,
            phi          = 0.50,
            psi          = 0.35,
            n_estagios   = None,
            alpha1_graus = 30.0,
            DF_alvo      = 0.45,
            AR           = 2.0,
        )

    compr1.resolver()
    return compr1


if __name__ == "__main__":
    from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
    ciclo1 = criar_ciclo_exemplo()

    ciclo_teste = ciclo1

    comp = CompressorMeanline(
        ciclo        = ciclo1,
        N            = 14000,
        HTR          = 0.75,
        n_estagios   = 8,
        phi          = 0.50,
        psi          = 0.35,
        alpha1_graus = 30.0,
        DF_alvo      = 0.45,
        AR           = 2.0,
    )

    print(f"r_tip entrada  = {comp.r_tip_entrada*100:.3f} cm")
    print(f"r_hub entrada  = {comp.r_hub_entrada*100:.3f} cm")
    print(f"r_mean         = {comp.r_mean*100:.3f} cm")
    print(f"A_entrada      = {comp.A_entrada*1e4:.2f} cm²")
    print(f"U              = {comp.U:.2f} m/s")
    print(f"u_ax           = {comp.u_ax:.2f} m/s")
    print(f"ΔTt/estágio    = {comp.delta_Tt_estagio:.2f} K")
    print(f"ΔTt total      = {comp.delta_Tt_total:.2f} K")
    comp.n_estagios_estimado_info()
    print()
    comp.resolver()
    comp.mostrar_resultados()


# ══════════════════════════════════════════════════════════════════════════
# CASOS HISTÓRICOS DE ESTABILIDADE E USO (PRÉ-REFATORAÇÃO)
#
# Os casos comentados abaixo foram testados ANTES da introdução de DF_alvo,
# quando σ era um parâmetro fixo de entrada (sigma=1.0 etc.). Eles NÃO são
# executáveis diretamente nesta versão (o construtor não aceita mais o
# argumento `sigma`). Mantidos apenas como registro histórico do processo
# de tentativa e erro documentado no TCC (seção de Discussão / sensibilidade
# a φ e ψ). Para reproduzir intenções equivalentes, substitua sigma=1.0 por
# um DF_alvo próximo de 0.50 (valor que, empiricamente, produzia DF≈0.49-0.50
# com σ=1.0 nesses casos).
# ══════════════════════════════════════════════════════════════════════════

# DICA: Se vc quer diminuir phi, diminua HTR e ajuste com psi.

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.6,
#         n_estagios   = 8,
#         phi          = 0.50,
#         psi          = 0.43,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.75,
#         n_estagios   = 8,
#         phi          = 0.68,
#         psi          = 0.32,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.70,
#         n_estagios   = 8,
#         phi          = 0.65,
#         psi          = 0.38,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.69,
#         n_estagios   = 8,
#         phi          = 0.47,
#         psi          = 0.335,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.65,
#         n_estagios   = 8,
#         phi          = 0.42,
#         psi          = 0.35,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.67,
#         n_estagios   = 8,
#         phi          = 0.44,
#         psi          = 0.34,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.65,
#         n_estagios   = 8,
#         phi          = 0.40,
#         psi          = 0.34,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 16000,
#         HTR          = 0.69,
#         n_estagios   = 8,
#         phi          = 0.55,
#         psi          = 0.36,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# compr1 = CompressorMeanline(
#         ciclo        = ciclo1,
#         N            = 15000,
#         HTR          = 0.69,
#         n_estagios   = 8,
#         phi          = 0.48,
#         psi          = 0.37,
#         alpha1_graus = 30.0,
#         sigma        = 1.0,
#         AR           = 2.0,
#     )

# ══════════════════════════════════════════════════════════════════════════
# Exemplo automático atual: criar_compressor_exemplo(), definido acima.
# ══════════════════════════════════════════════════════════════════════════
