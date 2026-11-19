"""Indicadores sobre o caso ciclo–combustor, sem modificar os objetos."""

import math


def indicadores_energeticos(ciclo, combustor):
    """Usa potência do ciclo; não substitui pelo fechamento dos meanlines.

    Potências em W, trabalhos por kg de ar e SFC em kg/kWh.
    Não inclui perdas mecânicas, gerador ou consumos auxiliares.
    """
    potencia = ciclo.W_líq
    energia_pci = ciclo.m_dot_f * combustor.h_PR
    calor_util = energia_pci * combustor.eta_b
    valores = (potencia, energia_pci, calor_util, ciclo.m_dot_ar,
               ciclo.m_dot_turbina, ciclo.w_turb, ciclo.w_compr)
    if not all(math.isfinite(v) and v > 0 for v in valores):
        raise ValueError("Indicadores requerem caso resolvido com energia e potência positivas.")
    return {
        "potencia_liquida_W": potencia,
        "energia_combustivel_PCI_W": energia_pci,
        "calor_util_W": calor_util,
        "eta_calor_util": potencia / calor_util,
        "eta_PCI": potencia / energia_pci,
        "eta_b": combustor.eta_b,
        "BWR": ciclo.m_dot_ar * ciclo.w_compr / (ciclo.m_dot_turbina * ciclo.w_turb),
        "SFC_kg_kWh": ciclo.m_dot_f * 3.6e6 / potencia,
        "trabalho_liquido_por_kg_ar_J_kg": potencia / ciclo.m_dot_ar,
    }
