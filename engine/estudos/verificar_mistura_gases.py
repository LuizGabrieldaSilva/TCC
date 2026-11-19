"""Verificação numérica da mistura congelada; não é validação experimental."""
import argparse
import contextlib
import io
import json
import math
from pathlib import Path

from engine.combustor import mistura_gases as m
from engine.ciclo.CicloBrayton import CicloBrayton
from engine.combustor.Combustor_1D_2_main import Combustor1D
from engine.reference_case import montar_caso_referencia


def executar():
    def perto(a,b,tol=1e-10):
        assert math.isclose(a,b,rel_tol=tol,abs_tol=1e-8),(a,b)

    # Integração numérica independente da primitiva, inclusive cruzando 1000 K.
    integrais=[]
    for especie in m.M:
        for a,b in [(298.15,900.),(900.,1600.),(1100.,2200.)]:
            passos=10000;h=(b-a)/passos
            num=h/3*(m.cp_molar(especie,a)+m.cp_molar(especie,b)+sum(
                (4 if j%2 else 2)*m.cp_molar(especie,a+j*h) for j in range(1,passos)))
            exato=m.delta_h_molar(especie,a,b)
            perto(num,exato,2e-7)
            perto(m.delta_h_molar(especie,b,a),-exato)
            perto(m.cp_molar(especie,1000.-1e-6),m.cp_molar(especie,1000.+1e-6),2e-7)
            integrais.append(dict(especie=especie,Ta=a,Tb=b,diferenca_J_mol=num-exato))

    conservacao=[]
    for nome,c in m.COMPOSICOES.items():
        for frac in (.01,.5,1.):
            f=frac*m.estequiometria(nome);p=m.produtos(nome,f);n=p['moles_por_mol_combustivel']
            a=c['C']+c['H']/4;lam=p['lambda_ar']
            perto(n['CO2'],c['C']);perto(2*n['H2O'],c['H'])
            perto(2*n['CO2']+n['H2O']+2*n['O2'],2*a*lam)
            perto(n['N2'],a*lam*m.AR_MOLAR['N2']/m.AR_MOLAR['O2'])
            perto(n['Ar'],a*lam*m.AR_MOLAR['Ar']/m.AR_MOLAR['O2'])
            massa=sum(v*m.M[s] for s,v in n.items())
            perto(massa,m.massa_combustivel(nome)*(1+1/f))
            perto(sum(p['fracoes_molares'].values()),1.)
            perto(sum(p['fracoes_massicas'].values()),1.)
            assert min(p['fracoes_massicas'].values())>=0
            perto(p['R_J_kg_K'],m.RU/p['M_kg_mol'])
            conservacao.append(dict(combustivel=nome,f=f,lambda_ar=lam,residuo_massa_kg_mol=massa-m.massa_combustivel(nome)*(1+1/f)))

    # Mesmo substituto elementar, mesma composição nas mesmas condições:
    # diferenças não podem ser inventadas pela identificação do combustível.
    p8=m.propriedades('JP-8',.02,1200.)
    pd=m.propriedades('diesel',.02,1200.)
    perto(p8['cp_J_kg_K'],pd['cp_J_kg_K']);perto(p8['R_J_kg_K'],pd['R_J_kg_K'])

    ref=montar_caso_referencia();casos=[];log=io.StringIO()
    from engine.compressor.Compressor_Meanline_main import CompressorMeanline
    from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.estudos.verificar_acoplamento import conferir
    with contextlib.redirect_stdout(log):
        for nome in m.COMPOSICOES:
            for auto in (False,True):
                c=CicloBrayton(**ref['REF_CICLO']);c.resolver();c.vazão_mássica_desejada(15.)
                b=Combustor1D(c,combustivel=nome);b.resolver();c.registrar_vazao_turbina(b.m_dot_turbina)
                p=b.dados_mistura;f=b.f
                # Energia recalculada diretamente das espécies, sem calor_balanco.
                h=sum(p['fracoes_massicas'][s]*m.delta_h_molar(s,m.T_REF,c.TIT)/m.M[s] for s in m.M)
                perto((1+f)*h-c.cp_ar*(c.T02r-m.T_REF),f*b.eta_b*b.h_PR)
                perto(c.m_dot_ar*c.q_ent,b.m_dot_f*b.eta_b*b.h_PR)
                perto(c.cp_gases*(c.TIT-m.T_REF),h)
                perto(c.k_gases,c.cp_gases/(c.cp_gases-c.R_gases))
                perto(b.f,p['f']);perto(b.f_stoich,p['f_stoich'])
                pc=dict(ref['REF_COMP']);pt=dict(ref['REF_TURB'])
                if auto:pc['n_estagios']=pt['n_estagios']=None
                comp=CompressorMeanline(c,**pc);comp.resolver()
                turb=TurbinaAxialMeanline(c,**pt);turb.resolver()
                rc=RadialCompressor(comp);rc.resolver();rt=RadialTurbina(turb);rt.resolver()
                conferir(comp,rc,'Compressor');conferir(turb,rt,'Turbina')
                perto(turb.cp,c.cp_gases);perto(turb.k,c.k_gases)
                casos.append(dict(combustivel=nome,estagios_automaticos=auto,f=f,
                    cp=c.cp_gases,R=c.R_gases,k=c.k_gases,lambda_ar=p['lambda_ar'],
                    fracoes_massicas=p['fracoes_massicas'],potencia_ciclo_kW=c.W_líq/1000,
                    estagios_comp=comp.n_estagios,estagios_turb=turb.n_estagios))
        # Mudança de combustível deve preservar modo de potência e acoplamento.
        c=CicloBrayton(**ref['REF_CICLO']);c.resolver();c.potência_líquida_desejada(2000.)
        b=Combustor1D(c,combustivel='diesel');b.resolver();c.registrar_vazao_turbina(b.m_dot_turbina)
        perto(c.W_líq,2e6)
    jp8=next(x for x in casos if x['combustivel']=='JP-8')
    diesel=next(x for x in casos if x['combustivel']=='diesel')
    assert jp8['f']!=diesel['f'] and jp8['cp']!=diesel['cp'] and jp8['R']!=diesel['R']

    recusados=0
    for func,args in [(m.produtos,('diesel',m.estequiometria('diesel')*1.01)),
                      (m.cp_molar,('N2',199.)),(m.cp_molar,('N2',6001.)),
                      (m.resolver_mistura,('JP-8',600.,1200.,1005.,1.1)),
                      (m.resolver_mistura,('JP-8',600.,1200.,1005.,.99,1.))]:
        try:func(*args)
        except ValueError:recusados+=1
        else:raise AssertionError(args)
    # Tentativa inválida não modifica propriedades já calculadas.
    anterior=(c.cp_gases,c.combustivel_mistura,c.eta_b_mistura)
    try:c.preparar_mistura('diesel',1.1)
    except ValueError:pass
    else:raise AssertionError('eta inválida aceita')
    assert anterior==(c.cp_gases,c.combustivel_mistura,c.eta_b_mistura)
    return dict(integrais=integrais,conservacao=conservacao,casos=casos,
                dominios_recusados=recusados,mesmo_substituto_sem_diferenca_artificial=True,
                modo_potencia_preservado=True,avisos=log.getvalue())


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--saida',type=Path,required=True)
    args=ap.parse_args();r=executar()
    args.saida.write_text(json.dumps(r,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Mistura: integração NASA, massa, elementos, energia, domínio e oito pipelines conferidos.')
