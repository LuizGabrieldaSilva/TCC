import csv
import os
from engine.diagnosticos import diagnosticar_maquina

#______________________________________________________________________________________________________________
# Exportação de parâmetros de projeto (meanline + radial) para CSV, um
# arquivo por máquina (compressor / turbina). Formato "long": uma linha
# por (estágio, seção radial), com colunas para ambas as fileiras da
# máquina (rotor+estator no compressor; bocal+rotor na turbina).
#
# Uso pretendido: conferência numérica em planilha (Excel, pandas), NÃO
# reconstrução de geometria -- para isso, usar export_dxf.py ou
# export_freecad_macro.py. CSV não carrega topologia/curvas, só escalares.
#
# Corda e Z são constantes por fileira/estágio. Solidez local = Z*c/(2πr).
# As colunas antigas sigma_rotor/sigma_estator mantêm a referência meanline;
# colunas adicionais explicitam a solidez local usada pelo radial/perfis.
# gamma_* continua sendo média de ângulos de ESCOAMENTO, não stagger metálico.
#______________________________________________________________________________________________________________


def csv_compressor(comp, rad_comp, caminho: str) -> str:
    """
    Exporta os parâmetros do compressor (meanline + radial) para CSV.

    PARÂMETROS:
        comp     - Objeto CompressorMeanline já resolvido (resolver() chamado)
        rad_comp - Objeto RadialCompressor já resolvido (resolver() chamado)
        caminho  - Caminho do arquivo .csv de saída

    RETORNA: o caminho do arquivo escrito.
    """
    if comp.Tt_saida[0] is None:
        raise RuntimeError("CompressorMeanline.resolver() deve ser chamado antes de exportar.")
    if rad_comp.r[0]["hub"] is None:
        raise RuntimeError("RadialCompressor.resolver() deve ser chamado antes de exportar.")
    areas = diagnosticar_maquina(comp, "Compressor")["estagios"]

    colunas = [
        "estagio", "secao", "cp_J_kg_K", "k", "R_J_kg_K",
        "Tt_entrada_K", "Pt_entrada_kPa", "Tt_saida_K", "Pt_saida_kPa", "pi_estagio",
        "r_cm", "U_m_s",
        "v1_m_s", "v2_m_s", "V1_m_s", "V2_m_s", "W1_m_s", "W2_m_s",
        "alpha1_deg", "alpha2_deg", "beta1_deg", "beta2_deg",
        "gamma_rotor_deg", "gamma_estator_deg",
        "M1", "M1R",
        "DF_rotor", "DF_estator", "grau_reacao_local",
        "r_hub_est_cm", "r_tip_est_cm", "h_pa_cm", "A_estagio_cm2",
        "corda_rotor_cm", "corda_estator_cm",
        "Z_rotor", "Z_estator",
        "sigma_rotor", "sigma_estator",
        "r_mean_aritmetico_cm", "HTR_entrada", "HTR_estagio",
        "sigma_rotor_local", "sigma_estator_local",
        "A_saida_meanline_cm2", "Pt2_kPa", "A2_cm2", "estacao2_status",
    ]

    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(colunas)

        for i in range(comp.n_estagios):
            for s in rad_comp.secoes:
                writer.writerow([
                    i + 1, s, comp.cp, comp.k, comp.R,
                    round(comp.Tt_entrada[i], 3), round(comp.Pt_entrada[i] / 1e3, 3),
                    round(comp.Tt_saida[i], 3), round(comp.Pt_saida[i] / 1e3, 3),
                    round(comp.pi_estagio[i], 5),
                    round(rad_comp.r[i][s] * 100, 4), round(rad_comp.U_r[i][s], 3),
                    round(rad_comp.v1[i][s], 3), round(rad_comp.v2[i][s], 3),
                    round(rad_comp.V1[i][s], 3), round(rad_comp.V2[i][s], 3),
                    round(rad_comp.W1[i][s], 3), round(rad_comp.W2[i][s], 3),
                    round(rad_comp.alpha1[i][s], 3), round(rad_comp.alpha2[i][s], 3),
                    round(rad_comp.beta1[i][s], 3), round(rad_comp.beta2[i][s], 3),
                    round(rad_comp.gamma_rotor[i][s], 3), round(rad_comp.gamma_estator[i][s], 3),
                    round(rad_comp.M1[i][s], 4), round(rad_comp.M1R[i][s], 4),
                    round(rad_comp.DF_rotor[i][s], 4), round(rad_comp.DF_estator[i][s], 4),
                    round(rad_comp.R_c[i][s], 4),
                    round(comp.r_hub_est[i] * 100, 4), round(comp.r_tip_est[i] * 100, 4),
                    round(comp.h_pa[i] * 100, 4), round(comp.A_estagio[i] * 1e4, 4),
                    round(comp.corda_rotor[i] * 100, 4), round(comp.corda_estator[i] * 100, 4),
                    comp.Z_rotor[i], comp.Z_estator[i],
                    round(comp.sigma_rotor[i], 5), round(comp.sigma_estator[i], 5),
                    round(comp.r_mean * 100, 5), comp.HTR, round(comp.HTR_estagio[i], 6),
                    round(rad_comp.sigma_rotor_local[i][s], 6),
                    round(rad_comp.sigma_estator_local[i][s], 6),
                    round(areas[i]["planos"]["3"]["area_m2"] * 1e4, 6),
                    None, None, "nao_determinada_sem_reparticao_perdas",
                ])

    return caminho


