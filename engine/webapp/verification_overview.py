"""Visão consolidada, somente leitura, dos avisos e das referências do caso."""

from collections import Counter
import pandas as pd
import streamlit as st

from engine.webapp.criteria_catalog import catalogo_criterios, criterio_do_aviso, REFERENCIAS
from engine.webapp.number_format import tabela_br, aviso_br


COMPONENTES = ('Ciclo','Combustor','Compressor','Turbina','Sistema')
ETAPAS = {
    'Ciclo':('ciclo',), 'Combustor':('combustor_1d',),
    'Compressor':('compressor_meanline','compressor_radial','compressor_perfis','compressor_geometria'),
    'Turbina':('turbina_meanline','turbina_radial','turbina_perfis','turbina_geometria'),
    'Sistema':('acoplamento_vazao','sensibilidade'),
}


def resumo_componentes(avisos, etapas):
    contagens=Counter(a.get('componente','Sistema') for a in avisos)
    linhas=[]
    nomes=list(COMPONENTES)+sorted(set(contagens)-set(COMPONENTES))
    for nome in nomes:
        estados=[etapas.get(k,'Não registrado') for k in ETAPAS.get(nome,())]
        if not estados or any(e=='Não registrado' for e in estados):situacao='Registro incompleto'
        elif any(e=='Falhou' for e in estados):situacao='Há etapa que falhou'
        elif any(not e.startswith('Calculada') for e in estados):situacao='Consultar estado das etapas'
        else:situacao='Etapas calculadas'
        linhas.append({'Componente':nome,'Avisos registrados':contagens[nome],
                       'Etapas da execução':situacao})
    return pd.DataFrame(linhas)


def registros_avisos(avisos, execucao_id):
    """IDs de seleção independentes de filtros/ordenação e de mensagens traduzidas."""
    registros=[];ocorrencias=Counter()
    for i,aviso in enumerate(avisos):
        original=aviso.get('_aviso_id',f'registro-{i}')
        ocorrencias[original]+=1
        chave=f'{execucao_id}:{original}:{ocorrencias[original]}'
        registros.append(dict(aviso=aviso, chave=chave, rotulo=f'A{i+1:03d}',
                              criterio_id=criterio_do_aviso(aviso)))
    return registros


def _descricao_local(aviso):
    partes=[f"Estágio {aviso['estagio']}" if aviso.get('estagio') else 'Geral (sem estágio)']
    partes += [str(aviso[k]) for k in ('fileira','secao') if aviso.get(k)]
    return ' · '.join(partes)


def _seletor_valido(chave, opcoes):
    if chave in st.session_state and st.session_state[chave] not in opcoes:
        del st.session_state[chave]


def _detalhes(criterio):
    st.markdown(f"**{criterio['nome']}**")
    st.table(pd.DataFrame([
        ('Natureza',criterio['natureza']),('Critério padrão / definição',criterio['criterio']),
        ('Origem / referência',criterio['fonte']),('Localização e alcance',criterio['alcance']),
    ],columns=['Campo','Informação']).set_index('Campo'))
    st.markdown(f"**Como interpretar.** {criterio['interpretar']}\n\n"
                f"**Próxima análise útil.** {criterio['analisar']}")


