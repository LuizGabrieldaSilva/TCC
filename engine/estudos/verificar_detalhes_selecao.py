"""Confere valores/locais e preservação da classificação dos candidatos."""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path


def executar(antes):
    from engine.estudos.verificar_acoplamento import montar_caso
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.geometry.airfoil4 import gerar_perfis_compressor, gerar_perfis_turbina
    from engine.webapp.stage_selection_details import tabela_criterios, tabela_localizacao
    saida = []
    locais_conferidos = 0
    for pi in (6., 8., 12.):
        ciclo, comp, turb, _, _ = montar_caso(pi, True)
        for modelo, compressor in ((comp,True),(turb,False)):
            s = modelo.selecao_estagios
            anterior = antes['casos'][len(saida)]
            # Só se acrescenta metadado; escores, justificativa e escolha são idênticos.
            reduzido = {**s, 'candidatos': [{k:v for k,v in r.items() if k!='detalhes_criterios'}
                                           for r in s['candidatos']]}
            assert reduzido == anterior
            for r in s['candidatos']:
                if not r['calculavel']:
                    continue
                m = type(modelo)(**{**modelo._entrada_selecao,
                                   'psi':r['psi_efetivo'],'n_estagios':r['n_estagios']})
                m.resolver()
                radial = (RadialCompressor if compressor else RadialTurbina)(m,n_secoes=s['n_secoes'])
                radial.resolver()
                perfis = (gerar_perfis_compressor if compressor else gerar_perfis_turbina)(radial)
                for d in r['detalhes_criterios']:
                    chave, local = d['criterio'], d['localizacao']
                    i = local['estagio']-1 if local['estagio'] is not None else None
                    campo = {'reacao_negativa':'R_c','reacao_acima_de_um':'R_c','reacao':'R_c',
                             'Mach_relativo':'M1R' if compressor else 'M3R','Mach_bocal':'M2'}.get(chave,chave)
                    if local['modelo']=='perfil':
                        valor = abs(perfis[local['estagio']][local['secao']][local['fileira']].theta_final)
                    elif chave=='psi':
                        valor = m.psi_efetivo
                    elif chave=='swirl_escape':
                        assert i==m.n_estagios-1 and local['fileira']=='rotor'
                        valor = abs(m.v3[i]/m.U)
                    elif local['modelo']=='radial':
                        valor = getattr(radial,campo)[i][local['secao']]
                    else:
                        valor = getattr(m,'grau_reacao' if campo=='R_c' else campo)[i]
                    assert math.isclose(valor,d['valor'],rel_tol=1e-12,abs_tol=1e-12)
                    baixo, alto = d['limite_inferior'], d['limite_superior']
                    if baixo is None:
                        excesso = max(0.,valor/alto-1.)
                    elif alto is None:
                        excesso = max(0.,baixo-valor)
                    else:
                        excesso = max(0.,(baixo-valor)/(alto-baixo),(valor-alto)/(alto-baixo))
                    assert math.isclose(excesso,r['criterios'][d['grupo']][chave],abs_tol=1e-12)
                    assert math.isclose(excesso,d['excesso_normalizado'],abs_tol=1e-12)
                    assert local['posicao']
                    if local['modelo']=='meanline':assert local['secao'] is None
                    tabela_localizacao(d)
                    locais_conferidos += 1
                tabela = tabela_criterios(r['detalhes_criterios'])
                assert len(tabela)==sum(len(r['criterios'][g]) for g in ('aerodinamica','geometria','faixas'))
                assert all('_' not in nome for nome in tabela['Critério'])
                assert all(',' in valor for valor in tabela['Valor real'])
            saida.append(s)
    return dict(casos=saida,locais_conferidos=locais_conferidos,
                escores_prioridades_e_escolhas_preservados=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--antes',type=Path,required=True)
    p.add_argument('--saida',type=Path,required=True)
    args=p.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        resultado=executar(json.loads(args.antes.read_text(encoding='utf-8-sig')))
    args.saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print(f"{resultado['locais_conferidos']} valores/limites/localizações conferidos; escolhas e prioridades preservadas.")
