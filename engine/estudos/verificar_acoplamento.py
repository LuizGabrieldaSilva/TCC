"""Verificação reproduzível do acoplamento; não equivale a validação completa.

Da pasta NEW: python -m engine.estudos.verificar_acoplamento --saida resultado.json
Antes/depois: --snapshot arquivo.json registra resultados sem exigir a correção.
"""

import argparse
import contextlib
import io
import json
import math
from pathlib import Path


def montar_caso(razao=8.0, automatico=False, n_secoes=7):
    # As importações atuais executam exemplos; capturar suas mensagens também.
    from engine.reference_case import montar_caso_referencia
    from engine.ciclo.CicloBrayton import CicloBrayton
    from engine.compressor.Compressor_Meanline_main import CompressorMeanline
    from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
    from engine.combustor.Combustor_1D_2_main import Combustor1D
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.aero.radial_turbina_3_main import RadialTurbina
    ref = montar_caso_referencia()
    ref["REF_CICLO"]["r_compr"] = razao
    if automatico:
        ref["REF_COMP"]["n_estagios"] = None
        ref["REF_TURB"]["n_estagios"] = None
    ciclo = CicloBrayton(**ref["REF_CICLO"])
    ciclo.resolver()
    ciclo.vazão_mássica_desejada(ref["REF_M_DOT"])
    comp = CompressorMeanline(ciclo=ciclo, **ref["REF_COMP"])
    comp.resolver()
    combustor = Combustor1D(ciclo=ciclo, **ref["REF_COMBUSTOR"])
    combustor.resolver()
    ciclo.registrar_vazao_turbina(combustor.m_dot_turbina)
    turb = TurbinaAxialMeanline(ciclo=ciclo, m_dot_turbina=combustor.m_dot_turbina, **ref["REF_TURB"])
    turb.resolver()
    rc, rt = RadialCompressor(comp, n_secoes=n_secoes), RadialTurbina(turb, n_secoes=n_secoes)
    rc.resolver()
    rt.resolver()
    return ciclo, comp, turb, rc, rt


def medir(modelo, radial, componente):
    entrada, saida, sinal = (1, 2, 1) if componente == "Compressor" else (2, 3, -1)
    estagios = []
    for i in range(modelo.n_estagios):
        trabalho = modelo.cp * modelo.delta_Tt_estagio
        valores = [sinal * radial.U_r[i][s] * (
            getattr(radial, f"v{saida}")[i][s] - getattr(radial, f"v{entrada}")[i][s]) for s in radial.secoes]
        dados = dict(estagio=i + 1, area=modelo.A_estagio[i], cubo=modelo.r_hub_est[i],
                     ponta=modelo.r_tip_est[i], trabalho_meanline=trabalho,
                     trabalho_radial=valores, HTR=modelo.r_hub_est[i] / modelo.r_tip_est[i])
        estagios.append(dados)
    campos = ("Tt_entrada", "Tt_saida", "Pt_entrada", "Pt_saida", "v1", "v2", "alpha1", "alpha2")
    indicadores = {}
    for campo in ("M1", "M1R", "M2", "M2R", "M3", "M3R", "DF_rotor", "DF_estator", "R_c"):
        if hasattr(radial, campo):
            valores = [valor for estagio in getattr(radial, campo) for valor in estagio.values()]
            assert all(math.isfinite(v) for v in valores), (componente, campo, "valor não finito")
            indicadores[campo] = dict(minimo=min(valores), maximo=max(valores))
    return dict(r_ref=modelo.r_mean, U=modelo.U, u_ax=modelo.u_ax,
                n_estagios=modelo.n_estagios, psi_efetivo=modelo.psi_efetivo,
                termodinamica_e_triangulos={k: getattr(modelo, k) for k in campos},
                estagios=estagios, indicadores_radiais=indicadores)


