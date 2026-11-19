"""Testes de domínio das APIs e fronteiras numéricas, sem mudar recomendações."""

import argparse
import contextlib
import copy
import io
import json
import math
from pathlib import Path


def executar():
    from engine.ciclo.CicloBrayton import CicloBrayton
    from engine.compressor.Compressor_Meanline_main import CompressorMeanline
    from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
    from engine.combustor.Combustor_1D_2_main import Combustor1D
    from engine.aero.radial_compressor_4_main import gerar_secoes as secoes_comp
    from engine.aero.radial_turbina_3_main import gerar_secoes as secoes_turb
    from engine.reference_case import montar_caso_referencia
    ref=montar_caso_referencia()
    # Exercita os domínios da API com propriedades prescritas; k é uma
    # propriedade derivada (não uma entrada) no modo composição automática.
    ref['REF_CICLO']['mistura_automatica']=False
    recusas=[]

    def rejeita(nome, func, texto='', tipo=ValueError):
        try:
            func()
        except tipo as erro:
            assert texto in str(erro),(nome,str(erro),texto)
            recusas.append(dict(caso=nome,erro=type(erro).__name__,mensagem=str(erro)))
        else:
            raise AssertionError('Entrada inválida aceita: '+nome)

    def ciclo(**mudancas):
        c=CicloBrayton(**{**ref['REF_CICLO'],**mudancas})
        c.resolver()
        return c

    invalidas={'T01':[0,-1,float('nan'),float('inf'),'300',True],
               'P01':[0,-1,None], 'r_compr':[0,1,.9,float('nan')],
               'cp':[0,-1], 'k':[0,1,float('inf')],
               'TIT':[0,400,1300], 'TIT_máx':[0],
               'e_compr':[0,-.1,1.01,True], 'e_turb':[0,float('nan'),1.1],
               'Delta_P_cc':[-.1,1,.875,float('inf')]}
    for campo,valores in invalidas.items():
        for valor in valores:
            rejeita(campo+'='+str(valor),lambda: ciclo(**{campo:valor}))
    rejeita('overflow de pressão',lambda: ciclo(P01=1e308,r_compr=1e308))
    rejeita('incremento não resolvido',lambda: ciclo(r_compr=math.nextafter(1.,2.),Delta_P_cc=0), 'precisão')
    c=ciclo(); c.vazão_mássica_desejada(15.)
    for metodo in (c.vazão_mássica_desejada,c.potência_líquida_desejada,c.registrar_vazao_turbina):
        for valor in (0,-1,float('nan'),float('inf'),True,'15',None):
            estado=copy.deepcopy(vars(c))
            rejeita(metodo.__name__+'='+str(valor),lambda: metodo(valor))
            assert vars(c)==estado,'Entrada recusada modificou execução válida'
    rejeita('vazão de gases menor que ar',lambda: c.registrar_vazao_turbina(14.))
    rejeita('overflow de potência por vazão',lambda: c.vazão_mássica_desejada(1e308))
    rejeita('overflow de energia do combustível',lambda: c.registrar_vazao_turbina(1e308))

    for classe,chave in ((CompressorMeanline,'REF_COMP'),(TurbinaAxialMeanline,'REF_TURB')):
        invalidas_maquina={'N':[0,float('nan'),True], 'HTR':[0,1,-.1,float('inf')],
                          'phi':[0,-1], 'psi':[0,float('nan')], 'AR':[0,-1],
                          'n_estagios':[0,-1,2.5,3.,True,'3'],
                          'n_secoes_avaliacao':[0,1,3.5,True]}
        angulo='alpha1_graus' if chave=='REF_COMP' else 'alpha2_graus'
        invalidas_maquina[angulo]=[-90,90,float('nan')]
        invalidas_maquina['DF_alvo' if chave=='REF_COMP' else 'sigma']=[0,float('inf')]
        for campo,valores in invalidas_maquina.items():
            for valor in valores:
                rejeita(classe.__name__+'/'+campo+'='+str(valor),
                        lambda: classe(ciclo=c,**{**ref[chave],campo:valor}),campo.split('_graus')[0])
    for valor in (0,-1,float('nan'),True):
        rejeita('vazão explícita turbina',lambda: TurbinaAxialMeanline(ciclo=c,m_dot_turbina=valor,**ref['REF_TURB']))
    for campo,valores in {'eta_b':[0,-1,1.1,float('nan'),True],
                         'h_PR':[0,-1,float('inf'),'42e6'],
                         'M_entrada':[0,1,-1,None,float('nan')]}.items():
        for valor in valores:
            rejeita('Combustor/'+campo+'='+str(valor),lambda: Combustor1D(ciclo=c,**{campo:valor}),campo)
    rejeita('combustível não textual',lambda: Combustor1D(ciclo=c,combustivel=[]),'Combustível')
    def baixo_PCI():
        b=Combustor1D(ciclo=c,h_PR=1000.)
        b.resolver()
    rejeita('denominador do combustível não positivo',baixo_PCI,'Balanço energético')
    for gerar in (secoes_comp,secoes_turb):
        for valor in (0,1,3.5,True,'7',None,float('inf')):
            rejeita('grade radial '+str(valor),lambda: gerar(valor),'n_secoes')
        assert gerar(2)[0]==['hub','tip']
        assert gerar(3)[0]==['hub','mid','tip']
        assert len(gerar(7)[0])==7

    # Faixas recomendadas permanecem avisos, sem se tornarem proibições.
    avisos=io.StringIO()
    with contextlib.redirect_stdout(avisos):
        CompressorMeanline(ciclo=c,**{**ref['REF_COMP'],'DF_alvo':.65})
        b=Combustor1D(ciclo=c,eta_b=.89)
        b.resolver()
    assert 'AVISO' in avisos.getvalue()
    assert b.f>0

    fronteiras=[]
    for razao in (1+1e-10,1+1e-8,1+1e-5,8.):
        ideal=ciclo(r_compr=razao,e_compr=1.,e_turb=1.,Delta_P_cc=0.)
        assert math.isclose(ideal.eta_compr,1.,rel_tol=1e-12)
        assert math.isclose(ideal.eta_turb,1.,rel_tol=1e-12)
        assert math.isclose(ideal.T02r,ideal.T01*razao**((ideal.k-1)/ideal.k),rel_tol=1e-13)
        assert math.isclose(ideal.T04r,ideal.TIT*(1/razao)**((ideal.k_gases-1)/ideal.k_gases),rel_tol=1e-13)
        ideal.vazão_mássica_desejada(15.)
        fronteiras.append(ideal.resultados())

    # Ordem de chamadas e invalidação dos resultados de uma nova solução.
    cru=CicloBrayton(**ref['REF_CICLO'])
    rejeita('vazão antes de resolver',lambda: cru.vazão_mássica_desejada(15.),tipo=RuntimeError)
    cru.resolver()
    rejeita('registro de gases antes da vazão de ar',lambda: cru.registrar_vazao_turbina(16.),tipo=RuntimeError)
    c.resolver()
    assert c.m_dot is None and c.W_líq is None and c.m_dot_f==0.
    rejeita('componente sem redefinir vazão',lambda: CompressorMeanline(ciclo=c,**ref['REF_COMP']),tipo=RuntimeError)
    c.vazão_mássica_desejada(15.)
    c.T01=float('nan')
    rejeita('ciclo alterado para NaN',c.resolver,'T01')
    rejeita('resultado antigo após falha',c.resultados,tipo=RuntimeError)

    # Saldo-base zero não pode dimensionar vazão por potência; a divisão deve
    # ser recusada explicitamente antes de alterar o estado.
    zero=ciclo()
    zero.w_turb=zero.w_compr
    zero.w_líq=0.
    rejeita('potência desejada com trabalho zero',lambda: zero.potência_líquida_desejada(100.),'Trabalho líquido')
    # Potência-alvo com massa de combustível conserva o alvo solicitado.
    alvo=ciclo(); alvo.potência_líquida_desejada(2000.)
    cc=Combustor1D(ciclo=alvo); cc.resolver()
    alvo.registrar_vazao_turbina(cc.m_dot_turbina)
    assert math.isclose(alvo.W_líq,2e6,rel_tol=1e-12)
    return dict(rejeicoes=recusas,fronteiras_validas=fronteiras,
                faixas_recomendadas_continuam_avisos=True,ordem_de_chamadas_conferida=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--saida',type=Path,required=True)
    args=p.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):resultado=executar()
    args.saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(f"{len(resultado['rejeicoes'])} recusas de domínio, quatro fronteiras válidas e ordem de chamadas conferidas.")
