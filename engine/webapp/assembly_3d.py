"""Malhas de visualização das pás calculadas, sem alterar a geometria CAD."""

import math

import numpy as np
import pandas as pd
import streamlit as st

from engine.webapp.number_format import tabela_br


def indices_pas(numero, replicar=False, setor=360, limite=None):
    """Índices inteiros da fileira real; uma amostra não muda o passo 2π/Z."""
    if numero < 1:
        raise ValueError('A fileira precisa ter pelo menos uma pá.')
    indices=list(range(numero)) if replicar else [0]
    if replicar:
        indices=[k for k in indices if 360*k/numero < setor]
    if limite and len(indices)>limite:
        indices=[indices[i] for i in np.linspace(0,len(indices)-1,limite,dtype=int)]
    return indices


def contornos(peca, pontos=20):
    """Subamostra os contornos existentes; mantém todas as seções radiais."""
    lados=[]
    for nome in ('extradorso_cart','intradorso_cart'):
        curvas=getattr(peca.pa,nome)
        if len(curvas)<2 or len({len(c) for c in curvas})!=1:
            raise ValueError('As seções precisam ter pontos correspondentes para desenhar a malha.')
        idx=np.linspace(0,len(curvas[0])-1,min(pontos,len(curvas[0])),dtype=int)
        lados.append(np.asarray(curvas,dtype=float)[:,idx,:])
    # Bordos coincidentes aparecem uma vez: evita triângulos de área nula.
    return np.concatenate((lados[0],lados[1][:,-2:0:-1,:]),axis=1)


def malha_fileira(peca, indices, pontos=20):
    """Liga pontos correspondentes; rotação rígida em torno do Z original do CAD."""
    base=contornos(peca,pontos)
    if not np.isfinite(base).all():
        raise ValueError('A geometria contém coordenadas não finitas.')
    ns,nc,_=base.shape
    faces=[]
    for s in range(ns-1):
        for c in range(nc):
            a=s*nc+c;b=s*nc+(c+1)%nc;d=(s+1)*nc+c;e=(s+1)*nc+(c+1)%nc
            faces.extend(((a,b,e),(a,e,d)))
    faces=np.asarray(faces,dtype=int)
    vertices=[];triangulos=[]
    for numero_pa,k in enumerate(indices):
        ang=2*math.pi*k/peca.Z_pas
        rot=np.array([[math.cos(ang),-math.sin(ang),0],
                      [math.sin(ang),math.cos(ang),0],[0,0,1]])
        vertices.append(base.reshape(-1,3)@rot.T)
        triangulos.append(faces+numero_pa*ns*nc)
    return np.concatenate(vertices),np.concatenate(triangulos),base


def perfil_cubo(pecas):
    """Raio constante sob cada raiz; ligação linear apenas nos vãos entre fileiras."""
    intervalos=[]
    for p in pecas:
        raiz=np.concatenate((np.asarray(p.pa.extradorso_cart[0],dtype=float),
                             np.asarray(p.pa.intradorso_cart[0],dtype=float)))
        raio=float(p.pa.r_secoes[0])
        if not np.isfinite(raiz).all() or not math.isfinite(raio) or raio<=0:
            raise ValueError('As raízes precisam ter coordenadas e raios de cubo válidos.')
        intervalos.append((float(raiz[:,2].min()),float(raiz[:,2].max()),raio))
    perfil=[]
    for inicio,fim,raio in sorted(intervalos):
        if perfil and inicio<perfil[-1][0]-1e-12:
            if not math.isclose(raio,perfil[-1][1],rel_tol=1e-9,abs_tol=1e-12):
                raise ValueError('Raízes com raios diferentes se sobrepõem axialmente; cubo esquemático não definido.')
            perfil[-1]=(max(fim,perfil[-1][0]),raio)
        else:
            perfil.extend(((inicio,raio),(fim,raio)))
    # Remove só posições repetidas idênticas, sem mudar os raios calculados.
    return np.asarray([p for i,p in enumerate(perfil) if i==0 or p!=perfil[i-1]])


def malha_cubo(pecas,setor=360):
    perfil=perfil_cubo(pecas)
    angulos=np.linspace(0,math.radians(setor),max(17,int(setor/5)+1))
    vertices=np.array([(raio*math.cos(t),raio*math.sin(t),z)
                       for z,raio in perfil for t in angulos])
    faces=[];n=len(angulos)
    for a in range(len(perfil)-1):
        for b in range(n-1):
            i=a*n+b;j=i+1;k=i+n;l=k+1
            faces.extend(((i,j,l),(i,l,k)))
    return vertices,np.asarray(faces,dtype=int),perfil


