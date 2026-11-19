#______________________________________________________________________________________________________________
# Interface web (MVP) para o pipeline de projeto preliminar de turbina a
# gás axial. Camada de INTERFACE apenas -- nenhuma lógica física nova é
# implementada aqui; o módulo só instancia as classes já existentes
# (engine.ciclo, engine.compressor, engine.turbina, engine.aero,
# engine.geometry, engine.cad, engine.estudos) com os parâmetros
# informados pelo usuário no formulário, e exibe os resultados já
# calculados por elas. Respeita o princípio "core físico separado da
# interface" (ver documento de especificação do orientador).
#
# Como rodar (a partir de NEW, mesma convenção de
# `python -m engine.pasta.arquivo` já usada no resto do projeto):
#
#     python -m streamlit run engine/webapp/streamlit_app.py
#
# Instalação e dependências completas: NEW/README.md e NEW/requirements.txt.
# FreeCAD é opcional e executa as macros em seu próprio interpretador.
#
# ══════════════════════════════════════════════════════════════════════════
# ESCOPO DESTA VERSÃO (MVP):
#   - Formulário com os parâmetros de ciclo + combustor + compressor + turbina
#   - Roda o pipeline completo (ciclo -> compressor -> combustor -> turbina -> radial -> perfis -> loft)
#   - Exibe, por estágio: tabela de parâmetros (seção a seção) + imagem
#     estática (matplotlib) das duas fileiras de pá daquele estágio
#   - Download de CSV (parâmetros) e DXF (geometria, zipado)
#
# NÃO incluído nesta versão (possível trabalho futuro):
#   - Exportação STEP (ver limitação documentada em export_freecad_macro.py)
# Seleção automática de estágios, diagramas e montagem 3D interativa já existem.
# ══════════════════════════════════════════════════════════════════════════

import os
import io
import json
import math
import html
import zipfile
import tempfile
import contextlib
import re
import hashlib
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 -- necessário para projection='3d'

import sys
#______________________________________________________________________________________________________________
# Garante que a pasta raiz do projeto (que contém o pacote `engine`) esteja
# no sys.path. Necessário porque `streamlit run` executa este arquivo como
# script standalone, colocando apenas a pasta deste arquivo (engine/webapp/)
# no caminho de busca -- diferente da convenção `python -m engine.pasta.x`
# usada no resto do projeto, que já resolve isso automaticamente.
_RAIZ_PROJETO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)
#______________________________________________________________________________________________________________


from engine.webapp.number_format import formato_br, tabela_br, figura_br, grafico_br, aviso_br
from engine.ciclo.CicloBrayton import CicloBrayton
from engine import design_criteria as dc
from engine.diagnosticos import diagnosticar_integracao
from engine.webapp.energy_indicators import exibir_indicadores, exibir_origem_criterios, _numero_br
from engine.webapp.energy_balance import exibir_balanco_energetico
from engine.webapp.reading_mode import escolher_modo, exibir_guia, orientacao_formulario, interpretar_ciclo
from engine.webapp.download_guidance import exibir_formatos, exibir_selecao_cad, zip_arquivos
from engine.webapp.verification_overview import exibir_consolidado
from engine.webapp.case_comparison import exibir_comparacao
from engine.webapp.assembly_3d import exibir_montagem
from engine.webapp.sensitivity_context import exibir_contexto_sensibilidade
from engine.webapp.case_io import parametros_dos_campos, contexto_modelo
from engine.webapp.case_reproducibility import (
    exibir_importacao, exibir_salvar_rascunho, exibir_pendencias, exibir_relatorio,
)
from engine.webapp.blade_profile import exibir_perfil_2d
from engine.webapp.stage_selection_details import tabela_criterios, tabela_localizacao, nome_criterio
from engine.webapp.stage_overview import exibir_comparacao_estagios
from engine.webapp.radial_distribution import exibir_distribuicao_radial
from engine.webapp.cycle_diagrams import exibir_visao_ciclo
from engine.webapp.velocity_triangles import exibir_triangulos
from engine.compressor.Compressor_Meanline_main import CompressorMeanline
from engine.combustor.Combustor_1D_2_main import (
    Combustor1D, COMBUSTOR_REF, COMBUSTIVEIS,
)
from engine.turbina.Turbine_Meanline_main import TurbinaAxialMeanline
from engine.aero.radial_compressor_4_main import RadialCompressor
from engine.aero.radial_turbina_3_main import RadialTurbina
from engine.geometry.airfoil4 import gerar_perfis_compressor, gerar_perfis_turbina
from engine.geometry.loft2 import loftar_compressor, loftar_turbina
from engine.cad.export_dxf import exportar_maquina_dxf
from engine.estudos.export_csv import csv_compressor, csv_turbina
from engine.estudos.sensibilidade import executar_varreduras
from engine.estudos.plot_sensibilidade import plot_serie, plot_duplo_eixo
from engine.reference_case import (
    REF_CICLO, REF_M_DOT, REF_COMP, REF_TURB, REF_COMBUSTOR, REF_N_SECOES,
    montar_caso_referencia,
)


st.set_page_config(page_title="TCC — Projeto Preliminar de Turbina Axial", layout="wide")


# ══════════════════════════════════════════════════════════════════════════
# AUXILIARES — CAPTURA DE AVISOS E EXECUÇÃO DO PIPELINE
# ══════════════════════════════════════════════════════════════════════════

def _capturar_stdout(func, *args, **kwargs):
    """
    Executa func(*args, **kwargs) capturando tudo que for impresso em
    stdout (os avisos de aero/constraints.py e o de câmber excessivo em
    geometry/airfoil4.py são via print(), não valor de retorno). Retorna
    (resultado, texto_capturado).
    """
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        resultado = func(*args, **kwargs)
    return resultado, buffer.getvalue()


def _extrair_avisos(texto: str, componente: str, origem: str) -> list[dict]:
    """Converte as mensagens de aviso impressas pelos módulos em registros localizáveis."""
    registros = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or "AVISOS" in linha.upper():
            continue

        if "AVISO:" in linha:
            mensagem = linha.split("AVISO:", 1)[1].strip()
        elif linha.startswith("•"):
            mensagem = linha.lstrip("•").strip()
        elif linha.startswith("⚠") and "Estágio" in linha:
            mensagem = linha.lstrip("⚠").strip()
        else:
            continue

        achado_estagio = re.search(r"Est[aá]gio\s+(\d+)", mensagem, flags=re.IGNORECASE)
        estagio = achado_estagio.group(1) if achado_estagio else None
        secao = None
        fileira = None
        achado_local = re.search(
            r"(?:\[|\()\s*(hub|mid|tip|r\d+)\s*(?:\]|\))",
            mensagem,
            flags=re.IGNORECASE,
        )
        if achado_local:
            secao = achado_local.group(1).lower()
        achado_fileira = re.search(r"\[(rotor|estator|bocal)\]", mensagem, flags=re.IGNORECASE)
        if achado_fileira:
            fileira = achado_fileira.group(1).lower()

        registros.append({
            "componente": componente,
            "origem": origem,
            "estagio": estagio,
            "secao": secao,
            "fileira": fileira,
            "mensagem": mensagem,
        })
        identidade = "\0".join(str(registros[-1][campo] or "") for campo in (
            "componente", "origem", "estagio", "secao", "fileira", "mensagem",
        ))
        registros[-1]["_aviso_id"] = hashlib.sha256(
            identidade.encode("utf-8")
        ).hexdigest()[:20]
    return registros


def _classificar_aviso(mensagem: str) -> tuple[str, str]:
    """Fornece uma leitura didática sem mudar a classificação do modelo."""
    texto = mensagem.casefold()
    if "difere" in texto and "ciclo" in texto:
        criterio = f"Aviso de fechamento emitido para desvio relativo acima de {formato_br(dc.FECHAMENTO_AVISO_PCT, f'g')}%; a mensagem contém o desvio calculado."
    elif "diferença de" in texto and "estágio" in texto:
        criterio = "Aviso emitido quando a diferença entre quantidade estimada e adotada excede 1 estágio."
    elif "fora da faixa" in texto or "fora de [" in texto or "faixa típica" in texto:
        criterio = "Faixa de comparação ou orientação adotada na ferramenta; não implica reprovação automática."
    elif re.search(r"\s[<>]=?\s", mensagem):
        criterio = "Limite de verificação; operador e valor-limite aparecem na mensagem."
    else:
        criterio = "Observação do modelo; consulte a mensagem para o critério mencionado."

    if "df_rotor" in texto or "df_estator" in texto:
        interpretacao = "O fator de difusão ultrapassou o critério registrado; isso sinaliza risco aerodinâmico, como separação e aumento de perdas."
    elif any(mach in texto for mach in ("m1r", "m2", "m3r")):
        interpretacao = "O Mach local excedeu o limite dessa verificação; revise a estação e o triângulo de velocidades correspondente."
    elif "aumento de entalpia estática" in texto:
        interpretacao = "Para a definição estática de reação, a mensagem indica uma fileira com aumento de entalpia estática. Revise a distribuição de carga; o aviso não é uma proibição universal desse escoamento."
    elif "grau de reação" in texto or "r_c" in texto:
        if "< 0" in texto or "> 1.0" in texto:
            interpretacao = "A reação cruzou um limiar de verificação. No compressor, reação negativa indica rotor em aceleração; revise a definição e a distribuição de carga. O valor isolado não é uma proibição física universal."
        else:
            interpretacao = "A reação está fora da faixa comparativa adotada; a faixa é um critério de projeto, não uma validação completa."
    elif "swirl residual" in texto:
        interpretacao = "A velocidade tangencial residual na saída excedeu o limite relativo à velocidade periférica."
    elif "saída calculada" in texto or "π_total calculado" in texto:
        interpretacao = "O desvio entre meanline e ciclo ultrapassou o limiar de emissão de aviso. Esse limiar não é a tolerância de coincidência numérica nem uma tolerância de projeto."
    elif "φ_eq" in mensagem or "\u03c6_eq" in texto:
        if "> 1" in texto:
            interpretacao = "A mistura global foi sinalizada como rica. O modelo não calcula fuligem, temperatura das paredes ou distribuição local da mistura."
        elif "< 0.2" in texto:
            interpretacao = "A mistura global ficou abaixo do limiar adotado. Isso não prevê extinção da chama: o modelo não resolve as zonas locais de combustão."
        else:
            interpretacao = "A razão de equivalência global está fora da faixa comparativa adotada; não é um critério completo de estabilidade da chama."
    elif "m_entrada" in texto:
        interpretacao = "O Mach prescrito excede a orientação contextual usada pelo modelo para a entrada do combustor."
    elif "η_b" in mensagem:
        interpretacao = "A eficiência de combustão saiu da faixa de entrada/aviso adotada na interface."
    elif re.search(r"\bf\s*=", mensagem):
        interpretacao = "A razão combustível/ar excedeu o limite configurado pelo verificador do combustor."
    elif "θ_final" in mensagem or "t/c" in texto:
        interpretacao = "A geometria do perfil acionou um aviso da aproximação geométrica; isso não invalida automaticamente o cálculo do ciclo."
    elif "htr" in texto or "ψ =" in mensagem or "φ =" in mensagem or "df_alvo" in texto:
        interpretacao = "Um parâmetro está fora do intervalo de orientação adotado na ferramenta; consulte a origem e o domínio de aplicação antes de interpretar o resultado."
    elif "diferença de" in texto and "estágio" in texto:
        interpretacao = "O número de estágios escolhido difere da estimativa baseada na carga informada."
    else:
        interpretacao = "O módulo emitiu esta observação; leia a mensagem original e considere as hipóteses do componente."
    return criterio, interpretacao


def _tabela_avisos_selecionavel(container, avisos: list[dict], chave: str) -> None:
    """Mostra avisos e os detalhes do critério da linha selecionada."""
    linhas = []
    detalhes_por_id = {}
    mensagens_por_id = {}
    for aviso in avisos:
        if aviso["componente"] in {"Sistema", "Ciclo"}:
            local = "Global (ciclo/sistema)"
        else:
            local = (
                f"Estágio {aviso['estagio']}" if aviso["estagio"]
                else "Geral (sem estágio específico)"
            )
            if aviso["fileira"]:
                local += f" · {aviso['fileira']}"
            if aviso["secao"]:
                local += f" · seção {aviso['secao']}"

        criterio, interpretacao = _classificar_aviso(aviso["mensagem"])
        aviso_id = aviso["_aviso_id"]
        linhas.append({
            "_aviso_id": aviso_id,
            "Origem": aviso["origem"],
            "Localização": local,
            "Aviso e valor/limite": aviso["mensagem"],
        })
        detalhes_por_id[aviso_id] = {
            "Tipo de critério": criterio,
            "Interpretação": interpretacao,
        }
        mensagens_por_id[aviso_id] = aviso["mensagem"]

    tabela = pd.DataFrame(linhas).reset_index(drop=True)
    ids_visiveis = "|".join(tabela["_aviso_id"].astype(str))
    chave_tabela = hashlib.sha256(ids_visiveis.encode("utf-8")).hexdigest()[:12]
    container.caption(
        "Dica: clique no aviso cortado para selecioná-lo. Se necessário, clique nele "
        "novamente; a mensagem completa aparece no quadro abaixo."
    )
    evento = container.dataframe(
        tabela_br(tabela),
        width="stretch",
        hide_index=True,
        column_config={"_aviso_id": None},
        on_select="rerun",
        selection_mode="single-row",
        key=f"avisos_{chave}_{chave_tabela}",
    )

    linhas_selecionadas = evento.selection.rows
    if linhas_selecionadas:
        # O índice retornado é posicional na tabela exibida. Recuperamos o ID
        # dessa linha e buscamos os detalhes por ID, nunca pela posição global.
        aviso_id = tabela.iloc[linhas_selecionadas[0]]["_aviso_id"]
        aviso_completo = container.container(
            width=1000,
            border=True,
            key=f"aviso_completo_{chave}_{aviso_id}",
        )
        aviso_completo.markdown("**Aviso completo selecionado**")
        aviso_completo.write(aviso_br(mensagens_por_id[aviso_id]))
        container.dataframe(
            tabela_br(pd.DataFrame([detalhes_por_id[aviso_id]])),
            width="stretch",
            hide_index=True,
            key=f"detalhe_{chave}_{aviso_id}",
        )
    else:
        container.caption("Selecione uma linha para ver o tipo de critério e sua interpretação.")


def _painel_verificacoes(
    container, avisos: list[dict], componentes: set[str], titulo: str,
) -> None:
    """Exibe verificações recolhíveis e separadas por componente/localização."""
    avisos_componente = [
        aviso for aviso in avisos if aviso["componente"] in componentes
    ]
    chave = "_".join(sorted(componentes)).casefold().replace(" ", "_")

    with container.expander(titulo, expanded=False):
        container.caption(
            "Os avisos registram critérios e faixas implementados; não equivalem, por si sós, "
            "a uma validação física completa. Uma recomendação fora da faixa não torna o caso "
            "automaticamente inválido."
        )
        if not avisos_componente:
            container.info(
                "Nenhum aviso foi emitido pelos verificadores executados neste componente. "
                "Isso não significa que todas as verificações físicas possíveis tenham sido realizadas."
            )
            return

        if componentes & {"Sistema", "Ciclo"}:
            container.markdown("#### AVISOS GERAIS")
            _tabela_avisos_selecionavel(container, avisos_componente, f"{chave}_gerais")
            return

        avisos_gerais = [aviso for aviso in avisos_componente if not aviso["estagio"]]
        avisos_localizados = [aviso for aviso in avisos_componente if aviso["estagio"]]

        if avisos_gerais:
            container.markdown("#### AVISOS GERAIS")
            _tabela_avisos_selecionavel(container, avisos_gerais, f"{chave}_gerais")

        if avisos_localizados:
            container.markdown("#### Avisos por estágio")
            _tabela_avisos_selecionavel(
                container, avisos_localizados, f"{chave}_localizados",
            )

        if not avisos_gerais and not avisos_localizados:
            container.info("Nenhum aviso foi emitido para este componente.")


