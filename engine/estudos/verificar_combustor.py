"""Verifica o bloco 2: escala de comprimento e origem dos combustíveis.

Da pasta NEW: python -m engine.estudos.verificar_combustor --antes caminho.json --saida resultado.json
O exemplo de comprimento testa somente a escala, não o desempenho do JT9D.
"""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace


def executar(antes=None):
    avisos = io.StringIO()
    with contextlib.redirect_stdout(avisos):
        from engine.ciclo.CicloBrayton import CicloBrayton
        from engine.combustor.Combustor_1D_2_main import (
            Combustor1D, COMBUSTIVEIS, F_STOICH, COMBUSTOR_REF, FONTES_COMBUSTIVEIS,
        )
        from engine.reference_case import montar_caso_referencia
        ref = montar_caso_referencia()
        c = CicloBrayton(**ref["REF_CICLO"])
        c.resolver()
        c.vazão_mássica_desejada(ref["REF_M_DOT"])
    if antes:
        assert antes["COMBUSTIVEIS"] == COMBUSTIVEIS
        assert antes["F_STOICH"] == F_STOICH
        assert antes["COMBUSTOR_REF"] == COMBUSTOR_REF
    assert set(FONTES_COMBUSTIVEIS) == set(COMBUSTIVEIS) == set(F_STOICH)
    casos = {}
    for fuel in COMBUSTIVEIS:
        with contextlib.redirect_stdout(avisos):
            b = Combustor1D(c, combustivel=fuel)
            b.resolver()
        valores = b.resultados()
        fontes = b.fontes_combustivel()
        for prop in ("h_PR", "f_stoich"):
            assert fontes[prop]["valor"] == getattr(b, prop)
            assert all(fontes[prop][key] for key in ("status", "origem", "hipotese", "unidade"))
        origem = fontes["h_PR"]["origem"]
        fontes["h_PR"]["origem"] = "Cópia de teste"
        assert b.fontes_combustivel()["h_PR"]["origem"] == origem
        q_util = b.m_dot_f * b.h_PR * b.eta_b
        q_gases = b.m_dot_tot * b.cp_gases * (b.TIT-b.T_ref_entalpia) - b.m_dot_ar * b.cp_ar * (b.T02r-b.T_ref_entalpia)
        assert math.isclose(q_util, q_gases, rel_tol=1e-12, abs_tol=1e-7)
        esperado = COMBUSTOR_REF["L_ref"] * (b.P02 / COMBUSTOR_REF["Pt3_ref"]) ** (-COMBUSTOR_REF["r_exp"]) * math.sqrt(COMBUSTOR_REF["Tt4_ref"] / b.TIT)
        assert math.isclose(b.L_comb, esperado, rel_tol=1e-13)
        if antes:
            antigo = antes["casos"][fuel]
            for key in antigo:
                if key != "L_comb_cm":
                    assert antigo[key] == valores[key], (fuel, key, "mudança não prevista")
            fator = (c.P02 / c.P03) ** (-COMBUSTOR_REF["r_exp"])
            assert math.isclose(valores["L_comb_cm"], antigo["L_comb_cm"] * fator, rel_tol=1e-13)
        casos[fuel] = dict(resultados=valores, fontes=b.fontes_combustivel(),
                           residuo_energia_W=q_util - q_gases)

    # Dados do exemplo de Mattingly p. 822: fixture de entrada para isolar
    # a lei de escala. Não representa solução do ciclo completo do JT9D.
    dados = dict(vars(c))
    dados.update(T02r=600., P02=350 * 6894.757293168, TIT=2900 * 5 / 9,
                 dados_mistura=None,T_ref_entalpia=0.,mistura_automatica=False)
    exemplo = {}
    for perda in (0., .05, .2):
        dados.update(P03=dados["P02"] * (1 - perda), Delta_P_cc=perda)
        with contextlib.redirect_stdout(avisos):
            b = Combustor1D(SimpleNamespace(**dados))
            b.resolver()
        exemplo[str(perda)] = b.L_comb / .0254
        assert abs(exemplo[str(perda)] - 16.0) < .025, exemplo
    assert len(set(exemplo.values())) == 1, "Escala não pode usar a pressão de saída."
    publicado_sem_arredondar = 17.3 * (350 / 316) ** (-.714) * math.sqrt(2865 / 2900)
    assert abs(exemplo["0.05"] - publicado_sem_arredondar) < .005

    dados.update(P02=COMBUSTOR_REF["Pt3_ref"], P03=COMBUSTOR_REF["Pt3_ref"] * .95,
                 TIT=COMBUSTOR_REF["Tt4_ref"], Delta_P_cc=.05)
    with contextlib.redirect_stdout(avisos):
        igual = Combustor1D(SimpleNamespace(**dados)); igual.resolver()
        custom = Combustor1D(c, h_PR=44e6); custom.resolver()
    assert math.isclose(igual.L_comb, COMBUSTOR_REF["L_ref"], rel_tol=1e-13)
    assert custom.fontes_combustivel()["h_PR"]["status"] == "Fornecido pelo chamador"
    assert custom.fontes_combustivel()["h_PR"]["valor"] == 44e6
    assert custom.fontes_combustivel()["f_stoich"] == casos["JP-4"]["fontes"]["f_stoich"]
    assert math.isclose(F_STOICH["gas_natural"], .232 / 4, rel_tol=1e-13)
    jp8_tab = 10333 * 4.184 * 1000
    assert abs(COMBUSTIVEIS["JP-8"] / jp8_tab - 1) < .001
    assert FONTES_COMBUSTIVEIS["diesel"]["h_PR"]["status"] == "Fonte específica pendente"
    return dict(casos=casos, exemplo_Mattingly_L_in=exemplo, L_in_pela_escala_publicada=publicado_sem_arredondar,
                tolerancia_exemplo_in=.025, referencia_recuperada_m=igual.L_comb,
                PCI_JP8_tabela_convertido_Jkg=jp8_tab,
                regressao="Somente L_comb mudou nos quatro combustíveis." if antes else "Sem snapshot anterior.",
                avisos=avisos.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--antes", type=Path)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    antes = json.loads(args.antes.read_text(encoding="utf-8-sig")) if args.antes else None
    resultado = executar(antes)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("Quatro combustíveis conferidos; escala de Mattingly e rastreabilidade verificadas.")
