"""Balanço visual de potências do ciclo resolvido, sem modificar o modelo."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine.webapp.energy_indicators import _numero_br


def dados_balanco(ciclo):
    """Potências em W; trabalhos específicos nas bases usadas pelo ciclo."""
    producao = ciclo.m_dot_turbina*ciclo.w_turb
    consumo = ciclo.m_dot_ar*ciclo.w_compr
    liquida = ciclo.W_líq
    valores = (producao,consumo,liquida,ciclo.m_dot_ar,ciclo.m_dot_turbina,ciclo.w_líq)
    if not all(math.isfinite(v) for v in valores):
        raise ValueError('O balanço visual requer valores finitos do ciclo resolvido.')
    if ciclo.m_dot_ar<=0 or ciclo.m_dot_turbina<=0:
        raise ValueError('O balanço visual requer vazões positivas.')
    return dict(producao_W=producao,consumo_W=consumo,liquida_W=liquida,
                residuo_W=producao-consumo-liquida,
                fracao_consumida=consumo/producao if producao!=0 else None,
                linhas=[
                    {'Grandeza':'Produção da turbina','Trabalho específico (kJ/kg)':ciclo.w_turb/1000,
                     'Base do trabalho':'kg de gases','Vazão (kg/s)':ciclo.m_dot_turbina,'Potência (kW)':producao/1000},
                    {'Grandeza':'Consumo do compressor','Trabalho específico (kJ/kg)':ciclo.w_compr/1000,
                     'Base do trabalho':'kg de ar','Vazão (kg/s)':ciclo.m_dot_ar,'Potência (kW)':consumo/1000},
                    {'Grandeza':'Saldo líquido do ciclo','Trabalho específico (kJ/kg)':ciclo.w_líq/1000,
                     'Base do trabalho':'kg de ar','Vazão (kg/s)':ciclo.m_dot_ar,'Potência (kW)':liquida/1000},
                ])


def figura_balanco(dados):
    """Cascata: produção → retirada do compressor → saldo do ciclo (kW)."""
    turb,comp,liq = (dados[c]/1000 for c in ('producao_W','consumo_W','liquida_W'))
    fig,ax = plt.subplots(figsize=(8,4.4))
    ax.bar(0,turb,width=.58,color='#2474b5')
    # A retirada começa no saldo e alcança a produção da turbina.
    ax.bar(1,comp,bottom=turb-comp,width=.58,color='#d97a22',hatch='//')
    ax.bar(2,liq,width=.58,color='#28894b' if liq>=0 else '#b23a48')
    ax.plot([.29,.71],[turb,turb],color='gray',linestyle=':',linewidth=1)
    ax.plot([1.29,1.71],[turb-comp,turb-comp],color='gray',linestyle=':',linewidth=1)
    escala = max(abs(turb),abs(comp),abs(liq),1.)
    for x,y,texto in ((0,turb,f'+{_numero_br(turb,1)} kW'),
                      (1,turb,f'−{_numero_br(comp,1)} kW'),
                      (2,liq,f'{_numero_br(liq,1)} kW')):
        ax.annotate(texto,(x,y),xytext=(0,8 if y>=0 else -14),textcoords='offset points',
                    ha='center',va='bottom' if y>=0 else 'top',fontsize=10)
    ax.set_ylim(min(0,liq,turb-comp)-.09*escala,max(turb,liq,0)+.15*escala)
    ax.axhline(0,color='gray',linewidth=.8)
    ax.set_xticks([0,1,2],['Turbina\nprodução','Compressor\nretirada do eixo','Ciclo\nsaldo líquido'])
    ax.set_ylabel('Potência (kW)')
    ax.set_title('Balanço de potências no eixo — valores do ciclo',fontsize=11)
    ax.grid(axis='y',alpha=.25)
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def _numero_latex(valor):
    return f'{valor:.2f}'.replace('.',r'{,}')


def exibir_balanco_energetico(ciclo):
    dados = dados_balanco(ciclo)
    with st.expander('Balanço energético visual — potências no eixo',expanded=False):
        st.caption('A turbina produz potência; uma parcela aciona o compressor e o saldo é a potência líquida. '
                   'A barra laranja representa uma retirada: leia os valores e os sinais, além das cores.')
        fig = figura_balanco(dados)
        st.pyplot(figura_br(fig),width='stretch')
        plt.close(fig)
        st.latex(r'\dot W_{\mathrm{liq}}=\dot W_t-\dot W_c')
        st.latex(r'\dot W_{\mathrm{liq}}\approx ('+_numero_latex(dados['producao_W']/1000)
                 +'-'+_numero_latex(dados['consumo_W']/1000)+r')\;\mathrm{kW}\approx '
                 +_numero_latex(dados['liquida_W']/1000)+r'\;\mathrm{kW}')
        if dados['fracao_consumida'] is not None:
            st.write(f"Neste caso, o compressor consome **{_numero_br(dados['fracao_consumida']*100,2)}%** "
                     'da potência produzida pela turbina (**BWR**). Essa razão não é a eficiência térmica.')
        if st.checkbox('Mostrar valores, bases e conversão para potência',key='balanco_energetico_detalhes'):
            tabela = pd.DataFrame(dados['linhas'])
            colunas_numericas = ['Trabalho específico (kJ/kg)', 'Vazão (kg/s)', 'Potência (kW)']
            st.dataframe(tabela_br(tabela.style.format({c: _numero_br for c in colunas_numericas})),
                         hide_index=True,width='stretch')
            st.latex(r'\dot W_t=\dot m_g w_t,\qquad \dot W_c=\dot m_a w_c,\qquad '
                     r'w_{\mathrm{liq},a}=\frac{\dot m_g}{\dot m_a}w_t-w_c')
            st.markdown('**Trabalho específico** é energia por unidade de massa, em kJ/kg. '
                        '**Potência** é energia por tempo, em kW: kg/s × kJ/kg = kJ/s = kW. '
                        'A turbina usa a vazão de gases (ar + combustível); o compressor usa a vazão de ar. '
                        'Por isso, os trabalhos específicos dos dois componentes têm bases de massa diferentes.')
            st.caption(f"Os valores numéricos da equação estão arredondados. Resíduo usando os valores completos (produção − consumo − saldo): {formato_br(dados['residuo_W'], f'.3e')} W. Esse resíduo verifica a identidade do próprio modelo; não é validação experimental.")
        st.caption('Base: resultados do ciclo desta execução, com transmissão mecânica ideal, sem gerador '
                   'ou consumos auxiliares. A potência líquida não é uma previsão de potência elétrica. '
                   'A comparação com os trabalhos dos meanlines permanece no painel de fechamento; '
                   'o balanço de calor e as eficiências estão nos painéis correspondentes.')
    return dados
