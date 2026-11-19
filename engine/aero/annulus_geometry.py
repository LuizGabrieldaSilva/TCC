"""Geometria de anular com raio médio ARITMÉTICO constante.

r_m = (r_tip + r_hub)/2; não é o raio de áreas iguais de Dixon & Hall.
A = 2*pi*r_m*h é identidade geométrica para esta definição.
"""

import math


def raios_anular(area, raio_medio, *, contexto="Anular"):
    """Preserva a área calculada pelo escoamento e o raio de referência."""
    if not all(math.isfinite(v) and v > 0 for v in (area, raio_medio)):
        raise ValueError(f"{contexto}: área e raio médio devem ser positivos e finitos.")
    altura = area / (2 * math.pi * raio_medio)
    cubo = raio_medio - altura / 2
    ponta = raio_medio + altura / 2
    if not all(math.isfinite(v) for v in (altura, cubo, ponta)) or not (0 < cubo < ponta):
        raise ValueError(
            f"{contexto}: área {area:.6g} m² incompatível com raio médio aritmético "
            f"{raio_medio:.6g} m; o anular exige 0 < r_hub < r_tip. "
            "Reveja as condições de escoamento e a geometria de entrada."
        )
    return cubo, ponta, altura


def referencia_radial(cubo, ponta, raio_referencia, *, contexto="Radial"):
    """Impede reinterpretar velocidades meanline em outro raio geométrico."""
    if not all(math.isfinite(v) and v > 0 for v in (cubo, ponta, raio_referencia)) or ponta <= cubo:
        raise ValueError(f"{contexto}: raios inválidos no acoplamento meanline–radial.")
    medio_geometrico = (cubo + ponta) / 2
    if not math.isclose(medio_geometrico, raio_referencia, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError(
            f"{contexto}: raio médio geométrico {medio_geometrico:.9g} m difere da "
            f"referência meanline {raio_referencia:.9g} m. Recalcule o meanline com "
            "a hipótese de raio médio aritmético constante."
        )
    return raio_referencia
