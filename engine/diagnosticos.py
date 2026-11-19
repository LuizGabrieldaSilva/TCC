"""Diagnósticos sem ajustar entradas ou modificar os objetos calculados.

Áreas pela continuidade com propriedades estáticas meanline. Não se inventa
Pt entre fileiras; não há reconstrução do anular CAD ou integração radial.
"""

from engine import design_criteria as dc
import math


RTOL = dc.COINCIDENCIA_RTOL
ATOL = dc.COINCIDENCIA_ATOL  # tolerância de comparação numérica nas unidades SI; não de projeto


def comparar(grandeza, unidade, alvo, calculado):
    if not all(math.isfinite(v) for v in (alvo, calculado)):
        raise ValueError(f"{grandeza}: comparação requer valores finitos.")
    residuo = calculado - alvo
    return dict(grandeza=grandeza, unidade=unidade, alvo=alvo, calculado=calculado,
                residuo=residuo, residuo_pct=100 * residuo / abs(alvo) if alvo != 0 else None,
                coincide=math.isclose(calculado, alvo, rel_tol=RTOL, abs_tol=ATOL))


def _plano(Tt, Pt, Cx, Ctheta, m_dot, cp, k):
    if (not all(math.isfinite(v) for v in (Tt, Cx, Ctheta, m_dot, cp, k))
            or min(Tt, Cx, m_dot, cp) <= 0 or k <= 1):
        raise ValueError("Plano de escoamento: entradas não admissíveis.")
    C = math.hypot(Cx, Ctheta)
    T = Tt - C ** 2 / (2 * cp)
    if not math.isfinite(T) or T <= 0:
        raise ValueError("Plano de escoamento: temperatura estática não positiva.")
    R = cp * (1 - 1 / k)
    dado = dict(Tt_K=Tt, Pt_Pa=Pt, Cx_m_s=Cx, Ctheta_m_s=Ctheta, C_m_s=C,
                T_K=T, M=C / math.sqrt(k * R * T), P_Pa=None,
                rho_kg_m3=None, area_m2=None,
                status="Não determinada: pressão total entre fileiras não disponível.")
    if Pt is not None:
        if not math.isfinite(Pt) or Pt <= 0:
            raise ValueError("Plano de escoamento: pressão total não admissível.")
        P = Pt * (T / Tt) ** (k / (k - 1))
        rho = P / (R * T)
        dado.update(P_Pa=P, rho_kg_m3=rho, area_m2=m_dot / (rho * Cx), status="Determinada no meanline")
    return dado


def diagnosticar_maquina(modelo, componente):
    """Planos 1/2/3 de cada estágio, sem atribuir pressão à estação 2.

    Compressor: 1→rotor→2→estator→3; V3=V1 por hipótese do modelo.
    Turbina: 1→bocal→2→rotor→3; Tt2=Tt1 porque o bocal não faz trabalho.
    """
    if componente not in ("Compressor", "Turbina"):
        raise ValueError("Componente deve ser Compressor ou Turbina.")
    if not modelo.Tt_saida or modelo.Tt_saida[0] is None:
        raise RuntimeError("Resolva o modelo antes de obter os diagnósticos.")
    compressor = componente == "Compressor"
    estagios = []
    for i in range(modelo.n_estagios):
        tt1, tt3 = modelo.Tt_entrada[i], modelo.Tt_saida[i]
        ct3 = modelo.v1[i] if compressor else modelo.v3[i]
        argumentos = (modelo.u_ax, modelo.m_dot, modelo.cp, modelo.k)

        def plano(tt, pt, ct):
            cx, massa, cp, k = argumentos
            return _plano(tt, pt, cx, ct, massa, cp, k)

        planos = {
            "1": plano(tt1, modelo.Pt_entrada[i], modelo.v1[i]),
            "2": plano(tt3 if compressor else tt1, None, modelo.v2[i]),
            "3": plano(tt3, modelo.Pt_saida[i], ct3),
        }
        rep = modelo.A_estagio[i]
        estagios.append(dict(estagio=i+1, planos=planos, area_representativa_m2=rep,
                             residuo_area_entrada_m2=planos["1"]["area_m2"]-rep,
                             # Diagnóstico condicional: não é vazão real calculada
                             # para uma saída com área própria e variável.
                             desvio_vazao_se_area_CAD_imposta_na_saida_pct=
                             100 * (rep / planos["3"]["area_m2"] - 1)))
    interfaces = []
    for i in range(1, len(estagios)):
        anterior = estagios[i-1]["planos"]["3"]
        seguinte = estagios[i]["planos"]["1"]
        interfaces.append(dict(de=i, para=i+1, comparacoes=[
            comparar(campo, unidade, anterior[campo], seguinte[campo])
            for campo, unidade in (("Tt_K", "K"), ("Pt_Pa", "Pa"),
                                    ("Cx_m_s", "m/s"), ("Ctheta_m_s", "m/s"), ("area_m2", "m²"))
        ]))
    return dict(componente=componente, modo="automático" if modelo.calculo_automatico else "manual",
                estagios=estagios, interfaces=interfaces,
                selecao_estagios=getattr(modelo, "selecao_estagios", None))


