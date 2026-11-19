"""Conferência das bases energéticas; não substitui validação experimental."""

import contextlib
import io
import json
import math
import pickle
from pathlib import Path


def executar():
    from engine.ciclo.CicloBrayton import CicloBrayton
    from engine.combustor.Combustor_1D_2_main import Combustor1D
    from engine.indicadores import indicadores_energeticos
    from engine.reference_case import montar_caso_referencia
    from engine.estudos.sensibilidade import rodar_caso_ciclo
    resultados = []
    for massa in (15., 16.):
        for eficiencia in (.95, .99, 1.):
            for combustivel in ('JP-4', 'gas_natural'):
                ref = montar_caso_referencia()
                ref['REF_M_DOT'] = massa
                ref['REF_COMBUSTOR'].update(eta_b=eficiencia, combustivel=combustivel)
                c = CicloBrayton(**ref['REF_CICLO'])
                c.resolver()
                c.vazão_mássica_desejada(massa)
                b = Combustor1D(c, **ref['REF_COMBUSTOR'])
                b.resolver()
                c.registrar_vazao_turbina(b.m_dot_turbina)
                antes = pickle.dumps((c, b))
                d = indicadores_energeticos(c, b)
                assert pickle.dumps((c, b)) == antes
                perto = lambda x, y: math.isclose(x, y, rel_tol=1e-11, abs_tol=1e-10)
                assert perto(d['eta_calor_util'], c.eta_ciclo)
                assert perto(d['eta_PCI'], eficiencia*c.eta_ciclo)
                assert perto(d['BWR'], c.BWR)
                assert perto(d['trabalho_liquido_por_kg_ar_J_kg'], c.w_líq)
                # Independent units check: 1 kWh = 3.6 MJ.
                assert perto(d['eta_PCI'], 3.6e6/(d['SFC_kg_kWh']*b.h_PR))
                assert perto(d['calor_util_W'], c.m_dot_ar*c.q_ent)
                s = rodar_caso_ciclo({}, ref)
                assert s['valido']
                assert perto(s['eta_PCI_pct'], 100*d['eta_PCI'])
                assert perto(s['eta_calor_util_pct'], s['eta_ciclo_pct'])
                assert perto(s['SFC_kg_kWh'], d['SFC_kg_kWh'])
                resultados.append(dict(massa=massa, combustivel=combustivel, **d))
    return resultados


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--saida', required=True)
    args = parser.parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        resultados = executar()
    Path(args.saida).write_text(json.dumps(resultados, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    print(f'{len(resultados)} casos aprovados: bases, identidades energeticas, sensibilidade e ausencia de mutacao.')
