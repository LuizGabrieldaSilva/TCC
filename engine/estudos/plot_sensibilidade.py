#______________________________________________________________________________________________________________
# Plotagem dos resultados de engine.estudos.sensibilidade -- um gráfico por
# métrica de interesse, com a referência de projeto destacada e, quando
# aplicável, a faixa comparativa adotada no projeto sombreada e o critério
# de verificação marcado. M=1 identifica a condição sônica local.
#
# Casos inválidos ou sem métrica ficam como lacunas; não se conectam os
# vizinhos através de uma faixa inviável. As mensagens são exibidas pela interface.
#______________________________________________________________________________________________________________

import os
import math
import matplotlib.pyplot as plt

from engine import design_criteria as dc
from engine.estudos.sensibilidade import (
    REF_CICLO, REF_COMP, REF_TURB,
    executar_varreduras,
)

PASTA_SAIDA = "saida_dxf/graficos_sensibilidade"


def _filtrar_validos(resultados: list, param_nome: str) -> tuple:
    """Retorna (xs, ys_dict_por_metrica) só dos casos válidos."""
    validos = [r for r in resultados if r["valido"]]
    xs = [r[param_nome] for r in validos]
    return xs, validos


def serie_com_lacunas(resultados, param_nome, metrica):
    """Preserva a ordem das amostras e não inventa valores para pontos inválidos."""
    xs=[];ys=[]
    for r in resultados:
        xs.append(r[param_nome]);v=r.get(metrica)
        ys.append(v if r.get('valido',False) and isinstance(v,(int,float)) and math.isfinite(v) else float('nan'))
    return xs,ys


def _marcar_lacunas(ax,xs,series):
    falhas=[x for i,x in enumerate(xs) if any(not math.isfinite(ys[i]) for ys in series)]
    if falhas:
        linha, = ax.plot(falhas,[.04]*len(falhas),'rx',transform=ax.get_xaxis_transform(),
                label='Não calculado/sem métrica (sem valor no eixo y)')
        return linha
    return None


def plot_serie(resultados: list, param_nome: str, metrica: str,
               titulo: str, xlabel: str, ylabel: str, arquivo,
               valor_referencia: float = None,
               faixa_recomendada: tuple = None,
               linha_limite: float = None,
               rotulo_limite: str = None):
    """
    Plot genérico de uma métrica em função de um parâmetro variado.

    faixa_recomendada: (min, max) -- faixa comparativa adotada no projeto.
        O nome do argumento é preservado por compatibilidade; não atribui
        o intervalo a uma referência bibliográfica universal.
    linha_limite: linha de referência/critério de verificação informado.
        M=1 identifica condição sônica; outros critérios dependem do contexto.
    """
    xs, ys = serie_com_lacunas(resultados, param_nome, metrica)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, ys, marker='o', color='C0', linewidth=1.8)
    lacunas = _marcar_lacunas(ax,xs,[ys])

    if faixa_recomendada is not None:
        ax.axhspan(faixa_recomendada[0], faixa_recomendada[1],
                    color='green', alpha=0.12, label='Faixa comparativa (projeto)')

    if linha_limite is not None:
        ax.axhline(linha_limite, color='red', linestyle='--', linewidth=1.2,
                    label=rotulo_limite or f'Critério de verificação = {linha_limite}')

    if valor_referencia is not None:
        idx_ref = next((i for i, x in enumerate(xs)
                        if math.isclose(float(x), float(valor_referencia), rel_tol=0.0, abs_tol=1e-12)), None)
        if idx_ref is not None and math.isfinite(ys[idx_ref]):
            ax.plot(xs[idx_ref], ys[idx_ref], marker='*', color='orange', markersize=16,
                    zorder=5, label='Caso de referência')

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.grid(alpha=0.3)
    if faixa_recomendada is not None or linha_limite is not None or valor_referencia is not None or lacunas:
        ax.legend(fontsize=8)

    fig.tight_layout()
    if arquivo is not None:
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        caminho = os.path.join(PASTA_SAIDA, arquivo)
        fig.savefig(caminho, dpi=150)
        plt.close(fig)
        print(f"Salvo: {caminho}")
        return None
    return fig


