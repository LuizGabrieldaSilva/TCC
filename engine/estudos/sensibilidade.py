#______________________________________________________________________________________________________________
# Estudo de sensibilidade paramétrica (Grupo A: aerodinâmico/geométrico) e
# Grupo B (ciclo). Varia um parâmetro por vez (one-at-a-time), mantendo os
# demais no caso de referência da execução, e registra métricas de saída
# para cada rodada.
#
# Não modifica nenhum módulo existente -- só instancia e chama repetidamente
# CicloBrayton / CompressorMeanline / Combustor1D / TurbinaAxialMeanline /
# RadialCompressor / RadialTurbina / loftar_compressor / loftar_turbina.
#
# Casos que disparam ValueError esperado (ex.: DF_alvo inatingível,
# escoamento supersônico na entrada) são capturados e registrados como
# "caso inválido" -- não interrompem a varredura. valido=True indica que
# o cálculo foi concluído, não aprovação física ou validação experimental.
#______________________________________________________________________________________________________________

import io
import contextlib
import math
from typing import Optional

from engine.ciclo.CicloBrayton import CicloBrayton
from engine.indicadores import indicadores_energeticos
from engine.compressor.Compressor_Meanline_main import CompressorMeanline
from engine.combustor.Combustor_1D_2_main import Combustor1D
from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
from engine.aero.radial_compressor_4_main import RadialCompressor
from engine.aero.radial_turbina_3_main import RadialTurbina
from engine.geometry.loft2 import loftar_compressor, loftar_turbina
from engine.reference_case import (
    REF_CICLO, REF_M_DOT, REF_COMP, REF_TURB, REF_COMBUSTOR, REF_N_SECOES,
    montar_caso_referencia,
)


def _referencias_ativas(caso_referencia: Optional[dict] = None) -> tuple:
    """Obtém cópias dos parâmetros padrão ou do caso recebido da interface."""
    caso = montar_caso_referencia() if caso_referencia is None else caso_referencia
    return (
        caso["REF_CICLO"], caso["REF_M_DOT"], caso["REF_COMP"],
        caso["REF_TURB"], caso.get("REF_COMBUSTOR", REF_COMBUSTOR),
        caso["REF_N_SECOES"],
    )


