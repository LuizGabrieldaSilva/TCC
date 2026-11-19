"""Desenhos didáticos dos perfis já calculados; nenhuma geração de geometria."""

from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
import math

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import streamlit as st
from engine.webapp.energy_indicators import _numero_br


def coordenadas(perfil, xs, ys, normalizar=True, orientar=False):
    """Mesma rotação plana por stagger usada no loft, sem alterar as listas."""
    escala = perfil.corda if normalizar else .01  # c ou cm
    angulo = math.radians(perfil.stagger) if orientar else 0.
    co, si = math.cos(angulo), math.sin(angulo)
    return ([((x*co-y*si)/escala) for x, y in zip(xs, ys)],
            [((x*si+y*co)/escala) for x, y in zip(xs, ys)])


def figura_perfil(perfil, camadas, normalizar=True, orientar=False):
    """Desenha contornos armazenados, corda, espessura amostrada e tangentes."""
    fig, ax = plt.subplots(figsize=(8, 4.8))
    def linha(xs, ys, **kw):
        x, y = coordenadas(perfil, xs, ys, normalizar, orientar)
        return ax.plot(x, y, **kw)
    if 'Extradorso' in camadas:
        linha(perfil.x_extradorso, perfil.y_extradorso, color='#2474b5', label='Extradorso')
    if 'Intradorso' in camadas:
        linha(perfil.x_intradorso, perfil.y_intradorso, color='#d55e00', label='Intradorso')
    if 'Linha de câmber' in camadas:
        linha(perfil.x_camber, perfil.y_camber, color='#238b45', ls='--', label='Linha de câmber')
    if 'Corda' in camadas:
        linha([0, perfil.corda], [0, 0], color='#777777', ls='-.', label='Corda')
    if 'Espessura' in camadas:
        j = min(range(len(perfil.x_camber)), key=lambda i: abs(perfil.x_camber[i]/perfil.corda-.5))
        xs = [perfil.x_extradorso[j], perfil.x_intradorso[j]]
        ys = [perfil.y_extradorso[j], perfil.y_intradorso[j]]
        x, y = coordenadas(perfil, xs, ys, normalizar, orientar)
        ax.annotate('', xy=(x[0], y[0]), xytext=(x[1], y[1]),
                    arrowprops=dict(arrowstyle='<->', color='#923c97', lw=1.6))
        ax.plot([], [], color='#923c97', label='Espessura normal perto de x/c = 0,5')
    if 'Ângulos metálicos' in camadas:
        escala = perfil.corda if normalizar else .01
        for x0, y0, beta, nome in ((perfil.x_camber[0], perfil.y_camber[0], perfil.beta1_linha, 'Entrada'),
                                   (perfil.x_camber[-1], perfil.y_camber[-1], perfil.beta2_linha, 'Saída')):
            x, y = coordenadas(perfil, [x0], [y0], normalizar, orientar)
            ang = math.radians(beta if orientar else beta-perfil.stagger)
            comprimento = .22*perfil.corda/escala
            ax.annotate('', xy=(x[0]+comprimento*math.cos(ang), y[0]+comprimento*math.sin(ang)),
                        xytext=(x[0], y[0]), arrowprops=dict(arrowstyle='->', color='#923c97', lw=1.5))
            ax.annotate(f'{nome}: γ metal = {_numero_br(beta, 2)}°', (x[0], y[0]),
                        xytext=(0, 20 if nome=='Entrada' else -28), textcoords='offset points',
                        ha='left' if nome=='Entrada' else 'right', fontsize=9)
        ax.plot([], [], color='#923c97', label='Tangentes à linha de câmber')
    if 'Stagger' in camadas:
        escala = perfil.corda if normalizar else .01
        axial = 0. if orientar else -math.radians(perfil.stagger)
        corda = math.radians(perfil.stagger) if orientar else 0.
        raio = .3*perfil.corda/escala
        ax.plot([0, raio*1.3*math.cos(axial)], [0, raio*1.3*math.sin(axial)], ':', color='#777777')
        angulos = [axial+(corda-axial)*j/40 for j in range(41)]
        ax.plot([raio*math.cos(a) for a in angulos], [raio*math.sin(a) for a in angulos],
                color='#a05a00', label=f'Stagger ζ = {_numero_br(perfil.stagger, 2)}°')
    inicio = coordenadas(perfil, [0, perfil.corda], [0, 0], normalizar, orientar)
    ax.scatter(*inicio, s=20, color='#333333', zorder=4)
    ax.margins(.20)
    _acabamento(ax, normalizar, orientar, 'Perfil 2D desta seção')
    _organizar_figura(fig, ax, ncol=2)
    return fig