def _executar_com_avisos(
    componente: str,
    origem: str,
    func,
    avisos: list[dict],
    saidas_capturadas: list[str],
):
    """Executa uma etapa isolando stdout para associar avisos ao componente de origem."""
    resultado, texto = _capturar_stdout(func)
    avisos.extend(_extrair_avisos(texto, componente, origem))
    if texto.strip():
        saidas_capturadas.append(f"[{componente} — {origem}]\n{texto.strip()}")
    return resultado


def _tabela_didatica(container, linhas: list[tuple[str, str, str]]) -> None:
    """Renderiza uma tabela compacta com dicas individuais nos nomes das grandezas."""
    linhas_html = "".join(
        "<tr>"
        f"<td><span tabindex='0' title='{html.escape(str(ajuda), quote=True)}' "
        "style='cursor:help;border-bottom:1px dotted currentColor;'>"
        f"{html.escape(str(termo))}</span></td>"
        f"<td style='text-align:right;white-space:nowrap;'>{html.escape(str(valor))}</td>"
        "</tr>"
        for termo, valor, ajuda in linhas
    )
    tabela = (
        "<div style='overflow-x:auto;'>"
        "<table class='didactic-values-table' style='width:100%;border-collapse:collapse;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:.45rem .6rem;border-bottom:1px solid rgba(128,128,128,.35);'>Grandeza</th>"
        "<th style='text-align:right;padding:.45rem .6rem;border-bottom:1px solid rgba(128,128,128,.35);'>Valor</th>"
        "</tr></thead>"
        f"<tbody>{linhas_html}</tbody></table></div>"
        "<style>.didactic-values-table td{padding:.42rem .6rem;border-bottom:1px solid rgba(128,128,128,.18)}"
        ".didactic-values-table tbody tr:hover{background:rgba(128,128,128,.08)}</style>"
    )
    container.markdown(tabela, unsafe_allow_html=True)


def _painel_estagios_didatico(container, maquina, razao_total: float, razao_alvo: float) -> None:
    """Explica a relação entre ψ solicitado, estágios e ψ efetivo sem alterar o modelo."""
    automatico = maquina.calculo_automatico
    modo = "automático" if automatico else "manual"
    col_psi, col_n_estimado, col_n_usado, col_psi_efetivo = container.columns(4)
    col_psi.metric("ψ solicitado", f"{formato_br(maquina.psi, f'.4f')}")
    col_n_estimado.metric("N estimado", _numero_br(maquina.n_estagios_estimado, 8 if automatico else 2))
    col_n_usado.metric("N adotado", f"{maquina.n_estagios} ({modo})")
    col_psi_efetivo.metric("ψ efetivo", f"{formato_br(maquina.psi_efetivo, f'.4f')}")

    container.caption(
        f"Razão de pressão total calculada: {formato_br(razao_total, f'.3f')}  │  alvo do ciclo: {formato_br(razao_alvo, f'.3f')}."
    )
    with container.expander("Como o número de estágios e ψ se relacionam") as explicacao:
        explicacao.markdown(
            r"A estimativa segue "
            r"$N_{\mathrm{estimado}}=\Delta T_{t,\mathrm{total}}/\Delta T_{t,\mathrm{estagio}}$, "
            r"com $\Delta T_{t,\mathrm{estagio}}=\psi_{\mathrm{solicitado}}U^2/c_p$."
        )
        if automatico:
            explicacao.markdown(
                f"**Modo automático:** os inteiros vizinhos da estimativa são comparados pelos critérios implementados, resultando em {maquina.n_estagios} estágios. O programa redistribui a variação total de temperatura entre esses estágios e recalcula ψ efetivo ({formato_br(maquina.psi_efetivo, f'.4f')}). Por isso ele pode diferir do ψ solicitado, inclusive ultrapassá-lo. O valor solicitado é uma preferência, não um teto de carga."
            )
        else:
            explicacao.markdown(
                f"**Modo manual:** foram adotados {maquina.n_estagios} estágios conforme a entrada do usuário, e ψ efetivo permanece igual ao solicitado ({formato_br(maquina.psi_efetivo, f'.4f')}). A estimativa não é arredondada nem substitui essa escolha; compare a razão de pressão calculada com o alvo do ciclo."
            )
    if automatico:
        selecao = getattr(maquina, "selecao_estagios", None)
        with container.expander("Seleção automática — comparação dos candidatos"):
            if selecao is None:
                container.info("Recalcule para consultar a comparação dos candidatos desta execução.")
            else:
                container.markdown(f"**Escolhido: {selecao['escolhido']} estágios.** {selecao['justificativa']}")
                linhas = []
                for candidato in selecao['candidatos']:
                    def numero(chave):
                        return _numero_br(candidato[chave], 6) if chave in candidato else "—"
                    linhas.append({
                        "Estágios": str(candidato['n_estagios']),
                        "Escolhido": "Sim" if candidato['selecionado'] else "Não",
                        "Calculável": "Sim" if candidato['calculavel'] else "Não",
                        "ψ efetivo": numero('psi_efetivo'),
                        "Excesso aero. máximo": numero('excesso_aero_max'),
                        "Excesso de câmber": numero('excesso_camber'),
                        "Excesso de faixas máximo": numero('excesso_faixas_max'),
                        "Afastamento relativo de ψ": numero('afastamento_psi_relativo'),
                    })
                container.dataframe(tabela_br(pd.DataFrame(linhas)), hide_index=True, width="stretch")
                escolhido = next(c for c in selecao['candidatos'] if c['selecionado'])
                if not escolhido['atende_criterios_comparados']:
                    container.info("O candidato escolhido ainda ultrapassa um ou mais critérios comparados. A seleção não significa aprovação física.")
                container.caption(
                    "Ordem de preferência: candidato calculável com fechamento do ciclo; menor pior excesso aerodinâmico; "
                    "menor soma dos excessos por família; menor excesso de câmber; menores excessos nas faixas comparativas; "
                    "menor afastamento de ψ; menor número de estágios no desempate. Não se usa a contagem bruta de avisos. "
                    "Empates numéricos são tratados com 12 casas decimais nos índices."
                )
                container.caption(
                    f"Avaliação com {selecao['n_secoes']} seções radiais e perfis de todas as fileiras. "
                    "Índices são excessos normalizados adotados para comparação, não probabilidades de falha. "
                    "Para limite superior: máximo de zero e valor/limite − 1. Para faixa: distância fora dela dividida por sua largura. "
                    "Mensagens repetidas não aumentam o peso: usa-se o pior valor por família. O loft/colisões e a resistência não entram nessa escolha."
                )
                ids = [c['n_estagios'] for c in selecao['candidatos']]
                n = container.selectbox("Detalhes do candidato", ids,
                                        index=ids.index(selecao['escolhido']),
                                        key=f"candidato_{selecao['componente']}")
                detalhe = next(c for c in selecao['candidatos'] if c['n_estagios'] == n)
                if not detalhe['calculavel']:
                    container.write(detalhe['motivo_rejeicao'])
                else:
                    criterios = detalhe.get('detalhes_criterios')
                    if criterios:
                        container.dataframe(tabela_br(tabela_criterios(criterios)), hide_index=True, width="stretch")
                        container.caption(
                            "Valor real e localização correspondem ao extremo que determina cada índice. "
                            "Para faixa sem ultrapassagem, mostra-se o extremo mais próximo de uma borda; "
                            "para limite inferior, o mínimo; para limite superior, o máximo. "
                            "Em empate, aparece a primeira ocorrência na ordem de avaliação. "
                            "Câmber e swirl são apresentados em módulo; as demais grandezas são adimensionais."
                        )
                        indice = container.selectbox(
                            "Critério — valores e localização completos", list(range(len(criterios))),
                            index=max(range(len(criterios)), key=lambda i: criterios[i]['excesso_normalizado']),
                            format_func=lambda i: nome_criterio(criterios[i]),
                            key=f"criterio_candidato_{selecao['componente']}_{n}",
                        )
                        container.table(tabela_br(tabela_localizacao(criterios[indice])))
                    else:
                        container.info("Recalcule o caso para consultar valores reais, limites e localizações dos critérios.")
                    container.caption(
                        f"Compressor: Mach relativo, DF e reação negativa; turbina: Mach relativo/bocal e reação fora de {formato_br(dc.REACAO_MIN, f'g')}–{formato_br(dc.REACAO_MAX_TURBINA, f'g')}. Câmber: {formato_br(dc.CAMBER_COMP_GRAUS, f'g')}° no compressor e {formato_br(dc.CAMBER_TURB_GRAUS, f'g')}° na turbina. Faixas: ψ e reação; swirl apenas no escape da turbina. Valores/limites são os adotados no projeto; esta ordem de prioridade é uma política de seleção, não regra universal da literatura."
                    )
    with container.expander("Geometria do anular — raio médio e HTR por estágio"):
        container.markdown(
            "O raio médio é a **média aritmética entre cubo e ponta**, mantida constante em cada "
            "componente. A área varia pela altura das pás: cubo e ponta mudam ao redor dessa referência. "
            "O HTR informado define a **entrada**; os HTR dos demais estágios são resultados. "
            "A turbina usa essa mesma hipótese e não mantém a ponta fixa."
        )
        container.latex(r"r_m=\frac{r_{tip}+r_{hub}}{2},\quad h_i=\frac{A_i}{2\pi r_m},\quad "
                        r"r_{hub,i}=r_m-\frac{h_i}{2},\quad r_{tip,i}=r_m+\frac{h_i}{2}")
        container.caption(
            "Esta referência difere do raio que divide o anular em áreas iguais, "
            "rₑ = √[(r_tip² + r_hub²)/2]. A continuidade é aproximada pelas condições meanline, "
            "sem integração radial de densidade."
        )
        container.dataframe(tabela_br(pd.DataFrame([
            {"Estágio": i + 1, "Área (cm²)": maquina.A_estagio[i] * 1e4,
             "Cubo (cm)": maquina.r_hub_est[i] * 100, "Ponta (cm)": maquina.r_tip_est[i] * 100,
             "Raio médio (cm)": maquina.r_mean * 100, "Altura (cm)": maquina.h_pa[i] * 100,
             "HTR local": maquina.HTR_estagio[i]} for i in range(maquina.n_estagios)
        ]).round(5)), hide_index=True, width="stretch")


def _rodar_pipeline(params: dict, estado_etapas: dict | None = None) -> dict:
    """
    Roda o pipeline completo (ciclo -> compressor -> combustor -> turbina -> radial ->
    perfis -> loft) com os parâmetros do formulário. Levanta ValueError/
    RuntimeError se algum estágio for inviável (ex.: DF_alvo inatingível,
    escoamento supersônico na entrada) -- quem chama decide como exibir.
    """
    avisos_detalhados = []
    saidas_capturadas = []
    if estado_etapas is None:
        estado_etapas = _novo_estado_etapas()

    def etapa(componente, origem, func):
        chave = _ETAPA_POR_ORIGEM[(componente, origem)]
        estado_etapas[chave] = "Em execução"
        antes = len(avisos_detalhados)
        try:
            resultado = _executar_com_avisos(
                componente, origem, func, avisos_detalhados, saidas_capturadas,
            )
        except Exception:
            estado_etapas[chave] = "Falhou"
            raise
        quantidade = len(avisos_detalhados) - antes
        estado_etapas[chave] = (
            f"Calculada com avisos ({quantidade})" if quantidade else "Calculada"
        )
        return resultado

    def resolver_objeto(classe, **kwargs):
        objeto = classe(**kwargs)
        objeto.resolver()
        return objeto

    def resolver_ciclo():
        ciclo = CicloBrayton(
            T01=params["T01"], P01=params["P01"] * 1e3,
            r_compr=params["r_compr"], TIT=params["TIT"],
            e_turb=params["e_turb"], e_compr=params["e_compr"],
            Delta_P_cc=params["Delta_P_cc"], TIT_máx=params["TIT_max"],
            cp=params.get('cp_ar', REF_CICLO['cp']),
            k=(REF_CICLO['k'] if params.get('mistura_automatica',True) else
               params.get('cp_ar', REF_CICLO['cp']) / (
                params.get('cp_ar', REF_CICLO['cp']) - params.get('R_ar', REF_CICLO['R_gases']))),
            cp_gases=params.get('cp_gases', REF_CICLO['cp_gases']),
            R_gases=params.get('R_gases', REF_CICLO['R_gases']),
            mistura_automatica=params.get('mistura_automatica', True),
        )
        ciclo.resolver()
        ciclo.vazão_mássica_desejada(params["m_dot"])
        return ciclo

    def _rodar():
        ciclo = etapa("Ciclo", "Modelo termodinâmico", resolver_ciclo)

        comp = etapa(
            "Compressor", "Meanline",
            lambda: resolver_objeto(
                CompressorMeanline,
                ciclo=ciclo, N=params["N_comp"], HTR=params["HTR_comp"],
                n_estagios=params["n_estagios_comp"], phi=params["phi_comp"],
                psi=params["psi_comp"], alpha1_graus=params["alpha1_comp"],
                DF_alvo=params["DF_alvo"], AR=params["AR_comp"],
                n_secoes_avaliacao=params["n_secoes"],
            ),
        )

        rad_comp = etapa(
            "Compressor", "Distribuição radial",
            lambda: resolver_objeto(RadialCompressor, comp=comp, n_secoes=params["n_secoes"]),
        )

        perfis_comp = etapa(
            "Compressor", "Geometria dos perfis",
            lambda: gerar_perfis_compressor(rad_comp),
        )
        maquina_comp = etapa(
            "Compressor", "Montagem geométrica",
            lambda: loftar_compressor(rad_comp, perfis=perfis_comp, replicar=False),
        )

        combustor = etapa(
            "Combustor", "Modelo 1D",
            lambda: resolver_objeto(
                Combustor1D,
                ciclo=ciclo, combustivel=params["combustivel"],
                eta_b=params["eta_b"], M_entrada=params["M_entrada"],
            ),
        )
        etapa(
            "Ciclo", "Acoplamento da vazão",
            lambda: ciclo.registrar_vazao_turbina(combustor.m_dot_turbina),
        )

        turb = etapa(
            "Turbina", "Meanline",
            lambda: resolver_objeto(
                TurbinaAxialMeanline,
                ciclo=ciclo, N=params["N_turb"], HTR=params["HTR_turb"],
                n_estagios=params["n_estagios_turb"], phi=params["phi_turb"],
                psi=params["psi_turb"], alpha2_graus=params["alpha2_turb"],
                sigma=params["sigma_turb"], AR=params["AR_turb"],
                m_dot_turbina=combustor.m_dot_turbina,
                n_secoes_avaliacao=params["n_secoes"],
            ),
        )

        rad_turb = etapa(
            "Turbina", "Distribuição radial",
            lambda: resolver_objeto(RadialTurbina, turb=turb, n_secoes=params["n_secoes"]),
        )

        perfis_turb = etapa(
            "Turbina", "Geometria dos perfis",
            lambda: gerar_perfis_turbina(rad_turb),
        )
        maquina_turb = etapa(
            "Turbina", "Montagem geométrica",
            lambda: loftar_turbina(rad_turb, perfis=perfis_turb, replicar=False),
        )

        return dict(
            ciclo=ciclo, comp=comp, rad_comp=rad_comp, maquina_comp=maquina_comp,
            combustor=combustor, turb=turb, rad_turb=rad_turb, maquina_turb=maquina_turb,
            perfis_comp=perfis_comp, perfis_turb=perfis_turb,
        )

    resultado, texto = _capturar_stdout(_rodar)
    resultado["diagnosticos"] = diagnosticar_integracao(
        resultado["ciclo"], resultado["comp"], resultado["turb"], resultado["combustor"],
    )
    if texto.strip():
        avisos_detalhados.extend(_extrair_avisos(texto, "Sistema", "Pipeline"))
        saidas_capturadas.append(texto.strip())
    resultado["avisos_texto"] = "\n\n".join(saidas_capturadas)
    resultado["avisos_detalhados"] = avisos_detalhados
    return resultado


