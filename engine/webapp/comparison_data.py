"""Fotografias numéricas e comparações; não altera os modelos nem escolhe candidatos."""

from copy import deepcopy
import math

import pandas as pd

from engine.indicadores import indicadores_energeticos
from engine.webapp.stage_overview import dados_estagios
from engine.webapp.radial_distribution import dados_radiais
from engine.webapp.number_format import formato_br


ROTULOS = {
    'mistura_automatica':'Propriedades da mistura calculadas (NASA Glenn)',
    'T01':'Temperatura de entrada (K)','P01':'Pressão de entrada (kPa)',
    'r_compr':'Razão de pressão do ciclo','TIT':'TIT (K)','TIT_max':'TIT máxima (K)',
    'e_compr':'Eficiência politrópica do compressor','e_turb':'Eficiência politrópica da turbina',
    'Delta_P_cc':'Perda relativa de pressão do combustor','m_dot':'Vazão de ar (kg/s)',
    'combustivel':'Combustível','eta_b':'Eficiência de combustão','M_entrada':'Mach prescrito no combustor',
    'N_comp':'Rotação do eixo (rpm)','N_turb':'Rotação da turbina (rpm)',
    'HTR_comp':'HTR de entrada do compressor','HTR_turb':'HTR de entrada da turbina',
    'n_estagios_comp':'Estágios do compressor (entrada)','n_estagios_turb':'Estágios da turbina (entrada)',
    'phi_comp':'φ do compressor','psi_comp':'ψ solicitado do compressor',
    'phi_turb':'φ da turbina','psi_turb':'ψ solicitado da turbina',
    'alpha1_comp':'Ângulo α₁ do compressor (°)','alpha2_turb':'Ângulo α₂ do bocal (°)',
    'DF_alvo':'DF alvo do compressor','AR_comp':'h/c do compressor','AR_turb':'h/c da turbina',
    'sigma_turb':'Solidez alvo da turbina','n_secoes':'Seções radiais',
    'cp_ar':'cp do ar (J/kg·K)','cp_gases':'cp dos gases (J/kg·K)',
    'R_ar':'Constante R do ar (J/kg·K)','R_gases':'Constante R dos gases (J/kg·K)',
}


def finito(valor):
    return isinstance(valor,(int,float)) and math.isfinite(valor)


def _extremo(itens,menor=False):
    if not itens or any(not finito(v) for v,_ in itens):return None,'Não determinado: há valor ausente/não finito'
    return (min if menor else max)(itens,key=lambda x:x[0])


def capturar_caso(r,execucao):
    """Copia somente escalares/tabelas necessários; nenhum objeto físico fica compartilhado."""
    metricas={};c=r['ciclo'];ind=indicadores_energeticos(c,r['combustor'])
    def add(chave,grupo,nome,unidade,valor,local='Global'):
        metricas[chave]={'grupo':grupo,'nome':nome,'unidade':unidade,
                         'valor':valor if finito(valor) else None,'local':local}
    for chave,nome,unidade,valor in (
        ('eta_util','Eficiência sobre calor útil','%',100*ind['eta_calor_util']),
        ('eta_PCI','Eficiência sobre PCI','%',100*ind['eta_PCI']),
        ('potencia','Potência líquida do ciclo','kW',ind['potencia_liquida_W']/1000),
        ('trabalho','Trabalho líquido por kg de ar','kJ/kg de ar',c.w_líq/1000),
        ('SFC','SFC','kg/kWh',ind['SFC_kg_kWh']),('BWR','BWR','—',ind['BWR']),
        ('m_gases','Vazão de gases','kg/s',c.m_dot_turbina)):
        add(chave,'Ciclo',nome,unidade,valor)
    b=r['combustor']
    for chave,nome,unidade,valor in (
        ('comb_area','Área transversal estimada','cm²',b.A_comb*1e4),
        ('comb_diametro','Diâmetro equivalente','cm',b.D_comb*100),
        ('comb_comprimento','Comprimento estimado por escala','cm',b.L_comb*100)):
        add(chave,'Combustor',nome,unidade,valor,'Modelo 1D simplificado')
    componentes={}
    for chave,nome in (('comp','Compressor'),('turb','Turbina')):
        m=r[chave];rad=r['rad_'+chave];perfis=r['perfis_'+chave]
        fileiras=('rotor','estator') if chave=='comp' else ('bocal','rotor')
        radiais=[];perfil_dados=[]
        for i in range(m.n_estagios):
            tabela=dados_radiais(rad,nome,i)
            rh,rt=rad.r[i][rad.secoes[0]],rad.r[i][rad.secoes[-1]]
            for linha in tabela.to_dict(orient='records'):
                linha['Estágio']=i+1
                linha['Altura relativa']=(linha['Raio (cm)']/100-rh)/(rt-rh)
                radiais.append(linha)
            for fileira in fileiras:
                zeta_hub=perfis[i+1][rad.secoes[0]][fileira].stagger
                for secao in rad.secoes:
                    perfil=perfis[i+1][secao][fileira]
                    perfil_dados.append({'Estágio':i+1,'Seção':secao,'Fileira':fileira,
                        'Raio (cm)':rad.r[i][secao]*100,
                        'Altura relativa':(rad.r[i][secao]-rh)/(rt-rh),
                        'Reação radial':rad.R_c[i][secao], 'Stagger (°)':perfil.stagger,
                        'Torção em relação ao cubo (°)':perfil.stagger-zeta_hub})
        componentes[chave]={'nome':nome,'n_estagios':m.n_estagios,'fileiras':fileiras,
                           'estagios':dados_estagios(m,rad,nome).to_dict(orient='records'),
                           'radiais':radiais,'perfis':perfil_dados,
                           'psi_efetivo':m.psi_efetivo,
                           'automatico':execucao['parametros'][f'n_estagios_{chave}'] is None}
        add(chave+'_n',nome,'Estágios adotados','estágios',m.n_estagios)
        add(chave+'_psi',nome,'ψ efetivo','—',m.psi_efetivo,'Meanline')
        campos=[('R_c','Reação mínima radial','—',True),('R_c','Reação máxima radial','—',False),
                ('M1R' if chave=='comp' else 'M3R','Mach relativo máximo radial','—',False)]
        if chave=='comp':campos.append(('DF_rotor','DF máximo radial do rotor','—',False))
        for numero,(campo,rotulo,unidade,menor) in enumerate(campos):
            itens=[(v,f'Estágio {i+1} · {s}') for i,d in enumerate(getattr(rad,campo)) for s,v in d.items()]
            v,local=_extremo(itens,menor)
            add(f'{chave}_extremo_{numero}',nome,rotulo,unidade,v,local)
        for campo,rotulo,menor in (('r_hub_est','Raio mínimo do cubo',True),('r_tip_est','Raio máximo da ponta',False)):
            v,local=_extremo([(v*100,f'Estágio {i+1}') for i,v in enumerate(getattr(m,campo))],menor)
            add(chave+'_'+campo,nome,rotulo,'cm',v,local)
        add(chave+'_axial',nome,'Extensão axial da montagem (convenção CAD)','cm',r['maquina_'+chave].z_total*100)
        for fileira in fileiras:
            itens=[]
            for i in range(1,m.n_estagios+1):
                linha=next(v for v in perfil_dados if v['Estágio']==i and v['Fileira']==fileira and v['Seção']==rad.secoes[-1])
                itens.append((abs(linha['Torção em relação ao cubo (°)']),f'Estágio {i} · {fileira} · ponta − cubo'))
            v,local=_extremo(itens)
            add(chave+'_torcao_'+fileira,nome,f'Máximo |torção ponta − cubo| · {fileira}','°',v,local)
    add('avisos','Registros','Quantidade de mensagens','mensagens',len(r.get('avisos_detalhados',[])))
    inicio=execucao['iniciada_em']
    return deepcopy({'id':execucao['id'],'nome':execucao.get('nome_caso','Caso calculado'),
                     'inicio':inicio.isoformat() if hasattr(inicio,'isoformat') else str(inicio),
                     'parametros':execucao['parametros'],'modelo':execucao.get('contexto_modelo'),
                     'metricas':metricas,'componentes':componentes,
                     'avisos':r.get('avisos_detalhados',[])})


