"""Comparação didática dos estágios já calculados; não resolve modelos."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine import design_criteria as dc


def _extremo(valores, menor=False):
    if not all(math.isfinite(v) for v in valores.values()):
        return float('nan'), 'Não determinado: há seção com valor não finito'
    secao = (min if menor else max)(valores, key=valores.get)
    return valores[secao], secao


def dados_estagios(maquina, radial, componente):
    """Uma linha por estágio, com base/unidade explícitas nos títulos."""
    compressor = componente == 'Compressor'
    linhas = []
    for i in range(maquina.n_estagios):
        mach = radial.M1R[i] if compressor else radial.M3R[i]
        reacoes = radial.R_c[i]
        mach_max, maior_mach = _extremo(mach)
        reacao_min, menor_reacao = _extremo(reacoes, menor=True)
        reacao_max, maior_reacao = _extremo(reacoes)
        linha = {
            'Estágio': i+1,
            'T₀ entrada meanline (K)': maquina.Tt_entrada[i],
            'T₀ saída meanline (K)': maquina.Tt_saida[i],
            'P₀ entrada meanline (kPa)': maquina.Pt_entrada[i]/1000,
            'P₀ saída meanline (kPa)': maquina.Pt_saida[i]/1000,
            'Razão de pressão do estágio (meanline)': maquina.pi_estagio[i],
            'Reação meanline': maquina.grau_reacao[i],
            'Reação mínima radial': reacao_min,
            'Reação máxima radial': reacao_max,
            'Seção da reação mínima': menor_reacao,
            'Seção da reação máxima': maior_reacao,
            'Mach relativo máximo radial': mach_max,
            'Seção do Mach relativo máximo': maior_mach,
            'Pás do rotor Z': maquina.Z_rotor[i],
        }
        if compressor:
            linha.update({
                'Pás do estator Z': maquina.Z_estator[i],
                'DF máximo radial do rotor': _extremo(radial.DF_rotor[i])[0],
                'DF máximo radial do estator': _extremo(radial.DF_estator[i])[0],
            })
        else:
            linha['Pás do bocal Z'] = maquina.Z_bocal[i]
        linhas.append(linha)
    return pd.DataFrame(linhas)


def grupos_graficos(componente):
    grupos = {
        'Temperatura total — meanline': (
            ['T₀ entrada meanline (K)', 'T₀ saída meanline (K)'], 'Temperatura total (K)'),
        'Pressão total — meanline': (
            ['P₀ entrada meanline (kPa)', 'P₀ saída meanline (kPa)'], 'Pressão total (kPa)'),
        'Razão de pressão por estágio — meanline': (
            ['Razão de pressão do estágio (meanline)'], 'Razão de pressão (adimensional)'),
        'Reação — meanline e extremos radiais': (
            ['Reação meanline', 'Reação mínima radial', 'Reação máxima radial'], 'Grau de reação (adimensional)'),
        'Mach relativo — máximo radial': (
            ['Mach relativo máximo radial'], 'Mach relativo (adimensional)'),
        'Número de pás por fileira': (
            ['Pás do rotor Z', 'Pás do estator Z' if componente == 'Compressor' else 'Pás do bocal Z'], 'Número inteiro de pás'),
    }
    if componente == 'Compressor':
        grupos['Difusão — máximos radiais'] = (
            ['DF máximo radial do rotor', 'DF máximo radial do estator'], 'Fator de difusão (adimensional)')
    return grupos


def figura_comparativa(dados, componente, grupo, estagio):
    colunas, unidade = grupos_graficos(componente)[grupo]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for coluna in colunas:
        valores = [v if math.isfinite(v) else float('nan') for v in dados[coluna]]
        ax.plot(dados['Estágio'], valores, marker='o', linewidth=1.5, label=coluna)
    ax.axvline(estagio, color='gray', linestyle=':', linewidth=1, label='Estágio em foco')
    if grupo == 'Mach relativo — máximo radial':
        ax.axhline(dc.MACH_SONICO, color='red', linestyle='--', linewidth=1,
                   label=f"Condição sônica (M={formato_br(dc.MACH_SONICO, f'g')})")
    elif grupo == 'Difusão — máximos radiais':
        ax.axhline(dc.DF_MAX, color='red', linestyle='--', linewidth=1,
                   label=f"Critério de difusão (DF={formato_br(dc.DF_MAX, f'g')})")
    ax.set_title(f'{componente} — {grupo}', fontsize=11)
    ax.set_xlabel('Estágio')
    ax.set_ylabel(unidade)
    ax.set_xticks(dados['Estágio'])
    ax.grid(alpha=.25)
    # A legenda fica fora do campo dos dados e faz parte da altura da figura.
    ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(.5,-.22), ncol=2)
    fig.tight_layout()
    return fig


def exibir_comparacao_estagios(maquina, radial, componente):
    """Retorna índice base zero do estágio em foco na tabela/geometria."""
    chave = componente.lower()
    opcoes = list(range(1, maquina.n_estagios+1))
    # Uma execução nova pode ter menos estágios que a anterior.
    if st.session_state.get(f'estagio_foco_{chave}', 1) not in opcoes:
        st.session_state[f'estagio_foco_{chave}'] = 1
    with st.expander('Comparação entre estágios e estágio em foco', expanded=False):
        st.caption('Compara os estágios desta execução. As linhas conectam resultados discretos; '
                   'não representam o escoamento contínuo dentro das fileiras.')
        c1,c2 = st.columns([1,2])
        estagio = c1.selectbox('Estágio em foco — tabela radial e geometria', opcoes,
                              format_func=lambda x:f'Estágio {x}', key=f'estagio_foco_{chave}')
        grupos = grupos_graficos(componente)
        grupo = c2.selectbox('Grandeza para comparar entre estágios', list(grupos),
                             key=f'grupo_estagios_{chave}')
        dados = dados_estagios(maquina, radial, componente)
        fig = figura_comparativa(dados, componente, grupo, estagio)
        st.pyplot(figura_br(fig), width='stretch')
        plt.close(fig)
        st.caption('Meanline é o valor no raio médio de referência. Extremos radiais são obtidos '
                   'nas seções efetivamente calculadas; não são médias nem uma busca contínua em raio.')
        if grupo.startswith('Reação') and componente == 'Compressor':
            st.caption('A faixa comparativa do verificador de reação do compressor aplica-se ao meanline. '
                       'A reação radial é mostrada para comparação; sua verificação própria sinaliza valores negativos.')
        elif grupo.startswith('Reação'):
            st.caption('Na turbina, a reação estática é a queda de entalpia estática no rotor dividida '
                       'pela queda estática no estágio, conforme a definição usada pelo modelo.')
        if grupo.startswith('Razão de pressão'):
            st.caption('Compressão: P₀ saída / P₀ entrada. Expansão: P₀ entrada / P₀ saída. '
                       'São razões por estágio, não a razão acumulada do componente.')
        if grupo.startswith('Mach'):
            estacao = 'entrada do rotor · estação local 1' if componente == 'Compressor' else 'saída do rotor · estação local 3'
            st.caption(f'Mach relativo: {estacao}. O máximo pode mudar de seção entre estágios.')
        if dados[grupos[grupo][0]].isna().any().any():
            st.warning('Há valores não finitos neste conjunto. O gráfico mantém lacunas; '
                       'consulte os avisos e as seções antes de interpretar os extremos.')
        if st.checkbox('Mostrar valores e localização dos extremos', key=f'tabela_estagios_{chave}'):
            colunas = ['Estágio', *grupos[grupo][0]]
            if grupo.startswith('Reação'):
                colunas += ['Seção da reação mínima','Seção da reação máxima']
            elif grupo.startswith('Mach'):
                colunas += ['Seção do Mach relativo máximo']
            st.dataframe(tabela_br(dados[colunas]), hide_index=True, width='stretch')
        st.caption('A seleção acima controla os resultados radiais e a geometria logo abaixo. '
                   'Os painéis de triângulos e de perfis mantêm seus seletores próprios, identificados em cada painel. '
                   'Critérios e avisos completos permanecem na área de verificações do componente.')
    return estagio-1
