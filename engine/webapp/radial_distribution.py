"""Leitura dos resultados radiais e conferência didática de vórtice livre."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine import design_criteria as dc


def grupos_radiais(componente):
    if componente == 'Compressor':
        return {
            'Ângulos absolutos': (['alpha1', 'alpha2'], ['α₁', 'α₂'], 'Ângulo absoluto (°)'),
            'Ângulos relativos do modelo': (['beta1', 'beta2'], ['β₁', 'β₂'], 'Ângulo relativo do modelo (°)'),
            'Mach na entrada do rotor': (['M1', 'M1R'], ['M₁ absoluto', 'M₁R relativo'], 'Mach (adimensional)'),
            'Reação': (['R_c'], ['Reação radial'], 'Grau de reação (adimensional)'),
            'Fator de difusão': (['DF_rotor', 'DF_estator'], ['DF rotor', 'DF estator'], 'Fator de difusão (adimensional)'),
        }
    return {
        'Ângulos absolutos': (['alpha1', 'alpha2', 'alpha3'], ['α₁', 'α₂', 'α₃'], 'Ângulo absoluto (°)'),
        'Ângulos relativos do modelo': (['beta2', 'beta3'], ['β₂', 'β₃'], 'Ângulo relativo do modelo (°)'),
        'Mach absoluto': (['M1', 'M2', 'M3'], ['M₁', 'M₂', 'M₃'], 'Mach absoluto (adimensional)'),
        'Mach relativo': (['M2R', 'M3R'], ['M₂R', 'M₃R'], 'Mach relativo (adimensional)'),
        'Reação estática': (['R_c'], ['Reação estática radial'], 'Grau de reação estática (adimensional)'),
    }


def dados_radiais(radial, componente, estagio):
    """Estágio base zero; preserva todas as seções e valores do núcleo."""
    campos = list(dict.fromkeys(c for cols, _, _ in grupos_radiais(componente).values() for c in cols))
    return pd.DataFrame([
        {'Seção': s, 'Raio (cm)': radial.r[estagio][s]*100,
         **{c:getattr(radial,c)[estagio][s] for c in campos}}
        for s in radial.secoes
    ])


def estacoes_vortice(componente):
    if componente == 'Compressor':
        return {1:'1 — entrada do rotor', 2:'2 — saída do rotor / entrada do estator'}
    return {1:'1 — entrada do bocal', 2:'2 — saída do bocal / entrada do rotor', 3:'3 — saída do rotor'}


def dados_vortice(radial, componente, estagio, estacao):
    """r Cθ e resíduo assinado, em m²/s; percentual usa |referência|."""
    if estacao not in estacoes_vortice(componente):
        raise ValueError('Estação não disponível para este componente.')
    maquina = radial.comp if componente == 'Compressor' else radial.turb
    campo = f'v{estacao}'  # v minúsculo no núcleo é Cθ; V maiúsculo é módulo.
    referencia = maquina.r_mean*getattr(maquina,campo)[estagio]
    linhas = []
    for s in radial.secoes:
        raio, tangencial = radial.r[estagio][s], getattr(radial,campo)[estagio][s]
        produto = raio*tangencial
        residuo = produto-referencia
        percentual = 100*residuo/abs(referencia) if referencia != 0 else None
        linhas.append({'Seção':s, 'Raio (cm)':raio*100, 'Cθ (m/s)':tangencial,
                       'r·Cθ (m²/s)':produto, 'Referência meanline (m²/s)':referencia,
                       'Diferença (m²/s)':residuo, 'Diferença relativa (%)':percentual})
    return pd.DataFrame(linhas)


def _eixo_radial(ax, dados, secao):
    # Manter cubo, ponta e seção escolhida legíveis também em malhas maiores.
    n = len(dados)
    passo = max(1, math.ceil(n/9))
    indices = sorted({0,n-1,*range(0,n,passo),int(dados.index[dados['Seção']==secao][0])})
    ax.set_xticks([dados.iloc[i]['Raio (cm)'] for i in indices],
                  [f"{formato_br(dados.iloc[i]['Raio (cm)'], f'.2f')}\n{dados.iloc[i]['Seção']}" for i in indices])
    raio = dados.loc[dados['Seção']==secao,'Raio (cm)'].iloc[0]
    ax.axvline(raio,color='gray',linestyle=':',linewidth=1,label=f'Seção em foco: {secao}')
    ax.set_xlabel('Raio (cm) e seção — cubo (hub) → ponta (tip)')
    ax.grid(alpha=.25)


def figura_radial(dados, componente, grupo, secao):
    campos, rotulos, unidade = grupos_radiais(componente)[grupo]
    fig, ax = plt.subplots(figsize=(8,4.6))
    for campo, rotulo in zip(campos,rotulos):
        valores = [v if math.isfinite(v) else float('nan') for v in dados[campo]]
        ax.plot(dados['Raio (cm)'],valores,marker='o',label=rotulo)
    if grupo.startswith('Mach'):
        ax.axhline(dc.MACH_SONICO,color='red',linestyle='--',linewidth=1,label='Condição sônica (M=1)')
    if grupo == 'Fator de difusão':
        ax.axhline(dc.DF_MAX,color='red',linestyle='--',linewidth=1,label=f"Critério de difusão (DF={formato_br(dc.DF_MAX, f'g')})")
    _eixo_radial(ax,dados,secao)
    ax.set_ylabel(unidade)
    ax.set_title(f'{componente} — {grupo}',fontsize=11)
    ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.25),ncol=2)
    fig.tight_layout()
    return fig


def figura_vortice(dados, componente, estacao, secao):
    fig, ax = plt.subplots(figsize=(8,4.6))
    valores = [v if math.isfinite(v) else float('nan') for v in dados['r·Cθ (m²/s)']]
    referencia = dados['Referência meanline (m²/s)'].iloc[0]
    ax.plot(dados['Raio (cm)'],valores,marker='o',label='r·Cθ calculado em cada seção')
    ax.axhline(referencia,color='#c45a13',linestyle='--',label='rₘ·Cθ,ₘ — referência meanline')
    finitos = [v for v in valores if math.isfinite(v)]
    if finitos and math.isfinite(referencia) and max(finitos)-min(finitos) <= 1e-8*max(1,abs(referencia)):
        # Evita ampliar ruído de arredondamento até parecer variação física.
        margem = max(.02*abs(referencia),1e-6)
        ax.set_ylim(referencia-margem,referencia+margem)
    _eixo_radial(ax,dados,secao)
    ax.set_ylabel('r·Cθ (m²/s)')
    ax.set_title(f'{componente} — vórtice livre · estação local {estacao}',fontsize=11)
    ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.25),ncol=2)
    fig.tight_layout()
    return fig


def _destacar_secao(tabela, secao):
    estilo = tabela.style.apply(lambda linha:['background-color: rgba(255,165,0,0.15)' if linha['Seção']==secao else ''
                                              for _ in linha],axis=1).format(precision=6,na_rep='—',decimal=',',thousands='.')
    residuos = [c for c in ('Diferença (m²/s)','Diferença relativa (%)') if c in tabela.columns]
    if residuos:
        estilo = estilo.format('{:.3e}',subset=residuos,na_rep='—', decimal=",", thousands=".")
    return estilo


def exibir_distribuicao_radial(radial, componente, estagio):
    chave = componente.lower()
    sec_key = f'radial_secao_{chave}'
    if st.session_state.get(sec_key,radial.secoes[len(radial.secoes)//2]) not in radial.secoes:
        del st.session_state[sec_key]
    with st.expander('Distribuição radial — do cubo à ponta e vórtice livre',expanded=False):
        st.caption(f'Estágio em foco: {estagio+1}. Para mudar o estágio, use o seletor em '
                   '“Comparação entre estágios e estágio em foco”, logo acima. '
                   f'Esta execução possui {len(radial.secoes)} seções radiais.')
        c1,c2 = st.columns([1,2])
        secao = c1.selectbox('Seção radial em foco',radial.secoes,index=len(radial.secoes)//2,key=sec_key)
        grupos = grupos_radiais(componente)
        grupo = c2.selectbox('Grandeza para comparar ao longo do raio',list(grupos),key=f'radial_grupo_{chave}')
        dados = dados_radiais(radial,componente,estagio)
        aba_grandezas, aba_vortice = st.tabs(['Grandezas ao longo do raio','Conferência de r·Cθ'])
        with aba_grandezas:
            fig = figura_radial(dados,componente,grupo,secao)
            st.pyplot(figura_br(fig),width='stretch')
            plt.close(fig)
            st.caption('Os pontos são resultados nas seções calculadas; as linhas apenas os conectam. '
                       'Cθ é a velocidade tangencial absoluta. As convenções de α e β são as do núcleo, '
                       'explicadas no painel de triângulos de velocidade.')
            if grupo.startswith('Reação'):
                st.caption('A reação varia com o raio. A faixa comparativa do compressor é verificada no meanline; '
                           'na turbina a reação usa quedas de entalpia estática de rotor e estágio. '
                           'Consulte os avisos do componente para os critérios efetivamente aplicados.')
            if st.checkbox('Mostrar valores radiais',key=f'radial_tabela_{chave}'):
                campos,rotulos,_ = grupos[grupo]
                tabela = dados[['Seção','Raio (cm)',*campos]].rename(columns=dict(zip(campos,rotulos)))
                st.dataframe(tabela_br(_destacar_secao(tabela,secao)),hide_index=True,width='stretch')
        with aba_vortice:
            st.markdown('**Hipótese de vórtice livre.** Em cada estação, o modelo impõe '
                        'que raio × velocidade tangencial absoluta permaneça constante ao longo da altura da pá.')
            st.latex(r'r\,C_\theta(r)=r_m\,C_{\theta,m},\qquad C_\theta(r)=C_{\theta,m}\frac{r_m}{r}')
            estacoes = estacoes_vortice(componente)
            estacao = st.selectbox('Estação local para conferir r·Cθ',list(estacoes),
                                  format_func=estacoes.get,key=f'radial_estacao_{chave}')
            conferencia = dados_vortice(radial,componente,estagio,estacao)
            fig = figura_vortice(conferencia,componente,estacao,secao)
            st.pyplot(figura_br(fig),width='stretch')
            plt.close(fig)
            st.caption('A constante pode mudar entre estações e estágios: o rotor altera a velocidade tangencial. '
                       'Esta conferência verifica a implementação de uma relação imposta pelo modelo; '
                       'não constitui validação independente do escoamento real.')
            if st.checkbox('Mostrar constantes e diferenças por seção',key=f'radial_constantes_{chave}'):
                st.dataframe(tabela_br(_destacar_secao(conferencia,secao)),hide_index=True,width='stretch')
            st.caption('Diferença = r·Cθ − rₘ·Cθ,ₘ. Percentual = 100 × diferença / |referência|; '
                       'quando a referência é zero, o percentual fica “—” e a diferença absoluta continua disponível. '
                       'Resíduos muito pequenos podem ser de arredondamento numérico.')
        st.caption('A seção em foco é destacada pela linha pontilhada e pela linha da tabela. '
                   'Mais seções refinam a amostragem; não eliminam as hipóteses 1D, de velocidade axial '
                   'prescrita e de vórtice livre. O painel usa os dados da última execução calculada.')
