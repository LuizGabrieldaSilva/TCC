"""Reação estática de estágio de turbina, sem impor C1²=C3².

Dixon & Hall, 7ª ed., Eq. 4.3a, p. 123 (PDF 133):
R=(h2-h3)/(h1-h3). Bocal adiabático sem trabalho, h01=h02.
"""

import math


def reacao_estatica(trabalho, C1, C2, C3, *, contexto="Turbina"):
    """Retorna (R, queda estática no rotor, queda estática no estágio), J/kg.

    trabalho=h01-h03>0; h=h0-C²/2. O denominador deve representar
    uma queda estática positiva. Valores R<0 ou R>1 não são truncados;
    os verificadores aerodinâmicos decidem como sinalizá-los.
    """
    if (not all(math.isfinite(v) for v in (trabalho, C1, C2, C3))
            or trabalho <= 0 or min(C1, C2, C3) < 0):
        raise ValueError(f"{contexto}: trabalho deve ser positivo e velocidades finitas e não negativas.")
    rotor = trabalho + (C3 ** 2 - C2 ** 2) / 2
    estagio = trabalho + (C3 ** 2 - C1 ** 2) / 2
    if not math.isfinite(rotor) or not math.isfinite(estagio) or estagio <= 1e-12 * max(trabalho, 1.):
        raise ValueError(f"{contexto}: reação indefinida; queda estática do estágio não positiva ou numericamente nula.")
    return rotor / estagio, rotor, estagio