def csv_turbina(turb, rad_turb, caminho: str) -> str:
    """
    Exporta os parâmetros da turbina (meanline + radial) para CSV.
    Ver docstring de csv_compressor() para o formato geral.
    grau_reacao_local é a razão estática rotor/estágio; a razão
    rotor/trabalho de eixo é exportada separadamente como diagnóstico.
    """
    if turb.Tt_saida[0] is None:
        raise RuntimeError("TurbinaAxialMeanline.resolver() deve ser chamado antes de exportar.")
    if rad_turb.r[0]["hub"] is None:
        raise RuntimeError("RadialTurbina.resolver() deve ser chamado antes de exportar.")

    colunas = [
        "estagio", "secao",
        "cp_J_kg_K", "k", "R_J_kg_K",
        "Tt_entrada_K", "Pt_entrada_kPa", "Tt_saida_K", "Pt_saida_kPa", "pi_estagio",
        "r_cm", "U_m_s",
        "v1_m_s", "v2_m_s", "v3_m_s", "V1_m_s", "V2_m_s", "V3_m_s", "W2_m_s", "W3_m_s",
        "alpha1_deg", "alpha2_deg", "alpha3_deg", "beta2_deg", "beta3_deg",
        "gamma_bocal_deg", "gamma_rotor_deg",
        "M1", "M2", "M2R", "M3", "M3R",
        "grau_reacao_local",
        "r_hub_est_cm", "r_tip_est_cm", "h_pa_cm", "A_estagio_cm2",
        "corda_bocal_cm", "corda_rotor_cm",
        "Z_bocal", "Z_rotor",
        "r_mean_aritmetico_cm", "HTR_entrada", "HTR_estagio",
        "sigma_alvo_meanline", "sigma_bocal_local", "sigma_rotor_local",
        "reacao_estatica_meanline", "rotor_por_trabalho_local",
        "queda_h_estatica_rotor_local_J_kg", "queda_h_estatica_estagio_local_J_kg",
        "A_saida_meanline_cm2",
        "Pt2_kPa", "A2_cm2", "estacao2_status",
    ]

    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(colunas)

        for i in range(turb.n_estagios):
            for s in rad_turb.secoes:
                writer.writerow([
                    i + 1, s, turb.cp, turb.k, turb.R,
                    round(turb.Tt_entrada[i], 3), round(turb.Pt_entrada[i] / 1e3, 3),
                    round(turb.Tt_saida[i], 3), round(turb.Pt_saida[i] / 1e3, 3),
                    round(turb.pi_estagio[i], 5),
                    round(rad_turb.r[i][s] * 100, 4), round(rad_turb.U_r[i][s], 3),
                    round(rad_turb.v1[i][s], 3), round(rad_turb.v2[i][s], 3), round(rad_turb.v3[i][s], 3),
                    round(rad_turb.V1[i][s], 3), round(rad_turb.V2[i][s], 3), round(rad_turb.V3[i][s], 3),
                    round(rad_turb.W2[i][s], 3), round(rad_turb.W3[i][s], 3),
                    round(rad_turb.alpha1[i][s], 3), round(rad_turb.alpha2[i][s], 3), round(rad_turb.alpha3[i][s], 3),
                    round(rad_turb.beta2[i][s], 3), round(rad_turb.beta3[i][s], 3),
                    round(rad_turb.gamma_bocal[i][s], 3), round(rad_turb.gamma_rotor[i][s], 3),
                    round(rad_turb.M1[i][s], 4), round(rad_turb.M2[i][s], 4), round(rad_turb.M2R[i][s], 4),
                    round(rad_turb.M3[i][s], 4), round(rad_turb.M3R[i][s], 4),
                    round(rad_turb.R_c[i][s], 4),
                    round(turb.r_hub_est[i] * 100, 4), round(turb.r_tip_est[i] * 100, 4),
                    round(turb.h_pa[i] * 100, 4), round(turb.A_estagio[i] * 1e4, 4),
                    round(turb.corda_bocal[i] * 100, 4), round(turb.corda_rotor[i] * 100, 4),
                    turb.Z_bocal[i], turb.Z_rotor[i],
                    round(turb.r_mean * 100, 5), turb.HTR, round(turb.HTR_estagio[i], 6),
                    turb.sigma, round(rad_turb.sigma_bocal_local[i][s], 6),
                    round(rad_turb.sigma_rotor_local[i][s], 6),
                    round(turb.grau_reacao[i], 6),
                    round(rad_turb.reacao_rotor_por_trabalho[i][s], 6),
                    round(rad_turb.queda_h_estatica_rotor[i][s], 6),
                    round(rad_turb.queda_h_estatica_estagio[i][s], 6),
                    round(turb.A_saida_estagio[i] * 1e4, 6),
                    None, None, "nao_determinada_sem_reparticao_perdas",
                ])

    return caminho
