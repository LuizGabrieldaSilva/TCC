"""Nomes e valores legíveis dos critérios; não define prioridades de seleção."""

import pandas as pd

from engine.webapp.energy_indicators import _numero_br


GRUPOS = {'aerodinamica': 'Aerodinâmica', 'geometria': 'Geometria', 'faixas': 'Faixas comparativas'}
NOMES = {
    'reacao_negativa': 'Reação — limite inferior',
    'reacao_acima_de_um': 'Reação — limite superior',
    'Mach_relativo': 'Mach relativo do rotor',
    'Mach_bocal': 'Mach na saída do bocal',
    'DF_rotor': 'Fator de difusão do rotor',
    'DF_estator': 'Fator de difusão do estator',
    'camber': 'Câmber metálico |θ|',
    'psi': 'Coeficiente de carga ψ',
    'reacao': 'Reação — faixa comparativa',
    'swirl_escape': 'Swirl no escape |Cθ/U|',
}
ORIGENS = {'radial': 'Distribuição radial', 'meanline': 'Meanline (raio médio)', 'perfil': 'Geometria do perfil'}


def nome_criterio(detalhe):
    return NOMES[detalhe['criterio']]


def valor_real(detalhe):
    sufixo = '°' if detalhe['unidade'] == '°' else ''
    return _numero_br(detalhe['valor'], 6) + sufixo


def limite_formatado(detalhe):
    inferior, superior = detalhe['limite_inferior'], detalhe['limite_superior']
    sufixo = '°' if detalhe['unidade'] == '°' else ''
    numero = lambda v: _numero_br(v, 6).rstrip('0').rstrip(',') + sufixo
    if inferior is None:
        return '≤ ' + numero(superior)
    if superior is None:
        return '≥ ' + numero(inferior)
    return numero(inferior) + ' a ' + numero(superior)


def local_resumido(detalhe):
    local = detalhe['localizacao']
    partes = [f"Estágio {local['estagio']}" if local['estagio'] is not None else 'Todos os estágios']
    if local['secao'] is not None:
        partes.append('seção ' + local['secao'])
    if local['fileira'] is not None:
        partes.append(local['fileira'])
    partes.append(ORIGENS[local['modelo']])
    return ' · '.join(partes)


def tabela_criterios(detalhes):
    return pd.DataFrame([{
        'Grupo': GRUPOS[d['grupo']], 'Critério': nome_criterio(d),
        'Valor real': valor_real(d), 'Limite / faixa': limite_formatado(d),
        'Localização': local_resumido(d),
        'Excesso normalizado': _numero_br(d['excesso_normalizado'], 8),
    } for d in detalhes])


def tabela_localizacao(detalhe):
    local = detalhe['localizacao']
    return pd.DataFrame([
        ('Critério', nome_criterio(detalhe)),
        ('Valor real / limite', valor_real(detalhe) + ' / ' + limite_formatado(detalhe)),
        ('Origem', ORIGENS[local['modelo']]),
        ('Estágio', str(local['estagio']) if local['estagio'] is not None else 'Todos — carga uniforme'),
        ('Seção radial', local['secao'] if local['secao'] is not None else 'Não se aplica — valor meanline'),
        ('Fileira', local['fileira'] or 'Estágio completo / componente'),
        ('Posição / definição', local['posicao']),
    ], columns=['Campo', 'Informação']).set_index('Campo')
