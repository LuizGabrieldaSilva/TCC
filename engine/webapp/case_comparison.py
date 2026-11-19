"""Comparação de execuções e amostragem radial, a pedido do usuário."""

from copy import deepcopy
import json
import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from engine.webapp.comparison_data import (
    capturar_caso, entradas_alteradas, tabela_metricas, condicoes_discretizacao,
    estudar_secoes, finito,
)
from engine.webapp.case_reproducibility import _sensibilidade_json
from engine.webapp.number_format import tabela_br, figura_br, aviso_br, formato_br


def tabela_contagens(tabela, colunas, linhas=None):
    """Inteiros apenas na apresentação das contagens; preserva dados e ausentes."""
    vista=tabela_br(tabela)
    colunas=[c for c in colunas if c in tabela.columns]
    if colunas:
        subset=colunas if linhas is None else (linhas,colunas)
        vista.format(lambda v: formato_br(v,',.0f') if finito(v) else '—',
                     subset=subset,na_rep='—')
    return vista


def tabela_comparacao(tabela):
    contagens=tabela.index[tabela['Unidade'].isin(['estágios','mensagens'])]
    return tabela_contagens(tabela,['Referência','Atual','Atual − referência'],contagens)


def tabela_avisos(avisos):
    tabela=pd.DataFrame(avisos)[['Caso','componente','origem','estagio','secao','mensagem']].rename(
        columns={'componente':'Componente','origem':'Origem','estagio':'Estágio',
                 'secao':'Seção','mensagem':'Aviso e valor/limite'})
    tabela['Estágio']=tabela['Estágio'].fillna('Geral')
    tabela['Seção']=tabela['Seção'].fillna('Não se aplica')
    return tabela_br(tabela)


def amostras_coincidem(a,b,campo,x):
    """Compara as mesmas abscissas e ordenadas, sem interpolar ou omitir ausentes."""
    return bool(a) and len(a)==len(b) and all(
        finito(va.get(c)) and finito(vb.get(c)) and
        math.isclose(va[c],vb[c],rel_tol=1e-9,abs_tol=1e-10)
        for va,vb in zip(a,b) for c in (x,campo))


def selecionar(label,opcoes,chave,**kwargs):
    if chave in st.session_state and st.session_state[chave] not in opcoes:
        del st.session_state[chave]
    return st.selectbox(label,opcoes,key=chave,**kwargs)


def figura_sobreposta(a,b,campo,ylabel,titulo,x='Altura relativa',xlabel='Altura relativa: cubo = 0 → ponta = 1'):
    fig,ax=plt.subplots(figsize=(8,4.2))
    for nome,dados,marcador,estilo in (('Referência',a,'o','--'),('Atual',b,'s','-')):
        ax.plot([v[x] for v in dados],[v[campo] if finito(v[campo]) else float('nan') for v in dados],
                marker=marcador,linestyle=estilo,markerfacecolor='none',
                markersize=8 if nome=='Referência' else 5,label=nome,
                zorder=3 if nome=='Referência' else 2)
    if amostras_coincidem(a,b,campo,x):
        titulo+='\nCurvas coincidem numericamente nas amostras comparadas'
    ax.set(xlabel=xlabel,ylabel=ylabel,title=titulo);ax.grid(alpha=.25)
    ax.legend(fontsize=9);fig.tight_layout()
    return fig


def figura_estudo(resultados,chave):
    fig,ax=plt.subplots(figsize=(8,4.2));xs=[];ys=[];invalidos=[];meta=None
    for r in resultados:
        xs.append(r['n_secoes'])
        m=r['caso']['metricas'].get(chave) if r['valido'] else None
        v=m['valor'] if m else None;ys.append(v if finito(v) else float('nan'))
        if m:meta=m
        if not finito(v):invalidos.append(r['n_secoes'])
    ax.plot(xs,ys,'o-',label='Resultados nas seções calculadas')
    if invalidos:
        ax.plot(invalidos,[.04]*len(invalidos),'rx',transform=ax.get_xaxis_transform(),
                clip_on=False,label='Não calculado/não determinado (marcação sem valor físico)')
    ax.set_xticks(xs);ax.set_xlabel('Número de seções radiais')
    if meta:ax.set_ylabel(f"{meta['nome']} ({meta['unidade']})")
    ax.set_title('Efeito da discretização radial');ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.tight_layout();return fig


