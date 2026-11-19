"""Bloco 3: continuidade e reação estática da turbina, sem zerar swirl.

Da pasta NEW: python -m engine.estudos.verificar_estagios_turbina --antes snapshot.json --saida resultado.json
"""

import argparse
import contextlib
import io
import json
import math
from copy import deepcopy
from pathlib import Path


def executar(antes=None):
    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        from engine.estudos.verificar_acoplamento import montar_caso, conferir, medir
        from engine.aero.reacao_turbina import reacao_estatica
        from engine.aero.constraints import checar_estagio_turbina_meanline
        from engine.aero.radial_turbina_3_main import RadialTurbina

    def perto(a, b, atol=1e-8):
        assert math.isfinite(a) and math.isfinite(b)
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=atol), (a, b)

    # Triângulo sintético: U=300, Cx=100, Ctheta2=250, Ctheta3=50.
    # w=60 kJ/kg, dh_rotor=30 kJ/kg, dh_estagio=61,25 kJ/kg.
    r, rotor, estagio = reacao_estatica(60000, 100, math.hypot(100, 250), math.hypot(100, 50))
    perto(rotor, 30000); perto(estagio, 61250); perto(r, 30000 / 61250)
    perto(reacao_estatica(60000, math.hypot(100, 50), math.hypot(100, 250), math.hypot(100, 50))[0], .5)
    assert reacao_estatica(10000, 100, math.hypot(100, 400), math.hypot(100, 300))[0] < 0
    for dados in ((0, 1, 2, 1), (1, -1, 2, 1), (1, float("nan"), 2, 1),
                  (1, math.sqrt(3), 0, 1), (1, 10, 1, 1)):
        try:
            reacao_estatica(*dados)
        except ValueError:
            pass
        else:
            raise AssertionError((dados, "reação não admissível aceita"))
    args_aviso = dict(grau_reacao=.5, M2=.5, M3R=.5, v3=60, U=300, estagio=1)
    assert not checar_estagio_turbina_meanline(**args_aviso, verificar_swirl=False)
    assert len(checar_estagio_turbina_meanline(**args_aviso, verificar_swirl=True)) == 1

    preservados = ("Tt_entrada", "Tt_saida", "Pt_entrada", "Pt_saida", "v2", "v3",
                   "V2", "V3", "W2", "W3", "alpha2", "alpha3", "beta2", "beta3",
                   "M2", "M3", "M2R", "M3R")
    resultados = []
    casos = [(8, False, n) for n in (3, 7)] + [(pi, True, n) for pi in (6, 8, 12) for n in (3, 7)]
    for indice, (pi, auto, n) in enumerate(casos):
        with contextlib.redirect_stdout(log):
            c, comp, t, rc, rt = montar_caso(pi, auto, n)
        conferir(comp, rc, "Compressor")
        erro_euler = conferir(t, rt, "Turbina")
        interfaces = []
        trabalho = t.cp * t.delta_Tt_estagio
        for i in range(t.n_estagios):
            # Independentemente das formas com diferenças de velocidades,
            # recuperar reação pelas temperaturas estáticas de cada plano.
            dh_rotor = t.cp * (t.T2_est[i] - t.T3_est[i])
            dh_estagio = t.cp * (t.T1_est[i] - t.T3_est[i])
            perto(dh_rotor, t.queda_h_estatica_rotor[i])
            perto(dh_estagio, t.queda_h_estatica_estagio[i])
            perto(t.grau_reacao[i], dh_rotor / dh_estagio)
            perto(t.reacao_rotor_por_trabalho[i], 1 - (t.v2[i] + t.v3[i]) / (2 * t.U))
            for vel, tt, pt, area in ((t.V1[i], t.Tt_entrada[i], t.Pt_entrada[i], t.A_estagio[i]),
                                      (t.V3[i], t.Tt_saida[i], t.Pt_saida[i], t.A_saida_estagio[i])):
                temp = tt - vel ** 2 / (2 * t.cp)
                pressao = pt * (temp / tt) ** (t.k / (t.k - 1))
                perto(pressao / (t.R * temp) * t.u_ax * area, t.m_dot)
            for secao in rt.secoes:
                T1 = t.Tt_entrada[i] - rt.V1[i][secao] ** 2 / (2 * t.cp)
                T2 = t.Tt_entrada[i] - rt.V2[i][secao] ** 2 / (2 * t.cp)
                T3 = t.Tt_saida[i] - rt.V3[i][secao] ** 2 / (2 * t.cp)
                perto(rt.R_c[i][secao], (T2 - T3) / (T1 - T3))
            if i == 0:
                perto(t.v1[i], 0); perto(t.alpha1[i], 0)
                continue
            j = i - 1
            for a, b in ((t.v1[i], t.v3[j]), (t.V1[i], t.V3[j]),
                         (t.alpha1[i], t.alpha3[j]), (t.Tt_entrada[i], t.Tt_saida[j]),
                         (t.Pt_entrada[i], t.Pt_saida[j]), (t.T1_est[i], t.T3_est[j]),
                         (t.A_estagio[i], t.A_saida_estagio[j])):
                perto(a, b)
            # A igualdade é no mesmo raio físico: anulares têm malhas distintas.
            raio = (max(t.r_hub_est[i], t.r_hub_est[j]) + min(t.r_tip_est[i], t.r_tip_est[j])) / 2
            K_anterior = rt.v3[j]["hub"] * rt.r[j]["hub"]
            K_seguinte = rt.v1[i]["tip"] * rt.r[i]["tip"]
            perto(K_anterior, K_seguinte)
            perto(K_anterior / raio, K_seguinte / raio)
            perto(t.grau_reacao[i], t.reacao_rotor_por_trabalho[i])
            interfaces.append(dict(de=j+1, para=i+1, residuo_vtheta=t.v1[i]-t.v3[j],
                                   residuo_Tt=t.Tt_entrada[i]-t.Tt_saida[j],
                                   residuo_Pt=t.Pt_entrada[i]-t.Pt_saida[j],
                                   residuo_area_m2=t.A_estagio[i]-t.A_saida_estagio[j],
                                   residuo_K=K_seguinte-K_anterior))
        if antes:
            original = antes["casos"][indice]
            assert (original["pi"], original["automatico"], original["n_secoes"]) == (pi, auto, n)
            assert c.resultados() == original["ciclo"]
            assert medir(comp, rc, "Compressor") == original["compressor"]
            for campo in preservados:
                assert getattr(t, campo) == original["turbina"][campo], (campo, pi)
            for campo, valor in original["ref_turbina"].items():
                assert getattr(t, campo) == valor, (campo, pi)
        estado = deepcopy({campo: valor for campo, valor in vars(t).items() if isinstance(valor, list)})
        with contextlib.redirect_stdout(log):
            t.resolver()
        assert estado == {campo: getattr(t, campo) for campo in estado}, "resolver não idempotente"
        resultados.append(dict(pi=pi, automatico=auto, n_secoes=n, interfaces=interfaces,
                               erro_max_Euler_Jkg=erro_euler,
                               R_meanline=t.grau_reacao, rotor_por_trabalho=t.reacao_rotor_por_trabalho,
                               alpha1=t.alpha1, alpha3=t.alpha3, areas_entrada_m2=t.A_estagio,
                               areas_saida_m2=t.A_saida_estagio, Z_bocal=t.Z_bocal, Z_rotor=t.Z_rotor,
                               R_radial_min=min(x for linha in rt.R_c for x in linha.values())))
    # Limites de topologia: uma máquina de um estágio e saída axial sem swirl.
    extras = []
    for n_est, psi in ((1, t.psi), (3, t.phi * math.tan(math.radians(t.alpha2_graus)))):
        with contextlib.redirect_stdout(log):
            extra = type(t)(ciclo=c, N=t.N, HTR=t.HTR, phi=t.phi, psi=psi,
                            alpha2_graus=t.alpha2_graus, n_estagios=n_est, m_dot_turbina=t.m_dot)
            extra.resolver(); rad = RadialTurbina(extra); rad.resolver()
        conferir(extra, rad, "Turbina")
        if n_est == 3:
            for i in range(n_est):
                perto(extra.v3[i], 0)
                perto(extra.grau_reacao[i], extra.reacao_rotor_por_trabalho[i])
        extras.append(dict(n_estagios=n_est, psi=psi, v3=extra.v3, R=extra.grau_reacao))
    return dict(casos=resultados, testes_adicionais=extras,
                exemplo_sintetico_R=r, reacao_estatica_por_temperaturas=True,
                regressao="Ciclo, compressor, trabalho/triângulos do rotor e estados totais da turbina preservados." if antes else "Sem snapshot anterior.",
                avisos=log.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--antes", type=Path)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    antes = json.loads(args.antes.read_text(encoding="utf-8-sig")) if args.antes else None
    dados = executar(antes)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print("Oito casos e dois casos adicionais: continuidade, reação, energia e Euler conferidos.")
