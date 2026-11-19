"""Relações geométricas da cascata, com corda verdadeira e passo local."""

import math


def solidez_local(numero_pas, corda, raio):
    """σ = c/s, s = 2πr/Z; usa o Z inteiro efetivamente construído."""
    if (not math.isfinite(numero_pas) or numero_pas < 1
            or int(numero_pas) != numero_pas):
        raise ValueError("Número de pás deve ser inteiro e positivo.")
    if not all(math.isfinite(v) and v > 0 for v in (corda, raio)):
        raise ValueError("Corda e raio devem ser positivos e finitos.")
    return numero_pas * corda / (2 * math.pi * raio)