def _mostrar_figura(fig):
    st.pyplot(figura_br(fig),width='stretch');plt.close(fig)


def _comparar_radiais(a,b):
    componente=selecionar('Componente da comparação',['Compressor','Turbina'],'comparar_componente')
    k='comp' if componente=='Compressor' else 'turb'
    ma,mb=a['componentes'][k],b['componentes'][k]
    c1,c2=st.columns(2)
    with c1:ia=selecionar('Estágio na referência',list(range(1,ma['n_estagios']+1)),f'comparar_estagio_ref_{k}')
    with c2:ib=selecionar('Estágio no caso atual',list(range(1,mb['n_estagios']+1)),f'comparar_estagio_atual_{k}')
    st.caption('Os estágios são escolhidos separadamente. O mesmo número ordinal não garante a mesma '
               'posição física ou parcela do trabalho quando a quantidade de estágios muda. '
               'A altura relativa permite comparar a forma da distribuição; os raios físicos permanecem nas tabelas.')
    opcoes={'Reação radial':('R_c','Grau de reação (—)'),
            'Mach relativo':('M1R' if k=='comp' else 'M3R','Mach relativo (—)'),
            'Ângulo absoluto na entrada do rotor':('alpha1' if k=='comp' else 'alpha2','Ângulo absoluto (°)')}
    if k=='comp':opcoes['DF do rotor']=('DF_rotor','Fator de difusão (—)')
    grupo=selecionar('Grandeza radial',list(opcoes),f'comparar_grupo_{k}')
    campo,ylabel=opcoes[grupo]
    da=[v for v in ma['radiais'] if v['Estágio']==ia];db=[v for v in mb['radiais'] if v['Estágio']==ib]
    _mostrar_figura(figura_sobreposta(da,db,campo,ylabel,componente+' — '+grupo))
    if st.checkbox('Mostrar pontos radiais dos dois casos',key='comparar_tabela_radial'):
        st.dataframe(tabela_br(pd.DataFrame([dict(Caso=nome,**v) for nome,linhas in
                      (('Referência',da),('Atual',db)) for v in linhas])[
                          ['Caso','Estágio','Seção','Raio (cm)','Altura relativa',campo]]),hide_index=True,width='stretch')
    with st.expander('Reação e torção dos perfis — mesma seção, duas grandezas',expanded=False):
        fileira=selecionar('Fileira para comparar torção',list(ma['fileiras']),f'comparar_fileira_{k}')
        pa=[v for v in ma['perfis'] if v['Estágio']==ia and v['Fileira']==fileira]
        pb=[v for v in mb['perfis'] if v['Estágio']==ib and v['Fileira']==fileira]
        st.markdown('**Torção relativa ao cubo:** Δζ(r) = ζ(r) − ζ(cubo), usando o stagger metálico '
                    'do perfil entregue ao loft. O sinal é preservado; torção não é câmber nem deflexão do escoamento.')
        _mostrar_figura(figura_sobreposta(pa,pb,'Torção em relação ao cubo (°)','Δζ (°)',
                                         componente+' — torção ao longo da altura'))
        _mostrar_figura(figura_sobreposta(pa,pb,'Torção em relação ao cubo (°)','Δζ (°)',
                                         'Reação e torção nas seções calculadas',x='Reação radial',xlabel='Reação radial do estágio (—)'))
        st.caption('Cada ponto associa reação do estágio e torção da fileira na mesma seção. '
                   'As linhas seguem a ordem do cubo à ponta; não representam uma relação causal universal. '
                   'A reação é resultado do modelo. Consulte acima as entradas alteradas, os modos e os estágios adotados.')
        st.dataframe(tabela_br(pd.DataFrame([dict(Caso=nome,**v) for nome,linhas in
                     (('Referência',pa),('Atual',pb)) for v in linhas])),hide_index=True,width='stretch')