def figura_montagem(pecas, replicar=False, setor=360, limite=24, pontos=20,
                    secoes=False, eixos=True, vista='Isométrica', identidade='',
                    cubo=False, transparencia_cubo=0):
    import plotly.graph_objects as go

    fig=go.Figure();resumo=[]
    for p in pecas:
        ids=indices_pas(p.Z_pas,replicar,setor,limite)
        vertices,faces,base=malha_fileira(p,ids,pontos)
        cor='#2474b5' if p.tipo=='rotor' else '#d55e00'
        nome=f'Estágio {p.estagio} · {p.tipo}'
        # Permutação só da vista: Z axial horizontal; X/Y transversais.
        fig.add_trace(go.Mesh3d(x=vertices[:,2],y=vertices[:,0],z=vertices[:,1],
            i=faces[:,0],j=faces[:,1],k=faces[:,2],color=cor,name=nome,
            flatshading=False,showlegend=True,
            hovertemplate=nome+'<br>Pás desenhadas: '+str(len(ids))+
                '<br>Pás na fileira: '+str(p.Z_pas)+'<extra></extra>',
            lighting=dict(ambient=.65,diffuse=.75,specular=.15)))
        if secoes:
            linhas=[[],[],[]]
            # Seções da pá de referência apenas, para não sobrecarregar o anel.
            for curva in base:
                curva=np.vstack((curva,curva[0]))
                for dest,col in zip(linhas,(2,0,1)):
                    dest.extend(curva[:,col].tolist()+[None])
            fig.add_trace(go.Scatter3d(x=linhas[0],y=linhas[1],z=linhas[2],mode='lines',
                line=dict(color='#222222',width=3),name=nome+' · seções da pá 1',
                hoverinfo='skip',showlegend=False))
        resumo.append({'Estágio':p.estagio,'Fileira':p.tipo,'Pás na fileira':p.Z_pas,
                       'Pás desenhadas':len(ids),'Seções radiais':len(base),
                       'Passo angular (°)':360/p.Z_pas})
    if cubo:
        vertices,faces,_=malha_cubo(pecas,setor if replicar else 360)
        fig.add_trace(go.Mesh3d(x=vertices[:,2],y=vertices[:,0],z=vertices[:,1],
            i=faces[:,0],j=faces[:,1],k=faces[:,2],color='#9a9a9a',
            opacity=1-transparencia_cubo/100,name='Cubo esquemático · referência interna',
            showlegend=True,hovertemplate='Superfície interna de referência<br>Sem fixações ou dimensionamento mecânico<extra></extra>',
            lighting=dict(ambient=.75,diffuse=.5,specular=.05)))
    cameras={'Isométrica':dict(x=2.0,y=2.0,z=1.375),
             'Axial':dict(x=3.125,y=0,z=0),'Lateral':dict(x=0,y=3.125,z=0)}
    fig.update_layout(height=680,margin=dict(l=40,r=40,b=50,t=110),
        paper_bgcolor='#ffffff',font=dict(color='#222222'),separators=',.',
        legend=dict(orientation='h',y=1.04,x=0,yanchor='bottom',font=dict(size=10)),
        scene=dict(aspectmode='data',bgcolor='#ffffff',
            xaxis=dict(title='Z axial (m)',visible=eixos),
            yaxis=dict(title='X transversal (m)',visible=eixos),
            zaxis=dict(title='Y transversal (m)',visible=eixos),
            camera=dict(eye=cameras[vista],up=dict(x=0,y=0,z=1))),
        uirevision='enquadramento_v2:'+identidade)
    return fig,resumo


def _seletor(label,opcoes,chave,**kwargs):
    if chave in st.session_state and st.session_state[chave] not in opcoes:
        del st.session_state[chave]
    return st.selectbox(label,opcoes,key=chave,**kwargs)