def plot_duplo_eixo(resultados: list, param_nome: str,
                    metrica_esq: str, metrica_dir: str,
                    titulo: str, xlabel: str,
                    ylabel_esq: str, ylabel_dir: str,
                    arquivo, valor_referencia: float = None):
    """Plot com dois eixos y (esq/dir), útil para w_líq × η_ciclo vs π_total."""
    xs, y_esq = serie_com_lacunas(resultados, param_nome, metrica_esq)
    _, y_dir = serie_com_lacunas(resultados, param_nome, metrica_dir)

    fig, ax1 = plt.subplots(figsize=(7.5, 4.5))
    ax2 = ax1.twinx()

    l1, = ax1.plot(xs, y_esq, marker='o', color='C0', linewidth=1.8, label=ylabel_esq)
    l2, = ax2.plot(xs, y_dir, marker='s', color='C3', linewidth=1.8, label=ylabel_dir)
    lacunas = _marcar_lacunas(ax1,xs,[y_esq,y_dir])
    linha_referencia = None

    if valor_referencia is not None:
        idx = next((i for i, x in enumerate(xs)
                    if math.isclose(float(x), float(valor_referencia), rel_tol=0.0, abs_tol=1e-12)), None)
        if idx is not None:
            linha_referencia = ax1.axvline(
                valor_referencia, color='gray', linestyle=':', linewidth=1,
                label='Caso de referência',
            )

    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel_esq, color='C0')
    ax2.set_ylabel(ylabel_dir, color='C3')
    ax1.tick_params(axis='y', labelcolor='C0')
    ax2.tick_params(axis='y', labelcolor='C3')
    ax1.set_title(titulo)
    ax1.grid(alpha=0.3)
    handles = [l1, l2] + ([linha_referencia] if linha_referencia is not None else [])
    if lacunas:handles.append(lacunas)
    ax1.legend(handles=handles, fontsize=8, loc='best')

    fig.tight_layout()
    if arquivo is not None:
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        caminho = os.path.join(PASTA_SAIDA, arquivo)
        fig.savefig(caminho, dpi=150)
        plt.close(fig)
        print(f"Salvo: {caminho}")
        return None
    return fig