def _estudo_discretizacao(atual,execucao,rodar):
    st.markdown('Mantém as **entradas da execução calculada** e varia somente o número de seções. '
                'O estudo não usa alterações ainda não calculadas do formulário nem substitui o caso principal.')
    secoes=st.multiselect('Seções a avaliar',[3,5,7,9,11],default=[3,7,11],key='estudo_secoes_opcoes')
    st.caption('No automático, cada discretização pode escolher outros estágios por avaliar os critérios '
               'radiais e dos perfis. Se isso ocorrer, a diferença inclui uma mudança de projeto, além da amostragem. '
               'Mais seções não eliminam as hipóteses de meanline e vórtice livre.')
    if st.button('Executar estudo de seções',key='executar_estudo_secoes',disabled=len(secoes)<2):
        with st.spinner('Calculando as discretizações com os modelos existentes...'):
            resultados=estudar_secoes(atual['parametros'],execucao,secoes,rodar)
        st.session_state['estudo_secoes']={'origem':atual['id'],'secoes':sorted(set(secoes)),'resultados':resultados}
    estudo=st.session_state.get('estudo_secoes')
    if not estudo:return
    if estudo['origem']!=atual['id']:
        st.info('O estudo anterior pertence a outra execução. Execute novamente para estudar o caso atual.');return
    if estudo.get('secoes',[r['n_secoes'] for r in estudo['resultados']])!=sorted(set(secoes)):
        st.info('Os resultados abaixo são do último estudo executado. Clique em Executar estudo de seções para aplicar a nova seleção.')
    resultados=estudo['resultados'];linhas=[]
    for r in resultados:
        linha={'Seções':r['n_secoes'],'Estado':'Calculado' if r['valido'] else 'Não calculado',
               'Motivo':aviso_br(r.get('erro',''))}
        if r['valido']:
            caso=r['caso']
            for k,nome in (('comp','Compressor'),('turb','Turbina')):
                linha[nome+' · estágios']=caso['componentes'][k]['n_estagios']
                linha[nome+' · ψ efetivo']=caso['componentes'][k]['psi_efetivo']
            linha['Mensagens']=len(caso['avisos'])
        linhas.append(linha)
    st.dataframe(tabela_contagens(pd.DataFrame(linhas),
        ['Seções','Compressor · estágios','Turbina · estágios','Mensagens']),hide_index=True,width='stretch')
    falhas=[r for r in resultados if not r['valido']]
    if falhas:
        numero=selecionar('Discretização para ler o motivo completo',[r['n_secoes'] for r in falhas],'estudo_secoes_falha')
        st.write(aviso_br(next(r['erro'] for r in falhas if r['n_secoes']==numero)))
    validos=[r for r in resultados if r['valido']]
    if validos:
        base=validos[0]['caso']
        if any(not condicoes_discretizacao(base,r['caso'])['mesmos_estagios'] for r in validos):
            st.warning('O número de estágios mudou entre discretizações. Não interprete as diferenças como '
                       'convergência de uma mesma geometria. Use estágios manuais para estudar a amostragem com N fixo.')
        chaves=[k for k,m in base['metricas'].items() if m['grupo'] in ('Compressor','Turbina')]
        chave=selecionar('Grandeza do estudo de seções',chaves,'estudo_secoes_metrica',
                        format_func=lambda k:base['metricas'][k]['grupo']+' · '+base['metricas'][k]['nome'])
        _mostrar_figura(figura_estudo(resultados,chave))
        valores=[]
        for r in validos:
            m=r['caso']['metricas'][chave]
            valores.append({'Seções':r['n_secoes'],'Valor':m['valor'],'Unidade':m['unidade'],'Localização':m['local']})
        st.dataframe(tabela_contagens(pd.DataFrame(valores),['Valor']
            if base['metricas'][chave]['unidade'] in ('estágios','mensagens') else []),hide_index=True,width='stretch')
        if len(validos)>=2:
            with st.expander('Diferenças em relação à menor discretização calculada'):
                outro=selecionar('Discretização para detalhar',[r['n_secoes'] for r in validos[1:]],'estudo_secoes_detalhe')
                alvo=next(r['caso'] for r in validos if r['n_secoes']==outro)
                st.dataframe(tabela_comparacao(tabela_metricas(base,alvo)),hide_index=True,width='stretch')
    st.caption('Não há interpolação entre as seções dos casos. As curvas mostram apenas amostras calculadas; '
               'malhas de 5 e 7 seções, por exemplo, não contêm necessariamente os mesmos raios intermediários. '
               'Mensagens e valores extremos não precisam variar monotonicamente com a discretização.')
    st.download_button('Baixar dados do estudo de seções (JSON)',
        data=json.dumps(_sensibilidade_json(estudo),ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),
        file_name='estudo_secoes.json',mime='application/json',key='baixar_estudo_secoes',on_click='ignore')


