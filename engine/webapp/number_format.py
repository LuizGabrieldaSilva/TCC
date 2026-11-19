"""Convenções numéricas da interface, sem modificar dados ou exportações."""

import copy
import math
from numbers import Integral, Real
import re

import pandas as pd
from pandas.io.formats.style import Styler
from matplotlib.ticker import ScalarFormatter


def formato_br(valor, especificacao):
    """Preserva a precisão e a notação solicitadas pelo ponto de exibição."""
    return format(valor, especificacao).translate(str.maketrans({'.': ',', ',': '.'}))


def aviso_br(texto):
    """Só para mensagens de verificações; não usar em citações ou identificadores."""
    return re.sub(r'(?<![\w.,])[-+]?\d+\.\d+(?:[eE][-+]?\d+)?(?![\w.])',
                  lambda m: m[0].replace('.', ','), texto)


def celula_br(valor):
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, Integral):
        return str(valor)
    if isinstance(valor, Real):
        if not math.isfinite(valor):
            return '—'
        return formato_br(valor, '.3e' if 0 < abs(valor) < 1e-4 else ',.4f')
    return valor


def tabela_br(tabela):
    """Formata uma vista; mantém floats, IDs e índices no DataFrame original."""
    if isinstance(tabela, Styler):
        return tabela  # Esses pontos definem precisão/locale explicitamente.
    if not isinstance(tabela, pd.DataFrame):
        return tabela
    formatos = {c: aviso_br if c == 'Aviso e valor/limite' else celula_br for c in tabela.columns}
    return tabela.style.format(formatos, na_rep='—')


class _EscalaBR(ScalarFormatter):
    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace('.', ',')

    def get_offset(self):
        return super().get_offset().replace('.', ',')


def figura_br(fig):
    """Conserva ticks, potências de dez, escala, dados e limites dos eixos."""
    for ax in fig.axes:
        eixos = [ax.xaxis, ax.yaxis]
        if hasattr(ax, 'zaxis'):
            eixos.append(ax.zaxis)
        for eixo in eixos:
            formatter = eixo.get_major_formatter()
            if type(formatter) is ScalarFormatter:
                novo = _EscalaBR(useOffset=formatter.get_useOffset(), useMathText=formatter.get_useMathText())
                eixo.set_major_formatter(novo)
    return fig


def grafico_br(grafico):
    """Locale de apresentação do Vega; dados e expressões continuam numéricos."""
    spec = copy.deepcopy(grafico.to_dict())
    spec.setdefault('config', {})['locale'] = {'number': {
        'decimal': ',', 'thousands': '.', 'grouping': [3], 'currency': ['R$', '']}}
    return type(grafico).from_dict(spec)
