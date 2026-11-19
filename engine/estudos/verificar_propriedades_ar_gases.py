"""Verifica integração de cp distintos, compatibilidade legada e exportação.

Em NEW: python -m engine.estudos.verificar_propriedades_ar_gases --saida resultado.json
Não constitui validação experimental de propriedades ou desempenho.
"""
import argparse
import contextlib
import io
import json
import math
from copy import deepcopy
from pathlib import Path


def executar():
    from engine.ciclo.CicloBrayton import CicloBrayton
    from engine.combustor.Combustor_1D_2_main import Combustor1D
    from engine.compressor.Compressor_Meanline_main import CompressorMeanline
    from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.estudos.verificar_acoplamento import conferir
    from engine.reference_case import montar_caso_referencia
    from engine.indicadores import indicadores_energeticos
    from engine.estudos.sensibilidade import rodar_caso_ciclo
    from engine.webapp.cycle_diagrams import estados_ciclo, _diagrama
    from engine.webapp.case_io import contexto_modelo, exportar_entradas, ler_entradas, validar_parametros, UNIDADES_V1

    def perto(a,b):
        assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8),(a,b)

    ref = montar_caso_referencia()
    ref['REF_CICLO']['mistura_automatica'] = False  # su?te de propriedades prescritas
    def pipeline(unico=False, auto=False):
        p=deepcopy(ref['REF_CICLO'])
        if unico:
            p.update(cp_gases=p['cp'],R_gases=p['cp']*(1-1/p['k']))
        c=CicloBrayton(**p); c.resolver(); c.vazão_mássica_desejada(ref['REF_M_DOT'])
        b=Combustor1D(c,**ref['REF_COMBUSTOR']); b.resolver()
        c.registrar_vazao_turbina(b.m_dot_turbina)
        pc=deepcopy(ref['REF_COMP']);pt=deepcopy(ref['REF_TURB'])
        if auto:pc['n_estagios']=pt['n_estagios']=None
        comp=CompressorMeanline(c,**pc);comp.resolver()
        t=TurbinaAxialMeanline(c,**pt);t.resolver()
        rc=RadialCompressor(comp);rc.resolver();rt=RadialTurbina(t);rt.resolver()
        conferir(comp,rc,'Compressor');conferir(t,rt,'Turbina')
        perto(comp.cp,c.cp_ar);perto(comp.k,c.k_ar)
        perto(t.cp,c.cp_gases);perto(t.k,c.k_gases)
        perto(rt.cp,t.cp);perto(rc.cp,comp.cp)
        perto(b.m_dot_tot*b.cp_gases*b.TIT-b.m_dot_ar*b.cp_ar*b.T02r,b.m_dot_f*b.h_PR*b.eta_b)
        perto(c.m_dot_ar*c.q_ent,b.m_dot_f*b.h_PR*b.eta_b)
        perto(c.W_líq,c.m_dot_turbina*t.cp*(c.TIT-c.T04r)-c.m_dot_ar*comp.cp*(c.T02r-c.T01))
        ind=indicadores_energeticos(c,b)
        perto(ind['eta_calor_util'],c.eta_ciclo)
        perto(ind['eta_PCI'],b.eta_b*c.eta_ciclo)
        for dados in c.propriedades().values():
            perto(dados['cp_J_kg_K']*(1-1/dados['k']),dados['R_J_kg_K'])
        estados=estados_ciclo(c)
        perto(estados[0]['s'],0);perto(estados[2]['s'],0)
        assert estados[1]['s']>0 and estados[3]['s']>0
        for e,r,T,P in [(estados[0],c.R_ar,c.T01,c.P01),(estados[2],c.R_gases,c.TIT,c.P03)]:
            perto(e['v'],r*T/P)
        spec=_diagrama(estados,'s','T','Teste',set(),[])
        processos={d['processo'] for d in spec['layer'][0]['data']['values']}
        assert processos=={'Compressor: 01 → 02','Turbina: 03 → 04'}
        return c,b,comp,t,ind

    log=io.StringIO()
    resultados=[]
    with contextlib.redirect_stdout(log):
        for unico,auto in [(True,False),(False,False),(False,True)]:
            c,b,comp,t,ind=pipeline(unico,auto)
            if unico:perto(c.W_líq,2233239.6399407783)
            resultados.append(dict(cp_unico=unico,automatico=auto,propriedades=c.propriedades(),
                                   f=b.f,phi_eq=b.phi_eq,estagios_compressor=comp.n_estagios,
                                   estagios_turbina=t.n_estagios,T04_K=c.T04r,indicadores=ind))
        # Número publicado de Mattingly: agora reproduzido pelo solver com
        # cp_ar=1004, cp_gases=1235, sem trocar a temperatura para forçar ajuste.
        p=deepcopy(ref['REF_CICLO'])
        p.update(T01=300., r_compr=(653/300)**(1.4*.85/.4),TIT=1670.,TIT_máx=1670.,
                 cp=1004.,cp_gases=1235.,R_gases=287.)
        c=CicloBrayton(**p);c.resolver();c.vazão_mássica_desejada(15)
        b=Combustor1D(c,eta_b=1.);b.resolver()
        esperado=(1235*1670-1004*653)/(42.8e6-1235*1670)
        perto(b.f,esperado)
        assert abs(b.f-.0346)<.0001
        mattingly=dict(f_calculado=b.f,f_publicado=.0346,phi_calculado=b.phi_eq,
                      diferenca_f_pct=100*(b.f/.0346-1),tolerancia_f=.0001)

    # Entradas novas e migração explícita de JSON legado com fluido único.
    p=dict(mistura_automatica=False,T01=300.,P01=100.,r_compr=8.,TIT=1200.,e_compr=.85,e_turb=.8,
           Delta_P_cc=.05,TIT_max=1200.,m_dot=15.,**ref['REF_COMBUSTOR'],
           cp_ar=1005.,cp_gases=1148.,R_ar=287.1428571428571,R_gases=287.1428571428571,
           N_comp=14000.,N_turb=14000.,HTR_comp=.75,HTR_turb=.9,n_estagios_comp=8,n_estagios_turb=3,
           phi_comp=.5,psi_comp=.35,alpha1_comp=30.,DF_alvo=.45,AR_comp=2.,
           phi_turb=.53,psi_turb=1.198736,alpha2_turb=63.5,sigma_turb=1.,AR_turb=2.,n_secoes=7)
    original=exportar_entradas(p,'Teste cp',contexto_modelo())
    novo=ler_entradas(original)
    assert novo['parametros']==validar_parametros(p)
    antigo=json.loads(original)
    antigo['versao']=1
    antigo['unidades']=UNIDADES_V1
    for campo in ('cp_ar','cp_gases','R_ar','R_gases','mistura_automatica'):del antigo['parametros'][campo]
    for campo in ('cp_gases_J_kg_K','R_gases_J_kg_K'):del antigo['modelo'][campo]
    migrado=ler_entradas(json.dumps(antigo).encode())
    assert migrado['parametros']['cp_ar']==migrado['parametros']['cp_gases']==1005.
    perto(migrado['parametros']['R_ar'],migrado['parametros']['R_gases'])
    custom=deepcopy(p);custom['cp_gases']=1235.;custom['R_gases']=290.
    c_ref=montar_caso_referencia(custom)
    c_custom=CicloBrayton(**c_ref['REF_CICLO']);c_custom.resolver()
    perto(c_custom.cp_gases,1235.);perto(c_custom.R_gases,290.)
    with contextlib.redirect_stdout(io.StringIO()):
        curva=rodar_caso_ciclo({},caso_referencia=c_ref)
        c_custom.vazão_mássica_desejada(15.)
        b_custom=Combustor1D(c_custom,**ref['REF_COMBUSTOR']);b_custom.resolver()
        c_custom.registrar_vazao_turbina(b_custom.m_dot_turbina)
    assert curva['valido'];perto(curva['f'],b_custom.f);perto(curva['w_liq_kJ_kg'],c_custom.w_líq/1000)
    invalidos=0
    for override in ({'cp_gases':-1},{'cp_gases':float('nan')},{'R_gases':1148.},
                     {'R_gases':0.},{'k_gases':1.},{'cp_gases':1148.,'R_gases':287.,'k_gases':1.4}):
        try:CicloBrayton(300.,1e5,8.,1200.,**override)
        except ValueError:invalidos+=1
        else:raise AssertionError(override)
    for campo in ('cp_ar','cp_gases'):
        invalido=deepcopy(p);invalido[campo]=100.
        try:validar_parametros(invalido)
        except ValueError:invalidos+=1
        else:raise AssertionError(campo)
    return dict(casos=resultados,Mattingly_cp_distintos=mattingly,
                roundtrip_json_v3=True,migracao_json_v1_cp_unico=True,sensibilidade_cp_personalizado=True,
                entradas_invalidas_recusadas=invalidos,avisos=log.getvalue())


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--saida',type=Path,required=True)
    args=ap.parse_args();r=executar()
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('cp por região: balanços, Euler, referências de entropia, caso legado, Mattingly e JSON conferidos.')
