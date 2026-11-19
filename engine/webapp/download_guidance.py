"""Descrições, prévia e seleção de curvas CAD já calculadas."""

import io
from pathlib import Path
import tempfile
import zipfile

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch
from mpl_toolkits.mplot3d import proj3d
import pandas as pd
import streamlit as st

from engine.cad.export_dxf import exportar_peca_dxf, _fechar_perfil
from engine.webapp.number_format import figura_br, tabela_br, formato_br


def zip_arquivos(caminhos):
    """Inclui somente os arquivos desta exportação, sem restos de outro caso."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as pacote:
        for caminho in caminhos:
            pacote.write(caminho, arcname=Path(caminho).name)
    return buffer.getvalue()


def selecionar_pecas(maquina, alcance, estagio, fileira):
    return [p for p in maquina.pecas if
            (alcance == 'Componente completo' or p.estagio == estagio) and
            (alcance != 'Uma fileira' or p.tipo == fileira)]


def curvas_perfil(peca):
    """Os mesmos laços fechados que o escritor DXF produz, antes de arredondar."""
    return [_fechar_perfil(extra, intra) for extra, intra in
            zip(peca.pa.extradorso_cart, peca.pa.intradorso_cart)]


def limites_selecao(pecas):
    """Limites cartesianos das curvas exibidas, em metros, sem mudar a geometria."""
    pontos = [ponto for p in pecas for curva in curvas_perfil(p) for ponto in curva]
    return {nome:(min(p[i] for p in pontos), max(p[i] for p in pontos))
            for i,nome in enumerate(('X','Y','Z'))}


def figura_previa(pecas):
    tamanho = (5.5, 4.2) if len(pecas) == 1 else (9.2, 4.2) if len(pecas) == 2 else (10, 3.2)
    fig = plt.figure(figsize=tamanho)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_proj_type('ortho')
    limites = [[], [], []]
    for p in pecas:
        cor = '#2474b5' if p.tipo == 'rotor' else '#d55e00'
        for i, curva in enumerate(curvas_perfil(p)):
            # O eixo axial Z do CAD fica horizontal na prévia da máquina.
            xyz = list(zip(*[(z,y,x) for x,y,z in curva+[curva[0]]]))
            ax.plot(*xyz, color=cor, lw=.8,
                    label=f'Estágio {p.estagio} · {p.tipo}' if i == 0 else None)
            for destino, valores in zip(limites, xyz):
                destino.extend(valores)
        for curva in p.pa.camber_cart:
            ax.plot(*zip(*[(z,y,x) for x,y,z in curva]), color='#777777', ls='--', lw=.5, alpha=.7)
    spans = [max(v)-min(v) for v in limites]
    maior = max(spans) or 1.
    aspecto = [max(s, maior*.01) for s in spans]
    ax.set_box_aspect(aspecto)
    ax.view_init(elev=22, azim=-65)
    ax.set_axis_off()
    fig.subplots_adjust(left=.01, right=.82, bottom=.01, top=.99)
    for linha in ax.lines:
        linha.set_clip_on(False)
    # Ajusta somente o zoom uniforme. A razão entre as três escalas é preservada.
    fig.canvas.draw()
    xyz = [v for p in pecas for curva in curvas_perfil(p) for v in curva]
    px,py,_ = proj3d.proj_transform([v[2] for v in xyz], [v[1] for v in xyz],
                                   [v[0] for v in xyz], ax.get_proj())
    tela = ax.transData.transform(list(zip(px,py)))
    largura = max(v[0] for v in tela)-min(v[0] for v in tela)
    altura = max(v[1] for v in tela)-min(v[1] for v in tela)
    zoom = min(fig.bbox.width*.69/max(largura,1), fig.bbox.height*.80/max(altura,1))
    ax.set_box_aspect(aspecto, zoom=zoom)
    # Referência de orientação fora do campo das curvas, sem valores sobrepostos.
    centro = [sum(v)/len(v) for v in limites]
    origem = proj3d.proj_transform(*centro, ax.get_proj())
    for i,nome,cor in ((0,'Z','#555555'), (1,'Y','#555555'), (2,'X','#555555')):
        ponta = centro.copy();ponta[i] += maior*.1
        projetado = proj3d.proj_transform(*ponta, ax.get_proj())
        dx,dy = projetado[0]-origem[0],projetado[1]-origem[1]
        norma = max((dx*dx+dy*dy)**.5,1e-12)
        x,y = .90+.065*dx/norma, .16+.10*dy/norma
        fig.add_artist(FancyArrowPatch((.90,.16),(x,y),transform=fig.transFigure,
                                      arrowstyle='->',mutation_scale=10,color=cor))
        fig.text(x,y,nome,ha='center',va='bottom',fontsize=9)
    return figura_br(fig)


def arquivo_selecao(pecas, componente, secoes):
    """Reusa o escritor de peça; não altera os objetos nem cria novo loft."""
    if not pecas:
        raise ValueError('Selecione ao menos uma fileira calculada.')
    with tempfile.TemporaryDirectory(prefix='tcc_selecao_cad_') as pasta:
        caminhos = []
        for p in pecas:
            nome = f'{componente.lower()}_estagio{p.estagio:02d}_{p.tipo}.dxf'
            caminho = Path(pasta)/nome
            exportar_peca_dxf(p, str(caminho), nomes_secoes=secoes)
            caminhos.append(caminho)
        if len(caminhos) == 1:
            return caminhos[0].name, caminhos[0].read_bytes(), 'application/dxf'
        return f'{componente.lower()}_selecao_dxf.zip', zip_arquivos(caminhos), 'application/zip'


def exibir_formatos():
    with st.expander('Qual arquivo baixar e como utilizá-lo?', expanded=True):
        st.table(pd.DataFrame([
            ('CSV', 'Resultados meanline e radiais por estágio e seção.',
             'Consultar em planilha ou programa de análise. Não contém curvas de pá.'),
            ('JSON', 'Diagnósticos de integração ou indicadores energéticos, conforme o botão.',
             'Ler em editor ou programa. Estes arquivos não são uma configuração de entradas para recarregar o caso.'),
            ('DXF / ZIP', 'Curvas 3D de seções fechadas e linhas de câmber; uma pá por fileira.',
             'Importar em CAD, conferir unidades e construir o loft. ZIP apenas reúne os DXFs.'),
            ('STEP', 'Indisponível nesta interface.',
             'Não há exportação de sólido STEP validada neste fluxo.'),
        ], columns=['Formato', 'Conteúdo', 'Uso e alcance']).set_index('Formato'))
        st.caption('A interface usa vírgula decimal. Os arquivos técnicos mantêm sua convenção: '
                   'CSV com separador vírgula e decimal ponto, JSON com números nativos e DXF com coordenadas em metros. '
                   'Ao importar o CSV em uma planilha, configure esses separadores para evitar números tratados como texto.')


def exibir_selecao_cad(resultados, execucao_id):
    with st.expander('Prévia e exportação CAD por seleção', expanded=False):
        st.caption('Usa a geometria da execução calculada. As entradas do formulário só passam a valer após novo cálculo. '
                   'Compressor e turbina têm geometria de pás; o combustor 1D não possui um CAD exportável neste fluxo.')
        componente = st.selectbox('Componente da exportação', ['Compressor', 'Turbina'], key='cad_componente')
        sufixo = 'comp' if componente == 'Compressor' else 'turb'
        maquina = resultados['maquina_'+sufixo]
        radial = resultados['rad_'+sufixo]
        alcance = st.radio('Conteúdo da seleção', ['Uma fileira', 'Um estágio', 'Componente completo'],
                           horizontal=True, key='cad_alcance')
        estagios = sorted({p.estagio for p in maquina.pecas})
        if st.session_state.get('cad_estagio', estagios[0]) not in estagios:
            del st.session_state['cad_estagio']
        estagio = st.selectbox('Estágio da exportação', estagios, format_func=lambda n:f'Estágio {n}',
                               key='cad_estagio', disabled=alcance == 'Componente completo')
        fileiras = [p.tipo for p in maquina.pecas if p.estagio == estagio]
        if st.session_state.get('cad_fileira', fileiras[0]) not in fileiras:
            del st.session_state['cad_fileira']
        fileira = st.selectbox('Fileira da exportação', fileiras, key='cad_fileira', disabled=alcance != 'Uma fileira')
        pecas = selecionar_pecas(maquina, alcance, estagio, fileira)
        st.write(f'**Seleção: {len(pecas)} arquivo(s) DXF · {len(radial.secoes)} seções por pá.** '
                 'Cada arquivo contém uma pá de referência, não todas as pás da circunferência.')
        st.dataframe(tabela_br(pd.DataFrame([
            {'Estágio':p.estagio, 'Fileira':p.tipo, 'Pás na fileira Z':p.Z_pas,
             'Seções no DXF':len(p.pa.r_secoes), 'Raio do cubo (m)':p.pa.r_secoes[0],
             'Raio da ponta (m)':p.pa.r_secoes[-1]} for p in pecas])), hide_index=True, width='stretch')
        if st.checkbox('Mostrar prévia 3D das curvas selecionadas', value=True, key='cad_mostrar_previa'):
            st.markdown('**Curvas da seleção — uma pá de referência por fileira**')
            fig = figura_previa(pecas)
            st.pyplot(fig, width=int(fig.get_figwidth()*90))
            plt.close(fig)
            limites = limites_selecao(pecas)
            st.caption('Limites das curvas em metros — '+ ' · '.join(
                f'{eixo}: {formato_br(a,".5f")} a {formato_br(b,".5f")}' for eixo,(a,b) in limites.items()))
            st.caption('Azul: rotor; laranja: estator ou bocal; tracejado cinza: câmber de referência. '
                       'Coordenadas da geometria calculada, antes do arredondamento do escritor DXF. '
                       'O eixo axial Z do CAD aparece na horizontal da prévia. '
                       'A imagem não mostra superfícies, sólido, raios de concordância ou o anel de Z pás. '
                       'Os espaçamentos axiais são convenções de visualização do modelo, não um dimensionamento mecânico.')
            if alcance == 'Componente completo' and st.checkbox('Mostrar detalhe de um estágio', key='cad_detalhe'):
                if st.session_state.get('cad_detalhe_estagio', estagios[0]) not in estagios:
                    del st.session_state['cad_detalhe_estagio']
                detalhe = st.selectbox('Estágio em detalhe',estagios,
                    format_func=lambda n:f'Estágio {n}',key='cad_detalhe_estagio')
                st.caption('Ampliação da vista deste estágio. A seleção para download continua sendo o componente completo.')
                fig = figura_previa([p for p in pecas if p.estagio == detalhe])
                st.pyplot(fig,width=int(fig.get_figwidth()*90))
                plt.close(fig)
        assinatura = (execucao_id, componente, alcance, estagio, fileira)
        if st.button('Preparar arquivo desta seleção', key='cad_preparar'):
            nome, dados, mime = arquivo_selecao(pecas, componente, radial.secoes)
            st.session_state['cad_arquivo_preparado'] = (assinatura, nome, dados, mime)
        preparado = st.session_state.get('cad_arquivo_preparado')
        if preparado and preparado[0] == assinatura:
            _, nome, dados, mime = preparado
            st.download_button('⬇ Baixar DXF / ZIP desta seleção', data=dados, file_name=nome,
                               mime=mime, key='cad_baixar', width='stretch')
        else:
            st.caption('Após escolher o conteúdo, clique em Preparar arquivo desta seleção. '
                       'Uma mudança de seleção ou uma nova execução exige preparar novamente.')
        with st.expander('Da importação ao loft — orientação e limitações'):
            st.markdown('1. Extraia o ZIP, quando houver, e importe o DXF como **curvas 3D**.\n'
                        '2. Confira a unidade: **metros**. Compare os raios das seções com a tabela acima; '
                        'o cabeçalho indica metros, mas o programa CAD pode exigir confirmação.\n'
                        '3. Identifique as camadas `HUB_PERFIL` até `TIP_PERFIL` na exportação por seleção '
                        '(os pacotes completos existentes usam nomes `S00`, `S01` etc.). '
                        'Use os perfis na ordem do cubo para a ponta para construir um loft.\n'
                        '4. As camadas `CAMBER` são referências abertas; não são contornos para fechar o sólido. '
                        'Curvas-guia de bordo de ataque/fuga não são exportadas.\n'
                        '5. Confira a geometria resultante no CAD antes de fazer a repetição circular com Z pás.')
            st.caption('A prévia não comprova que o CAD construirá um sólido válido nem verifica colisões, '
                       'folgas, espessura estrutural, materiais ou fabricação. A importação/loft no FreeCAD '
                       'ainda precisa de uma verificação própria; ela não foi executada nesta implementação.')