def exibir_montagem(resultados,execucao_id):
    st.subheader('Geometria 3D — da pá à montagem')
    st.caption('Usa os resultados da execução calculada. Mudanças no formulário só entram após recalcular o caso.')
    componente=_seletor('Componente da montagem',['Compressor','Turbina'],'montagem_componente')
    maquina=resultados.get('maquina_comp' if componente=='Compressor' else 'maquina_turb')
    if maquina is None or not maquina.pecas:
        st.info('A geometria deste componente não está disponível nesta execução.');return
    nivel=st.radio('Nível da montagem',['Uma pá','Um estágio','Componente completo'],
                   horizontal=True,key='montagem_nivel')
    estagios=sorted({p.estagio for p in maquina.pecas})
    estagio=_seletor('Estágio da montagem',estagios,'montagem_estagio',
                    disabled=nivel=='Componente completo')
    fileira=_seletor('Fileira da montagem',[p.tipo for p in maquina.pecas if p.estagio==estagio],
                    'montagem_fileira',disabled=nivel!='Uma pá')
    pecas=[p for p in maquina.pecas if (nivel=='Componente completo' or p.estagio==estagio)
           and (nivel!='Uma pá' or p.tipo==fileira)]
    replicar=st.checkbox('Repetir pás ao redor do eixo',disabled=nivel=='Uma pá',key='montagem_replicar') and nivel!='Uma pá'
    c1,c2=st.columns(2)
    with c1:
        setor=st.select_slider('Setor visível (°)',options=[90,180,270,360],value=360,
            disabled=not replicar,key='montagem_setor')
        amostra=st.checkbox('Vista leve: até 24 pás por fileira',value=True,
            disabled=not replicar,key='montagem_leve',help='Desenha uma amostra nas posições reais. Desative para desenhar todas as pás do setor.')
        detalhe=st.radio('Detalhe dos contornos',['Leve','Detalhado'],horizontal=True,key='montagem_detalhe')
    with c2:
        secoes=st.checkbox('Mostrar seções da pá de referência',value=True,key='montagem_secoes')
        eixos=st.checkbox('Mostrar eixos e escala',value=True,key='montagem_eixos')
        vista=_seletor('Vista inicial',['Isométrica','Axial','Lateral'],'montagem_vista')
    cubo=False;transparencia=0
    if nivel=='Componente completo':
        cubo=st.checkbox('Mostrar cubo simplificado',value=True,key='montagem_cubo')
        transparencia=st.slider('Transparência do cubo (%)',0,90,0,5,
            disabled=not cubo,key='montagem_cubo_transparencia_v2')
        if cubo:
            st.caption('Cinza: superfície interna esquemática, acompanhando os raios do cubo calculados. '
                       'Não representa um único corpo girante: rotor gira; estator e bocal são estacionários.')
    st.caption('Azul: rotor. Laranja: estator ou bocal. Arraste para girar e use a roda do mouse para ampliar. '
               'A proporção geométrica entre os eixos é preservada. A vista leve omite pás, sem alterar o número calculado ou o passo angular.')
    assinatura=('enquadramento_v2',execucao_id,componente,nivel,estagio,fileira,replicar,setor,amostra,detalhe,secoes,eixos,vista,cubo,transparencia)
    if st.button('Gerar ou atualizar montagem 3D',key='montagem_gerar'):
        try:
            with st.spinner('Preparando a malha de visualização...'):
                fig,resumo=figura_montagem(pecas,replicar,setor,24 if amostra else None,
                    12 if detalhe=='Leve' else 36,secoes,eixos,vista,str(assinatura),
                    cubo=cubo,transparencia_cubo=transparencia)
            st.session_state['montagem_preparada']=(assinatura,fig,resumo)
        except ImportError:
            st.error('Instale a dependência da visualização: python -m pip install -r engine/webapp/requirements-3d.txt')
        except ValueError as erro:
            st.error(str(erro))
    preparado=st.session_state.get('montagem_preparada')
    if preparado and preparado[0]==assinatura:
        _,fig,resumo=preparado
        st.plotly_chart(fig,width='stretch',theme=None,key='montagem_grafico',
            config={'scrollZoom':True,'displaylogo':False})
        total=sum(v['Pás desenhadas'] for v in resumo)
        st.write(f'**{total} pá(s) desenhada(s) em {len(resumo)} fileira(s).** Objeto exibido: malha triangular de visualização.')
        with st.expander('Fileiras, contagens e passo angular'):
            st.dataframe(tabela_br(pd.DataFrame(resumo)),hide_index=True,width='stretch')
    else:
        st.info('Clique em Gerar ou atualizar montagem 3D para aplicar a seleção. A vista anterior não representa esta seleção.')
    with st.expander('Como a montagem é construída — hipóteses e limitações'):
        st.markdown('As seções vêm da mesma geometria usada na exportação CAD. Pontos correspondentes são '
            'ligados por triângulos; a repetição usa **360°/Z** em torno do eixo axial, como no macro do FreeCAD. '
            'A mudança de altura das pás entre estágios é mantida. O detalhe reduz apenas os pontos do contorno '
            'usados no desenho; todas as seções radiais calculadas permanecem.\n\n'
            'A malha tem extremidades abertas no cubo e na ponta: **não é um sólido CAD nem o loft do FreeCAD**. '
            'Não inclui discos, eixo físico, carcaça, fixações, folgas ou verificação de colisões. '
            'Os espaçamentos axiais e o alinhamento angular das fileiras são convenções da montagem existente; '
            'não são dimensionamento mecânico ou estudo de interação rotor–estator.\n\n'
            'O **cubo simplificado**, disponível na vista do componente completo, é uma superfície interna de referência. '
            'Mantém o raio de cubo calculado sob a extensão axial de cada raiz e faz uma ligação linear entre fileiras. '
            'A forma entre fileiras é esquemática, sem cálculo de escoamento nesse trecho. '
            'A superfície acompanha o setor visível, é aberta nas extremidades e não é exportada nos DXFs. '
            'Não modela a fixação das pás: rotor gira; estatores e bocais são estacionários.\n\n'
            'Compressor e turbina são mostrados separadamente. O combustor 1D e o difusor não têm geometria '
            'resolvida para montar uma máquina completa entre os componentes. Para examinar uma seção 2D, '
            'use o painel **Do escoamento ao perfil** na aba do componente. A visualização não modifica os DXFs.')