# ══════════════════════════════════════════════════════════════════════════
# AUXILIARES — TABELAS POR ESTÁGIO
# ══════════════════════════════════════════════════════════════════════════

def _tabela_comparacoes(linhas, alvo="Ciclo / alvo", calculado="Meanline / calculado"):
    unidades = {"Pa": (1e-3, "kPa"), "J/kg": (1e-3, "kJ/kg"), "W": (1e-3, "kW")}
    dados = []
    for linha in linhas:
        fator, unidade = unidades.get(linha["unidade"], (1, linha["unidade"]))
        dados.append({"Grandeza": f"{linha['grandeza']} ({unidade})",
                      alvo: _numero_br(linha["alvo"] * fator, 6),
                      calculado: _numero_br(linha["calculado"] * fator, 6),
                      "Calculado − alvo": _numero_br(linha["residuo"] * fator, 6),
                      "Diferença (%)": (_numero_br(linha["residuo_pct"], 6)
                                        if linha["residuo_pct"] is not None else "—")})
    return pd.DataFrame(dados)


def _painel_fechamento_global(diagnosticos):
    status = "alvos coincidem numericamente" if diagnosticos["alvos_coincidem"] else "há diferenças entre os alvos"
    with st.expander(f"Fechamento ciclo–meanline — {status}"):
        st.markdown(
            "Os indicadores principais são resultados do **ciclo**. A soma dos trabalhos dos "
            "meanlines é uma comparação independente; não resolve um novo ciclo integrado. "
            "O compressor usa vazão de ar e a turbina usa ar + combustível. Consumo e produção "
            "são positivos; potência líquida = produção − consumo, com transmissão mecânica ideal."
        )
        st.dataframe(tabela_br(_tabela_comparacoes(diagnosticos["potencias"])), width="stretch", hide_index=True)
        interface = st.selectbox("Acoplamento a conferir", list(diagnosticos["interfaces"]), key="interface_ciclo_meanline")
        st.dataframe(tabela_br(_tabela_comparacoes(diagnosticos["interfaces"][interface],
                                        "Usado pelo receptor", "Disponível na origem")),
                     width="stretch", hide_index=True)
        st.caption(
            f"Diferença = calculado − alvo; percentual = 100 × diferença / |alvo|. Para alvo zero, o percentual fica indefinido. Coincidência numérica: tolerância relativa {formato_br(dc.COINCIDENCIA_RTOL, f'g')} e absoluta {formato_br(dc.COINCIDENCIA_ATOL, f'g')} nas unidades SI. Isso não é tolerância de projeto. O limiar antigo de {formato_br(dc.FECHAMENTO_AVISO_PCT, f'g')}% para emitir certos avisos não transforma desvios menores em fechamento exato; eles permanecem nas tabelas. Os desvios não são perdas físicas adicionais."
        )
        st.markdown(
            "**Modo automático:** redistribui a carga pelos estágios e recalcula ψ efetivo. "
            "**Modo manual:** preserva N e ψ escolhidos e pode divergir do ciclo. "
            "O combustor continua usando T02 e P02 do ciclo; nenhuma dessas entradas é substituída "
            "silenciosamente pela saída meanline. Mesmo quando os alvos coincidem, o trecho "
            "compressor–combustor permanece sem difusor modelado: não se comprova continuidade "
            "de velocidade, swirl ou geometria nesse trecho."
        )


def _paineis_diagnostico_componente(dados):
    componente = dados["componente"]
    with st.expander(f"Comparação com o ciclo — {componente.lower()}"):
        st.dataframe(tabela_br(_tabela_comparacoes(dados["comparacoes"])), width="stretch", hide_index=True)
        st.caption(
            f"Modo desta execução: {dados['modo']}. O alvo é o resultado do ciclo; a coluna "
            "meanline é a saída realmente obtida pelos estágios. Diferenças são exibidas mesmo "
            "quando não ultrapassam o limiar de emissão dos avisos."
        )
    with st.expander(f"Áreas por estação — {componente.lower()}"):
        i = st.selectbox("Estágio das áreas", range(len(dados["estagios"])),
                         format_func=lambda n: f"Estágio {n+1}", key=f"area_estagio_{componente}")
        dado = dados["estagios"][i]
        nomes = ("1 — entrada do rotor", "2 — rotor/estator", "3 — saída do estator") if componente == "Compressor" else (
            "1 — entrada do bocal", "2 — bocal/rotor", "3 — saída do rotor")
        linhas = []
        for numero, nome in zip(("1", "2", "3"), nomes):
            plano = dado["planos"][numero]
            linhas.append({"Estação local": nome, "C absoluta (m/s)": f"{formato_br(plano['C_m_s'], f'.4f')}",
                           "T estática (K)": f"{formato_br(plano['T_K'], f'.4f')}",
                           "P total (kPa)": "Não determinada" if plano["Pt_Pa"] is None else f"{formato_br(plano['Pt_Pa'] / 1000.0, f'.4f')}",
                           "Área exigida (cm²)": "Não determinada" if plano["area_m2"] is None else f"{formato_br(plano['area_m2'] * 10000.0, f'.4f')}"})
        st.table(tabela_br(pd.DataFrame(linhas).set_index("Estação local")))
        st.latex(r"T=T_t-\frac{C^2}{2c_p},\quad P=P_t(T/T_t)^{k/(k-1)},\quad A=\frac{\dot m}{\rho C_x}")
        st.markdown(
            "**Estação 2:** a velocidade e a temperatura estão definidas, mas o modelo não "
            "reparte as perdas de pressão entre as fileiras. Portanto P total, densidade e área "
            "nesse plano permanecem não determinadas; não se assume bocal ou estator sem perdas."
        )
        st.caption(
            f"A área representativa usada no CAD deste estágio é {formato_br(dado['area_representativa_m2'] * 10000.0, f'.4f')} cm² e corresponde à entrada. A área exigida na saída é uma grandeza distinta. As diferenças decorrem da mudança de densidade/velocidade; o CAD ainda não resolve a variação axial do anular dentro das fileiras. A continuidade é meanline, sem integração radial de densidade. Fonte da relação de área: continuidade e gás ideal, equivalentes à função de vazão compressível usada nos meanlines."
        )
        if st.checkbox("Mostrar diagnóstico condicional da área CAD na saída",
                       key=f"area_condicional_{componente}"):
            st.markdown(
                f"Se a área representativa de entrada fosse imposta também à saída, mantendo o estado e as velocidades calculados, a vazão reconstruída diferiria da prescrita em **{formato_br(dado['desvio_vazao_se_area_CAD_imposta_na_saida_pct'], f'+.4f')}%**. Esse é um teste condicional da interpretação da geometria, não uma alteração da vazão do programa ou um erro de vazão calculado com a área própria da saída."
            )


def _painel_continuidade_turbina(turb):
    """Resultados meanline das interfaces e definição de reação usada no core."""
    with st.expander("Continuidade entre estágios e reação estática da turbina"):
        st.markdown(
            "Só a entrada do primeiro bocal é axial. Nos seguintes, o escoamento chega com a "
            "velocidade tangencial de saída do rotor anterior. O plano entre estágios não recebe "
            "trabalho, calor ou perda adicional de pressão no modelo. A área de entrada considera "
            "o ângulo herdado; não se acrescenta um retificador de escoamento."
        )
        st.dataframe(tabela_br(pd.DataFrame([
            {"Estágio": i + 1, "α₁ entrada (°)": turb.alpha1[i],
             "α₃ saída (°)": turb.alpha3[i], "R estática": turb.grau_reacao[i],
             "Queda rotor / trabalho": turb.reacao_rotor_por_trabalho[i]}
            for i in range(turb.n_estagios)
        ]).round(6)), hide_index=True, width="stretch")
        if turb.n_estagios > 1:
            anterior = st.selectbox(
                "Interface a conferir", range(1, turb.n_estagios),
                format_func=lambda i: f"Saída do estágio {i} → entrada do estágio {i + 1}",
                key="interface_estagios_turbina",
            )
            i, j = anterior - 1, anterior
            linhas = []
            for nome, saida, entrada in (
                ("C tangencial (m/s)", turb.v3[i], turb.v1[j]),
                ("C axial (m/s)", turb.u_ax, turb.u_ax),
                ("Temperatura total (K)", turb.Tt_saida[i], turb.Tt_entrada[j]),
                ("Pressão total (kPa)", turb.Pt_saida[i] / 1e3, turb.Pt_entrada[j] / 1e3),
                ("Temperatura estática (K)", turb.T3_est[i], turb.T1_est[j]),
                ("Área exigida no plano meanline (cm²)", turb.A_saida_estagio[i] * 1e4, turb.A_estagio[j] * 1e4),
            ):
                linhas.append({"Grandeza": nome, "Saída anterior": saida,
                               "Entrada seguinte": entrada, "Entrada − saída": entrada - saida})
            st.dataframe(tabela_br(pd.DataFrame(linhas).round(8)), hide_index=True, width="stretch")
        else:
            st.caption("Há um único estágio: não existe interface entre estágios a comparar.")
        st.latex(r"R=\frac{h_2-h_3}{h_1-h_3}=\frac{w+(C_3^2-C_2^2)/2}{w+(C_3^2-C_1^2)/2},\quad w=h_{01}-h_{03}")
        st.markdown(
            "**Reação estática** compara a queda de entalpia estática no rotor com a do estágio "
            "inteiro. A coluna **queda rotor / trabalho** usa o trabalho de eixo no denominador. "
            "As duas só coincidem quando as energias cinéticas de entrada e saída são iguais. "
            "Isso ocorre nos estágios seguintes de carga/triângulos uniformes deste modelo, "
            "mas não é imposto ao primeiro estágio. O sinal do swirl foi preservado."
        )
        st.caption(
            "Fonte: Dixon & Hall, 7ª ed., Eq. 4.3a, p. 123; condições de estágio repetitivo, "
            "pp. 125–127. Velocidades C são absolutas. Tabelas acima no raio médio. "
            "No radial, a constante r·Cθ é transferida e a continuidade é comparada no mesmo "
            "raio físico; hub/mid/tip podem ter raios diferentes de um estágio para outro. "
            "A área de saída é um diagnóstico de continuidade; a geometria CAD ainda usa um "
            "anular representativo por estágio, sem resolver a variação axial dentro das fileiras."
        )


def _painel_perfis_didatico(radial, perfis, componente):
    """Mostra os ângulos do perfil efetivamente entregue ao loft, sob demanda."""
    with st.expander("Do escoamento ao perfil — ângulos metálicos e solidez local"):
        if perfis is None:
            st.info("Recalcule o caso para consultar os perfis desta execução.")
            return
        compressor = componente == "Compressor"
        maquina = radial.comp if compressor else radial.turb
        fileiras = ("rotor", "estator") if compressor else ("bocal", "rotor")
        # Uma nova execução pode reduzir o número de estágios/seções.
        for chave, opcoes in ((f"perfil_estagio_{componente}", range(1, maquina.n_estagios + 1)),
                              (f"perfil_secao_{componente}", radial.secoes)):
            if chave in st.session_state and st.session_state[chave] not in opcoes:
                del st.session_state[chave]
        col1, col2, col3 = st.columns(3)
        estagio = col1.selectbox("Estágio do perfil", range(1, maquina.n_estagios + 1),
                                key=f"perfil_estagio_{componente}")
        secao = col2.selectbox("Seção do perfil", radial.secoes,
                              key=f"perfil_secao_{componente}")
        fileira = col3.selectbox("Fileira", fileiras, key=f"perfil_fileira_{componente}")
        perfil = perfis[estagio][secao][fileira]
        i = estagio - 1
        st.caption(
            "Valores do caso calculado e do perfil usado no loft. Ângulos medidos a partir do eixo "
            "axial, com tangencial positivo no sentido de U. No rotor do compressor, o ângulo "
            "geométrico de W é −β do modelo; nos estatores/bocais usa-se o ângulo absoluto."
        )
        st.table(tabela_br(pd.DataFrame([
            {"Posição": "Entrada", "Escoamento (°)": perfil.beta1_graus,
             "Metal (°)": perfil.beta1_linha,
             "Escoamento − metal (°)": perfil.beta1_graus - perfil.beta1_linha},
            {"Posição": "Saída", "Escoamento (°)": perfil.beta2_graus,
             "Metal (°)": perfil.beta2_linha,
             "Escoamento − metal (°)": perfil.delta},
        ]).set_index("Posição").style.format(_numero_br)))
        z = getattr(maquina, f"Z_{fileira}")[i]
        raio = radial.r[i][secao]
        st.table(tabela_br(pd.DataFrame([
            ("Número inteiro de pás Z", f"{z}"),
            ("Corda verdadeira c", f"{_numero_br(perfil.corda * 100)} cm"),
            ("Passo local s = 2πr/Z", f"{_numero_br(2 * math.pi * raio / z * 100)} cm"),
            ("Solidez local σ = c/s", _numero_br(perfil.sigma, 6)),
            ("Câmber metálico assinado θ", f"{_numero_br(perfil.theta_final)}°"),
            ("Stagger metálico ζ usado no loft", f"{_numero_br(perfil.stagger)}°"),
        ], columns=["Grandeza", "Valor"]).set_index("Grandeza")))
        st.markdown(
            "**Incidência** é a diferença entre escoamento e metal na entrada; neste modelo é zero. "
            "**Desvio** é essa diferença na saída. **Câmber** é a mudança de direção metálica entre "
            "entrada e saída. **Stagger** orienta a corda na máquina. A corda e Z permanecem "
            "constantes na fileira, enquanto o passo cresce com o raio e a solidez local diminui."
        )
        exibir_perfil_2d(radial, perfis, componente, estagio, secao, fileira)
        if compressor:
            st.latex(r"a_C=m\sqrt{s/c},\quad\theta=\frac{\gamma_{1,\mathrm{metal}}-\gamma_{2,\mathrm{escoamento}}}{1-a_C},\quad\delta=a_C\theta")
            st.caption(
                "Carter fechado no câmber metálico final, com m = 0,23 + 0,002|γ₂,escoamento| "
                "(ângulo em graus), a/c = 0,5. Fonte: Dixon & Hall, 7ª ed., Eqs. 3.34–3.35 "
                "e exemplo 3.1, pp. 86–87. γ aqui indica o ângulo assinado da fileira; "
                "a correlação é uma aproximação empírica para cascatas de compressor."
            )
        else:
            st.caption(
                "Turbina: incidência e desvio impostos como zero; Carter de compressor não é aplicado. "
                "A solidez exibida resulta de Z arredondado e do raio local, podendo diferir do alvo "
                "meanline. Isso não valida o desvio real ou o carregamento ótimo da cascata."
            )


