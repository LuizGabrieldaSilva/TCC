"""Condições e falhas das varreduras existentes; sem cálculos adicionais."""

import pandas as pd
import streamlit as st
from engine.webapp.comparison_data import ROTULOS, finito, formatar_entrada
from engine.webapp.number_format import tabela_br, aviso_br

VARREDURAS = {
    'comp_phi':('Compressor · φ','phi','phi_comp',['DF_rotor_max','reacao_min']),
    'comp_psi':('Compressor · ψ','psi','psi_comp',['Z_rotor_min']),
    'comp_htr':('Compressor · HTR','HTR','HTR_comp',['M1R_max']),
    'turb_phi':('Turbina · φ','phi','phi_turb',['deflexao_rotor_max_graus']),
    'turb_psi':('Turbina · ψ','psi','psi_turb',['M3R_max','reacao_min']),
    'turb_htr':('Turbina · HTR','HTR','HTR_turb',['M3R_max']),
    'ciclo_pi':('Ciclo · razão de pressão','r_compr','r_compr',['w_liq_kJ_kg','eta_ciclo_pct','SFC_kg_kWh']),
    'ciclo_tit':('Ciclo · TIT','TIT','TIT',['w_liq_kJ_kg','eta_ciclo_pct','SFC_kg_kWh']),
}


def tabela_pontos(resultados,chave):
    _,param,_,metricas=VARREDURAS[chave];linhas=[]
    for r in resultados:
        faltantes=[m for m in metricas if not finito(r.get(m))]
        valido=r.get('valido',False)
        motivo=r.get('erro','') if not valido else ('Métricas não determinadas: '+', '.join(faltantes) if faltantes else '')
        linhas.append({'Valor do parâmetro':r[param],
                       'Estado':'Calculado' if valido and not faltantes else 'Não calculado/sem métrica',
                       'Estágios adotados':r.get('n_estagios'),
                       'Avisos emitidos':'Sim' if r.get('houve_aviso') else 'Não' if valido else '—',
                       'Motivo':aviso_br(motivo)})
    return pd.DataFrame(linhas)


def exibir_contexto_sensibilidade(sens,parametros):
    with st.expander('Condições das varreduras e pontos não calculados',expanded=False):
        chaves=[k for k in VARREDURAS if k in sens]
        if not chaves:st.info('Nenhuma varredura disponível nesta execução.');return
        chave=st.selectbox('Varredura para conferir',chaves,format_func=lambda k:VARREDURAS[k][0],key='sens_contexto')
        _,_,entrada,_=VARREDURAS[chave]
        st.write(f'**Entrada variada:** {ROTULOS[entrada]}. Os demais valores de entrada são os da execução calculada.')
        if chave.startswith(('comp','turb')):
            comp='comp' if chave.startswith('comp') else 'turb'
            n=parametros[f'n_estagios_{comp}']
            st.caption('Modo desta varredura: '+('automático — os estágios podem mudar a cada ponto; ψ efetivo é recalculado.'
                                               if n is None else f'manual — {n} estágios fixos; ψ mantém o valor solicitado em cada ponto.'))
        else:
            st.caption('As curvas do ciclo avaliam o balanço termodinâmico global; não dimensionam os estágios das turbomáquinas para cada ponto.')
        tabela=tabela_pontos(sens[chave],chave)
        st.dataframe(tabela_br(tabela),hide_index=True,width='stretch')
        if (tabela['Estado']!='Calculado').any():
            st.warning('Há pontos inviáveis ou sem métrica. Eles permanecem na tabela e como lacunas nos gráficos. '
                       'O “×” vermelho na base do gráfico indica a posição do parâmetro; não representa um valor físico no eixo vertical.')
            indices=list(tabela.index[tabela['Estado']!='Calculado'])
            key=f'sens_falha_{chave}'
            if key in st.session_state and st.session_state[key] not in indices:del st.session_state[key]
            indice=st.selectbox('Ponto para ler o motivo completo',indices,key=key,
                format_func=lambda i:formatar_entrada(tabela.loc[i,'Valor do parâmetro']))
            st.write(tabela.loc[indice,'Motivo'])
        else:st.caption('Todos os pontos desta varredura possuem as métricas apresentadas nos gráficos. Isso não equivale a aprovação física.')
        if st.checkbox('Mostrar demais entradas mantidas',key='sens_entradas_fixas'):
            st.dataframe(tabela_br(pd.DataFrame([
                {'Entrada':ROTULOS.get(k,k),'Valor':formatar_entrada(v)}
                for k,v in parametros.items() if k not in (entrada,'N_turb')])),hide_index=True,width='stretch')
            st.caption('São entradas fixas, não resultados fixos: temperaturas, ψ efetivo, geometria e avisos podem mudar com o parâmetro variado. '
                       'As propriedades constantes e os critérios do modelo são os mesmos da execução.')
