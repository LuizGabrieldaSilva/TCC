#______________________________________________________________________________________________________________
# Ciclo Brayton com eficiências politrópicas e perda de pressão prescrita
import math
from engine.input_validation import positivo, real_finito, intervalo, erros_numericos

class CicloBrayton:
    """
    PARÂMETROS DE ENTRADA:
    
    As condições totais de entrada do ar são prescritas pelo usuário.
    T01         - Temperatura total de entrada no compressor   (K)
    P01         - Pressão total de entrada no compressor       (Pa)
    r_compr     - razão de pressão do compressor  
    k           - Razão entre os calores específicos (cp/cv)
    cp, k       - propriedades constantes do AR (nomes históricos da API)
    cp_gases    - calor específico constante dos gases; None conserva cp do ar
    R_gases     - constante dos gases; None assume R_ar
    k_gases     - opcional; compatível com cp_gases e R_gases, quando fornecidos
    TIT = T3    - Temperatura de entrada da turbina      (K)
    
    Ambos turbina e compressor serão modelados com eficiências politrópicas, assumidas constantes, 
    que serão usadas posteriormente para cálculos:
    
    e_compr     - Eficiência politrópica do compressor
    e_turb      - Eficiência politrópica da turbina
    
    Com ambas, serão calculadas as eficiências isentrópicas do compressor e da turbina(eta_compr e eta_turb).
    
    Delta_P_cc  - Fração de perda de pressão total no combustor (0.05 = 5%)
    
    TIT_máx     - Limite de temperatura prescrito para esta execução (padrão 1200 K).
                  Ajustável pelo usuário; não é uma previsão de resistência
                  térmica dos materiais nem limite universal sem resfriamento.
    """
    
    def __init__(self,
                 T01:float,
                 P01:float,
                 r_compr:float,
                 TIT :float,
                 e_turb:float = 0.80,
                 e_compr:float = 0.85,
                 cp:float = 1005.0,
                 k:float = 1.4,
                 Delta_P_cc:float = 0.05,
                 TIT_máx: float = 1200,
                 cp_gases: float = None,
                 R_gases: float = None,
                 k_gases: float = None,
                 mistura_automatica: bool = False,
                 ):
        
        self.T01 = T01
        self.P01 = P01
        self.r_compr = r_compr
        self.TIT = TIT
        self.e_turb = e_turb
        self.e_compr = e_compr
        self.cp = cp
        self.k = k
        if type(mistura_automatica) is not bool:
            raise ValueError('mistura_automatica deve ser bool.')
        self.mistura_automatica = mistura_automatica
        self.combustivel_mistura = 'JP-4'
        self.eta_b_mistura = .99
        self.PCI_mistura = None
        self.dados_mistura = None
        self.T_ref_entalpia = 298.15 if mistura_automatica else 0.
        if mistura_automatica:
            from engine.combustor.mistura_gases import R_AR
            positivo('cp_ar', cp)
            if cp <= R_AR:raise ValueError('cp_ar deve ser maior que R do ar seco.')
            self.k = k = cp/(cp-R_AR)
            cp_gases, R_gases, k_gases = 1148., R_AR, None
        # cp/k antigos identificam o AR. Omitir cp_gases preserva a API
        # histórica; o caso de referência novo fornece cp dos gases.
        self.cp_ar, self.k_ar = cp, k
        positivo('cp_ar', cp)
        real_finito('k_ar', k)
        if k <= 1:
            raise ValueError('k_ar deve ser maior que 1.')
        self.R_ar = cp * (1 - 1 / k)
        self.cp_gases = cp if cp_gases is None else cp_gases
        positivo('cp_gases', self.cp_gases)
        if k_gases is not None:
            real_finito('k_gases', k_gases)
            if k_gases <= 1:
                raise ValueError('k_gases deve ser maior que 1.')
            r_calculado = self.cp_gases * (1 - 1 / k_gases)
            if R_gases is not None and not math.isclose(R_gases, r_calculado, rel_tol=1e-10):
                raise ValueError('cp_gases, k_gases e R_gases são incompatíveis.')
            R_gases = r_calculado
        self.R_gases = self.R_ar if R_gases is None else R_gases
        positivo('R_gases', self.R_gases)
        if self.R_gases >= self.cp_gases:
            raise ValueError('R_gases deve ser menor que cp_gases para cv positivo.')
        self.k_gases = self.cp_gases / (self.cp_gases - self.R_gases)
        self.Delta_P_cc = Delta_P_cc
        self.TIT_máx = TIT_máx
        self._resolvido = False
        self._validar_entradas()
        
        #___________________________________________________________________________________________________________________
        # INICIALIZANDO OS PARÂMETROS DE TODOS OS ESTADOS COMO NONE(SERÃO CALCULADOS PELO MÉTODO RESOLVER())
        
        # SAÍDA DO COMPRESSOR - ESTADO 2 IDEAL
        # EFICIÊNCIA ISENTRÓPICA DO COMPRESSOR
        self.eta_compr = None
        
        self.T02s = None    # Temperatura total Isentrópica na saída do compressor (K)
        self.P02 = None     # Pressão total na saída do compressor (Pa)

        # SAÍDA DO COMPRESSOR - ESTADO 2 REAL (compressor não ideal)
        self.T02r = None    # Temperatura total real na saída do compressor (K)
        
        
        # ENTRADA DA TURBINA (SAÍDA DA CÂMARA DE COMBUSTÃO) - ESTADO 3
        # EFICIÊNCIA ISENTRÓPICA DA TURBINA
        self.eta_turb = None
        
        self.P03 = None     # Pressão total na saída da câmara de combustão (Pa)
        
        # SAÍDA DA TURBINA - ESTADO IDEAL 4
        self.T04s = None    # Temperatura total Isentrópica na saída da turbina (K)
        self.P04 = None     # Pressão total na saída da Turbina (Pa)
        
        self.r_turb = None  # Razão de Expansão na turbina (r_turb = P03/P04)
        
        # SAÍDA DA TURBINA - ESTADO REAL 4 (turbina não ideal)
        self.T04r = None    # Temperatura total real na saída do turbina (K)
        
        # CÁLCULOS DE ENERGIA - TRABALHOS E ENTRADA DE CALOR ESPECÍFICOS (J/kg)
        self.w_compr = None     # Trabalho Específico do Compressor
        self.w_turb = None      # Trabalho Específico da Turbina
        self.w_líq = None       # Trabalho Líquido Específico do Ciclo
        self.q_ent = None       # Entrada Específica de Calor
        
        # Eficiência do Ciclo e Razão de Trabalho Inversa
        self.eta_ciclo = None   # Eficiência Térmica do Ciclo
        self.BWR = None         # Razão de Trabalho Reversa (Back Work Ratio)
        
        # Vazão Mássica (kg/s) e Potência líquida do Ciclo (W)
        self.m_dot = None       # compatibilidade: vazão de ar usada pelo compressor
        self.m_dot_ar = None
        self.m_dot_f = 0.0
        self.m_dot_turbina = None
        self.W_líq = None
        self._modo_vazao = None
        self._W_líq_alvo = None
        self._q_ent_ar = None
        
        
    def _validar_entradas(self):
        for nome in ('cp_gases', 'R_gases'):
            positivo(nome, getattr(self, nome))
        if self.cp_gases <= self.R_gases:
            raise ValueError('cp_gases deve ser maior que R_gases.')
        self.cp_ar, self.k_ar = self.cp, self.k
        self.k_gases = self.cp_gases / (self.cp_gases - self.R_gases)
        for nome in ('T01', 'P01', 'TIT', 'TIT_máx', 'cp'):
            positivo(nome, getattr(self, nome))
        real_finito('r_compr', self.r_compr)
        if self.r_compr <= 1:
            raise ValueError('r_compr deve ser maior que 1 neste modelo de motor com compressão e expansão.')
        real_finito('k', self.k)
        if self.k <= 1:
            raise ValueError('k deve ser maior que 1.')
        self.R_ar = self.cp_ar * (1 - 1 / self.k_ar)
        for nome in ('e_compr', 'e_turb'):
            intervalo(nome, getattr(self, nome), 0., 1., incluir_minimo=False)
        intervalo('Delta_P_cc', self.Delta_P_cc, 0., 1., incluir_maximo=False)
        expansao = self.r_compr * (1-self.Delta_P_cc)
        real_finito('Razão de expansão disponível', expansao)
        if expansao <= 1:
            raise ValueError('r_compr*(1-Delta_P_cc) deve ser maior que 1: a pressão após o combustor precisa permitir expansão até P01.')
        if self.TIT > self.TIT_máx:
            raise ValueError(f'TIT ({self.TIT} K) excede o limite prescrito para esta execução ({self.TIT_máx} K).')

    @erros_numericos('CicloBrayton.resolver')
    def resolver(self) -> None:
        # Este método resolve todos os estados termodinâmicos do ciclo.
        
        # Para o ciclo Brayton ideal, o ar será o fluido de trabalho e será considerado um gás perfeitamente calórico (ou seja,
        # calores específicos constantes; cp e cv constantes)
        self._resolvido = False
        # Resolver novamente invalida a vazão e o acoplamento anteriores.
        self.m_dot = self.m_dot_ar = self.m_dot_turbina = self.W_líq = None
        self.m_dot_f = 0.0
        self._modo_vazao = self._W_líq_alvo = None
        self._validar_entradas()
        cp, k = self.cp, self.k
        
        #___________________________________________________________________________________________________________________
        # Estado 2:
        # Primeiramente, será calculada a eficiência isentrópica do compressor, através da eficiência politrópica:
        
        perto_unidade = abs(math.log(self.r_compr)) < 1e-6
        if perto_unidade:
            self.eta_compr = math.expm1((k-1)/k*math.log(self.r_compr)) / math.expm1((k-1)/(k*self.e_compr)*math.log(self.r_compr))
        else:
            self.eta_compr = (self.r_compr ** ((k - 1)/k) - 1) / (self.r_compr ** ((k - 1)/(k * self.e_compr)) - 1)
        
        # Agora, calcula-se a temperatura considerando o caso isentrópico (T02s) e depois a temperatura real (T02r)
        # Utilizando a relação isentrópica: (T02/T01) = (P02/P01)^((k - 1)/k)

        self.T02s = self.T01 * self.r_compr ** ((k - 1)/k)
        self.P02 = self.r_compr * self.P01
        
        # Pela equação de eficiência isentrópica do compressor:
        # eta_compr = (h02s - h01)/(h02r - h01) = cp(T02s - T01)/cp(T02r - T01) = (T02s - T01)/(T02r - T01)
        # Isolando T02r, temos:

        self.T02r = self.T01 + (self.T02s - self.T01)/self.eta_compr
        if perto_unidade:
            self.T02r = self.T01 * (1 + math.expm1((k-1)/(k*self.e_compr)*math.log(self.r_compr)))
        positivo('T02r calculada', self.T02r)
        positivo('P02 calculada', self.P02)
        if self.T02r <= self.T01:
            raise ValueError('r_compr está próximo demais de 1 para resolver a elevação de temperatura na precisão numérica disponível.')
        if self.TIT <= self.T02r:
            raise ValueError('TIT deve ser maior que T02r: este modelo requer adição positiva de calor no combustor.')
        #___________________________________________________________________________________________________________________
        # Estado 3:
        # No ciclo Brayton ideal, o aquecimento 2 → 3 é modelado como adição de calor à pressão constante.
        # Na prática, há queda de pressão no processo. 
        # Então, a pressão após o aquecimento é igual à P02 - % de queda de pressão.
        # A Queda de pressão relativa é definida pelo parâmetro Delta_P_cc, com um valor padrão de 5%:     

        self.P03 = self.P02 * (1 - self.Delta_P_cc)  # P03 menor que P02
        #___________________________________________________________________________________________________________________
        # Estado 4:
        # Considera-se que a pressão de saída é igual a pressão ambiente, logo, P04 = P01
        self.P04 = self.P01
        self.r_turb = self.P03 / self.P04  # Razão de expansão da turbina
        if self.mistura_automatica:
            from engine.combustor.mistura_gases import resolver_mistura
            self.dados_mistura = resolver_mistura(self.combustivel_mistura,self.T02r,self.TIT,
                self.cp_ar,self.eta_b_mistura,self.PCI_mistura)
            self.cp_gases = self.dados_mistura['cp_J_kg_K']
            self.R_gases = self.dados_mistura['R_J_kg_K']
            self.k_gases = self.dados_mistura['k']
        k = self.k_gases  # propriedades dos gases na expansão

        # Calculando a eficiência isentrópica da turbina, através da eficiência politrópica:
        
        # A equação da eficiência isentrópica da turbina deriva da relação isentrópica de temperatura,
        # que para a turbina fica:
        #           T04s/T03 = (P04/P03)^(k-1/k)
        # Como P04/P03 < 1, a temperatura cai, o que faz sentido fisicamente, pois a turbina expande e resfria o gás.
        # P04/P03 é a razão inversa de expansão (1/r_turb), que será usada a seguir, mantendo a lógica física.
        # Segundo SARAVANAMUTTOO:
        
        positivo('P03 calculada', self.P03)
        if not math.isfinite(self.r_turb) or self.r_turb <= 1:
            raise ValueError('A razão de expansão calculada deve ser finita e maior que 1; revise r_compr e Delta_P_cc.')
        expansao_perto_unidade = abs(math.log(self.r_turb)) < 1e-6
        if expansao_perto_unidade:
            self.eta_turb = math.expm1(-(k-1)*self.e_turb/k*math.log(self.r_turb)) / math.expm1(-(k-1)/k*math.log(self.r_turb))
        else:
            self.eta_turb = (1 - (1/self.r_turb) ** (((k - 1) * self.e_turb)/k)) / (1 - (1/self.r_turb) ** ((k - 1)/k))
        
        # Utilizando novamente a relação isentrópica:
        self.T04s = self.TIT * (self.P04/self.P03) ** ((k - 1)/k)
        
        # Temperatura Real Estado 4:
        self.T04r = self.TIT - self.eta_turb * (self.TIT - self.T04s)
        if expansao_perto_unidade:
            self.T04r = self.TIT * (1 + math.expm1(-(k-1)*self.e_turb/k*math.log(self.r_turb)))
        positivo('T04r calculada', self.T04r)
        if self.T04r >= self.TIT:
            raise ValueError('A expansão está próxima demais da unidade para resolver a queda de temperatura na precisão numérica disponível.')
        #___________________________________________________________________________________________________________________
        # CÁLCULOS DE ENERGIA - Trabalhos e entrada de calor específicos
        # Fazendo os cálculos de energia:
        
        self.w_compr = cp * (self.T02r - self.T01)
        self.w_turb = self.cp_gases * (self.TIT - self.T04r)
        self.w_líq  = self.w_turb - self.w_compr
        self.q_ent = self.cp_gases * (self.TIT-self.T_ref_entalpia) - self.cp_ar * (self.T02r-self.T_ref_entalpia)
        self._q_ent_ar = self.q_ent
        positivo('Trabalho do compressor', self.w_compr)
        positivo('Trabalho da turbina', self.w_turb)
        positivo('Calor de entrada', self.q_ent)
        real_finito('Trabalho líquido', self.w_líq)
        
        if self.w_líq < 0:
            raise ValueError ("O trabalho consumido pelo compressor é maior que o produzido pela turbina!!!")
        
        # Eficiência do ciclo e BWR:
        self.eta_ciclo = self.w_líq / self.q_ent

        # Razão de Trabalho Reverso (Back Work Ratio)
        self.BWR = self.w_compr / self.w_turb
        self._resolvido = True
        
        
    def vazão_mássica_desejada(self, m_dot:float) -> None:
        # Aqui o ciclo é modelado para uma vazão mássica desejada ou imposta pelo projeto.
        # Calcula-se a Potência Líquida do Ciclo à partir da vazão mássica (kg/s):
        self._verif_resolução()
        positivo('m_dot (kg/s)', m_dot)
        real_finito('Potência resultante', m_dot * (self.w_turb-self.w_compr))

        self.w_líq = self.w_turb - self.w_compr
        self.q_ent = self._q_ent_ar
        self.eta_ciclo = self.w_líq / self.q_ent
        self.BWR = self.w_compr / self.w_turb
        
        self.m_dot = m_dot      # (kg/s)
        self.m_dot_ar = m_dot
        self.m_dot_f = 0.0
        self.m_dot_turbina = m_dot
        self._modo_vazao = "massa"
        self._W_líq_alvo = None
        self.W_líq = self.m_dot * self.w_líq # (W)
        
    def potência_líquida_desejada(self, W_líq_kW: float) -> None:
        # Aqui o ciclo é modelado para uma potência líquida desejada ou imposta pelo projeto.
        # Calcula-se a Vazão Mássica do Ciclo à partir da potência líquida (kW)):
        self._verif_resolução()
        positivo('W_líq_kW', W_líq_kW)
        positivo('Potência desejada em W', W_líq_kW * 1e3)
        positivo('Trabalho líquido disponível para dimensionar a vazão', self.w_turb-self.w_compr)
        positivo('Vazão resultante', W_líq_kW * 1e3 / (self.w_turb-self.w_compr))

        self.w_líq = self.w_turb - self.w_compr
        self.q_ent = self._q_ent_ar
        self.eta_ciclo = self.w_líq / self.q_ent
        self.BWR = self.w_compr / self.w_turb
        
        self.W_líq = W_líq_kW * 1e3 # (W; O usuário deve colocar a potência desejada em kW)
        self.m_dot = self.W_líq / self.w_líq
        self.m_dot_ar = self.m_dot
        self.m_dot_f = 0.0
        self.m_dot_turbina = self.m_dot
        self._modo_vazao = "potencia"
        self._W_líq_alvo = self.W_líq

    @erros_numericos('CicloBrayton.registrar_vazao_turbina')
    def registrar_vazao_turbina(self, m_dot_turbina: float) -> float:
        """Registra a vazão de gases do combustor e fecha o balanço de massa.

        ``m_dot`` permanece como vazão de ar para o compressor. A turbina
        recebe ``m_dot_turbina`` (ar + combustível). Retorna a vazão de ar
        atualizada; no modo de potência alvo, o chamador deve recalcular o
        combustor com esse valor antes de dimensionar a turbina.
        """
        self._verif_resolução()
        if self.m_dot is None or self.m_dot <= 0:
            raise RuntimeError("Defina uma vazão de ar positiva antes da vazão da turbina.")
        positivo('m_dot_turbina (kg/s)', m_dot_turbina)
        positivo('Vazão mássica de ar atual', self.m_dot)
        if m_dot_turbina < self.m_dot:
            raise ValueError(
                f"Vazão da turbina ({m_dot_turbina}) deve ser finita e maior ou igual "
                f"à vazão de ar ({self.m_dot})."
            )

        razao_combustivel_ar = m_dot_turbina / self.m_dot - 1.0
        w_liq_por_ar = (1.0 + razao_combustivel_ar) * self.w_turb - self.w_compr
        real_finito('Razão combustível/ar', razao_combustivel_ar)
        real_finito('Trabalho líquido após acoplamento', w_liq_por_ar)
        if w_liq_por_ar <= 0:
            raise ValueError("A potência líquida fica não positiva após incluir a vazão de combustível.")

        # Validar os resultados antes de substituir o estado de uma execução válida.
        m_ar = self._W_líq_alvo / w_liq_por_ar if self._modo_vazao == 'potencia' else self.m_dot
        positivo('Vazão de ar após acoplamento', m_ar)
        m_f = razao_combustivel_ar * m_ar
        m_g = m_ar + m_f
        w_liq = (m_g/m_ar) * self.w_turb - self.w_compr
        q_ent = self._q_ent_ar + razao_combustivel_ar * self.cp_gases * (self.TIT-self.T_ref_entalpia)
        potencia = m_ar*w_liq
        for nome, valor in (('Vazão de combustível', m_f), ('Vazão de gases', m_g),
                            ('Trabalho líquido acoplado', w_liq), ('Calor acoplado', q_ent),
                            ('Potência acoplada', potencia)):
            real_finito(nome, valor)
        positivo('Calor acoplado', q_ent)
        positivo('Potência acoplada', potencia)
        self.m_dot = self.m_dot_ar = m_ar
        self.m_dot_f = m_f
        self.m_dot_turbina = m_g
        self.w_líq = w_liq
        self.q_ent = q_ent
        self.eta_ciclo = w_liq/q_ent
        self.BWR = self.w_compr / ((m_g/m_ar)*self.w_turb)
        self.W_líq = potencia
        return self.m_dot_ar
    
    def preparar_mistura(self, combustivel, eta_b, PCI=None):
        """Atualiza propriedades antes de construir a turbina, preservando o modo de vazão.

        Compressor usa o mesmo ar e não é recalculado aqui. Resultados de uma
        turbina previamente construída precisam ser reconstruídos pelo chamador.
        """
        if not self.mistura_automatica:return
        if (combustivel,eta_b,PCI)==(self.combustivel_mistura,self.eta_b_mistura,self.PCI_mistura):return
        from engine.combustor.mistura_gases import resolver_mistura
        self._verif_resolução()
        # Recusar entradas sem solução antes de modificar um ciclo válido.
        resolver_mistura(combustivel,self.T02r,self.TIT,self.cp_ar,eta_b,PCI)
        modo,massa,alvo=self._modo_vazao,self.m_dot,self._W_líq_alvo
        self.combustivel_mistura,self.eta_b_mistura,self.PCI_mistura=combustivel,eta_b,PCI
        self.resolver()
        if modo=='potencia':self.potência_líquida_desejada(alvo/1000)
        elif massa is not None:self.vazão_mássica_desejada(massa)

    def resultados(self) -> dict:
        # Retorna um dicionário com todos os resultados calculados.
        self._verif_resolução()
        return {
            "propriedades": self.propriedades(),
            "mistura": self.dados_mistura,
            "T_ref_entalpia_K": self.T_ref_entalpia,
            # Ciclo:
            "T01_K":   self.T01,
            "P01_kPa": self.P01 / 1e3,
            "T02r_K":   self.T02r,
            "P02_kPa": self.P02 / 1e3,
            "TIT_K":   self.TIT,
            "P03_kPa": self.P03 / 1e3,
            "T04r_K":   self.T04r,
            "P04_kPa": self.P04 / 1e3,
            # Trabalhos e calor específicos
            "w_compr_kJ_kg": self.w_compr / 1e3,
            "w_turb_kJ_kg": self.w_turb / 1e3,
            "w_líq_kJ_kg":  self.w_líq  / 1e3,
            "q_ent_kJ_kg":  self.q_ent  / 1e3,
            # Métricas
            "eta_ciclo_%": self.eta_ciclo * 100,
            "BWR":      self.BWR,
            # Vazão Mássica e Potência Líquida
            "m_dot_kg_s": self.m_dot,
            "m_dot_ar_kg_s": self.m_dot_ar,
            "m_dot_f_kg_s": self.m_dot_f,
            "m_dot_turbina_kg_s": self.m_dot_turbina,
            "W_líq_kW":   self.W_líq / 1e3 if self.W_líq else None,
        }
    
    def propriedades(self):
        """Propriedades efetivamente utilizadas; h=cp*T por convenção aproximada."""
        return {"ar": {"cp_J_kg_K": self.cp_ar, "k": self.k_ar, "R_J_kg_K": self.R_ar},
                "gases": {"cp_J_kg_K": self.cp_gases, "k": self.k_gases, "R_J_kg_K": self.R_gases}}

    def mostrar_resultados(self) -> None:
        # Impressão dos resultados de forma organizada.
        def linha():
            print("─" * 60)
            
        self._verif_resolução()
        r = self.resultados()
        
        linha()
        print("  CICLO BRAYTON — RESULTADOS")
        linha()
        print(f"""  Estado 1  │ T01 =        {r['T01_K']:>7.1f} K │ P01 = {r['P01_kPa']:7.1f} kPa
  Estado 2  │ T02r =       {r['T02r_K']:>7.1f} K │ P02 = {r['P02_kPa']:7.1f} kPa
  Estado 3  │ TIT = T03 =  {r['TIT_K']:>7.1f} K │ P03 = {r['P03_kPa']:7.1f} kPa
  Estado 4  │ T04r =       {r['T04r_K']:>7.1f} K │ P04 = {r['P04_kPa']:7.1f} kPa""")
        linha()
        print(f"  w_compr  = {r['w_compr_kJ_kg']:8.2f} kJ/kg")
        print(f"  w_turb   = {r['w_turb_kJ_kg']:8.2f} kJ/kg")
        print(f"  w_líq    = {r['w_líq_kJ_kg']:8.2f} kJ/kg")
        print(f"  q_ent    = {r['q_ent_kJ_kg']:8.2f} kJ/kg")
        linha()
        print(f"  η_ciclo = {r['eta_ciclo_%']:6.2f} %")
        print(f"  BWR = {r['BWR']:6.4f}")
        
        if self.m_dot:
            linha()
            print(f"  ṁ_ar    = {r['m_dot_ar_kg_s']:8.3f} kg/s")
            print(f"  ṁ_f     = {r['m_dot_f_kg_s']:8.4f} kg/s")
            print(f"  ṁ_turb  = {r['m_dot_turbina_kg_s']:8.3f} kg/s")
            print(f"  Ẇ_líq   = {r['W_líq_kW']:8.2f} kW")
        linha()
    
    def _verif_resolução(self) -> None:
        if not self._resolvido or self.w_líq is None:
            raise RuntimeError("Execute resolver() antes de acessar os resultados.")
        for nome in ('w_compr', 'w_turb', 'q_ent'):
            positivo(nome, getattr(self, nome))
        real_finito('w_líq', self.w_líq)
            
        

def criar_ciclo_exemplo(m_dot=15.0):
    """Cria e resolve um ciclo didático novo somente quando chamado."""
    from engine.reference_case import montar_caso_referencia
    ciclo1 = CicloBrayton(**montar_caso_referencia()['REF_CICLO'])
    ciclo1.resolver()
    ciclo1.vazão_mássica_desejada(m_dot)
    return ciclo1


if __name__ == "__main__":
    ciclo1 = criar_ciclo_exemplo(m_dot=3.085)

    ciclo1.mostrar_resultados()
