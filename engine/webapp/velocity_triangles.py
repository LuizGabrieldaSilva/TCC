"""Triângulos construídos com as velocidades radiais já resolvidas pelo núcleo."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import altair as alt
import matplotlib.pyplot as plt
from matplotlib.patches import Arc
import pandas as pd
import streamlit as st


CORES = {"C": "#2474b5", "W": "#c45a13", "U": "#28894b"}


def dados_triangulos(radial, componente, estagio, secao):
    """Lê valores do modelo; reconstrói apenas a componente Wθ = Cθ − U."""
    estacoes = (1, 2) if componente == "Compressor" else (2, 3)
    dados = []
    for estacao in estacoes:
        u = radial.U_r[estagio][secao]
        axial = radial.u_ax
        tangencial = getattr(radial, f"v{estacao}")[estagio][secao]
        relativo = tangencial - u
        dados.append(dict(
            estacao=estacao, axial=axial, tangencial=tangencial, U=u,
            W_tangencial=relativo,
            C=getattr(radial, f"V{estacao}")[estagio][secao],
            W=getattr(radial, f"W{estacao}")[estagio][secao],
            alpha=getattr(radial, f"alpha{estacao}")[estagio][secao],
            beta=getattr(radial, f"beta{estacao}")[estagio][secao],
            beta_geometrico=math.degrees(math.atan2(relativo, axial)),
            residuo=math.hypot(axial - axial, tangencial - (u + relativo)),
        ))
    return dados


def _vetores(dado, fator):
    return [
        dict(vetor="C", x=0.0, y=0.0, x2=dado["axial"] / fator,
             y2=dado["tangencial"] / fator, axial=dado["axial"],
             tangencial=dado["tangencial"], modulo=dado["C"]),
        dict(vetor="U", x=0.0, y=0.0, x2=0.0, y2=dado["U"] / fator,
             axial=0.0, tangencial=dado["U"], modulo=dado["U"]),
        dict(vetor="W", x=0.0, y=dado["U"] / fator, x2=dado["axial"] / fator,
             y2=dado["tangencial"] / fator, axial=dado["axial"],
             tangencial=dado["W_tangencial"], modulo=dado["W"]),
    ]


def _limites(dados, fator):
    # Mesmo intervalo nos dois eixos e nos dois triângulos: comprimentos comparáveis.
    valores = [0.0] + [d[chave] / fator for d in dados for chave in ("axial", "tangencial", "U")]
    minimo, maximo = min(valores), max(valores)
    margem = (maximo - minimo) * 0.2 or 1.0
    return [minimo - margem, maximo + margem]


def figura_triangulos(dados, componente, fator=1.0):
    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.7), constrained_layout=True)
    limites = _limites(dados, fator)
    unidade = "m/s" if fator == 1 else "normalizada por U"
    raio_arco = (limites[1] - limites[0]) * 0.11
    for ax, dado, nome in zip(eixos, dados, ("Entrada do rotor", "Saída do rotor")):
        for vetor in _vetores(dado, fator):
            cor = CORES[vetor["vetor"]]
            ax.annotate("", xy=(vetor["x2"], vetor["y2"]), xytext=(vetor["x"], vetor["y"]),
                        arrowprops=dict(arrowstyle="->", color=cor, lw=2.2))
            x = (vetor["x"] + vetor["x2"]) / 2
            y = (vetor["y"] + vetor["y2"]) / 2
            direcao = math.atan2(vetor["y2"] - vetor["y"], vetor["x2"] - vetor["x"])
            ax.annotate(vetor["vetor"], (x, y),
                        xytext=(-13 * math.sin(direcao), 13 * math.cos(direcao)),
                        textcoords="offset points", ha="center", va="center",
                        color=cor, fontweight="bold", fontsize=12,
                        bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1))
        for origem_y, angulo, rotulo, cor in (
            (0, dado["alpha"], "α", CORES["C"]),
            (dado["U"] / fator, dado["beta_geometrico"],
             "−β" if componente == "Compressor" else "β", CORES["W"]),
        ):
            ax.plot([0, raio_arco * 1.4], [origem_y, origem_y], "--", color="#aaaaaa", lw=0.8)
            ax.add_patch(Arc((0, origem_y), raio_arco * 2, raio_arco * 2,
                             theta1=min(0, angulo), theta2=max(0, angulo), color=cor))
            ax.annotate(rotulo, (raio_arco * 1.35, origem_y),
                        xytext=(4, -12 if angulo >= 0 else 12), textcoords="offset points",
                        color=cor, fontsize=10, ha="center", va="center",
                        bbox=dict(facecolor="white", edgecolor="none", alpha=0.9, pad=1))
        ax.set(xlim=limites, ylim=limites, xlabel=f"Componente axial ({unidade})",
               ylabel=f"Componente tangencial ({unidade})",
               title=f"{nome} · estação local {dado['estacao']}")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=0.2)
        ax.axhline(0, color="#aaaaaa", lw=0.7)
        ax.axvline(0, color="#aaaaaa", lw=0.7)
    return fig


def grafico_interativo(dado, dados, fator, titulo, componente="Compressor"):
    vetores = _vetores(dado, fator)
    limites = _limites(dados, fator)
    unidade = "m/s" if fator == 1 else "/ U"
    for v in vetores:
        direcao = math.atan2(v["y2"] - v["y"], v["x2"] - v["x"])
        v["angulo_seta"] = 90 - math.degrees(direcao)
        v["deslocamento_x"] = -15 * math.sin(direcao)
        # Coordenadas de tela crescem para baixo.
        v["deslocamento_y"] = -15 * math.cos(direcao)
        v["xm"], v["ym"] = (v["x"] + v["x2"]) / 2, (v["y"] + v["y2"]) / 2
    arcos, guias, rotulos_angulos = [], [], []
    raio = (limites[1] - limites[0]) * 0.11
    for vetor, origem, angulo, angulo_modelo, rotulo in (
        ("C", 0, dado["alpha"], dado["alpha"], "α"),
        ("W", dado["U"] / fator, dado["beta_geometrico"], dado["beta"],
         "−β" if componente == "Compressor" else "β"),
    ):
        info = dict(vetor=vetor, rotulo=rotulo, angulo_geometrico=angulo, angulo_modelo=angulo_modelo)
        guias.append(dict(x=0, y=origem, x2=raio * 1.4, y2=origem))
        for j in range(25):
            t = math.radians(angulo) * j / 24
            arcos.append(dict(**info, x=raio * math.cos(t), y=origem + raio * math.sin(t), ordem=j))
        rotulos_angulos.append(dict(**info, x=raio * 1.35, y=origem,
                                   deslocamento_y=12 if angulo >= 0 else -12))
    cor = {"field": "vetor", "type": "nominal", "legend": None,
           "scale": {"domain": list(CORES), "range": list(CORES.values())}}
    dica = [{"field": "vetor", "type": "nominal", "title": "Vetor"}] + [
        {"field": campo, "type": "quantitative", "format": ".2f", "title": nome}
        for campo, nome in (("axial", "Componente axial (m/s)"),
                            ("tangencial", "Componente tangencial (m/s)"), ("modulo", "Módulo (m/s)"))]

    def eixos(x, y):
        centro = (limites[0] + limites[1]) / 2
        metade = (limites[1] - limites[0]) / 2
        # O gráfico ocupa a coluna e expande o domínio do eixo mais largo.
        # Assim, uma unidade axial e uma tangencial têm o mesmo tamanho em pixels.
        def dominio(proporcao):
            margem = f"{metade!r} * max({proporcao}, 1)"
            return {"expr": f"[{centro!r} - {margem}, {centro!r} + {margem}]"}
        return {"x": {"field": x, "type": "quantitative", "title": f"Axial ({unidade})",
                      "scale": {"domain": dominio("width / max(height, 1)"), "zero": False, "nice": False}},
                "y": {"field": y, "type": "quantitative", "title": f"Tangencial ({unidade})",
                      "scale": {"domain": dominio("height / max(width, 1)"), "zero": False, "nice": False}}}

    marca_rotulo = {"type": "text", "fontSize": 14, "fontWeight": "bold",
                    "dx": {"expr": "datum.deslocamento_x"},
                    "dy": {"expr": "datum.deslocamento_y"}}
    marca_angulo = {"type": "text", "fontSize": 13, "fontWeight": "bold", "dx": 4,
                    "dy": {"expr": "datum.deslocamento_y"}}
    dica_angulos = [{"field": "rotulo", "type": "nominal", "title": "Ângulo desenhado"}] + [
        {"field": campo, "type": "quantitative", "format": ".2f", "title": nome}
        for campo, nome in (("angulo_geometrico", "Ângulo geométrico (°)"),
                            ("angulo_modelo", "Ângulo na tabela do modelo (°)"))]

    return alt.LayerChart.from_dict({
        "data": {"values": vetores}, "width": 480, "height": 460,
        "title": titulo, "background": "white",
        "autosize": {"type": "fit", "contains": "padding", "resize": True},
        "config": {"axis": {"labelColor": "#303030", "titleColor": "#303030", "tickCount": 5,
                            "gridColor": "#e5e7eb", "gridWidth": 0.7, "domainColor": "#a0a0a0",
                            "tickColor": "#a0a0a0", "labelFontSize": 12, "titleFontSize": 13,
                            "titlePadding": 10},
                   "view": {"stroke": "#dddddd"},
                   "title": {"color": "#202020", "fontSize": 15, "offset": 12}},
        "layer": [
            {"data": {"values": guias}, "mark": {"type": "rule", "strokeDash": [4, 3], "color": "#999999"},
             "encoding": {**eixos("x", "y"), "x2": {"field": "x2"}, "y2": {"field": "y2"}}},
            {"data": {"values": arcos}, "mark": {"type": "line", "strokeWidth": 1.4},
             "encoding": {**eixos("x", "y"), "color": cor, "detail": {"field": "vetor"},
                          "order": {"field": "ordem", "type": "quantitative"}, "tooltip": dica_angulos}},
            {"mark": {"type": "rule", "strokeWidth": 3},
             "encoding": {**eixos("x", "y"), "x2": {"field": "x2"}, "y2": {"field": "y2"},
                          "color": cor, "tooltip": dica}},
            {"mark": {"type": "point", "shape": "triangle-up", "filled": True, "size": 100},
             "encoding": {**eixos("x2", "y2"), "color": cor, "tooltip": dica,
                          "angle": {"field": "angulo_seta", "type": "quantitative",
                                    "scale": None}}},
            {"mark": {**marca_rotulo, "color": "white", "stroke": "white", "strokeWidth": 4},
             "encoding": {**eixos("xm", "ym"), "text": {"field": "vetor"}}},
            {"mark": marca_rotulo,
             "encoding": {**eixos("xm", "ym"), "text": {"field": "vetor"}, "color": cor}},
            {"data": {"values": rotulos_angulos},
             "mark": {**marca_angulo, "color": "white", "stroke": "white", "strokeWidth": 4},
             "encoding": {**eixos("x", "y"), "text": {"field": "rotulo"}}},
            {"data": {"values": rotulos_angulos}, "mark": marca_angulo,
             "encoding": {**eixos("x", "y"), "text": {"field": "rotulo"},
                          "color": cor, "tooltip": dica_angulos}},
        ],
    })


def exibir_triangulos(radial, componente, avisos):
    chave = "tri_comp" if componente == "Compressor" else "tri_turb"
    with st.expander("Triângulos de velocidade — estágio e seção radial", expanded=False):
        st.caption("Usa os resultados desta execução. Alterações no formulário só entram após recalcular o caso.")
        a, b = st.columns(2)
        with a:
            i = st.selectbox("Estágio", range(radial.n_est), format_func=lambda n: f"Estágio {n + 1}",
                             key=f"{chave}_estagio")
        with b:
            s = st.selectbox("Seção radial", radial.secoes, index=len(radial.secoes) // 2,
                             key=f"{chave}_secao")
        normalizado = st.checkbox("Normalizar as velocidades por U da seção selecionada", key=f"{chave}_norm")
        interativo = st.radio("Visualização dos triângulos", ["Imagem", "Interativa"], horizontal=True,
                              key=f"{chave}_modo") == "Interativa"
        dados = dados_triangulos(radial, componente, i, s)
        fator = dados[0]["U"] if normalizado else 1.0
        st.write(f"**{componente} · estágio {i + 1} · seção {s}** — raio {formato_br(radial.r[i][s] * 100, f'.2f')} cm; U = {formato_br(dados[0]['U'], f'.2f')} m/s.")
        st.caption("Axial positivo: sentido do escoamento (direita). Tangencial positivo: sentido da rotação (cima). "
                   "C é a velocidade absoluta (V no código), W é a relativa ao rotor e U é a periférica.")
        if componente == "Compressor":
            st.markdown("**Estações locais:** 1 → rotor → 2 → estator → 3. Os dois desenhos mostram as estações 1 e 2.")
        else:
            st.markdown("**Estações locais:** 1 → bocal → 2 → rotor → 3. Os dois desenhos mostram as estações 2 e 3.")
        if interativo:
            for coluna, d, nome in zip(st.columns(2), dados, ("Entrada do rotor", "Saída do rotor")):
                with coluna:
                    st.altair_chart(grafico_br(grafico_interativo(d, dados, fator, f"{nome} · estação {d['estacao']}", componente)),
                                    width="stretch", height=480, theme=None)
            st.caption("Passe o mouse sobre cada vetor para consultar suas componentes e seu módulo em m/s. "
                       "Os gráficos ajustam-se à largura disponível e preservam a proporção entre "
                       "as componentes axial e tangencial. Os arcos também mostram dicas com os ângulos.")
        else:
            fig = figura_triangulos(dados, componente, fator)
            try:
                st.pyplot(figura_br(fig), width="stretch")
            finally:
                plt.close(fig)
        st.markdown("**C — absoluta (azul) · W — relativa (laranja) · U — periférica (verde)**")
        st.caption("W parte da ponta de U e termina na ponta de C: C = U + W. "
                   + (f"Todos os vetores foram divididos pelo mesmo U = {formato_br(fator, f'.2f')} m/s. " if normalizado else "")
                   + "As tabelas abaixo mantêm as velocidades dimensionais.")
        linhas = []
        for d in dados:
            linhas.append({"Estação local": str(d["estacao"]), "C axial (m/s)": d["axial"],
                           "C tangencial (m/s)": d["tangencial"], "W tangencial (m/s)": d["W_tangencial"],
                           "C (m/s)": d["C"], "W (m/s)": d["W"], "α (°)": d["alpha"], "β do modelo (°)": d["beta"]})
        st.markdown("**Velocidades e ângulos da seção**")
        tabela = pd.DataFrame(linhas)
        st.table(tabela_br(tabela[["Estação local", "C axial (m/s)", "C tangencial (m/s)", "W tangencial (m/s)"]]
                 .style.format(precision=2, decimal=",")), hide_index=True)
        st.table(tabela_br(tabela[["Estação local", "C (m/s)", "W (m/s)", "α (°)", "β do modelo (°)"]]
                 .style.format(precision=2, decimal=",")), hide_index=True)
        modelo = radial.comp if componente == "Compressor" else radial.turb
        sinal = 1 if componente == "Compressor" else -1
        euler = sinal * dados[0]["U"] * (dados[1]["tangencial"] - dados[0]["tangencial"])
        referencia = modelo.cp * modelo.delta_Tt_estagio
        entrada, saida = (1, 2) if componente == "Compressor" else (2, 3)
        euler_meanline = sinal * modelo.U * (
            getattr(modelo, f"v{saida}")[i] - getattr(modelo, f"v{entrada}")[i]
        )
        with st.expander("Como interpretar: sinais, fechamento vetorial e trabalho de Euler"):
            st.latex(r"\vec C=\vec U+\vec W,\qquad C_x=W_x=u_{ax},\qquad W_\theta=C_\theta-U")
            st.latex(r"\alpha=\operatorname{atan2}(C_\theta,u_{ax})")
            if componente == "Compressor":
                st.latex(r"\beta_{\mathrm{modelo}}=\operatorname{atan2}(U-C_\theta,u_{ax})")
                st.write("No compressor, o β tabelado usa o sinal oposto ao ângulo geométrico de W. "
                         "Por isso o arco relativo do desenho é identificado como −β. Os valores da tabela "
                         "preservam a convenção usada no módulo de cálculo.")
                st.latex(r"w_{c,\mathrm{Euler}}=U(C_{\theta2}-C_{\theta1})")
            else:
                st.latex(r"\beta_{\mathrm{modelo}}=\operatorname{atan2}(C_\theta-U,u_{ax})")
                st.write("Na turbina, β usa o próprio sinal geométrico de W: valores negativos indicam "
                         "componente tangencial relativa contrária à rotação.")
                st.latex(r"w_{t,\mathrm{Euler}}=U(C_{\theta2}-C_{\theta3})")
            st.write(f"Trabalho específico {'consumido' if componente == 'Compressor' else 'produzido'}:")
            st.table(tabela_br(pd.DataFrame([
                {"Origem": "Euler — triângulos da seção radial", "Trabalho (kJ/kg)": euler / 1000},
                {"Origem": "Euler — velocidades do meanline", "Trabalho (kJ/kg)": euler_meanline / 1000},
                {"Origem": "cₚ ΔTₜ — queda/elevação por estágio do meanline", "Trabalho (kJ/kg)": referencia / 1000},
            ]).style.format({"Trabalho (kJ/kg)": "{:.4f}"}, decimal=",", thousands=".")), hide_index=True)
            st.write(f"Diferença absoluta entre Euler radial e cₚ ΔTₜ: **{formato_br(abs(euler - referencia), f'.3e')} J/kg**.")
            if not math.isclose(euler, referencia, rel_tol=1e-6, abs_tol=1e-6):
                st.warning("O trabalho radial não recuperou o trabalho meanline dentro da tolerância "
                           "de comparação. Investigue o acoplamento dos resultados desta execução.")
            else:
                st.caption("Euler radial e cₚ ΔTₜ concordam dentro da tolerância de comparação "
                           "(relativa 10⁻⁶; absoluta 10⁻⁶ J/kg). Isso verifica o fechamento interno, "
                           "não substitui a avaliação dos critérios aerodinâmicos.")
            st.caption(f"Raio de referência: {formato_br(modelo.r_mean * 100, f'.5f')} cm, média aritmética entre cubo e ponta constante por componente. U(r) = ωr continua variando ao longo da pá.")
            st.write(f"Maior resíduo |C − (U + W)| nas duas estações: **{formato_br(max((d['residuo'] for d in dados)), f'.3e')} m/s**.")
            st.caption("O fechamento vetorial reconstrói Wθ a partir de Cθ e U; é uma checagem da "
                       "representação, não uma validação física independente. O trabalho é por kg do fluido "
                       "do componente; não compara diretamente as potências do compressor e da turbina. "
                       "Os triângulos usam a velocidade axial constante e a distribuição radial do modelo.")
        locais = [aviso for aviso in avisos if aviso["componente"] == componente
                  and str(aviso.get("estagio")) == str(i + 1)
                  and aviso.get("secao") in (None, s)]
        if locais:
            with st.expander(f"Avisos associados ao estágio/seção selecionados ({len(locais)})"):
                for aviso in locais:
                    st.write(f"**{aviso['origem']}:** {aviso['mensagem']}")
