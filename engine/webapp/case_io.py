"""Entradas portáveis da interface; sem execução ou alteração do modelo físico."""

import hashlib
import json
import math
from pathlib import Path

from engine.reference_case import REF_CICLO
from engine.combustor.Combustor_1D_2_main import COMBUSTIVEIS
from engine import design_criteria as dc

FORMATO = 'tcc-turbina-axial/entradas'
VERSAO = 3
MAX_BYTES = 64 * 1024
# Correspondência explícita: chaves de cálculo e campos da interface.
CAMPOS = {
    'mistura_automatica':'mistura_automatica',
    'T01':'T01', 'P01':'P01', 'r_compr':'r_compr', 'TIT':'TIT',
    'e_compr':'e_compr', 'e_turb':'e_turb', 'Delta_P_cc':'Delta_P_cc',
    'TIT_max':'TIT_max', 'm_dot':'m_dot', 'combustivel':'combustivel',
    'eta_b':'eta_b', 'M_entrada':'M_entrada', 'HTR_comp':'HTR_comp',
    'phi_comp':'phi_comp', 'psi_comp':'psi_comp', 'alpha1_comp':'a1_comp',
    'DF_alvo':'DF_alvo', 'AR_comp':'AR_comp', 'HTR_turb':'HTR_turb',
    'phi_turb':'phi_turb', 'psi_turb':'psi_turb', 'alpha2_turb':'a2_turb',
    'sigma_turb':'sigma_turb', 'AR_turb':'AR_turb', 'n_secoes':'n_secoes',
    'cp_ar':'cp_ar', 'cp_gases':'cp_gases', 'R_ar':'R_ar', 'R_gases':'R_gases',
}
CHAVES = set(CAMPOS) | {'N_comp','N_turb','n_estagios_comp','n_estagios_turb'}
UNIDADES_V1 = {'temperaturas':'K','P01':'kPa','m_dot':'kg/s',
            'N_comp':'rpm','N_turb':'rpm','angulos':'graus',
            'demais':'adimensionais ou contagens; n_estagios=null indica automático'}
UNIDADES = {**UNIDADES_V1, **{chave:'J/(kg K)' for chave in
             ('cp_ar','cp_gases','R_ar','R_gases')}}
FAIXAS = {
    'r_compr':(1.1,None), 'm_dot':(.1,None), 'e_compr':(.5,1.), 'e_turb':(.5,1.),
    'Delta_P_cc':(0.,.30), 'eta_b':dc.ETA_COMBUSTOR, 'M_entrada':(.001,.20),
    'HTR_comp':(.3,.95), 'HTR_turb':(.3,.98), 'phi_comp':(.1,1.), 'phi_turb':(.1,1.),
    'psi_comp':(.05,1.), 'psi_turb':(.1,3.), 'DF_alvo':(.2,.6),
    'AR_comp':(.5,None), 'AR_turb':(.5,None), 'sigma_turb':(.3,None),
}