def _capturar_avisos(func, *args, **kwargs):
    """
    Executa func(*args, **kwargs) capturando tudo que for impresso em
    stdout (os avisos de constraints.py são via print()), e retorna
    (resultado, houve_aviso, texto_avisos). Não trata exceções -- quem
    chama decide o que fazer com elas.
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        resultado = func(*args, **kwargs)
    texto = buffer.getvalue()
    houve_aviso = "AVISO" in texto or "⚠" in texto
    return resultado, houve_aviso, texto


# ══════════════════════════════════════════════════════════════════════════
# GRUPO A — VARREDURA AERODINÂMICA (COMPRESSOR)
# ══════════════════════════════════════════════════════════════════════════

def rodar_caso_compressor(overrides: dict,
                          caso_referencia: Optional[dict] = None,
                          incluir_loft: bool = True) -> dict:
    """
    Roda o pipeline ciclo->meanline->radial e, opcionalmente, loft para o compressor, com
    os parâmetros de REF_COMP sobrescritos por "overrides". Retorna um
    dicionário de métricas de saída, ou {"valido": False, "erro": ...}
    se o caso não for viável.
    """
    ref_ciclo, ref_m_dot, ref_comp, _, _, ref_n_secoes = _referencias_ativas(caso_referencia)
    params = {**ref_comp, **overrides}

    try:
        ciclo = CicloBrayton(**ref_ciclo)
        ciclo.resolver()
        ciclo.vazão_mássica_desejada(ref_m_dot)

        with contextlib.redirect_stdout(io.StringIO()):
            comp = CompressorMeanline(ciclo=ciclo, n_secoes_avaliacao=ref_n_secoes, **params)

        (_, houve_aviso, _) = _capturar_avisos(comp.resolver)

        rad = RadialCompressor(comp=comp, n_secoes=ref_n_secoes)
        (_, houve_aviso_radial, _) = _capturar_avisos(rad.resolver)
        z_total_cm = None
        if incluir_loft:
            maquina = loftar_compressor(rad, replicar=False)
            z_total_cm = maquina.z_total * 100

        return {
            "valido": True,
            "houve_aviso": houve_aviso or houve_aviso_radial,
            "n_estagios": comp.n_estagios,
            "M1R_max": max(comp.M1R),
            "DF_rotor_max": max(comp.DF_rotor),
            "DF_estator_max": max(comp.DF_estator),
            "reacao_min": min(comp.grau_reacao),
            "reacao_max": max(comp.grau_reacao),
            "Z_rotor_min": min(comp.Z_rotor),
            "Z_rotor_max": max(comp.Z_rotor),
            "corda_min_cm": min(comp.corda_rotor + comp.corda_estator) * 100,
            "z_total_cm": z_total_cm,
            "erro_pi_pct": abs(comp.pi_total_calc - comp.r_compr) / comp.r_compr * 100,
        }
    except (ValueError, RuntimeError) as e:
        return {"valido": False, "erro": str(e)}


def rodar_caso_turbina(overrides: dict,
                       caso_referencia: Optional[dict] = None,
                       incluir_loft: bool = True) -> dict:
    """Equivalente a rodar_caso_compressor(), para a turbina."""
    ref_ciclo, ref_m_dot, _, ref_turb, ref_combustor, ref_n_secoes = _referencias_ativas(caso_referencia)
    params = {**ref_turb, **overrides}

    try:
        ciclo = CicloBrayton(**ref_ciclo)
        ciclo.resolver()
        ciclo.vazão_mássica_desejada(ref_m_dot)

        with contextlib.redirect_stdout(io.StringIO()):
            combustor = Combustor1D(ciclo=ciclo, **ref_combustor)
            combustor.resolver()
        ciclo.registrar_vazao_turbina(combustor.m_dot_turbina)

        with contextlib.redirect_stdout(io.StringIO()):
            turb = TurbinaAxialMeanline(
                ciclo=ciclo, m_dot_turbina=combustor.m_dot_turbina,
                n_secoes_avaliacao=ref_n_secoes, **params
            )

        (_, houve_aviso, _) = _capturar_avisos(turb.resolver)

        rad = RadialTurbina(turb=turb, n_secoes=ref_n_secoes)
        (_, houve_aviso_radial, _) = _capturar_avisos(rad.resolver)
        z_total_cm = None
        if incluir_loft:
            maquina = loftar_turbina(rad, replicar=False)
            z_total_cm = maquina.z_total * 100

        # câmber máximo exigiria gerar os perfis (mais caro); aproximado
        # aqui pela deflexão beta2-beta3 do rotor, que domina o câmber
        # final quando delta~0 (aplicar_carter=False na turbina)
        deflexao_max = max(abs(turb.beta2[i] - turb.beta3[i]) for i in range(turb.n_estagios))

        return {
            "valido": True,
            "houve_aviso": houve_aviso or houve_aviso_radial,
            "n_estagios": turb.n_estagios,
            "M2_max": max(turb.M2),
            "M3R_max": max(turb.M3R),
            "reacao_min": min(turb.grau_reacao),
            "reacao_max": max(turb.grau_reacao),
            "deflexao_rotor_max_graus": deflexao_max,
            "Z_rotor_min": min(turb.Z_rotor),
            "Z_rotor_max": max(turb.Z_rotor),
            "corda_min_cm": min(turb.corda_bocal + turb.corda_rotor) * 100,
            "z_total_cm": z_total_cm,
            "erro_pi_pct": abs(turb.pi_total_calc - turb.r_turb) / turb.r_turb * 100,
        }
    except (ValueError, RuntimeError) as e:
        return {"valido": False, "erro": str(e)}


def varrer_parametro(rodar_caso_func, nome_param: str, valores: list) -> list:
    """
    Roda rodar_caso_func({nome_param: v}) para cada v em valores, e
    retorna a lista de resultados (um dict por valor testado), cada um
    com o valor testado anexado sob a chave nome_param.
    """
    resultados = []
    for v in valores:
        r = rodar_caso_func({nome_param: v})
        r[nome_param] = v
        resultados.append(r)
    return resultados


def _valores_com_referencia(valores: list, referencia: float) -> list:
    """Garante que a varredura avalie o ponto exato do caso de referência."""
    valores = list(valores)
    if not any(math.isclose(float(v), float(referencia), rel_tol=0.0, abs_tol=1e-12)
               for v in valores):
        valores.append(referencia)
    return sorted(valores)


def executar_varreduras(caso_referencia: Optional[dict] = None) -> dict:
    """Calcula as curvas ao redor do caso recebido pela interface.

    As métricas usadas nos gráficos vêm dos meanlines. As etapas radiais
    ainda rodam com REF_N_SECOES para preservar os avisos do caso; a opção
    rápida pula apenas o loft CAD, que não altera as métricas plotadas.
    """
    ref_ciclo, _, ref_comp, ref_turb, _, _ = _referencias_ativas(caso_referencia)

    def rodar_comp(overrides):
        return rodar_caso_compressor(
            overrides, caso_referencia=caso_referencia, incluir_loft=False
        )

    def rodar_turb(overrides):
        return rodar_caso_turbina(
            overrides, caso_referencia=caso_referencia, incluir_loft=False
        )

    def rodar_ciclo(overrides):
        return rodar_caso_ciclo(overrides, caso_referencia=caso_referencia)

    return {
        "comp_phi": varrer_parametro(rodar_comp, "phi", _valores_com_referencia(
            [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70], ref_comp["phi"])),
        "comp_psi": varrer_parametro(rodar_comp, "psi", _valores_com_referencia(
            [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50], ref_comp["psi"])),
        "comp_htr": varrer_parametro(rodar_comp, "HTR", _valores_com_referencia(
            [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85], ref_comp["HTR"])),
        "turb_phi": varrer_parametro(rodar_turb, "phi", _valores_com_referencia(
            [0.40, 0.45, 0.50, 0.53, 0.60, 0.65, 0.70], ref_turb["phi"])),
        "turb_psi": varrer_parametro(rodar_turb, "psi", _valores_com_referencia(
            [0.80, 1.00, 1.10, 1.21, 1.40, 1.60, 1.80], ref_turb["psi"])),
        "turb_htr": varrer_parametro(rodar_turb, "HTR", _valores_com_referencia(
            [0.70, 0.75, 0.80, 0.85, 0.90, 0.93, 0.95], ref_turb["HTR"])),
        "ciclo_pi": varrer_parametro(rodar_ciclo, "r_compr", _valores_com_referencia(
            [4, 6, 8, 10, 12, 16, 20], ref_ciclo["r_compr"])),
        "ciclo_tit": varrer_parametro(rodar_ciclo, "TIT", _valores_com_referencia(
            [900, 1000, 1050, 1100, 1150, 1200], ref_ciclo["TIT"])),
    }


def imprimir_varredura(resultados: list, nome_param: str, colunas: list) -> None:
    """Imprime uma tabela simples da varredura, uma linha por valor testado."""
    largura_col = 14
    cabecalho = f"{nome_param:<{largura_col}}" + "".join(f"{c:<{largura_col}}" for c in colunas)
    print(cabecalho)
    print("─" * len(cabecalho))
    for r in resultados:
        if not r["valido"]:
            print(f"{r[nome_param]:<{largura_col}}INVÁLIDO: {r['erro'][:80]}")
            continue
        linha = f"{r[nome_param]:<{largura_col}}"
        for c in colunas:
            val = r.get(c, "-")
            if isinstance(val, float):
                linha += f"{val:<{largura_col}.4f}"
            else:
                linha += f"{str(val):<{largura_col}}"
        print(linha)
    print()


# ══════════════════════════════════════════════════════════════════════════
# GRUPO B — VARREDURA DE CICLO (π_total, TIT) + SFC
# ══════════════════════════════════════════════════════════════════════════

def rodar_caso_ciclo(overrides: dict, caso_referencia: Optional[dict] = None) -> dict:
    """
    Roda o ciclo com o combustor do pipeline para calcular SFC e vazões
    usando o mesmo balanço de massa e energia do caso de referência.
    """
    ref_ciclo, ref_m_dot, _, _, ref_combustor, _ = _referencias_ativas(caso_referencia)
    params = {**ref_ciclo, **overrides}
    try:
        ciclo = CicloBrayton(**params)
        ciclo.resolver()
        ciclo.vazão_mássica_desejada(ref_m_dot)

        with contextlib.redirect_stdout(io.StringIO()):
            combustor = Combustor1D(ciclo=ciclo, **ref_combustor)
            combustor.resolver()
        ciclo.registrar_vazao_turbina(combustor.m_dot_turbina)
        SFC = (ciclo.m_dot_f * 3600) / (ciclo.W_líq / 1000)   # kg/kWh
        indicadores = indicadores_energeticos(ciclo, combustor)

        return {
            "valido": True,
            "eta_ciclo_pct": ciclo.eta_ciclo * 100,
            "eta_calor_util_pct": indicadores["eta_calor_util"] * 100,
            "eta_PCI_pct": indicadores["eta_PCI"] * 100,
            "w_liq_kJ_kg": ciclo.w_líq / 1000,
            "BWR": ciclo.BWR,
            "f": combustor.f,
            "m_dot_ar_kg_s": ciclo.m_dot_ar,
            "m_dot_f_kg_s": ciclo.m_dot_f,
            "m_dot_turbina_kg_s": ciclo.m_dot_turbina,
            "SFC_kg_kWh": SFC,
        }
    except (ValueError, RuntimeError) as e:
        return {"valido": False, "erro": str(e)}


#_______________________________________________________________________________
if __name__ == "__main__":

    print("=" * 100)
    print("GRUPO A — SENSIBILIDADE AERODINÂMICA (COMPRESSOR)")
    print("=" * 100)

    colunas_a = ["n_estagios", "M1R_max", "DF_rotor_max", "reacao_min",
                 "reacao_max", "Z_rotor_min", "corda_min_cm", "houve_aviso"]

    print(f"\n--- φ (phi), referência = {REF_COMP['phi']:g} ---")
    res_phi = varrer_parametro(rodar_caso_compressor, "phi", _valores_com_referencia(
        [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70], REF_COMP["phi"]))
    imprimir_varredura(res_phi, "phi", colunas_a)

    print(f"\n--- ψ (psi), referência = {REF_COMP['psi']:g} ---")
    res_psi = varrer_parametro(rodar_caso_compressor, "psi", _valores_com_referencia(
        [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50], REF_COMP["psi"]))
    imprimir_varredura(res_psi, "psi", colunas_a)

    print(f"\n--- HTR, referência = {REF_COMP['HTR']:g} ---")
    res_htr = varrer_parametro(rodar_caso_compressor, "HTR", _valores_com_referencia(
        [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85], REF_COMP["HTR"]))
    imprimir_varredura(res_htr, "HTR", colunas_a)

    print("\n" + "=" * 100)
    print("GRUPO A — SENSIBILIDADE AERODINÂMICA (TURBINA)")
    print("=" * 100)

    colunas_a_turb = ["n_estagios", "M2_max", "M3R_max", "reacao_min", "reacao_max",
                       "deflexao_rotor_max_graus", "Z_rotor_min", "houve_aviso"]

    print(f"\n--- φ (phi), referência = {REF_TURB['phi']:g} ---")
    res_phi_t = varrer_parametro(rodar_caso_turbina, "phi", _valores_com_referencia(
        [0.40, 0.45, 0.50, 0.53, 0.60, 0.65, 0.70], REF_TURB["phi"]))
    imprimir_varredura(res_phi_t, "phi", colunas_a_turb)

    print(f"\n--- ψ (psi), referência = {REF_TURB['psi']:.6f} ---")
    valores_psi_t = sorted({0.80, 1.00, 1.10, 1.21, 1.40, 1.60, 1.80, REF_TURB["psi"]})
    res_psi_t = varrer_parametro(rodar_caso_turbina, "psi", valores_psi_t)
    imprimir_varredura(res_psi_t, "psi", colunas_a_turb)

    print(f"\n--- HTR, referência = {REF_TURB['HTR']:g} ---")
    res_htr_t = varrer_parametro(rodar_caso_turbina, "HTR", _valores_com_referencia(
        [0.70, 0.75, 0.80, 0.85, 0.90, 0.93, 0.95], REF_TURB["HTR"]))
    imprimir_varredura(res_htr_t, "HTR", colunas_a_turb)

    print("\n" + "=" * 100)
    print("GRUPO B — SENSIBILIDADE DE CICLO")
    print("=" * 100)

    colunas_b = ["eta_ciclo_pct", "w_liq_kJ_kg", "BWR", "SFC_kg_kWh"]

    print(f"\n--- π_total (r_compr), referência = {REF_CICLO['r_compr']:g} ---")
    res_pi = varrer_parametro(rodar_caso_ciclo, "r_compr", _valores_com_referencia(
        [4, 6, 8, 10, 12, 16, 20], REF_CICLO["r_compr"]))
    imprimir_varredura(res_pi, "r_compr", colunas_b)

    print(f"\n--- TIT, referência = {REF_CICLO['TIT']:g} ---")
    res_tit = varrer_parametro(rodar_caso_ciclo, "TIT", _valores_com_referencia(
        [900, 1000, 1050, 1100, 1150, 1200], REF_CICLO["TIT"]))
    imprimir_varredura(res_tit, "TIT", colunas_b)