def conferir(modelo, radial, componente):
    """Identidades internas: tolerância relativa 1e-10 e absoluta SI 1e-9."""
    def perto(a, b):
        assert math.isfinite(a) and math.isfinite(b)
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), (componente, a, b)
    entrada, saida, sinal = (1, 2, 1) if componente == "Compressor" else (2, 3, -1)
    max_erro = 0.0
    for i in range(modelo.n_estagios):
        rh, rt = modelo.r_hub_est[i], modelo.r_tip_est[i]
        assert 0 < rh < rt
        perto((rh + rt) / 2, modelo.r_mean)
        perto(math.pi * (rt ** 2 - rh ** 2), modelo.A_estagio[i])
        perto(modelo.h_pa[i], rt - rh)
        alvo = modelo.cp * modelo.delta_Tt_estagio
        perto(sinal * modelo.U * (getattr(modelo, f"v{saida}")[i] - getattr(modelo, f"v{entrada}")[i]), alvo)
        for s in radial.secoes:
            r, u = radial.r[i][s], radial.U_r[i][s]
            perto(u, modelo.omega * r)
            for j in (entrada, saida):
                v = getattr(radial, f"v{j}")[i][s]
                vm = getattr(modelo, f"v{j}")[i]
                perto(r * v, modelo.r_mean * vm)
                perto(getattr(radial, f"V{j}")[i][s], math.hypot(radial.u_ax, v))
                perto(getattr(radial, f"W{j}")[i][s], math.hypot(radial.u_ax, v - u))
            w = sinal * u * (getattr(radial, f"v{saida}")[i][s] - getattr(radial, f"v{entrada}")[i][s])
            perto(w, alvo)
            max_erro = max(max_erro, abs(w - alvo))
        # Nas malhas ímpares a seção central é exatamente a média aritmética.
        meio = radial.secoes[len(radial.secoes) // 2]
        if len(radial.secoes) % 2:
            perto(radial.r[i][meio], modelo.r_mean)
            for j in (entrada, saida):
                for nome in (f"v{j}", f"V{j}", f"W{j}", f"alpha{j}", f"beta{j}"):
                    perto(getattr(radial, nome)[i][meio], getattr(modelo, nome)[i])
        # Continuidade na estação usada para dimensionar o anular (aproximação meanline).
        j_area = 1
        velocidade = modelo.V1[i]
        t = modelo.Tt_entrada[i] - velocidade ** 2 / (2 * modelo.cp)
        p = modelo.Pt_entrada[i] * (t / modelo.Tt_entrada[i]) ** (modelo.k / (modelo.k - 1))
        perto(p / (modelo.R * t) * modelo.u_ax * modelo.A_estagio[i], modelo.m_dot)
    return max_erro


def executar(verificar=True):
    resultados = []
    # Não atribuir aos casos os avisos dos exemplos executados nas importações.
    with contextlib.redirect_stdout(io.StringIO()):
        from engine.aero.radial_compressor_4_main import RadialCompressor
        from engine.aero.radial_turbina_3_main import RadialTurbina
        from engine.combustor.Combustor_1D_2_main import Combustor1D
    casos = [(8.0, False, n) for n in (3, 7)] + [(p, True, n) for p in (6.0, 8.0, 12.0) for n in (3, 7)]
    for razao, automatico, secoes in casos:
        texto = io.StringIO()
        with contextlib.redirect_stdout(texto):
            ciclo, comp, turb, rc, rt = montar_caso(razao, automatico, secoes)
            erros = {nome: conferir(m, r, nome) for m, r, nome in (
                (comp, rc, "Compressor"), (turb, rt, "Turbina"))} if verificar else None
        if verificar and automatico:
            for real, alvo in ((comp.Tt_saida[-1], ciclo.T02r), (comp.Pt_saida[-1], ciclo.P02),
                               (turb.Tt_saida[-1], ciclo.T04r), (turb.Pt_saida[-1], ciclo.P04)):
                assert math.isclose(real, alvo, rel_tol=1e-9, abs_tol=1e-7), (real, alvo)
        resultados.append(dict(razao=razao, automatico=automatico, n_secoes=secoes,
            compressor=medir(comp, rc, "Compressor"), turbina=medir(turb, rt, "Turbina"),
            erro_max_euler_Jkg=erros, avisos=texto.getvalue(),
            desvio_pressao_pct=dict(compressor=(comp.pi_total_calc / ciclo.r_compr - 1) * 100,
                                   turbina=(turb.pi_total_calc / ciclo.r_turb - 1) * 100)))
    return resultados


def comparacao_bibliografica_geometria():
    """Saravanamuttoo, Gas Turbine Theory, pp. 210–211 (PDF 227–228).

    Compara apenas o dimensionamento do anular; não o compressor inteiro.
    Valores publicados arredondados a quatro casas, tolerância 5e-5 m.
    """
    from engine.aero.annulus_geometry import raios_anular
    rh, rt, h = raios_anular(0.0440, 0.1697)
    esperado = dict(cubo=0.1491, ponta=0.1903, altura=0.0413)
    calculado = dict(cubo=rh, ponta=rt, altura=h)
    for k in esperado:
        assert abs(calculado[k] - esperado[k]) <= 5e-5
    return dict(fonte="Gas Turbine Theory, pp. 210–211; PDF 227–228", escopo="Somente geometria do anular",
                esperado_m=esperado, calculado_m=calculado, tolerancia_absoluta_m=5e-5)


def verificar_limites():
    from engine.aero.annulus_geometry import raios_anular, referencia_radial
    for area, raio in ((0, 1), (-1, 1), (1, 0), (float("nan"), 1), (float("inf"), 1),
                       (4 * math.pi, 1), (5 * math.pi, 1)):
        try:
            raios_anular(area, raio)
        except ValueError:
            pass
        else:
            raise AssertionError(("Geometria inválida aceita", area, raio))
    try:
        referencia_radial(1, 2, 1)
    except ValueError:
        pass
    else:
        raise AssertionError("Referência incompatível aceita")


def comparar_antes(antes, depois):
    assert len(antes["casos"]) == len(depois["casos"])
    for a, d in zip(antes["casos"], depois["casos"]):
        for campo in ("razao", "automatico", "n_secoes"):
            assert a[campo] == d[campo]
        for maquina in ("compressor", "turbina"):
            for campo in ("r_ref", "U", "u_ax", "n_estagios", "psi_efetivo", "termodinamica_e_triangulos"):
                assert a[maquina][campo] == d[maquina][campo], (maquina, campo, "alteração não prevista")
            assert [e["area"] for e in a[maquina]["estagios"]] == [e["area"] for e in d[maquina]["estagios"]]
    return "Estados, triângulos meanline, áreas, U, velocidade axial e estágios preservados nos oito casos."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Registra o estado sem executar as novas verificações.")
    parser.add_argument("--saida", type=Path, help="Salva a verificação e comparação bibliográfica em JSON.")
    parser.add_argument("--antes", type=Path, help="Compara os campos preservados com um snapshot anterior.")
    args = parser.parse_args()
    resultado = dict(casos=executar(verificar=args.snapshot is None))
    if args.snapshot is None:
        verificar_limites()
        resultado["comparacao_bibliografica"] = comparacao_bibliografica_geometria()
        if args.antes:
            resultado["regressao"] = comparar_antes(json.loads(args.antes.read_text(encoding="utf-8")), resultado)
    destino = args.snapshot or args.saida
    if destino:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"{len(resultado['casos'])} casos concluídos. " + ("Snapshot registrado." if args.snapshot else "Identidades verificadas; comparação geométrica aprovada."))


if __name__ == "__main__":
    main()