def _organizar_figura(fig, ax, ncol):
    """Altura acompanha a geometria; eixo e legenda ocupam faixas distintas."""
    handles, labels = ax.get_legend_handles_labels()
    linhas = math.ceil(len(labels)/ncol)
    altura_legenda = .22*linhas+.12 if linhas else 0.
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    # A escala igual continua a cargo do axes. Limites apenas de tamanho da figura.
    altura_desenho = max(1.15, min(5.5, 6.72*(ymax-ymin)/(xmax-xmin)))
    rodape = .64+altura_legenda
    altura = altura_desenho+rodape+.62
    fig.set_size_inches(8, altura)
    fig.subplots_adjust(left=.12, right=.96, top=1-.62/altura, bottom=rodape/altura)
    if handles:
        fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5, .06/altura),
                   ncol=ncol, fontsize=8)


def _acabamento(ax, normalizar, orientar, titulo):
    unidade = '/c' if normalizar else ' (cm)'
    ax.set_xlabel(('Axial' if orientar else 'Ao longo da corda')+unidade)
    ax.set_ylabel(('Tangencial' if orientar else 'Normal à corda')+unidade)
    ax.set_title(titulo)
    ax.set_aspect('equal', adjustable='box')
    _eixos_br(ax)
    ax.grid(alpha=.22)


def _eixos_br(ax):
    for eixo in (ax.xaxis, ax.yaxis):
        eixo.set_major_formatter(FuncFormatter(lambda valor, pos: f'{valor:g}'.replace('.', ',')))


def secoes_comparacao(radial, i):
    """Seções existentes: extremos e a mais próxima de r_m (sem interpolar)."""
    maquina = radial.comp if hasattr(radial, 'comp') else radial.turb
    meio = min(radial.secoes, key=lambda s: abs(radial.r[i][s]-maquina.r_mean))
    return list(dict.fromkeys((radial.secoes[0], meio, radial.secoes[-1])))


def figura_espessura(perfil):
    """Distância entre pares de pontos armazenados, medida na normal ao câmber."""
    fig, ax = plt.subplots(figsize=(8, 2.7))
    xs = [x/perfil.corda for x in perfil.x_camber]
    ts = [math.hypot(xe-xi, ye-yi)/perfil.corda for xe, ye, xi, yi in zip(
        perfil.x_extradorso, perfil.y_extradorso, perfil.x_intradorso, perfil.y_intradorso)]
    ax.plot(xs, ts, color='#923c97', label='Espessura normal dos pontos gerados')
    ax.axhline(perfil.t_sobre_c, color='#777777', ls='--', label='t máximo/c prescrito')
    ax.set(xlabel='Posição ao longo da corda x/c', ylabel='Espessura normal t(x)/c')
    _eixos_br(ax)
    ax.grid(alpha=.22)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def figura_comparacao(perfis, secoes, fileira, normalizar=True, orientar=False):
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for secao, cor in zip(secoes, ('#2474b5', '#d55e00', '#238b45')):
        perfil = perfis[secao][fileira]
        for lado in ('extradorso', 'intradorso'):
            x, y = coordenadas(perfil, getattr(perfil, 'x_'+lado), getattr(perfil, 'y_'+lado), normalizar, orientar)
            ax.plot(x, y, color=cor, label=secao if lado=='extradorso' else None)
    _acabamento(ax, normalizar, orientar, 'Comparação radial dos contornos — mesma fileira')
    ax.margins(.15)
    _organizar_figura(fig, ax, ncol=3)
    return fig


