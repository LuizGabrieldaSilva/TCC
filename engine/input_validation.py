"""Domínios numéricos das APIs, separados dos critérios de recomendação."""

import math
from functools import wraps
from numbers import Integral, Real


def real_finito(nome, valor):
    try:
        valido = not isinstance(valor, bool) and isinstance(valor, Real) and math.isfinite(valor)
    except (OverflowError, TypeError):
        valido = False
    if not valido:
        raise ValueError(f"{nome} deve ser um número real finito (não aceita bool, NaN ou infinito).")


def positivo(nome, valor):
    real_finito(nome, valor)
    if valor <= 0:
        raise ValueError(f"{nome} deve ser maior que zero.")


def intervalo(nome, valor, minimo, maximo, *, incluir_minimo=True, incluir_maximo=True):
    real_finito(nome, valor)
    if ((valor < minimo if incluir_minimo else valor <= minimo)
            or (valor > maximo if incluir_maximo else valor >= maximo)):
        esquerda, direita = ('[' if incluir_minimo else '('), (']' if incluir_maximo else ')')
        raise ValueError(f"{nome} deve pertencer a {esquerda}{minimo}, {maximo}{direita}.")


def inteiro(nome, valor, minimo=1, *, permitir_none=False):
    if permitir_none and valor is None:
        return
    if isinstance(valor, bool) or not isinstance(valor, Integral) or valor < minimo:
        opcional = ' ou None para modo automático' if permitir_none else ''
        raise ValueError(f"{nome} deve ser inteiro e >= {minimo}{opcional}.")


def validar_maquina(N, HTR, phi, psi, AR, n_estagios, n_secoes_avaliacao, angulo, nome_angulo):
    for nome, valor in (('N (rpm)', N), ('phi', phi), ('psi', psi), ('AR', AR)):
        positivo(nome, valor)
    intervalo('HTR', HTR, 0., 1., incluir_minimo=False, incluir_maximo=False)
    intervalo(nome_angulo, angulo, -90., 90., incluir_minimo=False, incluir_maximo=False)
    inteiro('n_estagios', n_estagios, permitir_none=True)
    inteiro('n_secoes_avaliacao', n_secoes_avaliacao, minimo=2)


def verificar_ciclo_resolvido(ciclo):
    """Aceita também fixtures com atributos, sem exigir uma classe concreta."""
    if getattr(ciclo, '_resolvido', True) is False or getattr(ciclo, 'w_líq', None) is None:
        raise RuntimeError("Execute resolver() do ciclo com entradas válidas antes de calcular o componente.")
    real_finito('Trabalho líquido do ciclo', ciclo.w_líq)
    if getattr(ciclo, 'm_dot', None) is None:
        raise RuntimeError("Defina uma vazão mássica positiva no ciclo antes de calcular o componente.")
    positivo('Vazão mássica de ar do ciclo', ciclo.m_dot)
    positivo('cp do ciclo', ciclo.cp)
    real_finito('k do ciclo', ciclo.k)
    if ciclo.k <= 1:
        raise ValueError('k do ciclo deve ser maior que 1.')


def erros_numericos(contexto):
    """Converte falhas aritméticas de domínio em erro legível da API."""
    def decorar(func):
        @wraps(func)
        def executar(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (OverflowError, ZeroDivisionError) as erro:
                raise ValueError(f"{contexto}: parâmetros geraram overflow ou divisão por zero; revise o domínio e a escala das entradas.") from erro
        return executar
    return decorar