def _tabela_estagio_compressor(rad_comp: RadialCompressor, i: int) -> pd.DataFrame:
    linhas = []
    for s in rad_comp.secoes:
        linhas.append({
            "Seção": s,
            "r (cm)": round(rad_comp.r[i][s] * 100, 2),
            "α₁ (°)": round(rad_comp.alpha1[i][s], 2),
            "α₂ (°)": round(rad_comp.alpha2[i][s], 2),
            "β₁ (°)": round(rad_comp.beta1[i][s], 2),
            "β₂ (°)": round(rad_comp.beta2[i][s], 2),
            "M1": round(rad_comp.M1[i][s], 3),
            "M1R": round(rad_comp.M1R[i][s], 3),
            "DF rotor": round(rad_comp.DF_rotor[i][s], 3),
            "DF estator": round(rad_comp.DF_estator[i][s], 3),
            "Reação": round(rad_comp.R_c[i][s], 3),
        })
    return pd.DataFrame(linhas)


def _tabela_estagio_turbina(rad_turb: RadialTurbina, i: int) -> pd.DataFrame:
    linhas = []
    for s in rad_turb.secoes:
        linhas.append({
            "Seção": s,
            "r (cm)": round(rad_turb.r[i][s] * 100, 2),
            "α₁ (°)": round(rad_turb.alpha1[i][s], 2),
            "α₂ (°)": round(rad_turb.alpha2[i][s], 2),
            "α₃ (°)": round(rad_turb.alpha3[i][s], 2),
            "β₂ (°)": round(rad_turb.beta2[i][s], 2),
            "β₃ (°)": round(rad_turb.beta3[i][s], 2),
            "M2": round(rad_turb.M2[i][s], 3),
            "M3R": round(rad_turb.M3R[i][s], 3),
            "R estática": round(rad_turb.R_c[i][s], 3),
        })
    return pd.DataFrame(linhas)


# ══════════════════════════════════════════════════════════════════════════
# AUXILIAR — IMAGEM ESTÁTICA DO PAR DE PÁS DE UM ESTÁGIO
# ══════════════════════════════════════════════════════════════════════════

def _figura_par_pa(peca_a, cor_a: str, peca_b, cor_b: str, titulo: str):
    """
    Monta uma figura matplotlib 3D com as duas fileiras de pá de um
    estágio (rotor+estator, ou bocal+rotor), reaproveitando os objetos
    PaLofted já calculados por loftar_compressor()/loftar_turbina() --
    nenhuma geometria nova é gerada aqui, só renderização.
    """
    fig = plt.figure(figsize=(5, 4))
    ax = fig.add_subplot(111, projection='3d')

    for peca, cor in [(peca_a, cor_a), (peca_b, cor_b)]:
        for secao in peca.pa.extradorso_cart:
            xs, ys, zs = zip(*secao)
            ax.plot(xs, ys, zs, color=cor, linewidth=0.8)
        for secao in peca.pa.intradorso_cart:
            xs, ys, zs = zip(*secao)
            ax.plot(xs, ys, zs, color=cor, linewidth=0.8)

    ax.set_title(titulo, fontsize=9)
    ax.set_xlabel('x (m)', fontsize=7)
    ax.set_ylabel('y (m)', fontsize=7)
    ax.set_zlabel('z (m)', fontsize=7)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════
# AUXILIARES — DOWNLOADS
# ══════════════════════════════════════════════════════════════════════════

def _bytes_de_arquivo(caminho: str) -> bytes:
    with open(caminho, "rb") as f:
        return f.read()


