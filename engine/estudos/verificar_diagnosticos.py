"""Verifica o bloco 4 sem ajustar a solução física ou a geometria.

Da pasta NEW: python -m engine.estudos.verificar_diagnosticos --saida resultado.json
"""

import argparse
import contextlib
import io
import json
import math
import pickle
from pathlib import Path


def executar():
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        from engine.estudos.verificar_acoplamento import montar_caso
        from engine.combustor.Combustor_1D_2_main import Combustor1D
        from engine.diagnosticos import diagnosticar_integracao, comparar, _plano

    def perto(a, b, atol=1e-8):
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=atol), (a, b)

    zero = comparar("Teste de alvo zero", "W", 0, 1)
    assert zero["residuo_pct"] is None and not zero["coincide"]
    assert comparar("Zero", "W", 0, 0)["coincide"]
    p1 = _plano(500, 2e5, 100, 50, 10, 1005, 1.4)
    p2 = _plano(500, 2e5, 100, 50, 20, 1005, 1.4)
    perto(p2["area_m2"], 2 * p1["area_m2"])
    desconhecido = _plano(500, None, 100, 50, 10, 1005, 1.4)
    assert all(desconhecido[k] is None for k in ("Pt_Pa", "P_Pa", "rho_kg_m3", "area_m2"))
    for args in ((500, 0, 100, 0, 10, 1005, 1.4),
                 (500, 2e5, 0, 0, 10, 1005, 1.4),
                 (500, 2e5, 2000, 0, 10, 1005, 1.4),
                 (500, 2e5, 100, 0, 10, 1005, 1),
                 (float("nan"), 2e5, 100, 0, 10, 1005, 1.4)):
        try:
            _plano(*args)
        except ValueError:
            pass
        else:
            raise AssertionError((args, "entrada não admissível aceita"))
    # Somente área de saída do exemplo de Saravanamuttoo pp. 210–211
    # (PDF 227–228): valores publicados arredondados e R ligeiramente distinto.
    livro = _plano(452.5, 419e3, 150, 0, 20, 1005, 1.4)
    assert abs(livro["area_m2"] - .0440) < 1e-4

    resultados = []
    for pi, auto, n in [(8, False, n) for n in (3, 7)] + [(p, True, n) for p in (6, 8, 12) for n in (3, 7)]:
        with contextlib.redirect_stdout(log):
            c, comp, t, rc, rt = montar_caso(pi, auto, n)
            b = Combustor1D(c); b.resolver()
        objetos = (c, comp, t, b, rc, rt)
        antes = pickle.dumps(objetos)
        d = diagnosticar_integracao(c, comp, t, b)
        assert pickle.dumps(objetos) == antes, "Diagnóstico modificou os objetos físicos"
        assert d["alvos_coincidem"] == auto
        for nome, modelo in (("Compressor", comp), ("Turbina", t)):
            dados = d["componentes"][nome]
            for i, estagio in enumerate(dados["estagios"]):
                planos = estagio["planos"]
                assert planos["2"]["Pt_Pa"] is None and planos["2"]["area_m2"] is None
                perto(planos["1"]["area_m2"], modelo.A_estagio[i], atol=1e-12)
                if nome == "Turbina":
                    perto(planos["3"]["area_m2"], modelo.A_saida_estagio[i], atol=1e-12)
                for numero in ("1", "3"):
                    p = planos[numero]
                    perto(p["rho_kg_m3"] * p["Cx_m_s"] * p["area_m2"], modelo.m_dot)
                    alpha = math.atan2(p["Ctheta_m_s"], p["Cx_m_s"])
                    area_mfp = modelo.m_dot * math.sqrt(p["Tt_K"]) / (p["Pt_Pa"] * math.cos(alpha) * modelo._MFP(p["M"]))
                    perto(p["area_m2"], area_mfp, atol=1e-12)
            assert all(linha["coincide"] for interface in dados["interfaces"] for linha in interface["comparacoes"])
        wc_indep = comp.m_dot * comp.n_estagios * comp.cp * comp.delta_Tt_estagio
        wt_indep = t.m_dot * t.n_estagios * t.cp * t.delta_Tt_estagio
        perto(d["potencias"][0]["calculado"], wc_indep)
        perto(d["potencias"][1]["calculado"], wt_indep)
        perto(d["potencias"][2]["calculado"], wt_indep - wc_indep)
        if not auto:
            pressao = d["componentes"]["Compressor"]["comparacoes"][1]
            assert 0 < abs(pressao["residuo_pct"]) < 2 and not pressao["coincide"]
            if math.isclose(c.cp_ar,c.cp_gases,rel_tol=1e-12) and math.isclose(c.k_ar,c.k_gases,rel_tol=1e-12):
                perto(d["potencias"][2]["calculado"] / 1000, 2215.787186241923, atol=1e-6)
            # Com gases distintos o resultado histórico não é o alvo. As
            # potências continuam verificadas independentemente acima por Euler.
        # JSON estrito preserva desconhecidos como null, sem NaN ou zero fictício.
        texto = json.dumps(d, allow_nan=False)
        assert json.loads(texto)["componentes"]["Turbina"]["estagios"][0]["planos"]["2"]["area_m2"] is None
        resultados.append(dict(pi=pi, automatico=auto, n_secoes=n, diagnosticos=d))
    return dict(casos=resultados, area_exemplo_Saravanamuttoo_m2=livro["area_m2"],
                tolerancia_exemplo_m2=1e-4, testes_alvo_zero=True, objetos_preservados=True,
                avisos=log.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    dados = executar()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("Oito casos conferidos: resíduos, áreas, dados desconhecidos e preservação dos objetos físicos.")