def diagnosticar_integracao(ciclo, comp, turb, combustor):
    """Compara soluções do ciclo e das máquinas; não resolve um novo ciclo.

    Wc é consumo positivo, Wt é produção positiva. O líquido é Wt-Wc.
    Cada componente usa sua vazão real (ar no compressor, gases na turbina).
    """
    dados_comp = diagnosticar_maquina(comp, "Compressor")
    dados_turb = diagnosticar_maquina(turb, "Turbina")
    wc = comp.cp * (comp.Tt_saida[-1] - comp.Tt_entrada[0])
    wt = turb.cp * (turb.Tt_entrada[0] - turb.Tt_saida[-1])
    Wc, Wt = comp.m_dot * wc, turb.m_dot * wt
    Wc_ciclo, Wt_ciclo = ciclo.m_dot_ar * ciclo.w_compr, ciclo.m_dot_turbina * ciclo.w_turb
    dados_comp["comparacoes"] = [
        comparar("Temperatura total de saída", "K", ciclo.T02r, comp.Tt_saida[-1]),
        comparar("Pressão total de saída", "Pa", ciclo.P02, comp.Pt_saida[-1]),
        comparar("Trabalho específico consumido (por kg de ar)", "J/kg", ciclo.w_compr, wc),
    ]
    dados_turb["comparacoes"] = [
        comparar("Temperatura total de saída", "K", ciclo.T04r, turb.Tt_saida[-1]),
        comparar("Pressão total de saída", "Pa", ciclo.P04, turb.Pt_saida[-1]),
        comparar("Trabalho específico produzido (por kg de gases)", "J/kg", ciclo.w_turb, wt),
    ]
    potencias = [comparar("Consumo do compressor", "W", Wc_ciclo, Wc),
                 comparar("Produção da turbina", "W", Wt_ciclo, Wt),
                 comparar("Potência líquida", "W", ciclo.W_líq, Wt-Wc)]
    # Alvo = valor que o componente receptor utiliza na execução vigente.
    interfaces = {
        "Compressor → combustor": [
            comparar("Temperatura total", "K", combustor.T02r, comp.Tt_saida[-1]),
            comparar("Pressão total", "Pa", combustor.P02, comp.Pt_saida[-1]),
            comparar("Vazão de ar", "kg/s", combustor.m_dot_ar, comp.m_dot),
        ],
        "Combustor → turbina": [
            comparar("Temperatura total", "K", turb.T01_turb, combustor.TIT),
            comparar("Pressão total", "Pa", turb.P01_turb, combustor.P03),
            comparar("Vazão de gases", "kg/s", turb.m_dot, combustor.m_dot_turbina),
        ],
    }
    comparacoes = dados_comp["comparacoes"] + dados_turb["comparacoes"] + potencias
    comparacoes += [item for lista in interfaces.values() for item in lista]
    return dict(componentes={"Compressor": dados_comp, "Turbina": dados_turb},
                potencias=potencias, interfaces=interfaces,
                alvos_coincidem=all(item["coincide"] for item in comparacoes),
                tolerancias=dict(relativa=RTOL, absoluta_SI=ATOL),
                convencao_residuo="Calculado menos alvo; percentual dividido pelo módulo do alvo. Alvo zero: percentual não definido.",
                limite="Comparação de alvos termodinâmicos, não validação física completa. Não modela difusor nem pressão entre fileiras.")