def _zip_pasta(pasta: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome_arquivo in sorted(os.listdir(pasta)):
            zf.write(os.path.join(pasta, nome_arquivo), arcname=nome_arquivo)
    buffer.seek(0)
    return buffer.read()


def _tabela_entradas_execucao(parametros: dict, resultados: dict | None = None) -> pd.DataFrame:
    """Organiza a fotografia das entradas submetidas, sem recalcular grandezas."""
    rotulos = {
        "mistura_automatica": "Propriedades dos gases por composição NASA",
        "T01": "T01 — temperatura total de entrada (K)",
        "P01": "P01 — pressão total de entrada (kPa)",
        "r_compr": "Razão de pressão total do compressor",
        "TIT": "TIT — temperatura de entrada da turbina (K)",
        "e_compr": "Eficiência politrópica do compressor",
        "e_turb": "Eficiência politrópica da turbina",
        "Delta_P_cc": "Perda relativa de pressão do combustor",
        "TIT_max": "TIT máxima permitida (K)",
        "m_dot": "Vazão mássica de ar (kg/s)",
        "cp_ar": "cp do ar (J/kg·K)",
        "cp_gases": "cp dos gases (J/kg·K)",
        "R_ar": "R do ar (J/kg·K)",
        "R_gases": "R dos gases (J/kg·K)",
        "combustivel": "Combustível",
        "eta_b": "Eficiência de combustão η_b",
        "M_entrada": "Mach prescrito na entrada do combustor",
        "N_comp": "Rotação comum do eixo (rpm)",
        "HTR_comp": "HTR de entrada do compressor",
        "n_estagios_comp": "Número de estágios do compressor",
        "phi_comp": "Coeficiente de vazão φ do compressor",
        "psi_comp": "Coeficiente de carga ψ do compressor",
        "alpha1_comp": "Ângulo α₁ de entrada do compressor (°)",
        "DF_alvo": "Fator de difusão alvo do compressor",
        "AR_comp": "Razão de aspecto h/c do compressor",
        "HTR_turb": "HTR de entrada da turbina",
        "n_estagios_turb": "Número de estágios da turbina",
        "phi_turb": "Coeficiente de vazão φ da turbina",
        "psi_turb": "Coeficiente de carga ψ da turbina",
        "alpha2_turb": "Ângulo α₂ de saída do bocal (°)",
        "sigma_turb": "Solidez σ da turbina",
        "AR_turb": "Razão de aspecto h/c da turbina",
        "n_secoes": "Número de seções radiais",
    }
    linhas = []
    for chave, rotulo in rotulos.items():
        if chave not in parametros:
            continue
        valor = parametros[chave]
        if chave in {"n_estagios_comp", "n_estagios_turb"}:
            componente = "comp" if chave == "n_estagios_comp" else "turb"
            if valor is None:
                if resultados is not None:
                    adotados = resultados[componente].n_estagios
                    valor_formatado = f"Automático — {adotados} adotado(s)"
                else:
                    valor_formatado = "Automático — cálculo não concluído"
            else:
                valor_formatado = f"{valor} (manual)"
        elif chave == 'mistura_automatica':
            valor_formatado = 'Ativado' if valor else 'Desativado — propriedades prescritas'
        elif chave in {'cp_gases','R_ar','R_gases'} and parametros.get('mistura_automatica',False):
            valor_formatado = 'Inativo neste modo — consulte as propriedades calculadas na aba Combustor'
        elif chave == "combustivel":
            valor_formatado = "Gás natural" if valor == "gas_natural" else str(valor)
        elif chave == "Delta_P_cc":
            valor_formatado = f"{formato_br(valor, f'.2%')}"
        elif isinstance(valor, float):
            valor_formatado = f"{formato_br(valor, f'.6g')}"
        else:
            valor_formatado = str(valor)
        linhas.append({"Entrada": rotulo, "Valor submetido": valor_formatado})
    return pd.DataFrame(linhas)


_ETAPAS_EXECUCAO = (
    ("ciclo", "Ciclo Brayton"),
    ("compressor_meanline", "Compressor — meanline"),
    ("compressor_radial", "Compressor — distribuição radial"),
    ("compressor_perfis", "Compressor — geração de perfis"),
    ("compressor_geometria", "Compressor — montagem geométrica"),
    ("combustor_1d", "Combustor 1D"),
    ("acoplamento_vazao", "Acoplamento da vazão à turbina"),
    ("turbina_meanline", "Turbina — meanline"),
    ("turbina_radial", "Turbina — distribuição radial"),
    ("turbina_perfis", "Turbina — geração de perfis"),
    ("turbina_geometria", "Turbina — montagem geométrica"),
    ("sensibilidade", "Curvas de sensibilidade"),
)

_ETAPA_POR_ORIGEM = {
    ("Ciclo", "Modelo termodinâmico"): "ciclo",
    ("Ciclo", "Acoplamento da vazão"): "acoplamento_vazao",
    ("Compressor", "Meanline"): "compressor_meanline",
    ("Compressor", "Distribuição radial"): "compressor_radial",
    ("Compressor", "Geometria dos perfis"): "compressor_perfis",
    ("Compressor", "Montagem geométrica"): "compressor_geometria",
    ("Combustor", "Modelo 1D"): "combustor_1d",
    ("Turbina", "Meanline"): "turbina_meanline",
    ("Turbina", "Distribuição radial"): "turbina_radial",
    ("Turbina", "Geometria dos perfis"): "turbina_perfis",
    ("Turbina", "Montagem geométrica"): "turbina_geometria",
}


def _novo_estado_etapas() -> dict[str, str]:
    return {chave: "Não executada" for chave, _ in _ETAPAS_EXECUCAO}


def _tabela_estado_etapas(execucao: dict | None, resultados: dict | None, erro: str | None) -> pd.DataFrame:
    if execucao is None:
        if resultados is None and not erro:
            estados = {chave: "Aguardando cálculo" for chave, _ in _ETAPAS_EXECUCAO}
        else:
            estados = {chave: "Não registrado nesta execução" for chave, _ in _ETAPAS_EXECUCAO}
    else:
        estados = execucao.get("etapas", {})

    return pd.DataFrame([
        {"Etapa": nome, "Estado": estados.get(chave, "Não registrado")}
        for chave, nome in _ETAPAS_EXECUCAO
    ])


def _exibir_estado_execucao() -> None:
    """Identifica a última tentativa e quais entradas originaram os resultados."""
    resultados = st.session_state.get("resultados")
    erro = st.session_state.get("erro")
    execucao = st.session_state.get("ultima_execucao")

    if execucao is None:
        if resultados is not None:
            avisos = resultados.get("avisos_detalhados", [])
            if avisos:
                st.warning(f"Estado do caso: cálculo concluído com {len(avisos)} aviso(s).")
            else:
                st.success("Estado do caso: cálculo concluído; os verificadores executados não emitiram avisos.")
            st.caption(
                "Este resultado foi preservado de uma execução anterior à identificação das entradas. "
                "Envie o formulário novamente para registrar o identificador e a fotografia dos parâmetros."
            )
        elif erro:
            st.error("Estado do caso: cálculo não concluído.")
        else:
            st.info("Estado do caso: aguardando o primeiro cálculo.")
        return

    parametros = execucao["parametros"]
    if erro or resultados is None:
        st.error("Estado do caso: cálculo não concluído.")
    else:
        avisos = resultados.get("avisos_detalhados", [])
        if avisos:
            st.warning(f"Estado do caso: cálculo concluído com {len(avisos)} aviso(s).")
        else:
            st.success(
                "Estado do caso: cálculo concluído; os verificadores executados não emitiram avisos."
            )

    st.caption(
        f"Execução {execucao['id']} · iniciada em "
        f"{execucao['iniciada_em'].strftime('%d/%m/%Y %H:%M:%S %Z')}. "
        "Os resultados refletem as entradas desta execução; alterações no formulário só são "
        "aplicadas ao clicar em **Calcular e atualizar gráficos**."
    )
    with st.expander("Estado de cada etapa", expanded=False):
        st.dataframe(
            tabela_br(_tabela_estado_etapas(execucao, resultados, erro)),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            "‘Calculada com avisos’ indica que a etapa terminou, mas emitiu uma ou mais "
            "observações. ‘Não executada’ indica que o fluxo foi interrompido antes dessa etapa."
        )
        if not execucao.get("etapas"):
            st.caption("Clique em Calcular e atualizar gráficos para registrar os estados desta execução.")
    with st.expander("Entradas submetidas nesta execução", expanded=False):
        st.dataframe(
            tabela_br(_tabela_entradas_execucao(parametros, resultados)),
            width="stretch",
            hide_index=True,
        )


# ══════════════════════════════════════════════════════════════════════════
# FORMULÁRIO DE ENTRADA (BARRA LATERAL)
# ══════════════════════════════════════════════════════════════════════════

st.title("Projeto Preliminar de Turbina a Gás Axial")
st.caption(
    "Ferramenta computacional para projeto preliminar integrado "
    "(ciclo → meanline → distribuição radial → geometria de pá → CAD)."
)

# Símbolos LaTeX, significados e unidades para o glossário geral da interface.
# As explicações contextuais mais específicas permanecem nos tooltips dos campos e resultados.
GLOSSARIO = {
    "Ciclo Brayton": [
        (r"T_{01}", "Temperatura total na entrada do compressor", "Condição de entrada do ciclo.", "K"),
        (r"P_{01}", "Pressão total na entrada do compressor", "Condição de entrada do ciclo.", "Pa (interface: kPa)"),
        (r"T_{02r}", "Temperatura total real na saída do compressor", "O índice `r` indica a condição real com as perdas representadas.", "K"),
        (r"P_{02}", "Pressão total na saída do compressor", "Pressão usada como condição de entrada do combustor no modelo.", "Pa (interface: kPa)"),
        (r"T_{\mathrm{IT}}", "Temperatura de entrada na turbina (TIT)", "Temperatura total de saída do combustor definida no ciclo.", "K"),
        (r"P_{03}", "Pressão total após o combustor", "Calculada pela perda relativa de pressão atribuída ao combustor.", "Pa (interface: kPa)"),
        (r"T_{04r}", "Temperatura total real na saída da turbina", "Estado de saída da turbina no ciclo.", "K"),
        (r"P_{04}", "Pressão total na saída da turbina", "No ciclo atual, igual à pressão de entrada do compressor.", "Pa (interface: kPa)"),
        (r"\eta_{\mathrm{util}}", "Eficiência sobre calor útil", "Potência líquida dividida pelo calor útil transferido aos gases; corresponde a eta_ciclo no código.", "% ou adimensional"),
        (r"\eta_{\mathrm{PCI}}", "Eficiência sobre PCI", "Potência líquida dividida por vazão de combustível vezes PCI; igual a η_b vezes a eficiência sobre calor útil.", "% ou adimensional"),
        (r"w_{\mathrm{liq}}", "Trabalho específico líquido", "Trabalho líquido por unidade de massa de ar.", "J/kg (interface: kJ/kg)"),
        (r"\dot{W}_{\mathrm{liq}}", "Potência líquida", "Taxa de trabalho do ciclo; relacionada a `w_liq` pela vazão mássica de ar.", "W (interface: kW)"),
        (r"\mathrm{BWR}", "Razão de trabalho reverso", "Parcela do trabalho da turbina consumida pelo compressor.", "Adimensional"),
    ],
    "Combustor": [
        (r"\eta_b", "Eficiência de combustão", "Fração da energia química do combustível aproveitada no balanço do modelo.", "Adimensional"),
        (r"f", "Razão combustível/ar", "Vazão mássica de combustível dividida pela vazão mássica de ar.", "kg/kg"),
        (r"\phi_{\mathrm{eq}}", "Razão de equivalência", "Razão combustível/ar calculada dividida pela razão estequiométrica.", "Adimensional"),
        (r"M_{\mathrm{entrada}}", "Mach prescrito na entrada do combustor", "Usado para estimar a área 1D; não é calculado a partir do compressor. O difusor entre as máquinas não é modelado.", "Adimensional"),
        (r"\Delta P_{\mathrm{comb}}", "Perda relativa de pressão do combustor", "Fração aplicada à pressão total através do combustor no ciclo.", "% ou adimensional"),
        (r"\dot{m}_{\mathrm{ar}}", "Vazão mássica de ar", "Vazão de ar que entra no compressor e serve de base ao balanço do combustor.", "kg/s"),
        (r"\dot{m}_{f}", "Vazão mássica de combustível", "Calculada pelo produto de `f` pela vazão de ar.", "kg/s"),
        (r"\dot{m}_{\mathrm{total}}", "Vazão mássica total", "Soma das vazões de ar e combustível; é encaminhada à turbina.", "kg/s"),
    ],
    "Parâmetros de projeto": [
        (r"\phi", "Coeficiente de vazão", "Razão entre velocidade axial e velocidade periférica, `u_ax / U`.", "Adimensional"),
        (r"\psi", "Coeficiente de carga", "Trabalho específico do estágio normalizado por `U²`.", "Adimensional"),
        (r"\psi_{\mathrm{efetivo}}", "Coeficiente de carga efetivo", "Valor realmente usado após o ajuste automático do número de estágios, quando ativado.", "Adimensional"),
        (r"\mathrm{HTR}", "Razão cubo/ponta", "Entrada: define o anular inicial. Com raio médio aritmético constante, o HTR local varia entre estágios.", "Adimensional"),
        (r"\sigma", "Solidez", "Corda da pá dividida pelo passo circunferencial entre pás.", "Adimensional"),
        (r"\mathrm{AR}=h/c", "Razão de aspecto", "Altura da pá `h` dividida pela corda `c`.", "Adimensional"),
        (r"\mathrm{DF}_{\mathrm{alvo}}", "Fator de difusão alvo", "Valor de projeto usado para determinar a solidez do compressor.", "Adimensional"),
        (r"\pi_s,\;\pi_{\mathrm{total}}", "Razão de pressão", "Razão de pressão total do estágio (`s`) ou do componente/ciclo (`total`).", "Adimensional"),
    ],
    "Resultados das turbomáquinas": [
        (r"\alpha", "Ângulo absoluto do escoamento", "Ângulo da velocidade absoluta em relação ao eixo da máquina.", "graus (°)"),
        (r"\beta", "Ângulo relativo do escoamento", "Ângulo da velocidade relativa, observada pelo rotor, em relação ao eixo.", "graus (°)"),
        (r"M_1, M_2, M_3", "Número de Mach absoluto", "Mach do escoamento absoluto nas estações locais do estágio.", "Adimensional"),
        (r"M_{1R}, M_{2R}, M_{3R}", "Número de Mach relativo", "Mach da velocidade relativa ao rotor nas estações locais indicadas.", "Adimensional"),
        (r"\mathrm{DF}_{\mathrm{rotor}},\;\mathrm{DF}_{\mathrm{estator}}", "Fator de difusão", "Indicador de difusão aerodinâmica da fileira; compare com o critério adotado para o componente.", "Adimensional"),
        (r"R", "Grau de reação", "Fração da variação de entalpia estática do estágio associada ao rotor, conforme a definição adotada no modelo.", "Adimensional"),
        (r"Z_{\mathrm{rotor}},\;Z_{\mathrm{estator}},\;Z_{\mathrm{bocal}}", "Número de pás", "Quantidade de pás na fileira indicada.", "Pás (inteiro)"),
        (r"r", "Raio da seção", "Posição radial da seção hub, intermediária ou tip.", "m (tabelas: cm)"),
    ],
    "Estações e convenções": [
        (r"1, 2, 3\;\text{(compressor)}", "Estações locais do compressor", "1: entrada do rotor; 2: saída do rotor/entrada do estator; 3: saída do estator.", "—"),
        (r"1, 2, 3\;\text{(turbina)}", "Estações locais da turbina", "1: entrada do bocal; 2: saída do bocal/entrada do rotor; 3: saída do rotor.", "—"),
    ],
}

with st.sidebar:
    guiado = escolher_modo()
    st.header("Parâmetros de entrada")
    exibir_importacao()
    
    with st.expander("📖 Glossário de símbolos e estações"):
        st.caption(
            "Símbolos formatados como em textos técnicos. Os índices das estações são locais "
            "a cada componente; consulte os tooltips para detalhes específicos do caso."
        )
        busca_glossario = st.text_input(
            "Buscar símbolo ou termo", key="busca_glossario",
            placeholder="Ex.: Mach relativo, trabalho, T_{02r}",
        ).strip().casefold()
        busca_simbolo = (
            busca_glossario.replace("\\", "").replace("{", "").replace("}", "")
            .replace("_", "").replace("$", "")
        )
        itens_filtrados = {}
        for categoria, itens in GLOSSARIO.items():
            correspondencias = [
                item for item in itens
                if not busca_glossario
                or busca_glossario in " ".join(item).casefold()
                or busca_simbolo in (
                    " ".join(item).casefold().replace("\\", "")
                    .replace("{", "").replace("}", "").replace("_", "").replace("$", "")
                )
            ]
            if correspondencias:
                itens_filtrados[categoria] = correspondencias

        total_itens = sum(len(itens) for itens in itens_filtrados.values())
        st.caption(f"{total_itens} termo(s) encontrado(s)")
        if total_itens:
            for categoria, itens in itens_filtrados.items():
                st.markdown(f"**{categoria}**")
                linhas = [
                    "| Símbolo | Significado e descrição | Unidade |",
                    "|:--|:--|:--|",
                ]
                for simbolo, nome, descricao, unidade in itens:
                    linhas.append(
                        f"| ${simbolo}$ | **{nome}.** {descricao} | {unidade} |"
                    )
                st.markdown("\n".join(linhas))
        else:
            st.caption("Nenhum termo corresponde à busca.")
    
    with st.container(border=True):
        with st.expander('1 · Condições de operação', expanded=True):
            orientacao_formulario(guiado, 'Defina a entrada de ar e os alvos do ciclo. A vazão de combustível será calculada para atingir a TIT.')
            st.markdown("**Entrada e alvos do ciclo**")
            c1 = c2 = st
            T01 = c1.number_input('Temperatura total de entrada T01 (K)', value=REF_CICLO["T01"], step=5.0,
                help="Temperatura total do ar na entrada do compressor, antes da compressão.", key="T01")
            P01 = c2.number_input('Pressão total de entrada P01 (kPa)', value=REF_CICLO["P01"] / 1e3, step=5.0,
                help="Pressão total do ar na entrada do compressor. O campo é informado em kPa.", key="P01")
            r_compr = c1.number_input('Razão de pressão total do compressor π_total', value=REF_CICLO["r_compr"], step=0.5, min_value=1.1,
                help="Razão entre a pressão total de saída e a de entrada do compressor; é a razão de pressão-alvo do ciclo.", key="r_compr")
            TIT = c2.number_input('Temperatura de entrada da turbina TIT (K)', value=REF_CICLO["TIT"], step=25.0,
                help="Temperatura total na entrada da turbina, definida como a temperatura de saída do combustor.", key="TIT")
            m_dot = st.number_input('Vazão mássica de ar ṁ (kg/s)', value=REF_M_DOT, step=1.0, min_value=0.1,
                help="Vazão mássica de ar na entrada do compressor. O combustível é acrescentado depois, no combustor.", key="m_dot")
            combustivel = c1.selectbox(
                "Combustível", options=list(COMBUSTIVEIS),
                index=list(COMBUSTIVEIS).index(REF_COMBUSTOR["combustivel"]),
                format_func=lambda nome: "Gás natural" if nome == "gas_natural" else nome,
                key="combustivel",
                help=("Combustível disponível no modelo. O poder calorífico e a razão estequiométrica "
                      "são associados automaticamente conforme o catálogo do modelo. A aba Combustor "
                      "explica as fontes e hipóteses de cada propriedade, incluindo valores nominais "
                      "sem fonte específica confirmada. A tabela 2-4 de Mattingly não é uma tabela de PCI."),
            )
        with st.expander('2 · Escolhas de projeto', expanded=True):
            orientacao_formulario(guiado, 'Dimensione o eixo e as turbomáquinas. O modo automático escolhe estágios e ajusta ψ; o modo manual mantém suas escolhas.')
            st.markdown("**Eixo único**")
            c1 = c2 = st
            N_eixo = st.number_input(
                "Rotação do eixo N (rpm)",
                value=REF_COMP["N"], step=500.0, key="N_eixo",
                help=("Velocidade angular do eixo comum. Como o modelo representa um eixo único, "
                      "o mesmo valor de N é aplicado aos rotores do compressor e da turbina."),
            )
            st.caption("A rotação é comum ao compressor e à turbina; U depende também do raio de cada componente.")
            st.markdown("**Compressor**")
            c1 = c2 = st
            HTR_comp = c2.number_input('Razão cubo/ponta de entrada HTR — compressor', value=REF_COMP["HTR"], min_value=0.3, max_value=0.95, step=0.01, key="HTR_comp",
                help="Razão cubo/ponta na entrada. O raio médio aritmético permanece constante; o HTR dos demais estágios é calculado a partir das áreas.")
            auto_ne_comp = c1.checkbox("Calcular nº de estágios automaticamente", value=False, key="auto_ne_comp",
                help="Compara os inteiros vizinhos da estimativa por critérios meanline, radiais e de perfis; ajusta ψ para fechar o trabalho do ciclo. Não garante ausência de avisos.")
            if auto_ne_comp:
                c2.caption("ψ efetivo será ajustado — ver resultado após calcular")
            numero_manual_comp = c2.number_input("Número de estágios — compressor", value=REF_COMP["n_estagios"], min_value=1, step=1, key="ne_comp", disabled=auto_ne_comp,
                help="Número de estágios do compressor, definido manualmente. Não é usado no modo automático.")
            n_estagios_comp = None if auto_ne_comp else numero_manual_comp
            phi_comp = c2.number_input('Coeficiente de vazão φ — compressor', value=REF_COMP["phi"], min_value=0.1, max_value=1.0, step=0.01, key="phi_comp",
                help="Coeficiente de vazão do compressor: velocidade axial média dividida pela velocidade periférica da pá, u_ax/U.")
            psi_comp = c1.number_input('Coeficiente de carga ψ — compressor', value=REF_COMP["psi"], min_value=0.05, max_value=1.0, step=0.01, key="psi_comp",
                help="Coeficiente de carga do compressor: trabalho específico por estágio normalizado por U².")
            alpha1_comp = c2.number_input('Ângulo absoluto de entrada α₁ (°)', value=REF_COMP["alpha1_graus"], step=1.0, key="a1_comp",
                help="Ângulo absoluto de entrada do escoamento no rotor, medido em relação ao eixo da máquina.")
            DF_alvo = c1.number_input('Fator de difusão alvo DF — compressor', value=REF_COMP["DF_alvo"], min_value=0.2, max_value=0.6, step=0.01,
                help="Fator de difusão-alvo usado para estimar a solidez do compressor; valores altos indicam maior difusão e risco de separação.", key="DF_alvo")
            AR_comp = c2.number_input("Razão de aspecto h/c — compressor", value=REF_COMP["AR"], min_value=0.5, step=0.1, key="AR_comp",
                help="Razão entre altura radial da pá h e sua corda c.")
            st.markdown("**Turbina**")
            c1 = c2 = st
            HTR_turb = c2.number_input('Razão cubo/ponta de entrada HTR — turbina', value=REF_TURB["HTR"], min_value=0.3, max_value=0.98, step=0.01, key="HTR_turb",
                help="Razão cubo/ponta na entrada. O raio médio aritmético permanece constante; cubo, ponta e HTR local variam com a área de cada estágio.")
            auto_ne_turb = c1.checkbox("Calcular nº de estágios automaticamente", value=False, key="auto_ne_turb",
                help="Compara os inteiros vizinhos da estimativa por critérios meanline, radiais e de perfis; ajusta ψ para fechar a queda de temperatura do ciclo. Não garante ausência de avisos.")
            if auto_ne_turb:
                c2.caption("ψ efetivo será ajustado — ver resultado após calcular")
            numero_manual_turb = c2.number_input("Número de estágios — turbina", value=REF_TURB["n_estagios"], min_value=1, step=1, key="ne_turb", disabled=auto_ne_turb,
                help="Número de estágios da turbina, definido manualmente. Não é usado no modo automático.")
            n_estagios_turb = None if auto_ne_turb else numero_manual_turb
            phi_turb = c2.number_input('Coeficiente de vazão φ — turbina', value=REF_TURB["phi"], min_value=0.1, max_value=1.0, step=0.01, key="phi_turb",
                help="Coeficiente de vazão da turbina: velocidade axial média dividida pela velocidade periférica da pá, u_ax/U.")
            psi_turb = c1.number_input(
                'Coeficiente de carga ψ — turbina', value=REF_TURB["psi"], min_value=0.1, max_value=3.0, step=0.01,
                key="psi_turb",
                help=(f"Coeficiente de carga da turbina: queda de entalpia por estágio normalizada por U². Ajustado ao caso de referência com {formato_br(REF_M_DOT, f'g')} kg/s de ar e {REF_TURB['n_estagios']} estágios; outras condições podem exigir nova conciliação com o ciclo."),
            )
            alpha2_turb = c2.number_input('Ângulo absoluto de saída do bocal α₂ (°)', value=REF_TURB["alpha2_graus"], step=1.0, key="a2_turb",
                help="Ângulo absoluto do escoamento na saída do bocal e entrada do rotor, medido em relação ao eixo.")
            sigma_turb = c1.number_input('Solidez alvo no raio médio σ — turbina', value=REF_TURB["sigma"], min_value=0.3, step=0.1, key="sigma_turb",
                help="Alvo de corda/passo no raio médio, usado para escolher Z. Após arredondar Z, a solidez construída é Z·c/(2πr) e varia com o raio.")
            AR_turb = c2.number_input("Razão de aspecto h/c — turbina", value=REF_TURB["AR"], min_value=0.5, step=0.1, key="AR_turb",
                help="Razão entre altura radial da pá h e sua corda c.")
            st.markdown("**Discretização radial**")
            c1 = c2 = st
            n_secoes = st.slider("Número de seções radiais", min_value=3, max_value=11, value=REF_N_SECOES, step=2,
                help="Quantidade de posições radiais usadas para distribuir as propriedades entre hub e tip; valores ímpares incluem a seção média.", key="n_secoes")
        with st.expander('3 · Hipóteses e parâmetros do modelo', expanded=True):
            st.markdown('**Propriedades constantes por região**')
            mistura_automatica = st.checkbox('Calcular propriedades dos produtos pela composição (NASA Glenn)', value=True, key='mistura_automatica', help='Calcula produtos completos, f, cp equivalente, R e k. Mantém as propriedades constantes nesta execução. Desative para reproduzir exercícios com propriedades prescritas.')
            cp_ar = st.number_input('Calor específico do ar cp_ar (J/kg·K)', value=REF_CICLO['cp'], min_value=1.0, step=10.0, key='cp_ar', help='Usado no compressor e na entrada do combustor. Constante nesta execução; não é calculado em função da temperatura.')
            cp_gases = st.number_input('Calor específico dos gases cp_gases (J/kg·K)', value=REF_CICLO['cp_gases'], min_value=1.0, step=10.0, key='cp_gases', disabled=mistura_automatica, help='Usado apenas no modo prescrito. No automático, cp resulta da composição e da integral de cp(T) entre 298,15 K e TIT; veja os resultados na aba Combustor.')
            R_ar = st.number_input('Constante do gás — ar R_ar (J/kg·K)', value=REF_CICLO['cp'] * (1 - 1 / REF_CICLO['k']), min_value=0.1, step=1.0, format='%.6f', key='R_ar', disabled=mistura_automatica, help='Modo prescrito: R < cp. No automático, R do ar é calculado pela mesma composição seca N2/O2/Ar usada no balanço químico.')
            R_gases = st.number_input('Constante do gás — gases R_gases (J/kg·K)', value=REF_CICLO['R_gases'], min_value=0.1, step=1.0, format='%.6f', key='R_gases', disabled=mistura_automatica, help='Usado apenas no modo prescrito. No automático, R=Ru/M da mistura calculada.')
            if mistura_automatica:
                st.caption('Automático: os três campos desativados não são usados. R do ar vem da composição seca; cp dos gases equivale à entalpia sensível NASA de 298,15 K até TIT. cp e k ficam constantes na expansão; não há equilíbrio químico, dissociação ou cinética.')
            elif R_ar < cp_ar and R_gases < cp_gases:
                st.caption(f"k do ar = {formato_br(cp_ar/(cp_ar-R_ar), '.6f')}; k dos gases = {formato_br(cp_gases/(cp_gases-R_gases), '.6f')}. Propriedades constantes; h_ar = cp_ar·T e h_gases = cp_gases·T, com origem convencional comum. Sem entalpia sensível do combustível, dissociação ou composição calculada.")
            else:
                st.error('Cada constante R deve ser menor que o cp correspondente.')
            orientacao_formulario(guiado, 'Eficiências, perdas e Mach prescrito são hipóteses de entrada, não resultados de uma simulação detalhada.')
            st.markdown("**Eficiências e limite de temperatura**")
            c1 = c2 = st
            e_compr = c1.number_input('Eficiência politrópica do compressor η_compr', value=REF_CICLO["e_compr"], min_value=0.5, max_value=1.0, step=0.01,
                help="Eficiência politrópica adotada para representar as perdas durante a compressão.", key="e_compr")
            e_turb = c2.number_input('Eficiência politrópica da turbina η_turb', value=REF_CICLO["e_turb"], min_value=0.5, max_value=1.0, step=0.01,
                help="Eficiência politrópica adotada para representar as perdas durante a expansão na turbina.", key="e_turb")
            TIT_max = c2.number_input('Limite de temperatura adotado TIT máx. (K)', value=REF_CICLO["TIT_máx"], step=25.0,
                help="Limite de temperatura usado para verificar a entrada de TIT no ciclo.", key="TIT_max")
            st.markdown("**Combustor simplificado**")
            c1 = c2 = st
            eta_b = c2.number_input(
                "Eficiência de combustão η_b", min_value=dc.ETA_COMBUSTOR[0], max_value=dc.ETA_COMBUSTOR[1],
                value=REF_COMBUSTOR["eta_b"], step=0.005, format="%.3f", key="eta_b",
                help=("Mattingly, Elements of Propulsion, Exemplo 7.8, usa η_b = 0,99 como dado "
                      f"de um caso analisado — não como faixa universal. O intervalo {_numero_br(dc.ETA_COMBUSTOR[0], 2)}–{_numero_br(dc.ETA_COMBUSTOR[1], 2)} é "
                      "a faixa de entrada/aviso adotada nesta ferramenta."),
            )
            M_entrada = c1.number_input(
                'Mach prescrito na entrada do combustor M_entrada', min_value=0.001, max_value=0.20,
                value=REF_COMBUSTOR["M_entrada"], step=0.005, format="%.3f", key="M_entrada",
                help=("Valor prescrito pelo usuário; não é calculado a partir da saída do compressor. "
                      "O modelo não inclui o difusor entre compressor e combustor, portanto não calcula "
                      "a desaceleração do escoamento nesse trecho. "
                      "Orientação de Mattingly, Elements of Propulsion, §10.6.6: manter M < 0,10 "
                      "para obter razão de pressão total razoável (>0,975) nas condições estudadas. "
                      "É uma referência contextual, não um limite universal; o modelo emite aviso acima de 0,10."),
            )
            Delta_P_cc = c2.number_input(
                'Perda relativa de pressão do combustor ΔP (fração)', min_value=0.0, max_value=0.30,
                value=REF_CICLO["Delta_P_cc"], step=0.01, key="Delta_P_cc",
                help=("Fração da pressão total perdida; 0,05 corresponde a 5% e determina P03 a partir de P02. "
                      "O padrão atual é 5%; 0–30% é o intervalo de exploração da interface, não uma faixa "
                      "universal recomendada pela literatura. Mattingly trata a perda como desempenho "
                      "específico do combustor (π_b), dependente das condições e do projeto."),
            )
            st.caption("Hipóteses fixas: gás ideal com propriedades constantes do modelo; transmissão mecânica ideal; difusor não modelado. O Mach do combustor é prescrito. Critérios e faixas de aviso permanecem nos painéis de verificações.")
        submitted = st.button("Calcular e atualizar gráficos", width="stretch",
            help="Executa o caso com os parâmetros informados e atualiza resultados e curvas de sensibilidade.")

    parametros_atuais = parametros_dos_campos(st.session_state)
    exibir_salvar_rascunho(parametros_atuais)
    if submitted:
        if not mistura_automatica and (R_ar >= cp_ar or R_gases >= cp_gases):
            st.error('Não foi calculado: exige 0 < R < cp em cada fluido.')
            st.stop()
        params = dict(
            T01=T01, P01=P01, r_compr=r_compr, TIT=TIT, e_compr=e_compr, e_turb=e_turb,
            Delta_P_cc=Delta_P_cc, TIT_max=TIT_max, m_dot=m_dot,
            cp_ar=cp_ar, cp_gases=cp_gases, R_ar=R_ar, R_gases=R_gases,
            mistura_automatica=mistura_automatica,
            combustivel=combustivel, eta_b=eta_b, M_entrada=M_entrada,
            N_comp=N_eixo, HTR_comp=HTR_comp, 
            n_estagios_comp=int(n_estagios_comp) if n_estagios_comp is not None else None,
            phi_comp=phi_comp, psi_comp=psi_comp, alpha1_comp=alpha1_comp,
            DF_alvo=DF_alvo, AR_comp=AR_comp,
            N_turb=N_eixo, HTR_turb=HTR_turb, 
            n_estagios_turb=int(n_estagios_turb) if n_estagios_turb is not None else None,
            phi_turb=phi_turb, psi_turb=psi_turb, alpha2_turb=alpha2_turb,
            sigma_turb=sigma_turb, AR_turb=AR_turb,
            n_secoes=int(n_secoes),
        )
        caso_referencia = montar_caso_referencia(params)
        iniciada_em = datetime.now().astimezone()
        assinatura = hashlib.sha256(
            repr(sorted(params.items())).encode("utf-8")
        ).hexdigest()[:8]
        st.session_state["ultima_execucao"] = {
            "id": f"{iniciada_em.strftime('%Y%m%d-%H%M%S-%f')}-{assinatura}",
            "iniciada_em": iniciada_em,
            "parametros": params.copy(),
            "etapas": _novo_estado_etapas(),
            "nome_caso": st.session_state.get('nome_caso','Meu caso'),
            "contexto_modelo": contexto_modelo(),
        }
        st.session_state.pop('relatorio_preparado',None)
        estado_etapas = st.session_state["ultima_execucao"]["etapas"]
        st.session_state["caso_referencia"] = caso_referencia
        st.session_state.update(caso_referencia)
        st.session_state["sensibilidade"] = None
        st.session_state["erro_sensibilidade"] = None
        try:
            with st.spinner("Rodando pipeline (ciclo → compressor → combustor → turbina → radial → perfis → loft)..."):
                st.session_state["resultados"] = _rodar_pipeline(params, estado_etapas)
            st.session_state["erro"] = None
        except (ValueError, RuntimeError) as e:
            st.session_state["resultados"] = None
            st.session_state["erro"] = str(e)
        if st.session_state["resultados"] is not None:
            try:
                estado_etapas["sensibilidade"] = "Em execução"
                with st.spinner("Recalculando as curvas de sensibilidade para estes parâmetros..."):
                    st.session_state["sensibilidade"] = executar_varreduras(caso_referencia)
                estado_etapas["sensibilidade"] = "Calculada"
            except (ValueError, RuntimeError) as e:
                estado_etapas["sensibilidade"] = "Falhou"
                st.session_state["erro_sensibilidade"] = str(e)


# ══════════════════════════════════════════════════════════════════════════
# EXIBIÇÃO DOS RESULTADOS
# ══════════════════════════════════════════════════════════════════════════

exibir_pendencias(parametros_atuais, st.session_state.get('ultima_execucao'))

if st.session_state.get("erro"):
    _exibir_estado_execucao()
    st.error(aviso_br(f"Combinação de parâmetros inviável: {st.session_state['erro']}"))

elif st.session_state.get("resultados") is not None:
    if not hasattr(st.session_state['resultados']['ciclo'], 'dados_mistura'):
        st.info('As propriedades do modelo foram atualizadas. Confira as entradas e clique em Calcular e atualizar gráficos para gerar resultados compatíveis. Seus campos foram preservados.')
        st.stop()
    _exibir_estado_execucao()
    r = st.session_state["resultados"]
    ciclo, comp, rad_comp, maquina_comp = r["ciclo"], r["comp"], r["rad_comp"], r["maquina_comp"]
    turb, rad_turb, maquina_turb = r["turb"], r["rad_turb"], r["maquina_turb"]
    diagnosticos = r.get("diagnosticos") or diagnosticar_integracao(ciclo, comp, turb, r["combustor"])

    aba_ciclo, aba_combustor, aba_comp, aba_turb, aba_sensibilidade, aba_comparacao, aba_3d, aba_verificacoes, aba_download = st.tabs(
        ["Ciclo", "Combustor", "Compressor", "Turbina", "Sensibilidade", "Comparar projetos", "Geometria 3D", "Verificações", "Downloads"]
    )
    
    # ------------------------------------------------------------------
    # ABA: CICLO
    # ------------------------------------------------------------------
    with aba_ciclo:
        exibir_guia("Ciclo", guiado)
        _painel_verificacoes(
            st, r.get("avisos_detalhados", []), {"Ciclo", "Sistema"},
            "Verificações do ciclo e avisos gerais do sistema",
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("η sobre calor útil", f"{formato_br(ciclo.eta_ciclo * 100, f'.2f')} %",
                    help="Indicador eta_ciclo existente: potência líquida dividida pelo calor útil transferido aos gases. A eficiência sobre PCI está no painel de indicadores abaixo.")
        col2.metric("w_líq por kg de ar", f"{formato_br(ciclo.w_líq / 1000.0, f'.1f')} kJ/kg")
        col3.metric("BWR", f"{formato_br(ciclo.BWR, f'.3f')}", help="Potência consumida pelo compressor dividida pela potência produzida pela turbina, considerando suas vazões distintas.")
        col4.metric("Ẇ_líq", f"{formato_br(ciclo.W_líq / 1000.0, f'.1f')} kW")

        st.dataframe(tabela_br(pd.DataFrame([{
            "T01 (K)": ciclo.T01, "P01 (kPa)": ciclo.P01/1e3,
            "T02r (K)": round(ciclo.T02r, 1), "P02 (kPa)": round(ciclo.P02/1e3, 1),
            "TIT (K)": ciclo.TIT, "P03 (kPa)": round(ciclo.P03/1e3, 1),
            "T04r (K)": round(ciclo.T04r, 1), "P04 (kPa)": round(ciclo.P04/1e3, 1),
            "ṁ_ar (kg/s)": round(ciclo.m_dot_ar, 4),
            "ṁ_f (kg/s)": round(ciclo.m_dot_f, 4),
            "ṁ_turbina (kg/s)": round(ciclo.m_dot_turbina, 4),
        }])), width="stretch")

        interpretar_ciclo(ciclo, guiado)
        indicadores = exibir_indicadores(ciclo, r["combustor"])
        exibir_balanco_energetico(ciclo)
        exibir_origem_criterios()
        _painel_fechamento_global(diagnosticos)
        exibir_visao_ciclo(ciclo)

    # ------------------------------------------------------------------
    # ABA: COMBUSTOR 1D
    # ------------------------------------------------------------------
    with aba_combustor:
        exibir_guia("Combustor", guiado)
        combustor = r["combustor"]
        _painel_verificacoes(
            st, r.get("avisos_detalhados", []), {"Combustor"},
            "Verificações do combustor",
        )
        st.subheader("Câmara de combustão — modelo 1D simplificado")
        st.caption(
            "O combustor já participa do caso calculado: recebe as condições termodinâmicas "
            "de saída do compressor no modelo do ciclo, comparadas ao meanline no painel de fechamento, "
            "eleva a temperatura até a TIT definida no ciclo e envia ar + combustível à turbina. "
            "Combustível, eficiência, Mach de entrada e perda de pressão são definidos no formulário; "
            "a cada execução, os resultados são recalculados com esses valores."
        )
        st.info(
            "**Limitação de escopo — difusor não modelado.** O modelo não calcula a passagem "
            "entre a descarga do compressor e a zona de entrada do combustor. Assim, não representa "
            "a desaceleração do escoamento nem uma perda de pressão própria desse trecho. "
            "O Mach de entrada mostrado abaixo é prescrito no formulário e usado no dimensionamento "
            "1D da área do combustor; ele não é derivado do Mach de saída do compressor. "
            "A perda `ΔP combustor` representa apenas a perda global atribuída ao combustor no ciclo, "
            "sem uma parcela separada para um difusor."
        )

        st.markdown("#### Parâmetros e mistura")
        with st.expander('Propriedades utilizadas — ar e gases'):
            st.table(tabela_br(pd.DataFrame([{'Fluido': nome, **dados} for nome, dados in ciclo.propriedades().items()])), hide_index=True)
            st.caption('Valores efetivamente usados. Automático: cp equivalente pela integral NASA de 298,15 K a TIT, com composição congelada; R=Ru/M. São constantes na expansão, não cp(T) integrado na turbina. Modo prescrito: cp/R informados, com h=cp·T legado.')
        if combustor.dados_mistura is not None:
            mistura=combustor.dados_mistura
            with st.expander('Como a composição determina cp, R e k — NASA Glenn'):
                st.write(mistura['composicao_combustivel']['fonte'])
                st.caption('O cp calculado é o dos produtos de combustão, não o do combustível puro. Ar seco: 78,084% N₂, 20,9795% O₂ e 0,9365% Ar em mol; CO₂-traço omitido. Produtos em base úmida, incluindo vapor de água. Combustão completa pobre/estequiométrica; sem dissociação, fuligem, NOx ou biodiesel.')
                st.table(tabela_br(pd.DataFrame([{'Espécie':s,'Fração molar':z,'Fração mássica':mistura['fracoes_massicas'][s]} for s,z in mistura['fracoes_molares'].items()])),hide_index=True)
                st.write(f"Excesso global de ar: {formato_br(mistura['excesso_ar_pct'], '.2f')}%; λ = {formato_br(mistura['lambda_ar'], '.4f')}. Referência de entalpia: 298,15 K; limite superior do cp equivalente: {formato_br(combustor.TIT,'.2f')} K.")
                st.latex(r'\bar c_{p,g}=\frac{\int_{298{,}15}^{TIT} c_{p,\mathrm{mix}}(T)\,dT}{TIT-298{,}15},\quad R_g=R_u/M_{\mathrm{mix}},\quad k_g=\bar c_{p,g}/(\bar c_{p,g}-R_g)')
                st.caption('Fonte dos coeficientes: NASA/TP-2002-211556, Eq.1 p.2; CO₂ p.85, H₂O p.131, N₂ p.156, O₂ p.166. Os sete termos são usados. Argônio: cp molar=5Ru/2. f e composição são conciliados pelo balanço de energia; η_b representa fração de calor aproveitada, não queima parcial de espécies.')
                st.info('JP-8 e diesel usam o mesmo substituto elementar C₁₂H₂₃; não são combustíveis idênticos. Seus PCI distintos produzem f e propriedades diferentes neste cálculo. Para mesmo f e mesma temperatura, as propriedades coincidem: o modelo não distingue aditivos, estrutura molecular ou lote.')
        _tabela_didatica(st, [
            ("Combustível", "Gás natural" if combustor.combustivel == "gas_natural" else combustor.combustivel,
             "Tipo escolhido no formulário. O poder calorífico e a razão estequiométrica correspondentes são obtidos da tabela de combustíveis do modelo."),
            ("Eficiência de combustão η_b", f"{formato_br(combustor.eta_b, f'.1%')}",
             "Fração da energia química transferida aos gases no modelo. O valor vem do formulário; Mattingly usa 0,99 em um exemplo, sem definir isso como faixa universal."),
            ("Poder calorífico h_PR", f"{formato_br(combustor.h_PR / 1000000.0, f'.2f')} MJ/kg",
             "Poder calorífico inferior (PCI) usado no balanço, por massa de combustível. Pode ser publicado, aproximado ou adotado; consulte as fontes por propriedade abaixo."),
            ("Razão estequiométrica f_stoich", f"{formato_br(combustor.f_stoich, f'.4f')} kg/kg",
             "Razão combustível/ar de referência para combustão estequiométrica completa; usada no cálculo de φ_eq."),
            ("Mach de entrada M_entrada", f"{formato_br(combustor.M_entrada, f'.3f')}",
             "Valor prescrito no formulário, não calculado a partir da saída do último estágio do compressor. A orientação contextual de Mattingly é manter M abaixo de 0,10 nas condições discutidas."),
            ("Razão combustível/ar f", f"{formato_br(combustor.f, f'.5f')} kg/kg",
             "Massa de combustível necessária por unidade de massa de ar para atingir a TIT, calculada pelo balanço de energia adotado."),
            ("Razão de equivalência φ_eq", f"{formato_br(combustor.phi_eq, f'.3f')}",
             "Razão combustível/ar calculada dividida pela razão estequiométrica. Abaixo de 1 indica mistura global pobre; não garante estabilidade da chama."),
        ])

        with st.expander("Fontes e hipóteses do combustível", expanded=False):
            fontes = combustor.fontes_combustivel()
            st.table(tabela_br(pd.DataFrame([
                {"Propriedade": "PCI h_PR", "Valor usado": f"{formato_br(fontes['h_PR']['valor'] / 1000000.0, f'.4f')} MJ/kg",
                 "Situação da origem": fontes["h_PR"]["status"]},
                {"Propriedade": "f_stoich", "Valor usado": f"{formato_br(fontes['f_stoich']['valor'], f'.4f')} kg/kg",
                 "Situação da origem": fontes["f_stoich"]["status"]},
            ]).set_index("Propriedade")))
            for chave, nome in (("h_PR", "PCI"), ("f_stoich", "Razão estequiométrica")):
                dado = fontes[chave]
                st.markdown(f"**{nome} — origem.** {dado['origem']}")
                st.caption(dado["hipotese"])
            st.caption(
                "Os dados acompanham o combustível desta execução. Um valor nominal não representa "
                "todos os lotes ou composições reais. Gás natural e diesel mantêm PCI adotados no "
                "projeto, com fonte específica pendente; não são apresentados como dados validados "
                "dos livros. A tabela 2-4 de Mattingly contém constantes de propriedades de ar/gases, "
                "não os PCI deste catálogo."
            )

        st.markdown("#### Condições e vazões")
        col_cond, col_vazoes = st.columns(2)
        with col_cond:
            _tabela_didatica(col_cond, [
                ("Temperatura total de entrada T₀₂ᵣ", f"{formato_br(combustor.T02r, f'.2f')} K",
                 "Temperatura total usada pelo combustor, obtida na saída real do compressor do ciclo. No modo manual pode diferir da saída meanline; consulte o fechamento."),
                ("Temperatura de saída TIT", f"{formato_br(combustor.TIT, f'.2f')} K",
                 "Temperatura total dos gases na saída do combustor e entrada da turbina; vem do parâmetro TIT do ciclo."),
                ("Pressão total de entrada P₀₂", f"{formato_br(combustor.P_entrada / 1000.0, f'.2f')} kPa",
                 "Pressão total na entrada do combustor, igual à pressão total de saída do compressor neste modelo."),
                ("Pressão total de saída P₀₃", f"{formato_br(combustor.P_saida / 1000.0, f'.2f')} kPa",
                 "Pressão após o combustor, determinada por P02 e pela perda relativa ΔP informada no ciclo."),
                ("Perda relativa de pressão ΔP", f"{formato_br(combustor.Delta_P, f'.2%')}",
                 "Queda de pressão total aplicada como fração: P03 = P02 × (1 − ΔP). Não é calculada por uma correlação própria do combustor."),
                ("Aumento de temperatura ΔTₜ", f"{formato_br(combustor.delta_Tt, f'.2f')} K",
                 "Diferença entre TIT e a temperatura total de entrada T02r."),
            ])
        with col_vazoes:
            _tabela_didatica(col_vazoes, [
                ("Vazão de ar ṁ_ar", f"{formato_br(combustor.m_dot_ar, f'.5f')} kg/s",
                 "Vazão recebida do compressor; é a base usada para definir a razão combustível/ar."),
                ("Vazão de combustível ṁ_f", f"{formato_br(combustor.m_dot_f, f'.5f')} kg/s",
                 "Vazão de combustível calculada como f multiplicado pela vazão de ar ṁ_ar."),
                ("Vazão total ṁ_total", f"{formato_br(combustor.m_dot_tot, f'.5f')} kg/s",
                 "Soma das vazões de ar e combustível, sem sangrias ou extrações neste modelo."),
                ("Vazão enviada à turbina ṁ_turbina", f"{formato_br(combustor.m_dot_turbina, f'.5f')} kg/s",
                 "Vazão de gases passada ao cálculo da turbina; atualmente igual à vazão total do combustor."),
            ])

        st.markdown("#### Energia e fechamento do balanço")
        q_combustivel = combustor.m_dot_f * combustor.h_PR * combustor.eta_b
        q_gases = combustor.calor_balanco()
        residuo_energia = q_combustivel - q_gases
        residuo_pct = 100 * residuo_energia / q_combustivel if q_combustivel else 0.0
        _tabela_didatica(st, [
            ("Energia útil do combustível", f"{formato_br(q_combustivel / 1000.0, f'.2f')} kW",
             "ṁ_f × h_PR × η_b: parcela da energia química do combustível disponibilizada aos gases segundo a eficiência adotada."),
            ("Indicador auxiliar: aquecimento virtual do ar", f"{formato_br(combustor.Q_total / 1000.0, f'.2f')} kW",
             "Q_total: ṁ_ar × cp_ar × (TIT − T02r). Indicador auxiliar que mantém ar nas duas temperaturas; não inclui a mudança de propriedades nem a massa de combustível. Não é o balanço do combustor."),
            ("Aumento de entalpia dos gases¹", f"{formato_br(q_gases / 1000.0, f'.2f')} kW",
             "ṁ_g cp_g (TIT − T_ref) − ṁ_ar cp_ar (T02 − T_ref), incluindo a massa de combustível. T_ref=298,15 K no automático; zero convencional no modo prescrito."),
            ("Resíduo relativo do balanço¹", f"{formato_br(residuo_pct, f'.3g')}%",
             "Diferença percentual entre a energia útil do combustível e o aumento de entalpia dos gases; o fechamento decorre da equação usada para calcular f."),
            ("Resíduo absoluto do balanço¹", f"{formato_br(residuo_energia / 1000.0, f'.6f')} kW",
             "Diferença em potência entre a energia útil do combustível e a variação de entalpia calculada para os gases."),
        ])
        st.caption(
            "¹ Verificação com cp constantes e entalpias sensíveis relativas a 298,15 K no automático; no modo prescrito, conserva-se h=cp·T. "
            "O resíduo avalia o balanço usado para obter f; o aumento aproximado da entalpia do ar "
            "é uma grandeza distinta e não deve ser somado à energia do combustível."
        )

        st.markdown("#### Dimensões estimadas")
        _tabela_didatica(st, [
            ("Área transversal", f"{formato_br(combustor.A_comb * 10000.0, f'.2f')} cm²",
             "Área calculada pela relação de vazão compressível (MFP), usando pressão, temperatura, vazão de ar e Mach de entrada prescritos."),
            ("Diâmetro equivalente", f"{formato_br(combustor.D_comb * 100, f'.2f')} cm",
             "Diâmetro circular equivalente à área calculada; não representa a geometria interna real da câmara."),
            ("Comprimento estimado", f"{formato_br(combustor.L_comb * 100, f'.2f')} cm",
             f"Escala relativa ao combustor {COMBUSTOR_REF['nome']}, usando P02 de ENTRADA e TIT. Não é dimensionamento detalhado ou comprovação de estabilidade da chama."),
        ])

        with st.expander("Como o comprimento é estimado — referência JT9D", expanded=False):
            st.latex(r"L=L_{\mathrm{ref}}\left(\frac{P_{02}}{P_{\mathrm{entrada,ref}}}\right)^{-r}\sqrt{\frac{T_{\mathrm{saida,ref}}}{TIT}}")
            st.markdown(
                "**Correspondência das estações.** Na Eq. 10-34 de Mattingly, `Pt3` é a pressão "
                "total na entrada do combustor: corresponde a `P02` neste projeto. A temperatura "
                "`Tt4` do livro corresponde à nossa `TIT`. A pressão de saída `P03` não é usada "
                "nesta escala de comprimento."
            )
            _tabela_didatica(st, [
                ("Pressão de entrada usada nesta execução", f"{formato_br(combustor.P02 / 1000.0, f'.2f')} kPa",
                 "P02 atual do ciclo; corresponde a Pt3 na notação de Mattingly."),
                ("Comprimento de referência L_ref", f"{formato_br(COMBUSTOR_REF['L_ref'] * 100, f'.4f')} cm",
                 "Valor convertido e arredondado de 17,3 in para o JT9D."),
                ("Pressão de entrada de referência", f"{formato_br(COMBUSTOR_REF['Pt3_ref'] / 1000.0, f'.2f')} kPa",
                 "Valor convertido e arredondado de 316 psia; pressão absoluta na entrada da câmara de referência."),
                ("Temperatura de saída de referência", f"{formato_br(COMBUSTOR_REF['Tt4_ref'], f'.2f')} K",
                 "Valor convertido e arredondado de 2865 °R; corresponde à TIT da referência."),
                ("Expoente r", f"{formato_br(COMBUSTOR_REF['r_exp'], f'.3f')}",
                 "Expoente da Eq. 10-34 para n = 1, mantido como hipótese da escala."),
            ])
            st.caption(
                "Fonte: Mattingly, Elements of Gas Turbine Propulsion, Eq. 10-34, p. 821, e tabela "
                "10-5/exemplo JT9D, p. 822 (PDF local 886–887). Supõe projetos semelhantes, inclusive "
                "razão A4/Aref constante. A derivação usa escoamento estrangulado na entrada da "
                "turbina; o modelo atual não verifica essa condição nem a semelhança geométrica. "
                "Vazão e Mach influenciam a área calculada, mas não entram diretamente nesta escala. "
                "O comprimento é uma estimativa condicionada a essas hipóteses."
            )

        with st.expander("Como interpretar: equações, hipóteses e limitações", expanded=False):
            st.markdown(
                "**Razão combustível/ar.** O modelo calcula `f` pelo balanço de energia "
                "incluindo a vazão de combustível nos gases de saída:"
            )
            st.latex(r"f = \frac{c_{p,g}(TIT-T_{ref})-c_{p,a}(T_{02r}-T_{ref})}{\eta_b h_{PR}-c_{p,g}(TIT-T_{ref})}")
            st.caption('T_ref = 298,15 K no automático. No modo prescrito legado, T_ref = 0 K é uma convenção algébrica. No automático, f e composição são resolvidos conjuntamente, pois cp equivalente depende da composição.')
            st.markdown(
                "`φ_eq = f/f_stoich` compara a mistura calculada com a razão estequiométrica "
                "do combustível. Valor abaixo de 1 indica mistura global pobre; não é, sozinho, "
                "um critério completo de estabilidade ou segurança de combustão.\n\n"
                "**Grandezas de energia.** `Energia útil do combustível` é "
                "`ṁ_f h_PR η_b`. `Aumento de entalpia dos gases` aplica o balanço com "
                "`ṁ_ar + ṁ_f` na saída e deve coincidir com essa energia dentro das hipóteses "
                "e do arredondamento numérico. O valor chamado `Q_total` no núcleo é exibido "
                "como aquecimento virtual do ar: `ṁ_ar cp_ar (TIT − T₀₂ᵣ)`. "
                "Esse indicador auxiliar desconsidera tanto a mudança de cp quanto a massa de combustível; "
                "por isso, não é o mesmo que o calor útil total liberado pelo combustível."
            )
            st.markdown(
                f"**Hipóteses do modelo atual.** Gás ideal com propriedades constantes por região; `k=cp/(cp−R)`. No automático, composição completa congelada e entalpias sensíveis relativas a 298,15 K; no modo prescrito, conserva-se a convenção legada `h=cp·T`. `η_b` representa a fração da energia do PCI aproveitada no balanço, sem calcular combustível parcialmente queimado. Combustível sem entalpia sensível explícita; Mach prescrito em {formato_br(combustor.M_entrada, '.3f')}; sem equilíbrio químico, dissociação ou emissões."
            )
            st.markdown(
                "**Pressão e geometria.** A perda de pressão não é calculada por uma correlação "
                "do combustor: `ΔP` é a entrada do ciclo e determina `P₀₃`. A área e o diâmetro "
                "equivalente vêm da relação de vazão compressível (MFP) sob as condições de entrada. "
                f"O comprimento é uma estimativa de escala baseada na referência {COMBUSTOR_REF['nome']}, "
                "com pressão de entrada P02 e TIT, e não um dimensionamento detalhado."
            )
            st.markdown(
                "**Limitações.** O modelo não resolve zonas primária, secundária ou de diluição, "
                "atomização e evaporação do combustível, cinética química, emissões, distribuição "
                "local de temperatura, estabilidade da chama, resfriamento das paredes nem uma "
                "correlação independente para a perda de pressão. A geometria é preliminar e depende "
                "das hipóteses simplificadoras acima."
            )

    # ------------------------------------------------------------------
    # ABA: COMPRESSOR (dados à esquerda, imagem à direita, por estágio)
    # ------------------------------------------------------------------
    with aba_comp:
        exibir_guia("Compressor", guiado)
        _painel_verificacoes(
            st, r.get("avisos_detalhados", []), {"Compressor"},
            "Verificações do compressor",
        )
        _painel_estagios_didatico(st, comp, comp.pi_total_calc, comp.r_compr)
        _paineis_diagnostico_componente(diagnosticos["componentes"]["Compressor"])
        exibir_triangulos(rad_comp, "Compressor", r.get("avisos_detalhados", []))
        _painel_perfis_didatico(rad_comp, r.get("perfis_comp"), "Compressor")
        i = exibir_comparacao_estagios(comp, rad_comp, "Compressor")
        exibir_distribuicao_radial(rad_comp, "Compressor", i)
        with st.expander(f"Estágio em foco {i + 1}  —  π={formato_br(comp.pi_estagio[i], f'.3f')}, Z_rotor={comp.Z_rotor[i]}, Z_estator={comp.Z_estator[i]}"):
            col_dados, col_img = st.columns([1.3, 1])
            with col_dados:
                st.dataframe(tabela_br(_tabela_estagio_compressor(rad_comp, i)), width="stretch", hide_index=True)
            with col_img:
                peca_rotor = maquina_comp.pecas[2*i]
                peca_estator = maquina_comp.pecas[2*i + 1]
                fig = _figura_par_pa(
                    peca_rotor, "#3366CC", peca_estator, "#E69138",
                    f"Estágio {i+1} — rotor (azul) / estator (laranja)",
                )
                st.pyplot(figura_br(fig), width="stretch")
                plt.close(fig)

    # ------------------------------------------------------------------
    # ABA: TURBINA
    # ------------------------------------------------------------------
    with aba_turb:
        exibir_guia("Turbina", guiado)
        _painel_verificacoes(
            st, r.get("avisos_detalhados", []), {"Turbina"},
            "Verificações da turbina",
        )
        _painel_estagios_didatico(st, turb, turb.pi_total_calc, turb.r_turb)
        _paineis_diagnostico_componente(diagnosticos["componentes"]["Turbina"])
        _painel_continuidade_turbina(turb)
        exibir_triangulos(rad_turb, "Turbina", r.get("avisos_detalhados", []))
        _painel_perfis_didatico(rad_turb, r.get("perfis_turb"), "Turbina")
        i = exibir_comparacao_estagios(turb, rad_turb, "Turbina")
        exibir_distribuicao_radial(rad_turb, "Turbina", i)
        with st.expander(f"Estágio em foco {i + 1}  —  π={formato_br(turb.pi_estagio[i], f'.3f')}, Z_bocal={turb.Z_bocal[i]}, Z_rotor={turb.Z_rotor[i]}"):
            col_dados, col_img = st.columns([1.3, 1])
            with col_dados:
                st.dataframe(tabela_br(_tabela_estagio_turbina(rad_turb, i)), width="stretch", hide_index=True)
            with col_img:
                peca_bocal = maquina_turb.pecas[2*i]
                peca_rotor = maquina_turb.pecas[2*i + 1]
                fig = _figura_par_pa(
                    peca_bocal, "#E69138", peca_rotor, "#3366CC",
                    f"Estágio {i+1} — bocal (laranja) / rotor (azul)",
                )
                st.pyplot(figura_br(fig), width="stretch")
                plt.close(fig)

    # ------------------------------------------------------------------
    # ABA: SENSIBILIDADE (recalculada para os parâmetros desta execução)
    # ------------------------------------------------------------------
    with aba_sensibilidade:
        exibir_guia("Sensibilidade", guiado)
        sens = st.session_state.get("sensibilidade")
        caso = st.session_state.get("caso_referencia")
        erro_sens = st.session_state.get("erro_sensibilidade")

        if erro_sens:
            st.warning(aviso_br(f"Não foi possível concluir as curvas de sensibilidade: {erro_sens}"))
        elif sens is None or caso is None:
            st.info("Envie o formulário para calcular o projeto e atualizar os gráficos de sensibilidade.")
        else:
            exibir_contexto_sensibilidade(sens,st.session_state['ultima_execucao']['parametros'])
            st.caption(
                f"Referência desta execução: ṁ_ar={formato_br(caso['REF_M_DOT'], f'g')} kg/s, ψ compressor={formato_br(caso['REF_COMP']['psi'], f'g')}, ψ turbina={formato_br(caso['REF_TURB']['psi'], f'g')}, combustível={caso['REF_COMBUSTOR']['combustivel']}, η_b={formato_br(caso['REF_COMBUSTOR']['eta_b'], f'.3f')}, M entrada={formato_br(caso['REF_COMBUSTOR']['M_entrada'], f'.3f')}, ΔP combustor={formato_br(caso['REF_CICLO']['Delta_P_cc'], f'.1%')}. As estrelas indicam o resultado calculado no caso de referência atual."
            )
            st.caption(
                "As faixas sombreadas são comparações adotadas no projeto, não exigências universais da literatura. "
                "DF usa uma triagem empírica de difusão; Mach = 1 indica condição sônica local, sem aprovar o projeto. "
                "No compressor, o gráfico de reação mostra o mínimo radial, enquanto a faixa do verificador é aplicada ao meanline. "
                "No modo automático, cada ponto pode adotar outro número de estágios; isso pode produzir saltos nas curvas."
            )

            def exibir_serie(coluna, resultados, parametro, metrica, titulo,
                             xlabel, ylabel, referencia, **opcoes):
                figura = plot_serie(
                    resultados, parametro, metrica, titulo, xlabel, ylabel,
                    arquivo=None, valor_referencia=referencia, **opcoes,
                )
                coluna.pyplot(figura_br(figura), width="stretch")
                plt.close(figura)

            def exibir_duplo(coluna, resultados, parametro, metrica_esq, metrica_dir,
                             titulo, xlabel, ylabel_esq, ylabel_dir, referencia):
                figura = plot_duplo_eixo(
                    resultados, parametro, metrica_esq, metrica_dir, titulo, xlabel,
                    ylabel_esq, ylabel_dir, arquivo=None, valor_referencia=referencia,
                )
                coluna.pyplot(figura_br(figura), width="stretch")
                plt.close(figura)

            sub_comp, sub_turb, sub_ciclo = st.tabs(["Compressor", "Turbina", "Ciclo"])

            with sub_comp:
                c1, c2 = st.columns(2)
                exibir_serie(c1, sens["comp_phi"], "phi", "DF_rotor_max",
                    "DF máximo do rotor vs φ", "φ", "DF rotor máximo",
                    caso["REF_COMP"]["phi"], linha_limite=dc.DF_MAX,
                    rotulo_limite=f"Critério de difusão (DF={_numero_br(dc.DF_MAX, 1)})")
                exibir_serie(c2, sens["comp_phi"], "phi", "reacao_min",
                    "Reação mínima vs φ", "φ", "Grau de reação mínimo",
                    caso["REF_COMP"]["phi"], faixa_recomendada=dc.REACAO_COMP)
                c1, c2 = st.columns(2)
                exibir_serie(c1, sens["comp_htr"], "HTR", "M1R_max",
                    "Mach relativo máximo vs HTR de entrada", "HTR de entrada", "M1R máximo",
                    caso["REF_COMP"]["HTR"], linha_limite=dc.MACH_SONICO,
                    rotulo_limite=f"Limite sônico (M={formato_br(dc.MACH_SONICO, f'g')})")
                exibir_serie(c2, sens["comp_psi"], "psi", "Z_rotor_min",
                    "Número mínimo de pás do rotor vs ψ", "ψ", "Z rotor mínimo",
                    caso["REF_COMP"]["psi"])

            with sub_turb:
                c1, c2 = st.columns(2)
                exibir_serie(c1, sens["turb_psi"], "psi", "M3R_max",
                    "Mach relativo máximo na saída do rotor vs ψ", "ψ", "M3R máximo",
                    caso["REF_TURB"]["psi"], linha_limite=dc.MACH_SONICO,
                    rotulo_limite=f"Limite sônico (M={formato_br(dc.MACH_SONICO, f'g')})")
                exibir_serie(c2, sens["turb_htr"], "HTR", "M3R_max",
                    "Mach relativo máximo na saída do rotor vs HTR de entrada", "HTR de entrada", "M3R máximo",
                    caso["REF_TURB"]["HTR"], linha_limite=dc.MACH_SONICO,
                    rotulo_limite=f"Limite sônico (M={formato_br(dc.MACH_SONICO, f'g')})")
                c1, c2 = st.columns(2)
                exibir_serie(c1, sens["turb_psi"], "psi", "reacao_min",
                    "Reação estática mínima vs ψ", "ψ", "Reação estática mínima",
                    caso["REF_TURB"]["psi"], faixa_recomendada=dc.REACAO_TURB)
                exibir_serie(c2, sens["turb_phi"], "phi", "deflexao_rotor_max_graus",
                    "Deflexão máxima do rotor vs φ", "φ", "Deflexão (°)",
                    caso["REF_TURB"]["phi"])

            with sub_ciclo:
                st.caption("A eficiência nas curvas é referida ao calor útil transferido aos gases (eta_ciclo). A eficiência sobre PCI é η_b vezes esse valor; SFC usa a potência líquida do ciclo.")
                c1, c2 = st.columns(2)
                exibir_duplo(c1, sens["ciclo_pi"], "r_compr", "w_liq_kJ_kg",
                    "eta_ciclo_pct", "Trabalho e eficiência vs razão de pressão",
                    "π total", "Trabalho líquido (kJ/kg de ar)", "η sobre calor útil (%)",
                    caso["REF_CICLO"]["r_compr"])
                exibir_serie(c2, sens["ciclo_pi"], "r_compr", "SFC_kg_kWh",
                    "SFC vs razão de pressão", "π total", "SFC (kg/kWh)",
                    caso["REF_CICLO"]["r_compr"])
                c1, c2 = st.columns(2)
                exibir_duplo(c1, sens["ciclo_tit"], "TIT", "w_liq_kJ_kg",
                    "eta_ciclo_pct", "Trabalho e eficiência vs TIT",
                    "TIT (K)", "Trabalho líquido (kJ/kg de ar)", "η sobre calor útil (%)",
                    caso["REF_CICLO"]["TIT"])
                exibir_serie(c2, sens["ciclo_tit"], "TIT", "SFC_kg_kWh",
                    "SFC vs TIT", "TIT (K)", "SFC (kg/kWh)",
                    caso["REF_CICLO"]["TIT"])

    # ------------------------------------------------------------------
    # ABA: COMPARAR PROJETOS
    # ------------------------------------------------------------------
    with aba_comparacao:
        exibir_guia('Comparar projetos',guiado)
        exibir_comparacao(r,st.session_state['ultima_execucao'],_rodar_pipeline)

    # ------------------------------------------------------------------
    # ABA: VERIFICAÇÕES E REFERÊNCIAS
    # ------------------------------------------------------------------
    with aba_3d:
        exibir_guia('Geometria 3D',guiado)
        exibir_montagem(r,st.session_state['ultima_execucao']['id'])

    with aba_verificacoes:
        exibir_guia("Verificações", guiado)
        exibir_consolidado(r, st.session_state.get('ultima_execucao'), diagnosticos, _classificar_aviso)

    # ------------------------------------------------------------------
    # ABA: DOWNLOADS
    # ------------------------------------------------------------------
    with aba_download:
        exibir_guia("Downloads", guiado)
        st.write("Arquivos gerados a partir do caso calculado acima.")
        exibir_formatos()
        exibir_selecao_cad(r, st.session_state['ultima_execucao']['id'])
        st.markdown('**Tabelas e diagnósticos do caso**')
        st.download_button(
            "⬇ JSON — fechamento e áreas por estação",
            data=json.dumps(diagnosticos, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8"),
            file_name="diagnosticos_integracao.json", mime="application/json", width="stretch",
        )
        st.download_button(
            "⬇ JSON — indicadores energéticos e bases",
            data=json.dumps({"base_potencia": "ciclo, sem perdas mecanicas, gerador ou auxiliares",
                             "base_trabalho_liquido": "kg de ar", **indicadores},
                            ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8"),
            file_name="indicadores_energeticos.json", mime="application/json", width="stretch",
        )

        pasta_temp = st.session_state.setdefault("pasta_temp", tempfile.mkdtemp(prefix="tcc_webapp_"))

        col1, col2 = st.columns(2)

        with col1:
            caminho_csv_comp = os.path.join(pasta_temp, "parametros_compressor.csv")
            csv_compressor(comp, rad_comp, caminho_csv_comp)
            st.download_button(
                "⬇ CSV — parâmetros do compressor",
                data=_bytes_de_arquivo(caminho_csv_comp),
                file_name="parametros_compressor.csv", mime="text/csv",
                width="stretch",
            )

            caminho_csv_turb = os.path.join(pasta_temp, "parametros_turbina.csv")
            csv_turbina(turb, rad_turb, caminho_csv_turb)
            st.download_button(
                "⬇ CSV — parâmetros da turbina",
                data=_bytes_de_arquivo(caminho_csv_turb),
                file_name="parametros_turbina.csv", mime="text/csv",
                width="stretch",
            )

        with col2:
            pasta_dxf_comp = os.path.join(pasta_temp, "dxf_compressor")
            arquivos_dxf_comp = exportar_maquina_dxf(maquina_comp, pasta_dxf_comp)
            st.download_button(
                f"⬇ ZIP — DXF do compressor ({2*comp.n_estagios} peças)",
                data=zip_arquivos(arquivos_dxf_comp),
                file_name="compressor_dxf.zip", mime="application/zip",
                width="stretch",
            )

            pasta_dxf_turb = os.path.join(pasta_temp, "dxf_turbina")
            arquivos_dxf_turb = exportar_maquina_dxf(maquina_turb, pasta_dxf_turb)
            st.download_button(
                f"⬇ ZIP — DXF da turbina ({2*turb.n_estagios} peças)",
                data=zip_arquivos(arquivos_dxf_turb),
                file_name="turbina_dxf.zip", mime="application/zip",
                width="stretch",
            )

        st.caption(
            "STEP não está disponível neste fluxo: não há exportação de sólido validada nesta interface. "
            "Os DXFs fornecem curvas de seções para construção e conferência do loft no programa CAD."
        )
        exibir_relatorio(r, st.session_state['ultima_execucao'], diagnosticos,
                         _tabela_entradas_execucao(st.session_state['ultima_execucao']['parametros'],r),
                         _bytes_de_arquivo(caminho_csv_comp), _bytes_de_arquivo(caminho_csv_turb),
                         st.session_state.get('sensibilidade'), st.session_state.get('erro_sensibilidade'))

else:
    _exibir_estado_execucao()
