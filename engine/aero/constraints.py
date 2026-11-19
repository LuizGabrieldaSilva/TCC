#______________________________________________________________________________________________________________
# Módulo centralizador de verificações aerodinâmicas de viabilidade para os
# projetos meanline e radial (free vortex) de compressores e turbinas axiais.
#
# Funcionalidade:
#   - Funções puras: recebem valores numéricos + metadados de localização
#     (estágio, seção radial), retornam uma string de aviso ou None.
#   - Sem estado, sem classes — os módulos usam este arquivo por COMPOSIÇÃO
#     (importando e chamando), não por herança.
#   - Funções agregadoras (checar_estagio_*, checar_secao_*) chamam o
#     conjunto de verificações relevante para cada contexto de uma vez só,
#     retornando uma lista (possivelmente vazia) de avisos.
#______________________________________________________________________________________________________________

from typing import Optional, List, Tuple
import math
from engine import design_criteria as dc


# ══════════════════════════════════════════════════════════════════════════
# AUXILIAR DE FORMATAÇÃO
# ══════════════════════════════════════════════════════════════════════════

def _local(estagio: Optional[int], secao: Optional[str]) -> str:
    """Monta o prefixo 'Estágio N [secao]: ' ou 'Estágio N: '."""
    if estagio is None:
        return ""
    txt = f"Estágio {estagio}"
    if secao is not None:
        txt += f" [{secao}]"
    return txt + ": "


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES GENÉRICAS
# ══════════════════════════════════════════════════════════════════════════

def checar_faixa(valor: float,
                 minimo: Optional[float],
                 maximo: Optional[float],
                 descricao: str,
                 motivo: str = "fora de",
                 estagio: Optional[int] = None,
                 secao: Optional[str] = None,
                 fmt: str = ".3f") -> Optional[str]:
    """
    Verifica se "valor" está dentro de [minimo, maximo] (aviso "soft" de
    faixa recomendada). minimo/maximo podem ser None para lado sem limite.
    """
    if math.isnan(valor):
        return (f"{_local(estagio, secao)}{descricao} indefinido (NaN) — "
                "velocidade incompatível com a temperatura total.")
    fora = (minimo is not None and valor < minimo) or \
           (maximo is not None and valor > maximo)
    if not fora:
        return None

    min_txt = f"{minimo}" if minimo is not None else "-∞"
    max_txt = f"{maximo}" if maximo is not None else "+∞"
    return (f"{_local(estagio, secao)}{descricao} = {valor:{fmt}} "
            f"{motivo} [{min_txt}, {max_txt}].")


def checar_limite(valor: float,
                  limite: float,
                  descricao: str,
                  operador: str = ">",
                  motivo: str = "",
                  estagio: Optional[int] = None,
                  secao: Optional[str] = None,
                  fmt: str = ".3f") -> Optional[str]:
    """
    Verifica um limite simples (valor > limite, < limite, >=, <=).
    """
    if math.isnan(valor):
        return (f"{_local(estagio, secao)}{descricao} indefinido (NaN) — "
                "velocidade incompatível com a temperatura total.")
    if operador == ">":
        violado = valor > limite
    elif operador == "<":
        violado = valor < limite
    elif operador == ">=":
        violado = valor >= limite
    elif operador == "<=":
        violado = valor <= limite
    else:
        raise ValueError(f"Operador '{operador}' não suportado.")

    if not violado:
        return None

    sufixo = f" — {motivo}" if motivo else ""
    return (f"{_local(estagio, secao)}{descricao} = {valor:{fmt}} "
            f"{operador} {limite}{sufixo}.")


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES — FATOR DE DIFUSÃO (LIEBLEIN)
# ══════════════════════════════════════════════════════════════════════════

def checar_DF(DF: float,
              nome: str = "DF",
              limite: float = dc.DF_MAX,
              motivo: str = "",
              estagio: Optional[int] = None,
              secao: Optional[str] = None) -> Optional[str]:
    """Triagem empírica de difusão; o valor adotado não prevê toda separação."""
    return checar_limite(
        DF, limite, nome, operador=">",
        motivo=motivo, estagio=estagio, secao=secao,
    )


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES — GRAU DE REAÇÃO
# ══════════════════════════════════════════════════════════════════════════

def checar_grau_reacao(R_c: float,
                       faixa: Tuple[float, float] = dc.REACAO_COMP,
                       descricao: str = "grau de reação",
                       estagio: Optional[int] = None,
                       secao: Optional[str] = None) -> Optional[str]:
    """Compara a reação com a faixa adotada; não é aprovação física."""
    return checar_faixa(
        R_c, faixa[0], faixa[1], descricao,
        motivo="fora de", estagio=estagio, secao=secao,
    )


def checar_grau_reacao_negativo(R_c: float,
                                descricao: str = "grau de reação",
                                contexto: str = "rotor opera em aceleração (não difusor)",
                                estagio: Optional[int] = None,
                                secao: Optional[str] = None) -> Optional[str]:
    """Sinaliza reação negativa; a interpretação depende da definição e fileira."""
    if R_c >= dc.REACAO_MIN:
        return None
    return (f"{_local(estagio, secao)}{descricao} = {R_c:.3f} < {dc.REACAO_MIN:g} "
            f"— {contexto}.")