def validar_parametros(parametros):
    """Valida formato, domínio e limites dos campos atuais, sem resolver o caso."""
    if isinstance(parametros,dict) and set(parametros)==CHAVES-{'mistura_automatica'}:
        parametros={**parametros,'mistura_automatica':False}
    if not isinstance(parametros,dict) or set(parametros)!=CHAVES:
        raise ValueError('O arquivo deve conter exatamente as entradas do formato de caso atual.')
    p=parametros.copy()
    for k,v in p.items():
        if k=='mistura_automatica':
            if type(v) is not bool:raise ValueError('mistura_automatica deve ser booleano.')
        elif k=='combustivel':
            if not isinstance(v,str) or v not in COMBUSTIVEIS:
                raise ValueError('Combustível não disponível nesta versão da plataforma.')
        elif k.startswith('n_estagios_') or k=='n_secoes':
            if v is None and k.startswith('n_estagios_'):continue
            if type(v) is not int or v<1:raise ValueError(f'{k}: informe um inteiro positivo ou modo automático.')
        else:
            try:valido=type(v) in (int,float) and math.isfinite(v)
            except OverflowError:valido=False
            if not valido:raise ValueError(f'{k}: informe um número finito; valores booleanos não são aceitos.')
            p[k]=float(v)
    for k in ('T01','P01','TIT','TIT_max','N_comp','N_turb'):
        if p[k]<=0:raise ValueError(f'{k} deve ser maior que zero.')
    for k,(lo,hi) in FAIXAS.items():
        if p[k]<lo or (hi is not None and p[k]>hi):
            raise ValueError(f'{k} está fora dos limites do campo da interface.')
    if p['mistura_automatica']:
        from engine.combustor.mistura_gases import R_AR
        if p['cp_ar'] <= R_AR:raise ValueError('cp_ar deve superar R do ar seco.')
    for fluido in ('ar', 'gases'):
        if p['mistura_automatica']:continue
        if not 0 < p[f'R_{fluido}'] < p[f'cp_{fluido}']:
            raise ValueError(f'Exige 0 < R_{fluido} < cp_{fluido}.')
    for k in ('alpha1_comp','alpha2_turb'):
        if not -90<p[k]<90:raise ValueError(f'{k} deve estar entre −90° e 90°, sem os extremos.')
    if p['N_comp']!=p['N_turb']:
        raise ValueError('O modelo tem eixo único: N_comp e N_turb devem ser iguais.')
    if p['n_secoes'] not in (3,5,7,9,11):
        raise ValueError('n_secoes deve ser 3, 5, 7, 9 ou 11, conforme a interface.')
    return p


def parametros_dos_campos(estado):
    p={param:estado[campo] for param,campo in CAMPOS.items()}
    p.update(N_comp=estado['N_eixo'],N_turb=estado['N_eixo'])
    for comp in ('comp','turb'):
        p[f'n_estagios_{comp}']=None if estado[f'auto_ne_{comp}'] else estado[f'ne_{comp}']
    return p


def campos_dos_parametros(parametros):
    p=validar_parametros(parametros)
    campos={campo:p[param] for param,campo in CAMPOS.items()}
    campos['N_eixo']=p['N_comp']
    for comp in ('comp','turb'):
        n=p[f'n_estagios_{comp}']
        campos[f'auto_ne_{comp}']=n is None
        # O valor manual é irrelevante quando o modo automático está ativo.
        if n is not None:campos[f'ne_{comp}']=n
    return campos


