"""Fluxos de casos e relatório portátil baseados nas entradas/resultados da sessão."""

from collections import Counter
from datetime import datetime
import io
import json
import math
import zipfile
from numbers import Integral, Real

import pandas as pd
import streamlit as st

from engine.indicadores import indicadores_energeticos
from engine.webapp.case_io import (
    MAX_BYTES, aplicar_entradas, contexto_modelo, diferencas_entradas,
    exportar_entradas, ler_entradas,
)
from engine.webapp.criteria_catalog import catalogo_criterios, REFERENCIAS
from engine.webapp.number_format import formato_br, aviso_br


HIPOTESES = [
    'Gás ideal com propriedades constantes por região, distintas para ar e gases. k=cp/(cp−R). '
    'Automático: produtos completos CO2/H2O/N2/O2/Ar de combustível representativo; cp equivalente '
    'pela integral NASA entre 298,15 K e TIT e R=Ru/M; constantes na expansão. '
    'Prescrito: conserva h=cp*T legado. Sem equilíbrio, dissociação ou entalpia sensível do combustível.',
    'Eficiências politrópicas e perda relativa de pressão no combustor prescritas pelo usuário.',
    'Eixo único e transmissão mecânica ideal; sem gerador, consumos auxiliares ou previsão de potência elétrica.',
    'Combustor 1D: f inclui a massa de combustível na saída; combustível sem termo explícito de entalpia sensível. '
    'Q_total representa aquecimento virtual de ar com cp_ar, omite a mudança de propriedades e a massa de combustível, e não deve ser somado à energia do combustível.',
    'Mach de entrada no combustor prescrito; difusor compressor–combustor não modelado.',
    'Raio médio aritmético constante em cada componente; continuidade aproximada em meanline, sem integração radial de densidade.',
    'Distribuição radial por vórtice livre imposta nas estações calculadas; os extremos dependem da discretização.',
    'Perfis simplificados por arco circular e espessura parabólica. Compressor: incidência zero e desvio por Carter; '
    'turbina: incidência e desvio impostos como zero.',
    'Pressão total, densidade e área entre fileiras não são determinadas sem repartir as perdas nessa estação. '
    'A geometria usa uma área representativa por estágio, sem resolver a variação axial dentro das fileiras.',
    'Sensibilidade é uma varredura de projeto, não um mapa experimental ou uma simulação off-design de geometria fixa. '
    'No automático, cada ponto pode escolher outro número de estágios.',
    'Sem verificação de resistência, vibração, resfriamento, folgas, colisões, estabilidade de chama, estol/surge ou fabricação.',
]


def exibir_importacao():
    """Chamado antes dos widgets das entradas para permitir preenchimento atômico."""
    with st.expander('Salvar e recuperar casos',expanded=False):
        st.caption('Importe um JSON de entradas da plataforma para preencher os campos. '
                   'Confira os valores e clique em Calcular e atualizar gráficos para gerar novos resultados.')
        arquivo=st.file_uploader('JSON de entradas do caso',type=['json'],key='arquivo_caso')
        documento=None
        if arquivo is not None:
            try:
                if arquivo.size>MAX_BYTES:raise ValueError('O arquivo deve ter até 64 KiB.')
                documento=ler_entradas(arquivo.getvalue())
            except ValueError as erro:
                st.error(str(erro))
            else:
                p=documento['parametros']
                if documento['versao'] < 3:
                    st.info('Caso anterior: o modo de propriedades prescritas foi preservado. A composição automática não é ativada durante a importação. Confira as propriedades antes de recalcular.')
                st.write(f"**Caso:** {documento['nome']}")
                st.caption(f"Vazão: {formato_br(p['m_dot'],'.6g')} kg/s · "
                           f"Eixo: {formato_br(p['N_comp'],'.6g')} rpm · "
                           f"Seções radiais: {p['n_secoes']}. P01 é informado em kPa.")
                if documento['modelo'].get('sha256_fontes_engine')!=contexto_modelo()['sha256_fontes_engine']:
                    st.warning('A versão dos códigos de cálculo difere da versão registrada no arquivo. '
                               'As entradas podem ser recuperadas, mas os resultados precisam ser conferidos após o cálculo.')
        if st.button('Aplicar entradas do arquivo',key='aplicar_caso',disabled=documento is None):
            aplicar_entradas(documento,st.session_state)
            st.success('Entradas carregadas. Confira os campos antes de calcular. Os resultados anteriores continuam identificados pela execução de origem.')


