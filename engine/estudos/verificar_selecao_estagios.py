"""Verificação da política discreta, sem certificação de viabilidade física."""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path


def executar(antes):
    from engine.stage_selection import vizinhos, chave_classificacao, avaliar_criterios
    from engine.estudos.verificar_acoplamento import executar as casos_regressao, comparar_antes
    from engine.estudos.verificar_acoplamento import montar_caso
    assert vizinhos(3.0000002) == [3, 4]
    assert vizinhos(2.5) == [2, 3]
    assert vizinhos(3.) == [3]
    assert vizinhos(.2) == [1]
    for valor in (0, -1, float('nan'), float('inf')):
        try:
            vizinhos(valor)
        except ValueError:
            pass
        else:
            raise AssertionError('Estimativa inválida aceita')
    # A contagem de avisos não vota: importa a severidade por família.
    base = dict(excesso_aero_max=0., excesso_aero_soma=0., excesso_camber=0.,
                excesso_faixas_max=0., excesso_faixas_soma=0., afastamento_psi_relativo=0.)
    assert chave_classificacao(dict(base,n_estagios=3,avisos=100)) < chave_classificacao(dict(base,n_estagios=4,avisos=0))
    assert chave_classificacao(dict(base,n_estagios=4,excesso_faixas_max=1.)) < chave_classificacao(dict(base,n_estagios=3,excesso_aero_max=.01))
    resultados = casos_regressao()
    manuais = lambda d: dict(casos=[c for c in d['casos'] if not c['automatico']])
    comparar_antes(manuais(antes), manuais(dict(casos=resultados)))
    casos = []
    for pi in (6., 8., 12.):
        c, comp, turb, rc, rt = montar_caso(pi, True)
        for modelo, radial, nome in ((comp,rc,'Compressor'),(turb,rt,'Turbina')):
            s = modelo.selecao_estagios
            assert [r['n_estagios'] for r in s['candidatos']] == vizinhos(modelo.n_estagios_estimado)
            validos = [r for r in s['candidatos'] if r['calculavel']]
            escolhido = min(validos,key=chave_classificacao)
            assert escolhido['n_estagios'] == modelo.n_estagios == s['escolhido']
            assert sum(r['selecionado'] for r in s['candidatos']) == 1
            assert math.isclose(modelo.n_estagios*modelo.psi_efetivo*modelo.U**2,
                                modelo.delta_Tt_total*modelo.cp,rel_tol=1e-11)
            # Mesmo objeto pode ser resolvido novamente sem recursão/reutilização
            # de uma solução manual ou alteração do psi solicitado.
            psi, original = modelo.psi, json.dumps(s,sort_keys=True)
            modelo.resolver()
            assert modelo.psi==psi and modelo.calculo_automatico
            assert json.dumps(modelo.selecao_estagios,sort_keys=True)==original
            casos.append(s)
    # Uma grade radial inadmissível é rejeitada já na entrada da API,
    # sem iniciar a comparação dos candidatos.
    from engine.compressor.Compressor_Meanline_main import CompressorMeanline
    from engine.reference_case import montar_caso_referencia
    ref = montar_caso_referencia()['REF_COMP']
    ref['n_estagios'] = None
    try:
        invalido = CompressorMeanline(ciclo=c,n_secoes_avaliacao=1,**ref)
        invalido.resolver()
    except ValueError as erro:
        assert 'n_secoes_avaliacao' in str(erro)
    else:
        raise AssertionError('Candidatos com grade inválida aceitos')
    return dict(casos=casos, regressao_manual='Preservada nos dois casos de 3/7 seções.',
                politica='vizinhos_criterios_v1', repeticao_deterministica=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--antes',type=Path,required=True)
    p.add_argument('--saida',type=Path,required=True)
    args=p.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        resultado=executar(json.loads(args.antes.read_text(encoding='utf-8-sig')))
    args.saida.write_text(json.dumps(resultado,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print('Seleção, oito casos de fechamento, regressão manual, repetibilidade e falhas de candidatos conferidos.')