def contexto_modelo():
    raiz=Path(__file__).resolve().parents[1]
    fontes={str(p.relative_to(raiz)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(raiz.rglob('*')) if p.suffix in ('.py','.json') and 'webapp' not in p.relative_to(raiz).parts and '__pycache__' not in p.parts}
    return {'cp_J_kg_K':REF_CICLO['cp'],'k':REF_CICLO['k'],
            'cp_gases_J_kg_K':REF_CICLO['cp_gases'],'R_gases_J_kg_K':REF_CICLO['R_gases'],
            'combustiveis':COMBUSTIVEIS,
            'criterios':{k:v for k,v in vars(dc).items() if k.isupper()},
            'sha256_fontes_engine':hashlib.sha256(json.dumps(fontes,sort_keys=True).encode()).hexdigest()}


def exportar_entradas(parametros, nome, contexto, execucao_id=None):
    p=validar_parametros(parametros)
    documento={'formato':FORMATO,'versao':VERSAO,'nome':str(nome).strip()[:120] or 'Caso sem nome',
               'unidades':UNIDADES,'parametros':p,'modelo':contexto,'execucao_origem':execucao_id}
    return json.dumps(documento,ensure_ascii=False,indent=2,allow_nan=False).encode('utf-8')


def ler_entradas(conteudo):
    if not isinstance(conteudo,bytes) or len(conteudo)>MAX_BYTES:
        raise ValueError('Selecione um JSON de entradas de até 64 KiB.')
    def unicos(pares):
        d={}
        for k,v in pares:
            if k in d:raise ValueError('O JSON contém chaves repetidas.')
            d[k]=v
        return d
    try:
        d=json.loads(conteudo.decode('utf-8-sig'),object_pairs_hook=unicos,
                     parse_constant=lambda v: (_ for _ in ()).throw(ValueError('NaN e infinito não são aceitos.')))
    except (UnicodeError,json.JSONDecodeError,RecursionError) as erro:
        raise ValueError('Arquivo inválido: use o JSON de entradas exportado pela plataforma.') from erro
    esperadas={'formato','versao','nome','unidades','parametros','modelo','execucao_origem'}
    if not isinstance(d,dict) or set(d)!=esperadas or d['formato']!=FORMATO or type(d['versao']) is not int or d['versao'] not in (1,2,VERSAO):
        raise ValueError('Formato ou versão de caso não reconhecidos. Use o JSON de entradas, não o de resultados.')
    unidades_esperadas = UNIDADES_V1 if d['versao'] == 1 else UNIDADES
    if d['unidades']!=unidades_esperadas:raise ValueError('Unidades do arquivo incompatíveis com o formato atual.')
    if not isinstance(d['nome'],str) or len(d['nome'])>120:
        raise ValueError('O nome do caso deve ter até 120 caracteres.')
    modelo=d['modelo']
    chaves_modelo = {'cp_J_kg_K','k','combustiveis','criterios','sha256_fontes_engine'}
    if d['versao'] >= 2:
        chaves_modelo |= {'cp_gases_J_kg_K','R_gases_J_kg_K'}
    if (not isinstance(modelo,dict) or set(modelo)!=chaves_modelo):
        raise ValueError('Identificação do modelo ausente ou inválida.')
    assinatura=modelo['sha256_fontes_engine']
    if (not isinstance(assinatura,str) or len(assinatura)!=64
            or any(c not in '0123456789abcdef' for c in assinatura)
            or not isinstance(modelo['combustiveis'],dict) or not isinstance(modelo['criterios'],dict)):
        raise ValueError('Identificação dos códigos, combustíveis ou critérios inválida.')
    for chave in chaves_modelo - {'combustiveis','criterios','sha256_fontes_engine'}:
        v=modelo[chave]
        if type(v) not in (int,float) or not math.isfinite(v) or v<=0:
            raise ValueError('Propriedades do modelo ausentes ou inválidas.')
    if modelo['k'] <= 1:
        raise ValueError('k do modelo deve ser maior que 1.')
    if d['versao'] == 1:
        # Recuperar um caso antigo preserva seu cp único explicitamente;
        # não trocar silenciosamente pela nova hipótese com cp distintos.
        p = d['parametros']
        legadas = CHAVES - {'cp_ar','cp_gases','R_ar','R_gases','mistura_automatica'}
        if not isinstance(p,dict) or set(p) != legadas:
            raise ValueError('Entradas legadas inválidas.')
        cp = modelo['cp_J_kg_K']; r = cp * (1 - 1/modelo['k'])
        d['parametros'] = {**p,'cp_ar':cp,'cp_gases':cp,'R_ar':r,'R_gases':r}
    if d['versao'] < 3:
        if 'mistura_automatica' in d['parametros']:raise ValueError('Campo de mistura incompatível com versão antiga.')
        d['parametros']={**d['parametros'],'mistura_automatica':False}
    if d['execucao_origem'] is not None and not isinstance(d['execucao_origem'],str):
        raise ValueError('Identificador da execução inválido.')
    d['parametros']=validar_parametros(d['parametros'])
    return d


def aplicar_entradas(documento, estado):
    """Validação completa antes de atualizar qualquer campo; resultados são preservados."""
    campos=campos_dos_parametros(documento['parametros'])
    campos['nome_caso']=documento['nome']
    estado.update({k:v for k,v in campos.items() if k not in estado or estado[k]!=v})


def diferencas_entradas(atuais, submetidas):
    return [k for k in atuais if atuais[k]!=submetidas.get(k)]
