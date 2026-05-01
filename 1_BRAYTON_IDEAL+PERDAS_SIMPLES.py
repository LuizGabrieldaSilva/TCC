#______________________________________________________________________________________________________________

class CicloBrayton:
    """
    PARÂMETROS DE ENTRADA:
    
    Consideramos que o ar entra em condições ambientes padrões
    T01         - Temperatura total de entrada no compressor   (K)
    P01         - Pressão total de entrada no compressor       (Pa)
    r_compr     - razão de pressão do compressor  
    k           - Razão entre os calores específicos (cp/cv)
    cp          - calor específico à pressão constante   (J/kg.K)
    TIT = T3    - Temperatura de entrada da turbina      (K)
    
    Ambos turbina e compressor serão modelados com eficiências politrópicas, assumidas constantes, 
    que serão usadas posteriormente para cálculos:
    
    e_compr     - Eficiência politrópica do compressor
    e_turb      - Eficiência politrópica da turbina
    
    Com ambas, serão calculadas as eficiências isentrópicas do compressor e da turbina(eta_compr e eta_turb).
    
    delta_P_cc  - Porcentagem de perda de pressão no processo de aquecimento
    
    TIT_máx     - Limite de temperatura máxima para a entrada na turbina. Tem valor padrão 1200 K,
    para turbinas sem resfriamento; ajustável pelo usuário.
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
                 ):
        
        self.T01 = T01
        self.P01 = P01
        self.r_compr = r_compr
        self.TIT = TIT
        self.e_turb = e_turb
        self.e_compr = e_compr
        self.cp = cp
        self.k = k
        self.Delta_P_cc = Delta_P_cc
        self.TIT_máx = TIT_máx
        
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
        self.m_dot = None
        self.W_líq = None
        
        
    def resolver(self) -> None:
        # Este método resolve todos os estados termodinâmicos do ciclo.
        
        # Para o ciclo Brayton ideal, o ar será o fluido de trabalho e será considerado um gás perfeitamente calórico (ou seja,
        # calores específicos constantes; cp e cv constantes)
        cp, k = self.cp, self.k
        
        # Verificação do Limite de TIT:
        if self.TIT > self.TIT_máx:
            raise ValueError(
                f"TEMPERATURA MÁXIMA DE ENTRADA NA TURBINA EXCEDIDA!\n"
                f"{self.TIT_máx} K é o limite para uma turbina sem resfriamento."
                )
        
        #___________________________________________________________________________________________________________________
        # Estado 2:
        # Primeiramente, será calculada a eficiência isentrópica do compressor, através da eficiência politrópica:
        
        self.eta_compr = (self.r_compr ** ((k - 1)/k) - 1) / (self.r_compr ** ((k - 1)/(k * self.e_compr)) - 1)
        
        # Agora, calcula-se a temperatura considerando o caso isentrópico (T02s) e depois a temperatura real (T02r)
        # Utilizando a relação isentrópica: (T02/T01) = (P02/P01)^((k - 1)/k)

        self.T02s = self.T01 * self.r_compr ** ((k - 1)/k)
        self.P02 = self.r_compr * self.P01
        
        # Pela equação de eficiência isentrópica do compressor:
        # eta_compr = (h02s - h01)/(h02r - h01) = cp(T02s - T01)/cp(T02r - T01) = (T02s - T01)/(T02r - T01)
        # Isolando T02r, temos:

        self.T02r = self.T01 + (self.T02s - self.T01)/self.eta_compr
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

        # Calculando a eficiência isentrópica da turbina, através da eficiência politrópica:
        
        # A equação da eficiência isentrópica da turbina deriva da relação isentrópica de temperatura,
        # que para a turbina fica:
        #           T04s/T03 = (P04/P03)^(k-1/k)
        # Como P04/P03 < 1, a temperatura cai, o que faz sentido fisicamente, pois a turbina expande e resfria o gás.
        # P04/P03 é a razão inversa de expansão (1/r_turb), que será usada a seguir, mantendo a lógica física.
        # Segundo SARAVANAMUTTOO:
        
        self.eta_turb = (1 - (1/self.r_turb) ** (((k - 1) * self.e_turb)/k)) / (1 - (1/self.r_turb) ** ((k - 1)/k))
        
        # Utilizando novamente a relação isentrópica:
        self.T04s = self.TIT * (self.P04/self.P03) ** ((k - 1)/k)
        
        # Temperatura Real Estado 4:
        self.T04r = self.TIT - self.eta_turb * (self.TIT - self.T04s)
        #___________________________________________________________________________________________________________________
        # CÁLCULOS DE ENERGIA - Trabalhos e entrada de calor específicos
        # Fazendo os cálculos de energia:
        
        self.w_compr = cp * (self.T02r - self.T01)
        self.w_turb = cp * (self.TIT - self.T04r)
        self.w_líq  = self.w_turb - self.w_compr
        self.q_ent  = cp * (self.TIT - self.T02r)
        
        if self.w_líq < 0:
            raise ValueError ("O trabalho consumido pelo compressor é maior que o produzido pela turbina!!!")
        
        # Eficiência do ciclo e BWR:
        self.eta_ciclo = self.w_líq / self.q_ent

        # Razão de Trabalho Reverso (Back Work Ratio)
        self.BWR = self.w_compr / self.w_turb
        
        
    def vazão_mássica_desejada(self, m_dot:float) -> None:
        # Aqui o ciclo é modelado para uma vazão mássica desejada ou imposta pelo projeto.
        # Calcula-se a Potência Líquida do Ciclo à partir da vazão mássica (kg/s):
        self._verif_resolução()
        
        self.m_dot = m_dot      # (kg/s)
        self.W_líq = self.m_dot * self.w_líq # (W)
        
    def potência_líquida_desejada(self, W_líq_kW: float) -> None:
        # Aqui o ciclo é modelado para uma potência líquida desejada ou imposta pelo projeto.
        # Calcula-se a Vazão Mássica do Ciclo à partir da potência líquida (kW)):
        self._verif_resolução()
        
        self.W_líq = W_líq_kW * 1e3 # (W; O usuário deve colocar a potência desejada em kW)
        self.m_dot = self.W_líq / self.w_líq
    
    def resultados(self) -> dict:
        # Retorna um dicionário com todos os resultados calculados.
        self._verif_resolução()
        return {
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
            "W_líq_kW":   self.W_líq / 1e3 if self.W_líq else None,
        }
    
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
            print(f"  ṁ       = {r['m_dot_kg_s']:8.3f} kg/s")
            print(f"  Ẇ_líq   = {r['W_líq_kW']:8.2f} kW")
        linha()
    
    def _verif_resolução(self) -> None:
        if self.w_líq is None:
            raise RuntimeError("Execute resolver() antes de acessar os resultados.")
            
        

if __name__ == "__main__":
    ciclo1 = CicloBrayton(
        300,
        100e3,
        8,
        1200,)

    ciclo1.resolver()
    ciclo1.vazão_mássica_desejada(3.085)

    ciclo1.mostrar_resultados()
    print(ciclo1.eta_compr)
    print(ciclo1.eta_turb)

