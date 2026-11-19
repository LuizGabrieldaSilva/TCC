from engine import design_criteria as dc
from engine.aero.constraints import checar_combustor
from engine.input_validation import verificar_ciclo_resolvido, positivo, intervalo, real_finito, erros_numericos
#______________________________________________________________________________________________________________
# Modelo 1D Simplificado da Câmara de Combustão.
# Recebe um objeto CicloBrayton já resolvido e calcula:
#   - Balanço energético: razão combustível/ar (f) e vazões
#   - Razão de equivalência (φ_eq)
#   - Verificação do Mach de entrada
#   - Área transversal e comprimento estimado da câmara
#   - Queda de pressão total (já modelada no CicloBrayton via Delta_P_cc)
#
# Hipóteses:
#   - Gases ideais caloricamente perfeitos, cp_ar e cp_gases constantes por região
#   - Combustão completa (η_b = eficiência de combustão)
#   - O balanço que obtém f INCLUI a massa de combustível na saída.
#     Q_total é somente o indicador de aquecimento virtual do AR:
#     ṁ_ar · cp_ar · (TIT - T02r), sem mudança de fluido nem massa de fuel.
#     Calor do balanço: ṁ_total·h_gases(TIT) − ṁ_ar·h_ar(T02r).
#   - Automático: entalpias sensíveis relativas a 298,15 K, composição completa
#     congelada e cp equivalente constante. Prescrito: mantém h=cp*T legado.
#     Sem entalpia sensível do combustível, equilíbrio, dissociação ou cinética.
#   - Escoamento na entrada do combustor aproximadamente axial
#
# Referências:
#   - Mattingly, Cap. 6 (Eq. 6-36) e Cap. 10 (Seção 10-6 a 10-7)
#   - Razão f: Eq. (7-9) — Mattingly
#   - Comprimento: Eq. (10-34) — Mattingly
#______________________________________________________________________________________________________________

import math
from copy import deepcopy
from engine.combustor.mistura_gases import COMBUSTIVEIS

# Poderes caloríficos de combustíveis comuns (J/kg)
# Valores nominais preservados. As fontes/hipóteses de CADA propriedade
# estão em FONTES_COMBUSTIVEIS. A tabela 2-4 de Mattingly NÃO é tabela de PCI.
# Razão estequiométrica combustível/ar para combustíveis comuns
# f_stoich = massa de combustível / massa de ar para combustão completa
F_STOICH = {
    "JP-4"        : 0.0667,
    "JP-8"        : 0.0667,
    "gas_natural" : 0.0580,
    "diesel"      : 0.0664,
}

# Rastreabilidade por propriedade, sem atribuir dados não confirmados ao livro.
# "adotado" é uma hipótese do projeto, não uma propriedade certificada de lote.
FONTES_COMBUSTIVEIS = {
    "JP-4": {
        "h_PR": {
            "status": "Publicado em exemplo",
            "origem": "Mattingly, Elements of Gas Turbine Propulsion, p. 816 (PDF 881).",
            "hipotese": "O exemplo usa h_PR = 42.800 kJ/kg. Valor nominal do modelo; não caracteriza qualquer lote de JP-4.",
        },
        "f_stoich": {
            "status": "Publicado em exemplo",
            "origem": "Mattingly, p. 816 (PDF 881), exemplo com JP-4 e Eq. 10-27.",
            "hipotese": "O exemplo informa f_stoich = 0,0667 kg de combustível/kg de ar.",
        },
    },
    "JP-8": {
        "h_PR": {
            "status": "Nominal compatível com tabela",
            "origem": "Mattingly, tabela 10-6, p. 826 (PDF 891), coluna de valor típico de JP-8 (Jet A-1).",
            "hipotese": "A tabela informa 10.333 cal/g. Com 1 cal = 4,184 J: 43,233272 MJ/kg; o modelo mantém 43,2 MJ/kg arredondados. Não é o mínimo da especificação.",
        },
        "f_stoich": {
            "status": "Hipótese do projeto",
            "origem": "Aproximação adotada: mesmo f_stoich do JP-4 usado por Mattingly, p. 816.",
            "hipotese": "0,0667 não foi confirmado como valor específico de JP-8 nessa tabela; composição real não é modelada.",
        },
    },
    "gas_natural": {
        "h_PR": {
            "status": "Fonte específica pendente",
            "origem": "Valor nominal já adotado no projeto: 50,0 MJ/kg.",
            "hipotese": "Representação de gás predominantemente metano. A composição do gás natural varia; não foi confirmada uma fonte específica para este número nos trechos consultados.",
        },
        "f_stoich": {
            "status": "Hipótese de composição",
            "origem": "Modelo de metano com massas molares aproximadas: CH4 + 2 O2 → CO2 + 2 H2O; fração mássica de O2 no ar adotada como 0,232.",
            "hipotese": "Requer 4 kg O2/kg CH4; f_stoich = 0,232/4 = 0,0580. Não é cálculo para uma composição real de gás natural.",
        },
    },
    "diesel": {
        "h_PR": {
            "status": "Fonte específica pendente",
            "origem": "Valor nominal já adotado no projeto: 42,5 MJ/kg.",
            "hipotese": "Sem composição ou lote definido e sem fonte específica confirmada. Não atribuir à tabela 2-4 de Mattingly.",
        },
        "f_stoich": {
            "status": "Fonte específica pendente",
            "origem": "Valor nominal já adotado no projeto: 0,0664 kg/kg.",
            "hipotese": "Sem composição química definida para reproduzir a estequiometria. Usado como parâmetro adotado, não como valor bibliográfico validado.",
        },
    },
}

