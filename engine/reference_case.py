"""Fonte única dos parâmetros do caso de referência usado pela interface e estudos."""

from copy import deepcopy
from typing import Optional

# Unidades SI, exceto onde o nome da chave explicita outra unidade.
REF_CICLO = {
    "T01": 300.0,
    "P01": 100e3,
    "r_compr": 8.0,
    "TIT": 1200.0,
    "e_turb": 0.80,
    "e_compr": 0.85,
    "Delta_P_cc": 0.05,
    "TIT_máx": 1200.0,
    "cp": 1005.0,
    "k": 1.4,
    # Valores do modo PRESCRITO: Saravanamuttoo, exemplo 2.1, p.75.
    # No automático, cp/R/k dos gases são substituídos pela mistura calculada.
    "cp_gases": 1148.0,
    "R_gases": 1005.0 * (1 - 1 / 1.4),
    "mistura_automatica": True,
}

REF_M_DOT = 15.0  # Vazão de ar na entrada do compressor (kg/s)

REF_COMBUSTOR = {
    "combustivel": "JP-4",
    "eta_b": 0.99,
    "M_entrada": 0.05,
}

REF_COMP = {
    "N": 14000.0,
    "HTR": 0.75,
    "n_estagios": 8,
    "phi": 0.50,
    "psi": 0.35,
    "alpha1_graus": 30.0,
    "DF_alvo": 0.45,
    "AR": 2.0,
}

REF_TURB = {
    "N": 14000.0,
    "HTR": 0.90,
    "n_estagios": 3,
    "phi": 0.53,
    "psi": 1.198736,
    "alpha2_graus": 63.5,
    "sigma": 1.0,
    "AR": 2.0,
}

REF_N_SECOES = 7


def montar_caso_referencia(parametros_execucao: Optional[dict] = None) -> dict:
    """Retorna dicionários de referência para os parâmetros de uma execução.

    Sem argumentos, devolve uma cópia dos padrões. Com os parâmetros do
    formulário Streamlit, monta um caso independente para aquela sessão,
    sem alterar as configurações globais nem gravar valores no arquivo .py.
    """
    if parametros_execucao is None:
        return {
            "REF_CICLO": deepcopy(REF_CICLO),
            "REF_COMBUSTOR": deepcopy(REF_COMBUSTOR),
            "REF_M_DOT": REF_M_DOT,
            "REF_COMP": deepcopy(REF_COMP),
            "REF_TURB": deepcopy(REF_TURB),
            "REF_N_SECOES": REF_N_SECOES,
        }

    p = parametros_execucao
    ciclo = {
        **REF_CICLO,
        "T01": p["T01"],
        "P01": p["P01"] * 1e3,
        "r_compr": p["r_compr"],
        "TIT": p["TIT"],
        "e_compr": p["e_compr"],
        "e_turb": p["e_turb"],
        "Delta_P_cc": p["Delta_P_cc"],
        "TIT_máx": p["TIT_max"],
        "cp": p.get("cp_ar", REF_CICLO["cp"]),
        "k": (REF_CICLO['k'] if p.get('mistura_automatica',True) else
              p.get("cp_ar", REF_CICLO["cp"]) / (
            p.get("cp_ar", REF_CICLO["cp"]) - p.get("R_ar", REF_CICLO["cp"] * (1 - 1 / REF_CICLO["k"])))),
        "cp_gases": p.get("cp_gases", REF_CICLO["cp_gases"]),
        "mistura_automatica": p.get("mistura_automatica", True),
        "R_gases": p.get("R_gases", REF_CICLO["R_gases"]),
    }
    combustor = {
        "combustivel": p.get("combustivel", REF_COMBUSTOR["combustivel"]),
        "eta_b": p.get("eta_b", REF_COMBUSTOR["eta_b"]),
        "M_entrada": p.get("M_entrada", REF_COMBUSTOR["M_entrada"]),
    }
    compressor = {
        "N": p["N_comp"],
        "HTR": p["HTR_comp"],
        "n_estagios": p["n_estagios_comp"],
        "phi": p["phi_comp"],
        "psi": p["psi_comp"],
        "alpha1_graus": p["alpha1_comp"],
        "DF_alvo": p["DF_alvo"],
        "AR": p["AR_comp"],
    }
    turbine = {
        "N": p["N_turb"],
        "HTR": p["HTR_turb"],
        "n_estagios": p["n_estagios_turb"],
        "phi": p["phi_turb"],
        "psi": p["psi_turb"],
        "alpha2_graus": p["alpha2_turb"],
        "sigma": p["sigma_turb"],
        "AR": p["AR_turb"],
    }
    return {
        "REF_CICLO": ciclo,
        "REF_COMBUSTOR": combustor,
        "REF_M_DOT": p["m_dot"],
        "REF_COMP": compressor,
        "REF_TURB": turbine,
        "REF_N_SECOES": p["n_secoes"],
    }