def exibir_consolidado(resultados, execucao, diagnosticos, classificar_aviso):
    avisos=resultados.get('avisos_detalhados',[])
    execucao=execucao or {}
    catalogo=catalogo_criterios();por_id={c['id']:c for c in catalogo}
    st.subheader('Verificações e referências')
    st.caption('Consulte os avisos e as referências do caso calculado. Para explorar os resultados em detalhe, '
               'use também os painéis de Ciclo, Combustor, Compressor e Turbina.')
    st.dataframe(tabela_br(resumo_componentes(avisos,execucao.get('etapas',{}))),hide_index=True,width='stretch')
    st.caption('As contagens são de mensagens registradas, não de gravidade ou de critérios aprovados. '
               'Zero avisos não comprova segurança, estabilidade ou validade fora das hipóteses. '
               'Registros sem componente identificado são agrupados em Sistema; o estado das etapas '
               'está no resumo da execução no topo da página.')

    with st.expander('Avisos desta execução — mensagem, critério e interpretação',expanded=True):
        componentes=['Todos',*COMPONENTES,*sorted({a.get('componente','Sistema') for a in avisos}-set(COMPONENTES))]
        _seletor_valido('verificacao_componente',componentes)
        comp=st.selectbox('Filtrar avisos por componente',componentes,key='verificacao_componente')
        registros=[r for r in registros_avisos(avisos,execucao.get('id','sem-id'))
                   if comp=='Todos' or r['aviso'].get('componente')==comp]
        if not registros:
            st.info('Nenhum aviso registrado neste filtro. Consulte também os critérios e as limitações abaixo.')
        else:
            st.dataframe(tabela_br(pd.DataFrame([
                {'Aviso':r['rotulo'],'Componente':r['aviso'].get('componente','Sistema'),
                 'Origem':r['aviso'].get('origem','Não registrada'), 'Localização':_descricao_local(r['aviso']),
                 'Critério associado':por_id[r['criterio_id']]['nome'] if r['criterio_id'] else 'Não associado automaticamente',
                 'Aviso e valor/limite':r['aviso']['mensagem']} for r in registros])),
                hide_index=True,width='stretch')
            por_chave={r['chave']:r for r in registros}
            _seletor_valido('verificacao_aviso',por_chave)
            chave=st.selectbox('Aviso para leitura completa',list(por_chave),key='verificacao_aviso',
                format_func=lambda k:f"{por_chave[k]['rotulo']} · {por_chave[k]['aviso'].get('componente')} · {_descricao_local(por_chave[k]['aviso'])}")
            registro=por_chave[chave];aviso=registro['aviso']
            st.markdown('**Mensagem completa do registro selecionado**')
            st.write(aviso_br(aviso['mensagem']))
            if registro['criterio_id']:
                _detalhes(por_id[registro['criterio_id']])
                st.caption('A associação explica a família do aviso. O valor, operador e limite efetivamente '
                           'registrados são os da mensagem; o catálogo mostra os critérios padrão do projeto.')
            else:
                tipo,interpretacao=classificar_aviso(aviso['mensagem'])
                st.write(f'**Classificação do painel local:** {tipo}')
                st.write(interpretacao)
                st.caption('Este aviso não possui referência específica indicada no catálogo. '
                           'Consulte sua origem e o painel do componente para compreender o contexto.')

    with st.expander('Fechamento numérico disponível nesta execução',expanded=False):
        if not diagnosticos:
            st.info('Diagnósticos de integração não disponíveis nesta execução.')
        else:
            st.write('**Alvos coincidem numericamente.**' if diagnosticos['alvos_coincidem']
                     else '**Há diferenças entre os alvos do ciclo e os resultados das máquinas.**')
            linhas=[]
            for interface,itens in diagnosticos.get('interfaces',{}).items():
                for v in itens:
                    linhas.append({'Interface':interface,'Grandeza':v['grandeza'],'Unidade':v['unidade'],
                                   'Resíduo (calculado − alvo)':v['residuo'],'Diferença (%)':v['residuo_pct'],
                                   'Coincidência numérica':'Sim' if v['coincide'] else 'Não'})
            st.dataframe(tabela_br(pd.DataFrame(linhas)),hide_index=True,width='stretch')
            _detalhes(por_id['coincidencia'])
            st.caption('Os valores são lidos dos diagnósticos já calculados. As comparações completas de potências '
                       'e componentes permanecem em Fechamento ciclo–meanline, na aba Ciclo. '
                       'Não há verificação de continuidade de velocidade, swirl e geometria no difusor ausente.')

    with st.expander('Catálogo de critérios — natureza, origem e alcance',expanded=False):
        naturezas=['Todas',*sorted({c['natureza'] for c in catalogo})]
        natureza=st.selectbox('Natureza do critério',naturezas,key='verificacao_natureza')
        disponiveis=[c for c in catalogo if natureza=='Todas' or c['natureza']==natureza]
        st.dataframe(pd.DataFrame([{'Critério':c['nome'],'Componentes':', '.join(c['componentes']),
                                   'Natureza':c['natureza']} for c in disponiveis]),hide_index=True,width='stretch')
        por_codigo={c['id']:c for c in disponiveis}
        _seletor_valido('verificacao_criterio',por_codigo)
        codigo=st.selectbox('Critério para consultar',list(por_codigo),key='verificacao_criterio',
                             format_func=lambda k:por_codigo[k]['nome'])
        _detalhes(por_codigo[codigo])
        st.caption('Use a natureza do critério para distinguir definições físicas, correlações empíricas '
                   'e escolhas do projeto. A inclusão de um item no catálogo não significa que o caso '
                   'tenha sido aprovado nesse critério.')

    with st.expander('O que a plataforma verifica e o que permanece fora do modelo',expanded=False):
        st.table(pd.DataFrame([
            ('Consistência numérica','Resíduos e comparações disponíveis nos painéis e nos verificadores do projeto.',
             'Igualdade algébrica não demonstra desempenho real.'),
            ('Aerodinâmica','Triagens de Mach, DF, reação, carga e swirl nos contextos implementados.',
             'Não há mapa experimental, margem de estol/surge, CFD, choques ou modelo detalhado de perdas.'),
            ('Combustão','Balanço 1D, combustível adicionado e dimensões estimadas.',
             'Não prevê estabilidade da chama, química detalhada, emissões ou distribuição local da mistura.'),
            ('Acoplamento','Comparações ciclo–meanline e interfaces termodinâmicas.',
             'Difusor não modelado; pressão e área entre fileiras podem permanecer não determinadas.'),
            ('Geometria e CAD','Seções calculadas, perfis simplificados, montagem e exportação de curvas.',
             'Sem verificação automática de colisões, folgas, resistência, vibração, resfriamento ou fabricação.'),
            ('Referências','Fundamentos e exemplos relacionados aos métodos e às hipóteses apresentados.',
             'Cada referência se aplica ao assunto indicado; sua citação não valida, por si só, '
             'o conjunto da máquina nem transforma escolhas do projeto em limites universais.'),
        ],columns=['Área','Alcance existente','Limitação']).set_index('Área'))

    with st.expander('Referências do projeto e rastreabilidade bibliográfica',expanded=False):
        st.markdown('**Como consultar as referências.** Os assuntos abaixo ajudam a escolher a leitura para cada '
                    'parte do modelo. As páginas correspondem à numeração impressa do livro, que pode diferir '
                    'da contagem do leitor de PDF. Equações e exemplos indicados são pontos de consulta; '
                    'confira também suas hipóteses e condições de aplicação.')
        st.caption('Quando houver apenas indicação do livro ou do assunto, a referência é contextual. '
                   'Consulte a origem de cada critério no catálogo para distinguir fundamento teórico, '
                   'correlação empírica e valor adotado no projeto.')
        for titulo,uso,local in REFERENCIAS:
            st.markdown(f'**{titulo}**\n\n{uso}\n\n{local}')
        st.caption('As evidências numéricas e as ressalvas de cada comparação estão na matriz de rastreabilidade '
                   'e nos relatórios de verificação do projeto. Dados nominais de combustível sem fonte específica '
                   'confirmada continuam identificados em Fontes e hipóteses do combustível, na aba Combustor.')
