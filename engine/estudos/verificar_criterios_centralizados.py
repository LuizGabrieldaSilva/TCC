"""Compara mensagens e fronteiras com o checkpoint anterior à centralização.

Da pasta NEW: python -m engine.estudos.verificar_criterios_centralizados
"""
import contextlib
import importlib.util
import inspect
import io
import json
import math
from pathlib import Path

from engine.aero import constraints as novo
from engine import design_criteria as dc


def executar():
    checkpoint = Path(__file__).resolve().parents[3] / 'checkpoints/criterios_centralizados_2026-11-09'
    spec = importlib.util.spec_from_file_location('constraints_antes', checkpoint/'NEW/engine/aero/constraints.py')
    antigo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(antigo)
    comparacoes = 0
    # Cobrir bordas, extremos, NaN (comportamento histórico) e localização.
    valores = [-2., -.001, 0., .15, .2, .3, .4, .6, .7, 1., 1.3, 60., 90., float('nan')]
    valores += [math.nextafter(x, d) for x in (.08, .15, .2, .4, .6, .7, 1., 1.3, 60., 90.)
                for d in (-math.inf, math.inf)]
    funcoes = [n for n, f in inspect.getmembers(antigo, inspect.isfunction) if n.startswith('checar_')]
    for nome in funcoes:
        antes, depois = getattr(antigo, nome), getattr(novo, nome)
        assert inspect.signature(antes) == inspect.signature(depois), nome
        sig = inspect.signature(antes)
        for v in valores:
            kwargs = {}
            for parametro in sig.parameters.values():
                n = parametro.name
                if n == 'estagio': kwargs[n] = 3
                elif n == 'secao': kwargs[n] = 'hub'
                elif n == 'fileira': kwargs[n] = 'rotor'
                elif n == 'U': kwargs[n] = 100.
                elif n in ('minimo', 'maximo'): kwargs[n] = 0. if n == 'minimo' else 1.
                elif n == 'descricao': kwargs[n] = 'Grandeza'
                elif parametro.default is inspect.Parameter.empty: kwargs[n] = v
            assert antes(**kwargs) == depois(**kwargs), (nome, v)
            comparacoes += 1
    # Alcances que não podem se expandir durante esta refatoração.
    assert not novo.checar_secao_compressor_radial(.3, .3, .1, .5, 1, 'hub')
    assert novo.checar_estagio_compressor_meanline(.3, .3, .1, .5, 1)
    assert not novo.checar_estagio_turbina_meanline(.5, .5, .5, 50., 100., 1, verificar_swirl=False)
    assert novo.checar_estagio_turbina_meanline(.5, .5, .5, 50., 100., 1, verificar_swirl=True)
    # Personalizações explícitas da API continuam funcionando.
    assert novo.checar_mach(1.1, limite=1.2) is None
    assert novo.checar_DF(.7, limite=.8) is None
    assert novo.checar_camber_excessivo(95., limite=100.) is None
    assert novo.checar_grau_reacao(.2, faixa=(.1,.3)) is None
    from engine.geometry.airfoil4 import gerar_perfil_pa
    assert inspect.signature(gerar_perfil_pa).parameters['limite_camber'].default == dc.CAMBER_COMP_GRAUS
    from engine.diagnosticos import RTOL, ATOL
    assert (RTOL, ATOL) == (dc.COINCIDENCIA_RTOL, dc.COINCIDENCIA_ATOL)
    return dict(comparacoes_mensagens=comparacoes, funcoes=len(funcoes),
                assinaturas_preservadas=True, contextos_preservados=True, limites_personalizados=True)


if __name__ == '__main__':
    with contextlib.redirect_stdout(io.StringIO()):
        resultado = executar()
    saida = Path(__file__).resolve().parents[3] / 'checkpoints/criterios_centralizados_2026-11-09/criterios.json'
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(resultado, ensure_ascii=False))