# ------------------------------------------------------------------------
# REFERÊNCIA PARA ESTIMATIVA DE COMPRIMENTO — Eq. (10-34) Mattingly
# Combustor de referência: JT9D (Tabela 10-5, Mattingly, p. 822)
# L ∝ P_t3^(-r) / sqrt(T_t4),  com r = 0.714 (n = 1)
# ------------------------------------------------------------------------
COMBUSTOR_REF = {
    "nome"   : "JT9D (Mattingly, Tabela 10-5)",
    "L_ref"  : 0.4394,      # Comprimento de referência (m) — 17.3 in
    "Pt3_ref": 2179.0e3,    # ENTRADA do combustor no livro; equivale a P02 aqui (316 psia, aprox.)
    "Tt4_ref": 1592.0,      # Temperatura de referência (K) — 2865 °R
    "r_exp"  : 0.714,       # Expoente da Eq. (10-34) para n = 1
}


class Combustor1D:
    """
    PARÂMETROS DE ENTRADA:

    ciclo           - Objeto CicloBrayton já resolvido (com m_dot definido)
    combustivel     - Tipo de combustível: "JP-4", "JP-8", "gas_natural", "diesel"
                      (define h_PR e f_stoich automaticamente; fontes por
                      propriedade em fontes_combustivel())
                      
    eta_b           - Eficiência de combustão (adimensional)
                      Faixa típica: 0.95–0.99
                      
    h_PR            - Poder calorífico do combustível (J/kg)
                      Se fornecido, sobrescreve o valor padrão do combustivel
                      
    M_entrada       - Mach axial prescrito na entrada, não na zona primária.
                      Mattingly p. 823 discute M < 0.10 no contexto de
                      baixa perda de pressão; não é limite universal.

    TEORIA — BALANÇO ENERGÉTICO (Eq. 7-9, Mattingly):
    ────────────────────────────────────────────────────
    O balanço de energia entre entrada e saída do combustor:

        ṁ_ar · cp_ar · T02r + ṁ_f · h_PR · η_b = (ṁ_ar + ṁ_f) · cp_gases · TIT

    Dividindo por ṁ_ar e definindo f = ṁ_f / ṁ_ar:

        cp_ar · T02r + f · h_PR · η_b = (1 + f) · cp_gases · TIT

    Isolando f:

        f = (cp_gases · TIT - cp_ar · T02r) / (h_PR · η_b - cp_gases · TIT)

    TEORIA — RAZÃO DE EQUIVALÊNCIA (Eq. 10-27, Mattingly):
    ─────────────────────────────────────────────────────────
        φ_eq = f / f_stoich

    φ_eq < 1.0: mistura pobre (lean) — condição típica de operação
    φ_eq > 1.0: mistura rica (rich) — risco de fuligem e alta temperatura
    Faixas de triagem do projeto ficam em constraints.py. A razão global
    não determina sozinha a estabilidade da chama ou a mistura da zona primária.

    TEORIA — QUEDA DE PRESSÃO TOTAL:
    ──────────────────────────────────
    Já modelada no CicloBrayton via Delta_P_cc (queda relativa).
    Aqui verificamos o Mach de entrada, que deve ser baixo (M < 0.10)
    para minimizar a perda de pressão por arrasto interno.
    """

    @erros_numericos('Combustor1D')
    def __init__(self,
                 ciclo,
                 combustivel: str = "JP-4",
                 eta_b: float = 0.99,
                 h_PR: float = None,
                 M_entrada: float = 0.05,
                 ):

        verificar_ciclo_resolvido(ciclo)
        # ------------------------------------------------------------------
        # VERIFICAÇÃO DO OBJETO CICLO
        # ------------------------------------------------------------------
        if ciclo.w_líq is None:
            raise RuntimeError(
                "O objeto CicloBrayton deve ter resolver() chamado antes "
                "de ser passado ao Combustor1D."
            )
        if ciclo.m_dot is None:
            raise RuntimeError(
                "A vazão mássica do ciclo não foi definida. "
                "Chame vazão_mássica_desejada() ou potência_líquida_desejada() "
                "antes de instanciar o Combustor1D."
            )
        if not isinstance(combustivel, str) or combustivel not in COMBUSTIVEIS:
            raise ValueError(
                f"Combustível '{combustivel}' não reconhecido. "
                f"Opções: {list(COMBUSTIVEIS.keys())}"
            )

        if hasattr(ciclo,'preparar_mistura'):ciclo.preparar_mistura(combustivel,eta_b,h_PR)
        self.dados_mistura = getattr(ciclo,'dados_mistura',None)
        self.T_ref_entalpia = getattr(ciclo,'T_ref_entalpia',0.)

        # ------------------------------------------------------------------
        # PARÂMETROS HERDADOS DO CICLO
        # ------------------------------------------------------------------
        # O combustor recebe o ar na saída do compressor (Estado 2)
        # e entrega gases quentes à turbina (Estado 3 = TIT, P03)

        self.T02r      = ciclo.T02r     # Temperatura total de entrada (K)
        self.P02       = ciclo.P02      # Pressão total de entrada (Pa)
        self.TIT       = ciclo.TIT      # Temperatura total de saída = TIT (K)
        self.P03       = ciclo.P03      # Pressão total de saída (Pa)
        self.Delta_P   = ciclo.Delta_P_cc  # Queda relativa de pressão (-)
        self.m_dot_ar  = ciclo.m_dot    # Vazão mássica de ar (kg/s)
        self.cp        = ciclo.cp       # Calor específico do ar (J/kg·K)
        self.k         = ciclo.k        # Razão de calores específicos
        self.cp_ar     = ciclo.cp_ar
        self.cp_gases  = ciclo.cp_gases
        self.k_gases   = ciclo.k_gases
        self.R_gases   = ciclo.R_gases
        self.R         = self.cp * (1 - 1/self.k)  # Constante do gás (J/kg·K)

        # ------------------------------------------------------------------
        # PARÂMETROS DE ENTRADA DO COMBUSTOR
        # ------------------------------------------------------------------
        self.combustivel = combustivel
        self.eta_b       = eta_b
        self.h_PR        = h_PR if h_PR is not None else COMBUSTIVEIS[combustivel]
        self._h_PR_fornecido = h_PR is not None
        self.f_stoich    = F_STOICH[combustivel]
        if self.dados_mistura is not None:
            self.f_stoich = self.dados_mistura['f_stoich']
        self.M_entrada   = M_entrada
        self._resolvido = False
        self._validar_entradas()

        # ------------------------------------------------------------------
        # VERIFICAÇÕES DE ENTRADA
        # ------------------------------------------------------------------
        if not (dc.ETA_COMBUSTOR[0] <= eta_b <= dc.ETA_COMBUSTOR[1]):
            print(f"AVISO: η_b = {eta_b:.3f} está fora da faixa típica [{dc.ETA_COMBUSTOR[0]:.2f}, {dc.ETA_COMBUSTOR[1]:.2f}].")
        if not (0 < M_entrada < 1):
            raise ValueError(
                f"M_entrada = {M_entrada:.3f} inválido. "
                "O número de Mach deve estar entre 0 e 1 (escoamento subsônico)."
            )
        if M_entrada > dc.MACH_ENTRADA_COMBUSTOR_AVISO:
            print(
                f"AVISO: M_entrada = {M_entrada:.3f} > {dc.MACH_ENTRADA_COMBUSTOR_AVISO:.2f} — "
                f"Mach alto na entrada do combustor aumenta a perda de pressão "
                f"(Mattingly, p. 823)."
            )

        # ------------------------------------------------------------------
        # INICIALIZAÇÃO DOS RESULTADOS
        # ------------------------------------------------------------------
        self.f          = None   # Razão combustível/ar (kg_f / kg_ar)
        self.phi_eq     = None   # Razão de equivalência φ_eq = f / f_stoich
        self.m_dot_f    = None   # Vazão mássica de combustível (kg/s)
        self.m_dot_tot  = None   # Vazão mássica total = ar + combustível (kg/s)
        self.Q_total    = None   # Aumento aproximado de entalpia do ar (W), não calor útil total
        self.A_comb     = None   # Área transversal do combustor (m²)
        self.D_comb     = None   # Diâmetro equivalente (m)
        self.L_comb     = None   # Comprimento estimado do combustor (m)
        self.delta_Tt   = None   # Elevação de temperatura total (K)
        self.P_entrada  = None   # Pressão de entrada (= P02)
        self.P_saida    = None   # Pressão de saída (= P03)
        self.avisos     = []

    #___________________________________________________________________________
    # MÉTODO PRINCIPAL
    #___________________________________________________________________________

    def _validar_entradas(self):
        for nome in ('T02r', 'P02', 'TIT', 'P03', 'm_dot_ar', 'cp', 'h_PR', 'f_stoich'):
            positivo(nome, getattr(self, nome))
        intervalo('eta_b', self.eta_b, 0., 1., incluir_minimo=False)
        intervalo('M_entrada', self.M_entrada, 0., 1., incluir_minimo=False, incluir_maximo=False)
        real_finito('k', self.k)
        if self.k <= 1:
            raise ValueError('k deve ser maior que 1.')
        if self.TIT <= self.T02r:
            raise ValueError('TIT deve ser maior que T02r no combustor com adição positiva de calor.')

    @erros_numericos('Combustor1D.resolver')
    def resolver(self) -> None:
        """
        Resolve o balanço energético e geométrico do combustor 1D.

        SEQUÊNCIA DE CÁLCULO:
        1. Balanço energético → razão f e vazões
        2. Razão de equivalência φ_eq
        3. Calor total adicionado Q_total
        4. Área transversal via Eq. (9-8) adaptada para o combustor
        5. Verificações de viabilidade
        """
        self._resolvido = False
        self.f = None
        self._validar_entradas()
        cp  = self.cp
        k   = self.k
        R   = self.R

        avisos = []

        # ==================================================================
        # 1. BALANÇO ENERGÉTICO — Razão combustível/ar
        # Eq. (7-9) — Mattingly
        #
        # Derivação:
        #   h_ar(T02r) + f·h_PR·η_b = (1 + f)·h_gases(TIT)
        #   f = (h_gases(TIT) - h_ar(T02r)) / (h_PR·η_b - h_gases(TIT))
        #   h_j=cp_j*(T-T_ref); T_ref=298,15 K automático, zero prescrito.
        # No automático, cp_gases já veio da solução conjunta de composição/f.
        # ==================================================================
        numerador   = self.cp_gases * (self.TIT-self.T_ref_entalpia) - self.cp_ar * (self.T02r-self.T_ref_entalpia)
        denominador = self.h_PR * self.eta_b - self.cp_gases * (self.TIT-self.T_ref_entalpia)
        real_finito('Numerador do balanço de combustível', numerador)
        real_finito('Denominador do balanço de combustível', denominador)

        if denominador <= 0:
            raise ValueError(
                f"Balanço energético inviável: h_PR·η_b ({self.h_PR*self.eta_b/1e6:.2f} MJ/kg) "
                f"≤ h_gases(TIT) ({self.cp_gases*(self.TIT-self.T_ref_entalpia)/1e6:.2f} MJ/kg). "
                f"Aumente h_PR ou reduza TIT."
            )

        self.f = numerador / denominador
        positivo('Razão combustível/ar calculada', self.f)

        # ==================================================================
        # 2. VAZÕES MÁSSICAS
        # ṁ_f = f · ṁ_ar
        # ṁ_total = ṁ_ar + ṁ_f = ṁ_ar · (1 + f)
        # ==================================================================
        self.m_dot_f   = self.f * self.m_dot_ar        # (kg/s)
        self.m_dot_tot = self.m_dot_ar + self.m_dot_f  # (kg/s)

        # ==================================================================
        # 3. RAZÃO DE EQUIVALÊNCIA — Eq. (10-27) Mattingly
        # φ_eq = f / f_stoich
        # φ_eq < 1.0: mistura pobre (lean) — condição típica de operação
        # φ_eq > 1.0: mistura rica (rich) — risco de fuligem e alta temperatura
        # Faixa típica de operação: φ_eq ∈ [0.2, 0.7]
        # (limite inferior ajustado de 0.3 para 0.2 para refletir TIT moderado,
        # ~1200 K — comparado ao exemplo de Mattingly com TIT=1670K → φ_eq=0.519,
        # turbinas de TIT mais baixo operam naturalmente com φ_eq menor)
        # ==================================================================
        self.phi_eq = self.f / self.f_stoich

        # ==================================================================
        # 4. CALOR TOTAL ADICIONADO
        # Balanço: Q = ṁ_total·h_gases(TIT) - ṁ_ar·h_ar(T02r)
        # Indicador auxiliar: Q_total = ṁ_ar·cp_ar·(TIT - T02r)
        #
        # Q_total é mantido por compatibilidade como aquecimento VIRTUAL de ar.
        # Com cp distintos, omite também a mudança de propriedades; não é
        # o calor útil nem uma aproximação que ignore somente a massa de fuel.
        # h=cp*(T-T_ref); T_ref=298,15 K no automático e zero no prescrito legado.
        self.Q_total  = self.m_dot_ar * cp * (self.TIT - self.T02r)   # (W)
        self.delta_Tt = self.TIT - self.T02r                           # (K)

        # ==================================================================
        # 5. PRESSÕES DE ENTRADA E SAÍDA
        # ==================================================================
        self.P_entrada = self.P02
        self.P_saida   = self.P03   # já calculada no ciclo com Delta_P_cc

        # ==================================================================
        # 6. ÁREA TRANSVERSAL DO COMBUSTOR
        # Calculada via MFP (Eq. 9-8 — Mattingly), usando as condições
        # de entrada (T02r, P02) e o Mach de entrada M_entrada:
        #
        #   A = ṁ · √T_t / (P_t · cos(α) · MFP(M))
        #
        # Com α = 0 (entrada axial) e MFP calculado para M_entrada.
        # ==================================================================
        M  = self.M_entrada
        exp = (k + 1) / (2 * (k - 1))
        MFP = (M * math.sqrt(k / R)) / ((1 + ((k - 1) / 2) * M**2) ** exp)

        self.A_comb = (self.m_dot_ar * math.sqrt(self.T02r) / (self.P02 * MFP)) # (m²)
        self.D_comb = math.sqrt(4 * self.A_comb / math.pi)  # (m)

        # ==================================================================
        # 6b. COMPRIMENTO ESTIMADO DO COMBUSTOR — Eq. (10-34) Mattingly
        #
        # Lei de escala relativa a um combustor de referência conhecido:
        #   L ∝ P_t3^(-r) / sqrt(T_t4)
        #
        # Aplicada como razão entre o projeto atual e a referência:
        #   L = L_ref · (P02 / Pt3_ref)^(-r) · sqrt(T_t4_ref / TIT)
        # Pt3 no livro é a ENTRADA da câmara: P02 no ciclo deste projeto.
        # P03 é a saída da câmara e não deve substituir essa estação.
        #
        # Referência adotada: combustor JT9D (Tabela 10-5, Mattingly).
        # Esta é uma estimativa de escala — não um cálculo de primeiros
        # princípios — válida para combustores de geometria similar à
        # referência (mesma razão A4/A_ref).
        # ==================================================================
        ref = COMBUSTOR_REF
        self.L_comb = (
            ref["L_ref"] * (self.P02 / ref["Pt3_ref"]) ** (-ref["r_exp"]) * math.sqrt(ref["Tt4_ref"] / self.TIT)) # (m)

        # ==================================================================
        # 7. VERIFICAÇÕES DE VIABILIDADE
        # ==================================================================
        avisos.extend(checar_combustor(phi_eq=self.phi_eq, f=self.f))
        self.avisos = avisos
        for nome in ('m_dot_f', 'm_dot_tot', 'phi_eq', 'Q_total', 'A_comb', 'D_comb', 'L_comb'):
            positivo(nome+' calculado', getattr(self, nome))
        self._resolvido = True
        for aviso in self.avisos:
            print(f"AVISO: {aviso}")
        
        
    #___________________________________________________________________________
    # EXIBIÇÃO DE RESULTADOS
    #___________________________________________________________________________

    def mostrar_resultados(self) -> None:
        """Imprime os resultados do combustor de forma organizada."""
        self._verif_resolução()

        def linha():
            print("─" * 60)

        linha()
        print("  COMBUSTOR 1D — RESULTADOS")
        linha()
        print(f"  Combustível  : {self.combustivel}")
        print(f"  h_PR         : {self.h_PR/1e6:.2f} MJ/kg")
        print(f"  η_b          : {self.eta_b:.3f}")
        linha()
        print(f"  T entrada    : {self.T02r:8.2f} K  │  P entrada = {self.P_entrada/1e3:7.2f} kPa")
        print(f"  T saída(TIT) : {self.TIT:8.2f} K  │  P saída   = {self.P_saida/1e3:7.2f} kPa")
        print(f"  ΔTt          : {self.delta_Tt:8.2f} K")
        print(f"  ΔP/P         : {self.Delta_P*100:8.2f} %")
        linha()
        print(f"  f  (comb/ar) : {self.f:.5f}  kg_f/kg_ar")
        print(f"  φ_eq         : {self.phi_eq:.4f}  "
              f"({'pobre ✓' if self.phi_eq < 1.0 else 'RICA ✗'})")
        linha()
        print(f"  ṁ_ar         : {self.m_dot_ar:8.4f} kg/s")
        print(f"  ṁ_f          : {self.m_dot_f:8.4f} kg/s")
        print(f"  ṁ_total      : {self.m_dot_tot:8.4f} kg/s")
        print(f"  Q_ar (aprox.): {self.Q_total/1e3:8.2f} kW")
        linha()
        print(f"  M_entrada    : {self.M_entrada:.4f}")
        print(f"  A_comb       : {self.A_comb*1e4:8.2f} cm²")
        print(f"  D_comb       : {self.D_comb*100:8.2f} cm")
        print(f"  L_comb (est.): {self.L_comb*100:8.2f} cm  (ref.: {COMBUSTOR_REF['nome']})")
        print(f"    Escala usa P02 de entrada = {self.P02/1e3:.2f} kPa (Pt3 no livro).")
        for propriedade, dado in self.fontes_combustivel().items():
            print(f"  Fonte {propriedade}: {dado['status']} — {dado['origem']}")
        linha()

    def fontes_combustivel(self) -> dict:
        """Valores usados e sua origem, incluindo eventual PCI personalizado.

        Retorna uma cópia: consultar/editar o retorno não modifica as fontes
        globais ou os números empregados pelo cálculo.
        """
        fontes = deepcopy(FONTES_COMBUSTIVEIS[self.combustivel])
        if self._h_PR_fornecido:
            fontes["h_PR"] = {
                "status": "Fornecido pelo chamador",
                "origem": "Argumento h_PR do construtor Combustor1D.",
                "hipotese": "Substitui o PCI nominal do catálogo; a fonte e a adequação devem ser informadas por quem fornece esse valor.",
            }
        fontes["h_PR"].update(valor=self.h_PR, unidade="J/kg")
        if self.dados_mistura is not None:
            fontes['f_stoich'] = dict(status='Calculado por composição',
                origem=self.dados_mistura['composicao_combustivel']['fonte'],
                hipotese='Combustão completa com ar seco N2/O2/Ar. Aditivos, biodiesel e impurezas omitidos.')
        fontes["f_stoich"].update(valor=self.f_stoich, unidade="kg combustível/kg ar")
        return fontes

    def calor_balanco(self):
        """Potência sensível com a referência de entalpia desta execução."""
        return (self.m_dot_tot*self.cp_gases*(self.TIT-self.T_ref_entalpia)
                -self.m_dot_ar*self.cp_ar*(self.T02r-self.T_ref_entalpia))

    def resultados(self) -> dict:
        """Retorna dicionário com todos os resultados."""
        self._verif_resolução()
        return {
            "combustivel"    : self.combustivel,
            "mistura": self.dados_mistura,
            "T_ref_entalpia_K": self.T_ref_entalpia,
            "cp_ar_J_kg_K": self.cp_ar,
            "cp_gases_J_kg_K": self.cp_gases,
            "k_ar": self.k,
            "k_gases": self.k_gases,
            "R_ar_J_kg_K": self.R,
            "R_gases_J_kg_K": self.R_gases,
            "Q_balanco_kW": self.calor_balanco()/1000,
            "h_PR_MJ_kg"     : self.h_PR / 1e6,
            "eta_b"          : self.eta_b,
            "T02r_K"         : self.T02r,
            "TIT_K"          : self.TIT,
            "delta_Tt_K"     : self.delta_Tt,
            "P_entrada_kPa"  : self.P_entrada / 1e3,
            "P_saida_kPa"    : self.P_saida / 1e3,
            "Delta_P_pct"    : self.Delta_P * 100,
            "f"              : self.f,
            "phi_eq"         : self.phi_eq,
            "m_dot_ar_kg_s"  : self.m_dot_ar,
            "m_dot_f_kg_s"   : self.m_dot_f,
            "m_dot_tot_kg_s" : self.m_dot_tot,
            "m_dot_turbina_kg_s": self.m_dot_turbina,
            "Q_total_kW"     : self.Q_total / 1e3,
            "M_entrada"      : self.M_entrada,
            "A_comb_cm2"     : self.A_comb * 1e4,
            "D_comb_cm"      : self.D_comb * 100,
            "L_comb_cm"      : self.L_comb * 100,
        }

    #___________________________________________________________________________
    # MÉTODO AUXILIAR
    #___________________________________________________________________________

    def _verif_resolução(self) -> None:
        if not self._resolvido or self.f is None:
            raise RuntimeError(
                "Execute resolver() antes de acessar os resultados."
            )

    @property
    def m_dot_turbina(self) -> float:
        """Vazão de gases à saída do combustor, disponível para a turbina.

        Representa ṁ_ar + ṁ_combustível. Não inclui sangrias ou extrações
        entre o combustor e a turbina.
        """
        self._verif_resolução()
        return self.m_dot_tot


#_______________________________________________________________________________
if __name__ == "__main__":
    from engine.ciclo.CicloBrayton import criar_ciclo_exemplo
    ciclo1 = criar_ciclo_exemplo()

    class _CicloMock:
        T02r       = 603.5
        P02        = 800e3
        TIT        = 1200.0
        P03        = 760e3
        Delta_P_cc = 0.05
        m_dot      = 15.0
        cp         = 1005.0
        k          = 1.4
        w_líq      = 1.0

    ciclo_teste = ciclo1

    comb = Combustor1D(
        ciclo       = ciclo_teste,
        combustivel = "JP-4",
        eta_b       = 0.99,
        M_entrada   = 0.05,
    )

    comb.resolver()
    comb.mostrar_resultados()