def checar_grau_reacao_acima_de_um(R_c: float,
                                   descricao: str = "grau de reação",
                                   contexto: str = "estator em aceleração",
                                   estagio: Optional[int] = None,
                                   secao: Optional[str] = None) -> Optional[str]:
    """Sinaliza reação acima de um; não é uma proibição universal de escoamento."""
    if R_c <= dc.REACAO_MAX_TURBINA:
        return None
    return (f"{_local(estagio, secao)}{descricao} = {R_c:.3f} > {dc.REACAO_MAX_TURBINA} "
            f"— {contexto}.")


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES — NÚMERO DE MACH
# ══════════════════════════════════════════════════════════════════════════

def checar_mach(M: float,
                limite: float = dc.MACH_SONICO,
                nome: str = "M",
                motivo: str = "escoamento supersônico",
                estagio: Optional[int] = None,
                secao: Optional[str] = None) -> Optional[str]:
    """Verificação genérica de Mach acima de um limite."""
    return checar_limite(
        M, limite, nome, operador=">",
        motivo=motivo, estagio=estagio, secao=secao,
    )


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÃO — SWIRL RESIDUAL (TURBINA)
# ══════════════════════════════════════════════════════════════════════════

def checar_swirl(v3: float,
                 U: float,
                 limite_frac: float = dc.SWIRL_ESCAPE_MAX,
                 estagio: Optional[int] = None) -> Optional[str]:
    """Swirl residual na saída do rotor excessivo em relação a U."""
    razao = v3 / U
    if abs(razao) <= limite_frac:
        return None
    return (f"{_local(estagio, None)}v3/U = {razao:.3f} — swirl residual "
            f"alto na saída do rotor.")


# ══════════════════════════════════════════════════════════════════════════
# AGREGADORAS — MEANLINE
# ══════════════════════════════════════════════════════════════════════════

def checar_estagio_compressor_meanline(DF_rotor: float,
                                       DF_estator: float,
                                       grau_reacao: float,
                                       M1R: float,
                                       estagio: int) -> List[str]:
    """Conjunto de verificações do compressor no raio médio (meanline)."""
    checagens = [
        checar_DF(DF_rotor, nome="DF_rotor",
                  motivo="risco de separação no rotor", estagio=estagio),
        checar_DF(DF_estator, nome="DF_estator",
                  motivo="risco de separação no estator", estagio=estagio),
        checar_grau_reacao(grau_reacao, faixa=dc.REACAO_COMP, estagio=estagio),
        checar_mach(M1R, limite=dc.MACH_SONICO, nome="M1R",
                    motivo="escoamento supersônico no rotor", estagio=estagio),
    ]
    return [c for c in checagens if c is not None]


def checar_estagio_turbina_meanline(grau_reacao: float,
                                    M2: float,
                                    M3R: float,
                                    v3: float,
                                    U: float,
                                    estagio: int,
                                    verificar_swirl: bool = True) -> List[str]:
    """Triagem meanline; swirl de escape deve ser verificado só no último estágio.

    Os estágios intermediários transferem seu swirl ao bocal seguinte.
    """
    checagens = [
        checar_grau_reacao(grau_reacao, faixa=dc.REACAO_TURB, estagio=estagio),
        checar_mach(M2, limite=dc.MACH_BOCAL_TURBINA, nome="M2",
                    motivo="bocal supersônico — verifique α₂", estagio=estagio),
        checar_mach(M3R, limite=dc.MACH_SONICO, nome="M3R",
                    motivo="saída do rotor supersônica", estagio=estagio),
        checar_swirl(v3, U, limite_frac=dc.SWIRL_ESCAPE_MAX, estagio=estagio) if verificar_swirl else None,
    ]
    return [c for c in checagens if c is not None]


# ══════════════════════════════════════════════════════════════════════════
# AGREGADORAS — RADIAL (FREE VORTEX)
# ══════════════════════════════════════════════════════════════════════════

def checar_secao_compressor_radial(DF_rotor: float,
                                   DF_estator: float,
                                   R_c: float,
                                   M1R: float,
                                   estagio: int,
                                   secao: str) -> List[str]:
    """Conjunto de verificações de uma seção radial (hub/mid/tip) do compressor."""
    checagens = [
        checar_DF(DF_rotor, nome="DF_rotor",
                  motivo="risco de separação no rotor",
                  estagio=estagio, secao=secao),
        checar_DF(DF_estator, nome="DF_estator",
                  motivo="risco de separação no estator",
                  estagio=estagio, secao=secao),
        checar_grau_reacao_negativo(
            R_c, contexto="rotor opera em aceleração (não difusor)",
            estagio=estagio, secao=secao,
        ),
        checar_mach(M1R, limite=dc.MACH_SONICO, nome="M1R",
                    motivo="escoamento supersônico no rotor",
                    estagio=estagio, secao=secao),
    ]
    return [c for c in checagens if c is not None]


