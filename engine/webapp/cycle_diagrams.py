"""Apresentação dos estados totais do ciclo; não modifica o objeto calculado."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

_CORES = {
    "Compressor: 01 → 02": "#2474b5",
    "Combustor: 02 → 03": "#c45a13",
    "Turbina: 03 → 04": "#28894b",
    "Rejeição de calor equivalente: 04 → 01": "#808080",
    "Compressor isentrópico: 01 → 02s": "#8060a8",
    "Turbina isentrópica: 03 → 04s": "#8060a8",
}


def estados_ciclo(ciclo, ts_equivalente=False):
    """Grandezas equivalentes derivadas dos estados e propriedades do próprio ciclo."""
    condicoes = (
        ("01", "Entrada do compressor", ciclo.T01, ciclo.P01),
        ("02", "Saída do compressor", ciclo.T02r, ciclo.P02),
        ("03", "Saída do combustor / entrada da turbina", ciclo.TIT, ciclo.P03),
        ("04", "Saída da turbina", ciclo.T04r, ciclo.P04),
    )
    estados = []
    for i, (nome, local, temp, pressao) in enumerate(condicoes):
        gas = i >= 2
        cp, r = (ciclo.cp_gases, ciclo.R_gases) if gas else (ciclo.cp_ar, ciclo.R_ar)
        t_ref, p_ref = (ciclo.TIT, ciclo.P03) if gas else (ciclo.T01, ciclo.P01)
        cp_s, r_s = cp, r
        if ts_equivalente:
            cp_s, r_s = ciclo.cp_ar, ciclo.R_ar
            t_ref, p_ref = ciclo.T01, ciclo.P01
        estados.append(dict(estado=nome, local=local, T=temp, P=pressao/1000,
                            v=r*temp/pressao,
                            s=(cp_s*math.log(temp/t_ref)-r_s*math.log(pressao/p_ref))/1000,
                            modo_ts='equivalente' if ts_equivalente else 'componente',
                            fluido=('Fluido de referência único: 01' if ts_equivalente else
                                    'Gases: referência 03' if gas else 'Ar: referência 01')))
    return estados


def ideais_ciclo(ciclo, estados, ts_equivalente=False):
    """Referências auxiliares do desenho; não altera os estados do ciclo."""
    ideais = []
    for nome, indice, temp, pressao, rotulo in (
        ('Compressor isentrópico: 01 → 02s',0,ciclo.T02s,ciclo.P02,'02s'),
        ('Turbina isentrópica: 03 → 04s',2,ciclo.T04s,ciclo.P04,'04s'),
    ):
        cp, r = (ciclo.cp_ar,ciclo.R_ar) if indice==0 else (ciclo.cp_gases,ciclo.R_gases)
        t_ref,p_ref = (ciclo.T01,ciclo.P01) if indice==0 else (ciclo.TIT,ciclo.P03)
        if ts_equivalente:
            cp,r = ciclo.cp_ar,ciclo.R_ar
            inicio=estados[indice]
            temp=inicio['T']*(pressao/(inicio['P']*1000))**(r/cp)
            t_ref,p_ref=ciclo.T01,ciclo.P01
        fim=dict(estado=rotulo,local=nome,T=temp,P=pressao/1000,v=r*temp/pressao,
                 s=(cp*math.log(temp/t_ref)-r*math.log(pressao/p_ref))/1000)
        ideais.append((nome,estados[indice],fim))
    return ideais


def _ts_equivalente(estados):
    return estados[0].get('modo_ts')=='equivalente'


def _rotulo_entropia(estados):
    return ('Entropia equivalente (kJ/(kg·K))' if _ts_equivalente(estados) else
            'Variação de entropia relativa por fluido (kJ/(kg·K))')


def _diagrama(estados, eixo_x, eixo_y, titulo, selecionados, ideais, habilitar_zoom=False):
    nomes = {"v": "Volume específico total equivalente (m³/kg)",
             "s": _rotulo_entropia(estados),
             "P": "Pressão total (kPa)", "T": "Temperatura total (K)"}
    processos = ("Compressor: 01 → 02", "Combustor: 02 → 03", "Turbina: 03 → 04")
    linhas = []
    for i, processo in enumerate(processos):
        if eixo_x == 's' and not _ts_equivalente(estados) and i == 1:
            continue  # Não conectar entropias de fluidos/referências diferentes.
        for ordem, estado in enumerate(estados[i:i + 2]):
            linhas.append({**estado, "processo": processo, "ordem": ordem,
                           "tipo": "Ligação esquemática"})
    for ordem, estado in enumerate((estados[3], estados[0])):
        if eixo_x == 's' and not _ts_equivalente(estados):
            continue
        linhas.append({**estado, "processo": "Rejeição de calor equivalente: 04 → 01",
                       "ordem": ordem, "tipo": "Retorno equivalente"})
    for nome, inicio, fim in ideais:
        for ordem, estado in enumerate((inicio, fim)):
            linhas.append({**estado, "processo": nome, "ordem": ordem,
                           "tipo": "Referência isentrópica"})
    todos_estados = estados + [fim for _, _, fim in ideais]

    def dominio(campo):
        valores = [e[campo] for e in todos_estados]
        minimo, maximo = min(valores), max(valores)
        margem = (maximo - minimo) * 0.09 or 1.0
        return [minimo - margem, maximo + margem]

    eixos = {
        "x": {"field": eixo_x, "type": "quantitative", "title": nomes[eixo_x],
              "scale": {"zero": False, "domain": dominio(eixo_x)}},
        "y": {"field": eixo_y, "type": "quantitative", "title": nomes[eixo_y],
              "scale": {"zero": False, "domain": dominio(eixo_y)}},
    }
    tooltip = [{"field": "estado", "type": "nominal", "title": "Estado"},
               {"field": "local", "type": "nominal", "title": "Localização"}]
    tooltip += [{"field": campo, "type": "quantitative", "title": nomes[campo],
                 "format": ".4g"} for campo in ("T", "P", "v", "s")]
    pontos = [{**e, "destaque": e["estado"] in selecionados, "ideal": False} for e in estados]
    pontos += [{**fim, "destaque": False, "ideal": True} for _, _, fim in ideais]
    especificacao = {
        "title": titulo, "height": 380, "background": "#ffffff",
        "autosize": {"type": "fit", "contains": "padding", "resize": True},
        "config": {
            "axis": {"labelColor": "#303030", "titleColor": "#303030",
                     "gridColor": "#e5e5e5", "labelFontSize": 11,
                     "titleFontSize": 12, "titlePadding": 12, "tickCount": 6},
            "title": {"color": "#202020", "fontSize": 15, "anchor": "start"},
            "view": {"stroke": "#cccccc"},
        },
        # A seleção precisa pertencer a uma única camada. Sem views, o Vega-Lite
        # pode gerar sinais de zoom duplicados para linhas, pontos e rótulos.
        "params": [{"name": f"zoom_{eixo_x}", "select": "interval", "bind": "scales",
                    "views": [f"trajetorias_{eixo_x}"]}],
        "layer": [
            {"name": f"trajetorias_{eixo_x}",
             "data": {"values": linhas}, "mark": {"type": "line", "strokeWidth": 2},
             "encoding": {**eixos,
                 "color": {"field": "processo", "type": "nominal", "title": "Processo",
                           "scale": {"domain": list(_CORES), "range": list(_CORES.values())},
                           "legend": None},
                 "strokeDash": {"field": "tipo", "type": "nominal",
                                "scale": {"domain": ["Ligação esquemática", "Retorno equivalente",
                                                     "Referência isentrópica"],
                                          "range": [[1, 0], [6, 4], [2, 4]]}, "legend": None},
                 "detail": {"field": "processo"}, "order": {"field": "ordem"},
                 "tooltip": [{"field": "processo"}, {"field": "tipo"}]}},
            {"data": {"values": pontos},
             "mark": {"type": "point", "filled": True, "stroke": "#333333", "strokeWidth": 1},
             "encoding": {**eixos, "tooltip": tooltip,
                 "shape": {"condition": {"test": "datum.ideal", "value": "square"},
                           "value": "circle"},
                 "size": {"condition": {"test": "datum.destaque", "value": 170}, "value": 75},
                 "color": {"condition": {"test": "datum.destaque", "value": "#ffae42"},
                           "value": "#6cb5ff"}}},
            {"data": {"values": pontos}, "transform": [{"filter": "!datum.ideal"}],
             "mark": {"type": "text", "dx": 8, "dy": -13, "align": "left",
                      "fontWeight": "bold", "fontSize": 12, "color": "#202020"},
             "encoding": {**eixos, "text": {"field": "estado"}}},
            {"data": {"values": pontos}, "transform": [{"filter": "datum.ideal"}],
             "mark": {"type": "text", "dx": 8, "dy": 15, "align": "left",
                      "fontSize": 11, "color": "#604080"},
             "encoding": {**eixos, "text": {"field": "estado"}}},
        ],
    }
    if not habilitar_zoom:
        del especificacao["params"]
    return especificacao


def _legenda_interativa(mostrar_ideais):
    """Legenda no fluxo da página, independente da altura do canvas Vega."""
    itens = []
    for i, (nome, cor) in enumerate(_CORES.items()):
        if i >= 4 and not mostrar_ideais:
            continue
        traco = "solid" if i < 3 else "dashed" if i == 3 else "dotted"
        itens.append(
            "<div style='display:flex;align-items:center;gap:.55rem;min-width:0;'>"
            f"<span style='flex:0 0 26px;border-top:3px {traco} {cor};'></span>"
            f"<span style='overflow-wrap:anywhere;'>{nome}</span></div>"
        )
    st.markdown("**Legenda dos dois diagramas**")
    st.markdown(
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));"
        "gap:.65rem 1.25rem;margin:.3rem 0 1rem;font-size:.9rem;'>"
        + "".join(itens) + "</div>", unsafe_allow_html=True,
    )


def _figura_diagrama(estados, eixo_x, eixo_y, titulo, selecionados, ideais):
    """Imagem independente do renderizador JavaScript, com os mesmos dados."""
    rotulos = {"v": "Volume específico total equivalente (m³/kg)",
               "s": _rotulo_entropia(estados),
               "P": "Pressão total (kPa)", "T": "Temperatura total (K)"}
    fig, ax = plt.subplots(figsize=(7, 5.2), constrained_layout=True)
    for i, (nome, cor) in enumerate((('Compressor: 01 → 02', '#2474b5'),
                                    ('Combustor: 02 → 03', '#c45a13'),
                                    ('Turbina: 03 → 04', '#28894b'))):
        if eixo_x == 's' and not _ts_equivalente(estados) and i == 1:
            continue
        a, b = estados[i:i + 2]
        ax.plot([a[eixo_x], b[eixo_x]], [a[eixo_y], b[eixo_y]], color=cor, label=nome)
        ax.annotate('', xy=((a[eixo_x] + 2 * b[eixo_x]) / 3,
                            (a[eixo_y] + 2 * b[eixo_y]) / 3),
                    xytext=((2 * a[eixo_x] + b[eixo_x]) / 3,
                            (2 * a[eixo_y] + b[eixo_y]) / 3),
                    arrowprops=dict(arrowstyle='->', color=cor))
    a, b = estados[3], estados[0]
    if eixo_x != 's' or _ts_equivalente(estados):
        ax.plot([a[eixo_x], b[eixo_x]], [a[eixo_y], b[eixo_y]], '--', color='gray',
                label='04 → 01: rejeição de calor equivalente')
    for nome, inicio, fim in ideais:
        ax.plot([inicio[eixo_x], fim[eixo_x]], [inicio[eixo_y], fim[eixo_y]],
                ':', color='#8060a8', label=nome)
        ax.scatter(fim[eixo_x], fim[eixo_y], marker='s', color='#8060a8', s=35)
        ax.annotate(fim['estado'], (fim[eixo_x], fim[eixo_y]), xytext=(7, -14),
                    textcoords='offset points', fontsize=9)
    for e in estados:
        destaque = e['estado'] in selecionados
        ax.scatter(e[eixo_x], e[eixo_y], s=90 if destaque else 40,
                   color='#ffae42' if destaque else '#6cb5ff', edgecolors='#333333', zorder=4)
        ax.annotate(e['estado'], (e[eixo_x], e[eixo_y]), xytext=(7, 8),
                    textcoords='offset points', fontsize=10, fontweight='bold')
    ax.set(title=titulo, xlabel=rotulos[eixo_x], ylabel=rotulos[eixo_y])
    ax.grid(alpha=0.22)
    ax.margins(0.15)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), fontsize=8, frameon=False)
    return fig


def exibir_visao_ciclo(ciclo):
    estados = estados_ciclo(ciclo)
    st.subheader("Percurso do fluido e estados do ciclo")
    st.caption("Esquema funcional, sem escala geométrica. As setas indicam o sentido do escoamento.")
    componente = st.radio("Componente em destaque", ["Todos", "Compressor", "Combustor", "Turbina"],
                          horizontal=True, key="ciclo_componente_visual")
    pares = {"Compressor": (0, 1), "Combustor": (1, 2), "Turbina": (2, 3)}
    selecionados = {e["estado"] for e in estados} if componente == "Todos" else {
        estados[i]["estado"] for i in pares[componente]}
    explicacoes = {
        "Compressor": "Recebe trabalho do eixo e eleva a pressão e a temperatura totais do ar.",
        "Combustor": "Recebe combustível, eleva a temperatura até a TIT e aplica a perda de pressão prescrita.",
        "Turbina": "Expande os gases e fornece trabalho ao eixo; recebe a vazão de ar acrescida do combustível.",
    }
    for coluna, (nome, (a, b)) in zip(st.columns(3), pares.items()):
        with coluna:
            with st.container(border=True):
                st.markdown(f"**{'● ' if componente in ('Todos', nome) else ''}{nome} →**")
                st.caption(explicacoes[nome])
                for i in (a, b):
                    e = estados[i]
                    st.markdown(f"**{e['estado']}** · {formato_br(e['T'], f'.2f')} K · {formato_br(e['P'], f'.2f')} kPa")
    st.caption("01 → 02 → 03 → 04 são estações globais do ciclo. Os índices locais dos estágios "
               "do compressor e da turbina têm outra definição. O difusor compressor–combustor não é modelado.")

    st.subheader("Diagramas termodinâmicos do caso")
    ts_equivalente = st.radio(
        'Como observar o diagrama T–s',
        ['Ciclo equivalente — visão didática','Por componente — propriedades do modelo'],
        key='ciclo_modo_ts',
        help='Altera somente o desenho T–s. Temperaturas, pressões, potência e eficiência do caso permanecem as mesmas.',
    ) == 'Ciclo equivalente — visão didática'
    if ts_equivalente:
        st.info('Visão didática: as quatro etapas são conectadas usando um fluido de referência único, '
                'com cp e R do ar desta execução. Temperaturas e pressões vêm do caso calculado. '
                'O trecho do combustor não representa a mudança real de entropia da reação química e da mistura.')
    else:
        st.info('Visão por componente: a compressão usa as propriedades do ar e a expansão usa as dos gases. '
                'Cada trecho tem seu próprio zero de entropia: s01=0 e s03=0. As linhas desconectadas não '
                'representam interrupção do escoamento. A separação horizontal não mede uma perda no combustor.')
    with st.expander('Qual é a diferença entre estas visualizações?'):
        st.markdown(
            '**Duas maneiras de observar o mesmo caso.** Para compreender a sequência de funcionamento, '
            'comece pelo ciclo equivalente. Para examinar as variações calculadas com as propriedades de cada '
            'fluido, escolha a visão por componente. Alternar entre elas não recalcula o motor nem altera potência ou eficiência.\n\n'
            '**O que acontece em cada etapa?** No compressor (01 → 02), o ar é comprimido e sua temperatura '
            'aumenta. No combustor (02 → 03), a queima aquece o escoamento até a temperatura de entrada da '
            'turbina. Na turbina (03 → 04), os gases se expandem, esfriam e fornecem trabalho ao eixo.\n\n'
            '**Por que usar um ciclo equivalente?** No motor, o ar recebe combustível e se transforma em '
            'uma mistura com outras propriedades. Para organizar todas as etapas em um desenho conectado, '
            'a visão equivalente usa propriedades únicas de referência, iguais às do ar desta execução. '
            'As temperaturas e pressões são as calculadas; a posição horizontal dos pontos usa essa simplificação. '
            'Os cálculos dos componentes continuam usando suas respectivas propriedades.\n\n'
            '**Por que as linhas ficam separadas na outra visão?** A compressão e a expansão usam propriedades '
            'e referências próprias: o início de cada trecho recebe valor zero. Por isso, suas posições '
            'horizontais não podem ser comparadas para medir o efeito do combustor. Essa separação é uma '
            'convenção do desenho, não um defeito físico do motor.\n\n'
            '**Como ler o eixo da entropia?** A entropia é uma propriedade usada para descrever os estados '
            'do fluido e analisar transformações de energia. O deslocamento horizontal não é uma medida direta '
            'da quantidade de calor perdido nem da eficiência da máquina.\n\n'
            '**O que significa o retorno tracejado?** A ligação 04 → 01 fecha o desenho equivalente do Brayton. '
            'Na máquina aberta, os gases saem para o ambiente e uma nova quantidade de ar entra; o mesmo fluido '
            'não retorna diretamente ao compressor. Na visão por componente, esse retorno não é desenhado.\n\n'
            '**Como interpretar as linhas pontilhadas?** São referências de compressão e expansão sem geração '
            'de entropia. No T–s equivalente, elas seguem o fluido de referência único; por isso, a temperatura '
            'ideal de saída da turbina nesse desenho pode diferir daquela calculada com as propriedades dos gases. '
            'Na visão por componente e no P–v, usam os estados isentrópicos calculados pelo modelo.\n\n'
            '**Limitações comuns.** As linhas apenas conectam estados de entrada e saída: não descrevem todos '
            'os estados intermediários. Nenhuma das visões calcula a mudança completa de entropia da reação '
            'química e da mistura no combustor. A área desses desenhos não é apresentada como trabalho líquido do motor.'
        )
    st.caption('As linhas unem estados totais de extremidade; são esquemáticas e não descrevem a trajetória interna do escoamento.')
    estados_ts = estados_ciclo(ciclo,ts_equivalente=ts_equivalente)
    mostrar_ideais = st.checkbox("Sobrepor estados isentrópicos de referência", key="ciclo_ideais_visual")
    interativo = st.radio("Visualização dos diagramas", ["Imagem", "Interativa"],
                          horizontal=True, key="ciclo_renderizador_visual",
                          help="Imagem usa o mesmo renderizador dos gráficos de sensibilidade. "
                               "Interativa acrescenta consulta de valores ao passar o mouse e zoom opcional.") == "Interativa"
    habilitar_zoom = st.checkbox(
        "Ativar zoom e deslocamento nos diagramas", key="ciclo_zoom_visual",
        disabled=not interativo,
        help="Com esta opção desligada, a roda do mouse fica disponível para rolar a página. "
             "Ative somente quando quiser explorar os gráficos.",
    )
    ideais = ideais_ciclo(ciclo,estados) if mostrar_ideais else []
    ideais_ts = ideais_ciclo(ciclo,estados_ts,ts_equivalente) if mostrar_ideais else []
    esquerda, direita = st.columns(2)
    for coluna, x, y, titulo in ((esquerda, "v", "P", "P–v equivalente"),
                                 (direita, "s", "T", 'T–s equivalente — fluido de referência único' if ts_equivalente
                                  else 'T–s por componente — ar e gases')):
        with coluna:
            dados_grafico = estados_ts if x=='s' else estados
            ideais_grafico = ideais_ts if x=='s' else ideais
            if interativo:
                grafico = alt.LayerChart.from_dict(
                    _diagrama(dados_grafico, x, y, titulo, selecionados, ideais_grafico, habilitar_zoom)
                )
                st.altair_chart(grafico_br(grafico), width="stretch", height=420, theme=None)
            else:
                fig = _figura_diagrama(dados_grafico, x, y, titulo, selecionados, ideais_grafico)
                try:
                    st.pyplot(figura_br(fig), width="stretch")
                finally:
                    plt.close(fig)
    if interativo:
        _legenda_interativa(mostrar_ideais)
        st.caption("Passe o mouse sobre os pontos para consultar valores. Para ampliar ou deslocar "
                   "os gráficos, ative a opção de zoom; clique duas vezes no gráfico para restaurar a escala.")
    else:
        st.caption("As imagens são atualizadas com os resultados do caso e com as opções acima. "
                   "Os valores numéricos estão na tabela abaixo. A visualização Interativa permite consultar "
                   "valores ao passar o mouse.")
    st.caption("A área do P–v não é apresentada como trabalho líquido do motor.")
    with st.expander("Valores, equações e hipóteses dos diagramas"):
        # Apenas quatro estados: tabela estática cresce com o conteúdo e não
        # intercepta a rolagem da página como uma grade interativa.
        tabela_estados = pd.DataFrame(estados_ts).rename(columns={
            "estado": "Estado", "local": "Localização", "T": "T₀ (K)", "P": "P₀ (kPa)",
            "v": "v₀ equivalente (m³/kg)", "s": _rotulo_entropia(estados_ts), "fluido": "Referência de entropia"})
        st.markdown("**Estações e condições termodinâmicas**")
        st.table(tabela_br(tabela_estados[["Estado", "Localização", "T₀ (K)", "P₀ (kPa)"]]
                 .style.format({"T₀ (K)": "{:.2f}", "P₀ (kPa)": "{:.2f}"},
                               decimal=",", thousands=".")), hide_index=True)
        st.markdown("**Grandezas derivadas para os diagramas**")
        st.table(tabela_br(tabela_estados[["Estado", "Referência de entropia", "v₀ equivalente (m³/kg)", _rotulo_entropia(estados_ts)]]
                 .style.format({"v₀ equivalente (m³/kg)": "{:.5f}",
                                _rotulo_entropia(estados_ts): "{:.5f}"},
                               decimal=",", thousands=".")), hide_index=True)
        st.markdown("**Equações e propriedades utilizadas**")
        st.latex(r"R=c_p\frac{k-1}{k},\qquad v_0=\frac{RT_0}{P_0}")
        if ts_equivalente:
            st.latex(r"s_{eq,i}-s_{eq,01}=c_{p,ref}\ln(T_{0i}/T_{01})-R_{ref}\ln(P_{0i}/P_{01})")
            st.caption(f"Fluido de referência do T–s: cp = {formato_br(ciclo.cp_ar,'.3f')} J/(kg·K); "
                       f"R = {formato_br(ciclo.R_ar,'.6f')} J/(kg·K); s_eq,01 = 0. "
                       'A mesma referência vale nos quatro pontos. Ela não substitui as propriedades dos componentes abaixo.')
        else:
            st.latex(r"s_a-s_{01,a}=c_{p,a}\ln(T_0/T_{01})-R_a\ln(P_0/P_{01})")
            st.latex(r"s_g-s_{03,g}=c_{p,g}\ln(T_0/T_{03})-R_g\ln(P_0/P_{03})")
        st.table(tabela_br(pd.DataFrame([{'Fluido': nome, **dados} for nome, dados in ciclo.propriedades().items()])), hide_index=True)
        st.caption("Gás ideal com propriedades constantes por região, diferentes para ar e gases. "
                   "No T–s equivalente, somente a posição horizontal e as referências isentrópicas do desenho usam o fluido único. "
                   "Na visão por componente, os zeros de entropia são independentes. Não se calcula entropia de combustão. "
                   "O volume específico do P–v e da tabela usa R do ar ou dos gases conforme a estação; é total equivalente, "
                   "não o volume estático local. As referências isentrópicas usam as pressões de saída dos processos correspondentes.")