def exibir_comparacao(r,execucao,rodar):
    st.subheader('Comparar projetos')
    st.caption('Compare execuções calculadas. Alterações ainda não calculadas no formulário não entram aqui. '
               'A referência é mantida somente nesta sessão; baixe os dados antes de encerrá-la.')
    if not all(r.get(k) is not None for k in ('perfis_comp','perfis_turb')):
        st.info('Recalcule o caso para registrar os perfis necessários à comparação.');return
    atual=capturar_caso(r,execucao)
    if st.button('Fixar execução atual como referência',key='fixar_referencia_comparacao'):
        st.session_state['referencia_comparacao']=deepcopy(atual)
    referencia=st.session_state.get('referencia_comparacao')
    if referencia:
        st.write(f"**Referência:** {referencia['nome']} · `{referencia['id']}`")
        st.write(f"**Atual:** {atual['nome']} · `{atual['id']}`")
        if referencia['id']==atual['id']:st.info('A referência e o caso atual são a mesma execução. Altere as entradas e calcule um novo caso para comparar.')
    else:
        st.info('Fixe uma execução como referência. Depois altere as entradas e calcule novamente. '
                'A referência permanecerá preservada até você substituí-la pelo botão acima.')
    if referencia:
        with st.expander('Entradas alteradas e condições da comparação',expanded=True):
            alteradas=entradas_alteradas(referencia,atual)
            if alteradas:st.dataframe(tabela_br(pd.DataFrame(alteradas)),hide_index=True,width='stretch')
            else:st.write('As entradas dos dois casos são iguais.')
            for nome,caso in (('Referência',referencia),('Atual',atual)):
                st.caption(nome+': '+', '.join(f"{c['nome']}: {'automático' if c['automatico'] else 'manual'}, {c['n_estagios']} estágios"
                                              for c in caso['componentes'].values()))
            cond=condicoes_discretizacao(referencia,atual)
            if not cond['mesmo_modelo']:
                st.warning('A identificação do modelo difere ou não está disponível. As diferenças podem incluir mudanças de código ou propriedades.')
            if referencia['parametros']['n_secoes']!=atual['parametros']['n_secoes']:
                st.info('As discretizações são diferentes. '+
                        ('As demais entradas foram mantidas.' if cond['somente_secoes'] else 'Outras entradas também mudaram; não atribua toda diferença ao número de seções.'))
        with st.expander('Resultados globais, extremos radiais e dimensões',expanded=True):
            tabela=tabela_metricas(referencia,atual)
            st.dataframe(tabela_comparacao(tabela.drop(columns=['Local na referência','Local no atual'])),hide_index=True,width='stretch')
            st.caption('Diferença = atual − referência; percentual = 100 × diferença / |referência|. '
                       'Referência zero ou valor não determinado: percentual “—”. Para eficiências em %, '
                       'a diferença absoluta é em pontos percentuais. Extremos são das seções calculadas. '
                       'A extensão axial é uma convenção da montagem CAD. Contagem de avisos não mede gravidade nem aprova um projeto.')
            with st.expander('Localização dos extremos e avisos de cada caso'):
                st.dataframe(tabela_br(tabela[['Componente','Grandeza','Local na referência','Local no atual']]),hide_index=True,width='stretch')
                avisos=[dict(Caso=nome,**v) for nome,caso in (('Referência',referencia),('Atual',atual)) for v in caso['avisos']]
                if avisos:
                    st.dataframe(tabela_avisos(avisos),hide_index=True,width='stretch')
        with st.expander('Distribuições radiais, reação e torção',expanded=False):_comparar_radiais(referencia,atual)
        st.download_button('Baixar comparação dos dois casos (JSON)',
            data=json.dumps(_sensibilidade_json({'referencia':referencia,'atual':atual}),ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8'),
            file_name='comparacao_casos.json',mime='application/json',key='baixar_comparacao',on_click='ignore')
    with st.expander('Estudo de discretização — variar somente as seções radiais',expanded=False):
        _estudo_discretizacao(atual,execucao,rodar)