def checar_secao_turbina_radial(R_c: float,
                                M2: float,
                                M3R: float,
                                estagio: int,
                                secao: str) -> List[str]:
    """Conjunto de verificações de uma seção radial (hub/mid/tip ou quantas seções houverem) da turbina."""
    checagens = [
        checar_grau_reacao_negativo(
            R_c, descricao="R_c", contexto="aumento de entalpia estática no rotor; revise os triângulos",
            estagio=estagio, secao=secao,
        ),
        checar_grau_reacao_acima_de_um(
            R_c, descricao="R_c",
            contexto="aumento de entalpia estática no bocal; revise os triângulos",
            estagio=estagio, secao=secao,
        ),
        checar_mach(M2, limite=dc.MACH_BOCAL_TURBINA, nome="M2",
                    motivo="bocal supersônico", estagio=estagio, secao=secao),
        checar_mach(M3R, limite=dc.MACH_SONICO, nome="M3R",
                    motivo="saída do rotor supersônica",
                    estagio=estagio, secao=secao),
        checar_grau_reacao(R_c, faixa=dc.REACAO_TURB, descricao="R_c",
                            estagio=estagio, secao=secao),
    ]
    return [c for c in checagens if c is not None]

# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES — COMBUSTOR
# ══════════════════════════════════════════════════════════════════════════

def checar_phi_eq_rica(phi_eq: float,
                       limite: float = dc.PHI_EQ_RICA,
                       contexto: str = "mistura rica. Risco de fuligem e "
                                        "temperaturas excessivas nas paredes") -> Optional[str]:
    """Sinaliza mistura global rica, sem modelo preditivo de fuligem ou chama."""
    if phi_eq <= limite:
        return None
    return f"φ_eq = {phi_eq:.3f} > {limite} — {contexto}."


def checar_phi_eq_pobre(phi_eq: float,
                        limite: float = dc.PHI_EQ_POBRE,
                        contexto: str = "mistura muito pobre. Risco de "
                                         "extinção da chama (flameout)") -> Optional[str]:
    """
    Sinaliza mistura global abaixo do limiar adotado no projeto.
    Não prevê flameout: não há resolução das zonas locais de combustão.
    """
    if phi_eq >= limite:
        return None
    return f"φ_eq = {phi_eq:.3f} < {limite} — {contexto}."


def checar_phi_eq_faixa(phi_eq: float,
                        faixa: Tuple[float, float] = dc.PHI_EQ_COMBUSTOR) -> Optional[str]:
    """Comparação com a faixa global de φ_eq adotada no projeto."""
    return checar_faixa(
        phi_eq, faixa[0], faixa[1], "φ_eq",
        motivo="fora da faixa típica",
    )


def checar_razao_combustivel_ar(f: float,
                                limite: float = dc.COMBUSTIVEL_AR_MAX,
                                motivo: str = "razão combustível/ar alta. "
                                               "Verifique TIT e h_PR") -> Optional[str]:
    """Verificação de razão combustível/ar excessiva."""
    return checar_limite(
        f, limite, "f", operador=">", motivo=motivo, fmt=".4f",
    )


# ══════════════════════════════════════════════════════════════════════════
# AGREGADORA — COMBUSTOR
# ══════════════════════════════════════════════════════════════════════════

def checar_combustor(phi_eq: float, f: float) -> List[str]:
    """Conjunto de verificações do combustor 1D."""
    checagens = [
        checar_phi_eq_rica(phi_eq),
        checar_phi_eq_pobre(phi_eq, limite=dc.PHI_EQ_POBRE),
        checar_phi_eq_faixa(phi_eq, faixa=dc.PHI_EQ_COMBUSTOR),
        checar_razao_combustivel_ar(f, limite=dc.COMBUSTIVEL_AR_MAX),
    ]
    return [c for c in checagens if c is not None]


# ══════════════════════════════════════════════════════════════════════════
# VERIFICAÇÕES — GEOMETRIA DE PÁ (câmber circular)
# ══════════════════════════════════════════════════════════════════════════

def checar_camber_excessivo(theta_final: float,
                             limite: float = dc.CAMBER_COMP_GRAUS,
                             estagio: Optional[int] = None,
                             secao: Optional[str] = None,
                             fileira: Optional[str] = None) -> Optional[str]:
    """
    Câmber circular único fica geometricamente pouco realista para ângulos
    de curvatura muito grandes (perfis reais de alto carregamento usam
    câmber duplo/parabólico deslocado — fora do escopo deste projeto).
    Verificação "soft": apenas alerta, não invalida o resultado.
    """
    local = ""
    if estagio is not None:
        local = f"Estágio {estagio}"
        if fileira is not None:
            local += f" [{fileira}]"
        if secao is not None:
            local += f" ({secao})"
        local += ": "
    if abs(theta_final) <= limite:
        return None
    return (f"{local}θ_final = {theta_final:.2f}° > {limite}° — câmber "
            f"elevado para um único arco circular; considerar câmber "
            f"parabólico deslocado como refinamento futuro.")