def exibir_salvar_rascunho(parametros):
    with st.expander('Baixar entradas atuais',expanded=False):
        nome=st.text_input('Nome do caso',value='Meu caso',max_chars=120,key='nome_caso')
        st.caption('Salva os valores atuais dos campos, inclusive os ainda não calculados. '
                   'Resultados e gráficos pertencem à última execução calculada.')
        try:dados=exportar_entradas(parametros,nome,contexto_modelo())
        except ValueError as erro:st.info(f'Para salvar as entradas: {erro}')
        else:
            st.download_button('Baixar JSON das entradas atuais',data=dados,file_name='entradas_caso.json',
                               mime='application/json',key='baixar_rascunho',on_click='ignore',width='stretch')


def exibir_pendencias(atuais,execucao):
    if not execucao:return
    diferentes=diferencas_entradas(atuais,execucao['parametros'])
    if diferentes:
        st.warning('Há alterações nas entradas ainda não calculadas. '
                   'Os resultados, gráficos e downloads da execução continuam usando os valores anteriores. '
                   'Clique em Calcular e atualizar gráficos para aplicar as mudanças.')


def _json(dados):
    return json.dumps(dados,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')


def _sensibilidade_json(valor):
    """Preserva linhas inválidas e seus erros; valores ausentes viram null no JSON."""
    if isinstance(valor,pd.DataFrame):return _sensibilidade_json(valor.to_dict(orient='records'))
    if isinstance(valor,dict):return {k:_sensibilidade_json(v) for k,v in valor.items()}
    if isinstance(valor,(list,tuple)):return [_sensibilidade_json(v) for v in valor]
    if isinstance(valor,bool):return valor
    if isinstance(valor,Integral):return int(valor)
    if isinstance(valor,Real):return float(valor) if math.isfinite(valor) else None
    return valor


def _texto(v):
    if v is None:return 'Não determinado'
    if isinstance(v,float):return formato_br(v,'.8g')
    return str(v).replace('|','\\|').replace('\n',' ')


def _tabela(cabecalho,linhas):
    return '\n'.join(['| '+' | '.join(cabecalho)+' |',
                      '| '+' | '.join('---' for _ in cabecalho)+' |',
                      *['| '+' | '.join(_texto(v) for v in linha)+' |' for linha in linhas]])


def dados_relatorio(resultados,execucao,diagnosticos,sensibilidade=None,erro_sensibilidade=None):
    """Fotografia dos dados existentes, sem resolver modelos ou modificar objetos."""
    r=resultados;c=r['ciclo'];b=r['combustor']
    estados=[{'estacao':nome,'T_total_K':T,'P_total_Pa':P} for nome,T,P in (
        ('01',c.T01,c.P01),('02',c.T02r,c.P02),('03',c.TIT,c.P03),('04',c.T04r,c.P04))]
    maquinas={}
    for chave in ('comp','turb'):
        obj=r[chave]
        maquinas[chave]={'n_estagios':obj.n_estagios,'psi_solicitado':obj.psi,'psi_efetivo':obj.psi_efetivo,
                        'selecao_automatica':getattr(obj,'selecao_estagios',None),
                        'estagios':[{'estagio':i+1,'T_entrada_K':obj.Tt_entrada[i],
                                     'T_saida_K':obj.Tt_saida[i],'P_entrada_Pa':obj.Pt_entrada[i],
                                     'P_saida_Pa':obj.Pt_saida[i],'pi_estagio':obj.pi_estagio[i]}
                                    for i in range(obj.n_estagios)]}
    inicio=execucao['iniciada_em']
    return {'formato':'tcc-turbina-axial/relatorio','versao':1,
            'execucao':{'id':execucao['id'],'nome':execucao.get('nome_caso','Caso calculado'),
                        'iniciada_em':inicio.isoformat() if isinstance(inicio,datetime) else str(inicio),
                        'etapas':execucao.get('etapas',{})},
            'entradas':dict(execucao['parametros']),'unidade_P01_entrada':'kPa',
            'modelo':execucao.get('contexto_modelo'),
            'estados_ciclo':estados,'indicadores':indicadores_energeticos(c,b),
            'propriedades_utilizadas':c.propriedades(),
            'combustor':b.resultados(),'fontes_combustivel':b.fontes_combustivel(),
            'maquinas':maquinas,'diagnosticos':diagnosticos,
            'avisos':r.get('avisos_detalhados',[]),'hipoteses_e_limitacoes':HIPOTESES,
            'catalogo_criterios':catalogo_criterios(),'referencias':REFERENCIAS,
            'sensibilidade':_sensibilidade_json(sensibilidade or {}),
            'erro_sensibilidade':erro_sensibilidade}


def markdown_relatorio(dados,entradas_formatadas):
    d=dados;e=d['execucao'];i=d['indicadores'];avisos=d['avisos']
    partes=['# Relatório do caso — turbina a gás axial',f"**Caso:** {_texto(e['nome'])}",
            f"Execução: `{e['id']}` · Início: {e['iniciada_em']}",
            'Resultados de projeto preliminar sob as hipóteses abaixo. O fechamento numérico não comprova desempenho real ou aptidão para fabricação.',
            '## Entradas usadas no cálculo',
            _tabela(['Entrada','Valor submetido'],entradas_formatadas.itertuples(index=False,name=None)),
            'P01 nas entradas está em kPa. Os resultados JSON usam as unidades identificadas nas chaves. '
            'O JSON de entradas preserva os modos manual/automático; o número adotado consta nos resultados.',
            '## Propriedades constantes utilizadas',
            _tabela(['Fluido','cp (J/(kg K))','R (J/(kg K))','k'],
                [(nome,p['cp_J_kg_K'],p['R_J_kg_K'],p['k'])
                 for nome,p in d['propriedades_utilizadas'].items()]),
            'k = cp/(cp − R). Cada fluido tem propriedades constantes. O balanço do combustor '
            'usa entalpias sensíveis relativas a 298,15 K no automático e conserva h=cp*T no modo prescrito. '
            'No automático, cp dos produtos é equivalente à integral NASA de 298,15 K a TIT; '
            'a turbina mantém esse cp constante, sem integrar cp(T) na expansão. '
            'Composição, método e fontes constam em resultados.json.',
            '## Estado de cada etapa',_tabela(['Etapa','Estado'],e['etapas'].items()),
            '## Estados totais do ciclo',_tabela(['Estação','T total (K)','P total (Pa)'],
                [(v['estacao'],v['T_total_K'],v['P_total_Pa']) for v in d['estados_ciclo']]),
            '## Indicadores energéticos',_tabela(['Grandeza','Valor'],[
                ('Potência líquida do ciclo (kW)',i['potencia_liquida_W']/1000),
                ('Eficiência sobre calor útil (%)',100*i['eta_calor_util']),
                ('Eficiência sobre PCI (%)',100*i['eta_PCI']),('BWR',i['BWR']),
                ('SFC (kg/kWh)',i['SFC_kg_kWh'])]),
            'Potência do ciclo com transmissão mecânica ideal. Trabalho líquido por kg de ar; '
            'trabalho da turbina por kg de gases. Eficiência sobre PCI = η_b × eficiência sobre calor útil.',
            '## Combustor',_tabela(['Grandeza (unidade na chave)','Valor'],d['combustor'].items()),
            'Q_total_kW é um indicador auxiliar de aquecimento virtual de ar com cp_ar: '
            'omite a mudança de propriedades e a massa de combustível; não é o calor útil do combustível. '
            'As propriedades e suas fontes estão em resultados.json.',
            '## Máquinas e fechamento']
    for chave,nome in (('comp','Compressor'),('turb','Turbina')):
        m=d['maquinas'][chave]
        partes += [f'### {nome}',
                   f"Estágios adotados: {m['n_estagios']} · ψ solicitado: {_texto(m['psi_solicitado'])} · ψ efetivo: {_texto(m['psi_efetivo'])}.",
                   _tabela(['Estágio','T entrada (K)','T saída (K)','P entrada (Pa)','P saída (Pa)','Razão de pressão'],
                           [(v['estagio'],v['T_entrada_K'],v['T_saida_K'],v['P_entrada_Pa'],v['P_saida_Pa'],v['pi_estagio']) for v in m['estagios']])]
    partes += ['Alvos coincidem numericamente: '+('sim.' if d['diagnosticos']['alvos_coincidem'] else 'não.'),
               'Resíduos, áreas por estação, interfaces e critérios de seleção estão em resultados.json. '
               'As tabelas radiais estão nos CSVs. O limiar de aviso de fechamento não é uma tolerância de projeto.',
               '## Avisos registrados',f'Total: {len(avisos)}. Contagem por componente: '+
               ', '.join(f'{k}: {v}' for k,v in Counter(a['componente'] for a in avisos).items())+'.',
               _tabela(['Componente','Origem','Estágio','Seção','Mensagem'],
                       [(a['componente'],a['origem'],a.get('estagio'),a.get('secao'),aviso_br(a['mensagem'])) for a in avisos]),
               'Zero avisos não comprova aprovação física. As mensagens originais, sem tradução dos números, permanecem no JSON.',
               '## Hipóteses e limitações',*['- '+h for h in d['hipoteses_e_limitacoes']],
               '## Critérios e referências',
               _tabela(['Critério','Natureza','Definição/faixa padrão','Origem'],
                       [(c['nome'],c['natureza'],c['criterio'],c['fonte']) for c in d['catalogo_criterios']]),
               *[f'**{titulo}** — {uso} {local}' for titulo,uso,local in d['referencias']],
               'As páginas são impressas. Referências contextuais não fixam limites universais; confira as condições de aplicação de cada método.',
               '## Como recuperar e conferir',
               '1. Importe entradas.json em Salvar e recuperar casos e aplique as entradas.\n'
               '2. Confira os campos e clique em Calcular e atualizar gráficos.\n'
               '3. Compare os novos resultados com resultados.json e os CSVs deste pacote.\n'
               '4. Compare a identificação dos códigos, cp, k e critérios. Mudanças de versão podem mudar os resultados.',
               'O pacote não contém os livros, código-fonte, imagens dos gráficos ou sólidos CAD. '
               'As curvas de sensibilidade disponíveis são guardadas como dados no JSON; a geometria pode ser baixada separadamente em DXF.']
    if d['erro_sensibilidade']:partes += ['**Sensibilidade incompleta:** '+d['erro_sensibilidade']]
    if d['modelo'] is None:partes += ['**Versão do modelo não registrada:** recalcule o caso para registrar a identificação dos códigos e propriedades.']
    return '\n\n'.join(partes)+'\n'


def pacote_relatorio(dados,entradas_formatadas,csv_comp,csv_turb):
    buffer=io.BytesIO()
    arquivos={'relatorio.md':markdown_relatorio(dados,entradas_formatadas).encode('utf-8'),
              'resultados.json':_json(dados),'parametros_compressor.csv':csv_comp,'parametros_turbina.csv':csv_turb}
    if dados['modelo'] is not None:
        arquivos['entradas.json']=exportar_entradas(dados['entradas'],dados['execucao']['nome'],
                                                   dados['modelo'],dados['execucao']['id'])
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
        for nome,conteudo in arquivos.items():z.writestr(nome,conteudo)
    return buffer.getvalue()


def exibir_relatorio(resultados,execucao,diagnosticos,entradas_formatadas,csv_comp,csv_turb,sensibilidade,erro_sensibilidade):
    with st.expander('Salvar o caso calculado e seu relatório',expanded=False):
        st.caption('Exporta a execução identificada no topo da página. Alterações ainda não calculadas '
                   'nos campos não entram neste relatório. O ZIP reúne relatório em Markdown, entradas JSON, '
                   'resultados e dados de sensibilidade em JSON e tabelas CSV. Livros, imagens e CAD não são incluídos.')
        contexto=execucao.get('contexto_modelo')
        if contexto is not None:
            st.download_button('Baixar JSON das entradas calculadas',
                data=exportar_entradas(execucao['parametros'],execucao.get('nome_caso','Caso calculado'),contexto,execucao['id']),
                file_name='entradas_calculadas.json',mime='application/json',key='baixar_entradas_calculadas',on_click='ignore')
        else:st.info('Recalcule o caso para registrar a versão do modelo e exportar suas entradas com rastreabilidade.')
        if st.button('Preparar relatório da execução',key='preparar_relatorio'):
            dados=dados_relatorio(resultados,execucao,diagnosticos,sensibilidade,erro_sensibilidade)
            st.session_state['relatorio_preparado']=(execucao['id'],pacote_relatorio(dados,entradas_formatadas,csv_comp,csv_turb))
        preparado=st.session_state.get('relatorio_preparado')
        if preparado and preparado[0]==execucao['id']:
            st.download_button('Baixar relatório do caso (ZIP)',data=preparado[1],
                               file_name=f"relatorio_{execucao['id']}.zip",mime='application/zip',
                               key='baixar_relatorio',on_click='ignore')
