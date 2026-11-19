"""Limites adotados no projeto, compartilhados por avisos e apresentações.

Não são limites universais nem validação física. Os chamadores preservam o
contexto: reação comparativa do compressor só no meanline; swirl apenas no
escape da turbina. Domínios matemáticos de entrada ficam em input_validation.
As constantes são imutáveis; mudar um limite exige revisão e autorização.
"""

MACH_SONICO = 1.0
MACH_BOCAL_TURBINA = 1.3
DF_MAX = 0.6
REACAO_MIN = 0.0
REACAO_MAX_TURBINA = 1.0
REACAO_COMP = (0.4, 0.6)
REACAO_TURB = (0.3, 0.7)
PSI_COMP = (0.3, 0.6)
PSI_TURB = (1.0, 2.5)
CAMBER_COMP_GRAUS = 60.0
CAMBER_TURB_GRAUS = 90.0
SWIRL_ESCAPE_MAX = 0.15

# Orientações de entrada; não participam da classificação de candidatos.
HTR_COMP = (0.3, 0.9)
HTR_TURB = (0.5, 0.95)
PHI_MAQUINAS = (0.4, 0.7)
DF_ALVO_COMP = (0.35, 0.55)
ESPESSURA_RELATIVA_AVISO = 0.25
ETA_COMBUSTOR = (0.90, 1.00)
MACH_ENTRADA_COMBUSTOR_AVISO = 0.10
PHI_EQ_RICA = 1.0
PHI_EQ_POBRE = 0.2
PHI_EQ_COMBUSTOR = (0.2, 0.7)
COMBUSTIVEL_AR_MAX = 0.08

# Percentual de emissão de avisos versus tolerâncias de coincidência numérica
# (nas unidades SI). Não confundir esses três valores com tolerância de projeto.
FECHAMENTO_AVISO_PCT = 2.0
COINCIDENCIA_RTOL = 1e-9
COINCIDENCIA_ATOL = 1e-7


def limites_componente(compressor):
    """(faixa de ψ, faixa de reação, limite de câmber em graus)."""
    return ((PSI_COMP, REACAO_COMP, CAMBER_COMP_GRAUS) if compressor else
            (PSI_TURB, REACAO_TURB, CAMBER_TURB_GRAUS))
