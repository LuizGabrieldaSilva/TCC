"""Verificações de Carter, solidez e orientação dos perfis realmente loftados.

Da pasta NEW: python -m engine.estudos.verificar_geometria_perfis --saida resultado.json
Não substitui validação aerodinâmica, estrutural ou inspeção do sólido CAD.
"""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path


def executar():
    with contextlib.redirect_stdout(io.StringIO()):
        from engine.estudos.verificar_acoplamento import montar_caso, conferir
        from engine.geometry.airfoil4 import (
            gerar_perfil_pa, gerar_perfis_compressor, gerar_perfis_turbina,
        )
        from engine.geometry.loft2 import loftar_compressor, loftar_turbina
        from engine.aero.cascade_geometry import solidez_local
        from engine.aero.radial_turbina_3_main import RadialTurbina

    def perto(a, b, tol=1e-9):
        assert math.isfinite(a) and math.isfinite(b), (a, b)
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=tol), (a, b)

    # Dixon & Hall 7ª ed., exemplo 3.1, pp. 86–87 (PDF 97–98).
    # A API usa i=0: fornecer diretamente 47° isola a entrada metálica
    # 50°-3° do exemplo, sem alegar reprodução da sua incidência não nula.
    carter = gerar_perfil_pa(47, 30, 1 / .85, .05)
    assert abs(carter.delta - 6.2) < .05
    assert abs(carter.theta_final - 23.2) < .05
    espelhado = gerar_perfil_pa(-47, -30, 1 / .85, .05)
    perto(espelhado.delta, -carter.delta)
    perto(espelhado.theta_final, -carter.theta_final)
    for campo in ("x_camber", "x_extradorso", "x_intradorso"):
        for a, b in zip(getattr(carter, campo), getattr(espelhado, campo)):
            perto(a, b)
    for campo in ("y_camber", "y_extradorso", "y_intradorso"):
        for a, b in zip(getattr(carter, campo), getattr(espelhado, campo)):
            perto(a, -b)
    invalidos = 0
    for sigma, b1, b2 in ((0, 47, 30), (-1, 47, 30), (float("nan"), 47, 30),
                          (.29 ** 2, 47, 30), (.01, 47, 30), (.2, 80, -80)):
        try:
            gerar_perfil_pa(b1, b2, sigma, .05)
        except ValueError:
            invalidos += 1
        else:
            raise AssertionError((sigma, b1, b2, "entrada inválida aceita"))
    for z, c, r in ((0, .1, .2), (2.5, .1, .2), (2, -.1, .2), (2, .1, 0)):
        try:
            solidez_local(z, c, r)
        except ValueError:
            invalidos += 1
        else:
            raise AssertionError("Geometria de cascata inválida aceita")

    resultados, avisos = [], io.StringIO()
    casos = [(8, False, n) for n in (3, 7)] + [
        (pi, True, n) for pi in (6, 8, 12) for n in (3, 7)
    ]
    for pi, auto, n in casos:
        with contextlib.redirect_stdout(avisos):
            ciclo, comp, turb, rc, rt = montar_caso(pi, auto, n)
            pc = gerar_perfis_compressor(rc, n_pontos=200)
            pt = gerar_perfis_turbina(rt, n_pontos=200)
            mc = loftar_compressor(rc, perfis=pc, replicar=False)
            mt = loftar_turbina(rt, perfis=pt, replicar=False)
        maior_erro_tangente = 0.
        perfis_verificados = 0
        for m, rad, perfis, maquina, nome, fileiras in (
            (comp, rc, pc, mc, "Compressor", ("rotor", "estator")),
            (turb, rt, pt, mt, "Turbina", ("bocal", "rotor")),
        ):
            conferir(m, rad, nome)
            for i in range(m.n_estagios):
                for j, secao in enumerate(rad.secoes):
                    r = rad.r[i][secao]
                    for pos, fileira in enumerate(fileiras):
                        p = perfis[i + 1][secao][fileira]
                        z = getattr(m, f"Z_{fileira}")[i]
                        c = getattr(m, f"corda_{fileira}")[i]
                        perto(p.sigma, z * c / (2 * math.pi * r))
                        perto(p.sigma, getattr(rad, f"sigma_{fileira}_local")[i][secao])
                        perto(p.corda, c)
                        perto(p.beta1_graus - p.beta1_linha, 0)
                        perto(p.beta2_graus - p.beta2_linha, p.delta)
                        if nome == "Compressor":
                            perto(p.delta, p.m_carter * p.theta_final * math.sqrt(1 / p.sigma))
                            flow1 = (-rad.beta1[i][secao] if fileira == "rotor" else rad.alpha2[i][secao])
                            flow2 = (-rad.beta2[i][secao] if fileira == "rotor" else rad.alpha1[i][secao])
                        else:
                            perto(p.delta, 0)
                            flow1 = (rad.alpha1[i][secao] if fileira == "bocal" else rad.beta2[i][secao])
                            flow2 = (rad.alpha2[i][secao] if fileira == "bocal" else rad.beta3[i][secao])
                        perto(p.beta1_graus, flow1)
                        perto(p.beta2_graus, flow2)
                        # Derivadas unilaterais de 3 pontos da curva REAL
                        # entregue ao exportador, no plano desenrolado rθ,z.
                        curva = maquina.pecas[2 * i + pos].pa.camber_cil[j]
                        for inicio, alvo in ((True, p.beta1_linha), (False, p.beta2_linha)):
                            pontos = curva[:3] if inicio else curva[-3:]
                            pesos = (-3, 4, -1) if inicio else (1, -4, 3)
                            dt = sum(w * ponto[1] * r for w, ponto in zip(pesos, pontos))
                            dz = sum(w * ponto[2] for w, ponto in zip(pesos, pontos))
                            angulo = math.degrees(math.atan2(dt, dz))
                            erro = abs((angulo - alvo + 180) % 360 - 180)
                            assert erro < .02, (nome, i, secao, fileira, inicio, erro)
                            maior_erro_tangente = max(maior_erro_tangente, erro)
                        for curva_cart in (maquina.pecas[2*i+pos].pa.extradorso_cart[j],
                                           maquina.pecas[2*i+pos].pa.intradorso_cart[j]):
                            for x, y, axial in curva_cart:
                                perto(math.hypot(x, y), r)
                                assert math.isfinite(axial)
                        perfis_verificados += 1
            # Geometria e σ meanline permanecem iguais no raio de referência.
            meio = rad.secoes[len(rad.secoes) // 2]
            for i in range(m.n_estagios):
                for fileira in fileiras:
                    esperado = solidez_local(getattr(m, f"Z_{fileira}")[i],
                                             getattr(m, f"corda_{fileira}")[i], m.r_mean)
                    perto(getattr(rad, f"sigma_{fileira}_local")[i][meio], esperado)
            if nome == "Compressor":
                for i in range(m.n_estagios):
                    for secao in rad.secoes:
                        sr = rad.sigma_rotor_local[i][secao]
                        se = rad.sigma_estator_local[i][secao]
                        dv = abs(rad.v2[i][secao] - rad.v1[i][secao])
                        perto(rad.DF_rotor[i][secao], 1 - rad.W2[i][secao] / rad.W1[i][secao]
                              + dv / (2 * sr * rad.W1[i][secao]))
                        perto(rad.DF_estator[i][secao], 1 - rad.V1[i][secao] / rad.V2[i][secao]
                              + dv / (2 * se * rad.V2[i][secao]))
        resultados.append(dict(pi=pi, automatico=auto, n_secoes=n,
                               perfis=perfis_verificados, erro_tangente_max_graus=maior_erro_tangente))
    # Solidez do formulário diferente de 1 deve chegar aos perfis da turbina
    # através de Z/c reais, inclusive depois do arredondamento.
    with contextlib.redirect_stdout(avisos):
        for alvo in (.7, 1.4):
            t = type(turb)(ciclo=ciclo, N=turb.N, HTR=turb.HTR, phi=turb.phi,
                           psi=turb.psi, alpha2_graus=turb.alpha2_graus, sigma=alvo,
                           AR=turb.AR, n_estagios=3, m_dot_turbina=turb.m_dot)
            t.resolver()
            rad = RadialTurbina(t)
            rad.resolver()
            perfis = gerar_perfis_turbina(rad)
            for i in range(t.n_estagios):
                for s in rad.secoes:
                    for row in ("bocal", "rotor"):
                        perto(perfis[i+1][s][row].sigma,
                              getattr(t, f"Z_{row}")[i] * getattr(t, f"corda_{row}")[i]
                              / (2 * math.pi * rad.r[i][s]))
    return dict(carter_exemplo_3_1=dict(delta=carter.delta, theta=carter.theta_final),
                entradas_invalidas_rejeitadas=invalidos, casos=resultados,
                solidez_turbina_alvos_verificados=[.7, 1.4], avisos=avisos.getvalue())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    resultado = executar()
    args.saida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"{len(resultado['casos'])} casos de perfis conferidos; Carter, solidez e tangentes coerentes.")