#_______________________________________________________________________________
if __name__ == "__main__":

    # ══════════════════════════════════════════════════════════════════
    # Recalcula as varreduras em torno do caso de referência vigente.
    # ══════════════════════════════════════════════════════════════════
    res = executar_varreduras()
    res_phi, res_psi, res_htr = res["comp_phi"], res["comp_psi"], res["comp_htr"]
    res_phi_t, res_psi_t, res_htr_t = res["turb_phi"], res["turb_psi"], res["turb_htr"]
    res_pi, res_tit = res["ciclo_pi"], res["ciclo_tit"]

    # ══════════════════════════════════════════════════════════════════
    # COMPRESSOR
    # ══════════════════════════════════════════════════════════════════
    plot_serie(res_phi, "phi", "DF_rotor_max",
                "Compressor: DF_rotor máximo vs φ (triagem pelo critério de Lieblein)",
                "φ", "DF_rotor máximo", "compressor_DF_vs_phi.png",
                valor_referencia=REF_COMP["phi"], linha_limite=dc.DF_MAX, rotulo_limite=f"Critério de difusão (DF={dc.DF_MAX:g})")

    plot_serie(res_phi, "phi", "reacao_min",
                "Compressor: grau de reação mínimo vs φ",
                "φ", "Grau de reação (mínimo, hub)", "compressor_reacao_vs_phi.png",
                valor_referencia=REF_COMP["phi"], faixa_recomendada=dc.REACAO_COMP)

    plot_serie(res_htr, "HTR", "M1R_max",
                "Compressor: Mach relativo máximo (M1R) vs HTR de entrada",
                "HTR de entrada (hub/tip)", "M1R máximo", "compressor_M1R_vs_HTR.png",
                valor_referencia=REF_COMP["HTR"], linha_limite=dc.MACH_SONICO, rotulo_limite=f"Limite sônico (M={dc.MACH_SONICO:g})")

    plot_serie(res_psi, "psi", "Z_rotor_min",
                "Compressor: número mínimo de pás do rotor vs ψ",
                "ψ", "Z_rotor (mínimo entre estágios)", "compressor_Z_vs_psi.png",
                valor_referencia=REF_COMP["psi"])

    # ══════════════════════════════════════════════════════════════════
    # TURBINA
    # ══════════════════════════════════════════════════════════════════
    plot_serie(res_psi_t, "psi", "M3R_max",
                "Turbina: Mach relativo máximo na saída do rotor (M3R) vs ψ",
                "ψ", "M3R máximo", "turbina_M3R_vs_psi.png",
                valor_referencia=REF_TURB["psi"], linha_limite=dc.MACH_SONICO, rotulo_limite=f"Limite sônico (M={dc.MACH_SONICO:g})")

    plot_serie(res_htr_t, "HTR", "M3R_max",
                "Turbina: Mach relativo máximo na saída do rotor (M3R) vs HTR de entrada",
                "HTR de entrada (hub/tip)", "M3R máximo", "turbina_M3R_vs_HTR.png",
                valor_referencia=REF_TURB["HTR"], linha_limite=dc.MACH_SONICO, rotulo_limite=f"Limite sônico (M={dc.MACH_SONICO:g})")

    plot_serie(res_psi_t, "psi", "reacao_min",
                "Turbina: grau de reação vs ψ",
                "ψ", "Grau de reação", "turbina_reacao_vs_psi.png",
                valor_referencia=REF_TURB["psi"], faixa_recomendada=dc.REACAO_TURB)

    plot_serie(res_phi_t, "phi", "deflexao_rotor_max_graus",
                "Turbina: deflexão máxima do rotor vs φ",
                "φ", "Deflexão do rotor (°)", "turbina_deflexao_vs_phi.png",
                valor_referencia=REF_TURB["phi"])

    # ══════════════════════════════════════════════════════════════════
    # CICLO (comparação com teoria clássica — Saravanamuttoo Cap. 2)
    # ══════════════════════════════════════════════════════════════════
    plot_duplo_eixo(res_pi, "r_compr", "w_liq_kJ_kg", "eta_ciclo_pct",
                      "Ciclo: trabalho específico e eficiência vs π_total\n"
                      "(picos em razões de pressão distintas — resultado clássico)",
                      "π_total (razão de pressão do compressor)",
                      "w_líq (kJ/kg de ar)", "η sobre calor útil (%)",
                      "ciclo_wliq_eta_vs_pi.png", valor_referencia=REF_CICLO["r_compr"])

    plot_serie(res_pi, "r_compr", "SFC_kg_kWh",
                "Ciclo: SFC vs π_total",
                "π_total", "SFC (kg/kWh)", "ciclo_SFC_vs_pi.png",
                valor_referencia=REF_CICLO["r_compr"])

    plot_duplo_eixo(res_tit, "TIT", "w_liq_kJ_kg", "eta_ciclo_pct",
                      "Ciclo: trabalho específico e eficiência vs TIT",
                      "TIT (K)", "w_líq (kJ/kg de ar)", "η sobre calor útil (%)",
                      "ciclo_wliq_eta_vs_TIT.png", valor_referencia=REF_CICLO["TIT"])

    plot_serie(res_tit, "TIT", "SFC_kg_kWh",
                "Ciclo: SFC vs TIT",
                "TIT (K)", "SFC (kg/kWh)", "ciclo_SFC_vs_TIT.png",
                valor_referencia=REF_CICLO["TIT"])

    print(f"\nTodos os gráficos salvos em: {PASTA_SAIDA}/")