def entradas_alteradas(a,b):
    return [{'Entrada':ROTULOS.get(k,k),'Referência':formatar_entrada(a['parametros'].get(k)),
             'Atual':formatar_entrada(b['parametros'].get(k))} for k in sorted(a['parametros'].keys()|b['parametros'].keys())
            if a['parametros'].get(k)!=b['parametros'].get(k) and k!='N_turb']


def formatar_entrada(v):
    if v is None:return 'Automático'
    if v=='gas_natural':return 'Gás natural'
    return formato_br(v,'.8g') if isinstance(v,float) else str(v)


def diferenca(v0,v1):
    if not finito(v0) or not finito(v1):return None,None
    d=v1-v0
    return d,(100*d/abs(v0) if v0!=0 else None)


def tabela_metricas(a,b):
    linhas=[]
    for k,m in a['metricas'].items():
        atual=b['metricas'].get(k,{})
        v0,v1=m['valor'],atual.get('valor');d,pct=diferenca(v0,v1)
        linhas.append({'Componente':m['grupo'],'Grandeza':m['nome'],'Unidade':m['unidade'],
                       'Referência':v0,'Atual':v1,'Atual − referência':d,'Diferença (%)':pct,
                       'Local na referência':m['local'],'Local no atual':atual.get('local')})
    return pd.DataFrame(linhas)


def condicoes_discretizacao(a,b):
    outras=[k for k in a['parametros'].keys()|b['parametros'].keys()
            if k!='n_secoes' and a['parametros'].get(k)!=b['parametros'].get(k)]
    mesmo_modelo=(a['modelo'] is not None and a['modelo']==b['modelo'])
    mesmos_estagios=all(a['componentes'][k]['n_estagios']==b['componentes'][k]['n_estagios'] for k in ('comp','turb'))
    return {'somente_secoes':not outras,'mesmo_modelo':mesmo_modelo,'mesmos_estagios':mesmos_estagios}


def estudar_secoes(parametros,execucao,secoes,rodar):
    """Chamado somente por ação explícita; cada caso usa uma cópia das entradas calculadas."""
    resultados=[]
    for n in sorted(set(secoes)):
        if n not in (3,5,7,9,11):raise ValueError('Número de seções fora das opções da interface.')
        p=deepcopy(parametros);p['n_secoes']=n
        try:
            caso=rodar(p)
            e={**execucao,'parametros':p,'id':f"{execucao['id']}-secoes-{n}",
               'nome_caso':f"{execucao.get('nome_caso','Caso')} · {n} seções"}
            resultados.append({'n_secoes':n,'valido':True,'caso':capturar_caso(caso,e)})
        except (ValueError,RuntimeError) as erro:
            resultados.append({'n_secoes':n,'valido':False,'erro':str(erro)})
    return resultados
