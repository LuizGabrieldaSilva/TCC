"""Apresentação das definições e limites dos indicadores do caso executado."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import pandas as pd
import streamlit as st

from engine.indicadores import indicadores_energeticos
from engine import design_criteria as dc


def _numero_br(valor, casas=4):
    """Formata somente a apresentação, sem depender do locale do servidor."""
    return f"{valor:,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))


def exibir_indicadores(ciclo, combustor):
    dados = indicadores_energeticos(ciclo, combustor)
    with st.expander("Indicadores energéticos — definições, bases e hipóteses", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("Eficiência sobre calor útil", f"{_numero_br(dados['eta_calor_util']*100, 2)}%",
                  help="Potência líquida do ciclo dividida pelo calor útil transferido aos gases.")
        c2.metric("Eficiência sobre PCI", f"{_numero_br(dados['eta_PCI']*100, 2)}%",
                  help="Potência líquida do ciclo dividida por vazão de combustível × PCI, incluindo a fração da energia não aproveitada na combustão.")
        c3.metric("SFC", f"{_numero_br(dados['SFC_kg_kWh'])} kg/kWh",
                  help="Consumo de combustível por energia líquida produzida pelo ciclo.")
        st.latex(r"\dot Q_{\mathrm{PCI}}=\dot m_f h_{PR},\quad "
                 r"\dot Q_{\mathrm{util}}=\eta_b\dot Q_{\mathrm{PCI}}")
        st.latex(r"\eta_{\mathrm{util}}=\frac{\dot W_{\mathrm{liq}}}{\dot Q_{\mathrm{util}}},\quad "
                 r"\eta_{\mathrm{PCI}}=\frac{\dot W_{\mathrm{liq}}}{\dot Q_{\mathrm{PCI}}}"
                 r"=\eta_b\eta_{\mathrm{util}}")
        st.table(tabela_br(pd.DataFrame([
            {"Grandeza": "Energia química pelo PCI", "Valor (kW)": _numero_br(dados['energia_combustivel_PCI_W']/1000)},
            {"Grandeza": "Calor útil transferido aos gases", "Valor (kW)": _numero_br(dados['calor_util_W']/1000)},
            {"Grandeza": "Potência líquida do ciclo", "Valor (kW)": _numero_br(dados['potencia_liquida_W']/1000)},
        ]).set_index("Grandeza")))
        st.markdown(
            "A eficiência sobre calor útil considera a energia efetivamente transferida aos gases. "
            "A eficiência sobre PCI considera toda a energia química fornecida pelo combustível, "
            r"incluindo a fração não aproveitada na combustão, representada por $\eta_b$. "
            "O aumento aproximado de entalpia do ar, apresentado na aba Combustor, "
            "não é o denominador dessas eficiências."
        )
        st.latex(r"\dot W_{\mathrm{liq}}=\dot m_g w_t-\dot m_a w_c,\quad "
                 r"w_{\mathrm{liq},a}=(1+f)w_t-w_c,\quad "
                 r"\mathrm{BWR}=\frac{\dot m_a w_c}{\dot m_g w_t}")
        st.latex(r"\mathrm{SFC}\,[\mathrm{kg/kWh}]=\frac{3{,}6\times10^6\dot m_f}{\dot W_{\mathrm{liq}}\,[\mathrm W]}")
        st.caption(
            r"$\dot m_a$ é a vazão de ar; $\dot m_f$, a de combustível; "
            r"$\dot m_g=\dot m_a+\dot m_f$, a de gases. "
            r"O trabalho líquido específico é por kg de ar; $w_t$ é por kg de gás. "
            "BWR é razão de potências. A potência usada é a do ciclo; "
            "diferenças dos meanlines são mostradas no painel de fechamento. Não há rendimento mecânico, "
            "gerador ou consumo auxiliar: a eficiência sobre PCI não é uma eficiência elétrica. "
            "As eficiências politrópicas de entrada e as isentrópicas dos componentes têm definições distintas dessas eficiências globais."
        )
        st.caption(
            "Base: balanço de energia em regime permanente e definições de eficiência térmica e consumo específico, "
            "discutidos em Gas Turbine Theory (Saravanamuttoo et al., análise de ciclos) e Elements of Gas Turbine "
            r"Propulsion (Mattingly, análise de desempenho). Aplicam-se as hipóteses locais: gás ideal, $c_p$ constante, "
            r"$c_p$ distinto por região e $k=c_p/(c_p-R)$. No modo composição automática, "
            "entalpias sensíveis relativas a 298,15 K e cp equivalente NASA mantido constante na expansão; "
            "no prescrito, convenção legada h=cp·T. Combustível sem entalpia sensível explícita."
        )
    return dados


def exibir_origem_criterios():
    with st.expander("Como interpretar os critérios e suas origens", expanded=False):
        st.table(tabela_br(pd.DataFrame([
            (f"Mach = {_numero_br(dc.MACH_SONICO, 0)}", "Definição física de condição sônica; não é, por si só, limite universal de projeto de turbomáquinas."),
            (f"DF ≤ {_numero_br(dc.DF_MAX, 1)}", "Critério empírico de Lieblein para cascatas de compressor, discutido em Dixon & Hall; triagem de difusão, não previsão completa de separação."),
            (f"Reação: {_numero_br(dc.REACAO_COMP[0], 1)}–{_numero_br(dc.REACAO_COMP[1], 1)} (compressor); "
             f"{_numero_br(dc.REACAO_TURB[0], 1)}–{_numero_br(dc.REACAO_TURB[1], 1)} (turbina)", "Faixas comparativas adotadas no projeto. Não constituem exigências universais da literatura; a definição de reação e a localização devem ser conferidas."),
            (f"Bocal: M2 > {_numero_br(dc.MACH_BOCAL_TURBINA, 1)}; escape: |Cθ/U| > {_numero_br(dc.SWIRL_ESCAPE_MAX, 2)}", "Limiares de aviso adotados no código, não limites físicos universais. O swirl de escape é verificado no último estágio."),
            (f"Diferença ciclo–meanline: {_numero_br(dc.FECHAMENTO_AVISO_PCT, 0)}%", "Limiar de emissão de aviso do código; diferenças menores continuam visíveis no painel de fechamento e não significam igualdade."),
            (f"Câmber circular > {_numero_br(dc.CAMBER_COMP_GRAUS, 0)}° (compressor); > {_numero_br(dc.CAMBER_TURB_GRAUS, 0)}° (turbina)", "Limiares geométricos adotados no projeto; não são limites universais de deflexão nem validação aerodinâmica ou estrutural da pá."),
        ], columns=["Critério", "Origem e alcance"])))
        st.caption(
            "Resumo dos principais critérios; cada mensagem conserva seu valor, operador e localização. "
            "As faixas do combustor e as fontes das propriedades dos combustíveis estão descritas na aba Combustor. "
            "Ausência de aviso não garante estabilidade de combustão, margem de estol, integridade estrutural ou validade fora das hipóteses. "
            "Nenhum limite foi alterado nesta apresentação."
        )