def exibir_perfil_2d(radial, perfis, componente, estagio, secao, fileira):
    """Compartilha os seletores do painel de ângulos/perfil existente."""
    st.markdown('**Construção do perfil 2D**')
    st.caption('Usa o estágio, a seção e a fileira selecionados acima, nos resultados desta execução.')
    camadas = st.multiselect('Camadas do perfil',
        ['Extradorso', 'Intradorso', 'Linha de câmber', 'Corda', 'Espessura', 'Ângulos metálicos', 'Stagger'],
        default=['Extradorso', 'Intradorso', 'Linha de câmber', 'Corda'], key=f'perfil_2d_camadas_{componente}')
    a, b = st.columns(2)
    normalizar = a.checkbox('Normalizar coordenadas pela corda c', value=True, key=f'perfil_2d_norm_{componente}')
    orientar = b.checkbox('Orientar pelo stagger no plano axial–tangencial', key=f'perfil_2d_orientar_{componente}')
    perfil = perfis[estagio][secao][fileira]
    fig = figura_perfil(perfil, camadas, normalizar, orientar)
    desenho, sequencia = st.columns([3, 1])
    desenho.pyplot(figura_br(fig), use_container_width=True)
    plt.close(fig)
    sequencia.markdown('**Da entrada às coordenadas**\n\n'
        '1. Ângulos do escoamento.\n2. Incidência zero e hipótese de desvio.\n'
        '3. Ângulos metálicos da tabela.\n4. Arco circular de câmber e stagger.\n'
        '5. Espessura na normal ao câmber.\n6. Contornos entregues ao loft.')
    sequencia.caption('Compressor: desvio de Carter; consulte a correlação e seu alcance abaixo. '
                      'Turbina: desvio imposto como zero, sem correlação de desvio de turbina.')
    if 'Espessura' in camadas:
        fig = figura_espessura(perfil)
        st.pyplot(figura_br(fig), use_container_width=True)
        plt.close(fig)
    st.caption(
        'Corda: segmento entre os bordos. Câmber: linha média geométrica. Espessura: distância normal '
        'entre os contornos na amostra mais próxima de x/c = 0,5; a amostra pode não coincidir com o máximo. '
        'As setas metálicas são tangentes à linha de câmber, não ao contorno espesso. '
        'γ metal é sempre medido em relação ao eixo axial da máquina; no desenho alinhado à corda, '
        'a direção da seta é γ metal − ζ. ζ é o stagger mostrado na tabela acima.'
    )
    st.latex(r't(x)=(t/c)\,c\,4(x/c)(1-x/c),\qquad t_{\max}=(t/c)c')
    st.caption(f'Espessura prescrita deste perfil: t/c = {_numero_br(perfil.t_sobre_c)}; '
               f't máximo do modelo = {_numero_br(perfil.t_sobre_c*perfil.corda*100)} cm. '
               'Os contornos exibidos são os pontos já gerados com essa distribuição.')
    if st.checkbox('Sobrepor cubo, região do raio médio e ponta', key=f'perfil_2d_comparar_{componente}'):
        secoes = secoes_comparacao(radial, estagio-1)
        fig = figura_comparacao(perfis[estagio], secoes, fileira, normalizar, orientar)
        st.pyplot(figura_br(fig), use_container_width=True)
        plt.close(fig)
        st.table(tabela_br(pd.DataFrame([
            {'Seção': s, 'Raio (cm)': radial.r[estagio-1][s]*100,
             'Corda (cm)': perfis[estagio][s][fileira].corda*100,
             'Stagger ζ (°)': perfis[estagio][s][fileira].stagger,
             'Câmber θ (°)': perfis[estagio][s][fileira].theta_final}
            for s in secoes]).set_index('Seção').style.format(_numero_br)))
        st.caption('A seção intermediária é a disponível mais próxima do raio médio; não há interpolação. '
                   'Os bordos de entrada são alinhados na origem. Com a orientação ativada, cada seção '
                   'usa seu próprio stagger, evidenciando a torção; sem ela, as cordas ficam alinhadas. '
                   'A normalização remove diferenças de escala de corda, preservando a forma.')
    st.caption('Geometria simplificada: arco circular de câmber e espessura parabólica simétrica. '
               'O desenho não demonstra distribuição de pressão, resistência, ausência de colisões ou '
               'desempenho aerodinâmico. As hipóteses de incidência/desvio e os avisos existentes continuam aplicáveis.')
