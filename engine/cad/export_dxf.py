import os
import math
#______________________________________________________________________________________________________________
# Exportação de geometria lofted (engine.geometry.loft) para arquivos DXF
# (formato R12 ASCII), para importação em CAD (SolidWorks, Fusion 360,
# Inventor, Rhino, etc.) e construção do sólido via comando de loft/varredura
# guiada entre seções.
#
# Sem dependências externas — o writer DXF é implementado diretamente,
# escrevendo o subconjunto mínimo do formato R12 (HEADER + TABLES/LAYER +
# ENTITIES com POLYLINE 3D), suficiente para qualquer CAD moderno importar.
#
# ══════════════════════════════════════════════════════════════════════════
# DECISÕES DE ESCOPO (ver justificativa completa na conversa/relatório):
#
#   - Exporta sempre a PÁ DE REFERÊNCIA (hub->tip, uma única pá por fileira),
#     nunca o anel replicado (Z pás). A repetição circular deve ser feita
#     no próprio CAD via padrão circular (circular pattern), que preserva
#     a relação paramétrica — reimportar Z cópias de curvas cruas seria
#     redundante e não editável como conjunto.
#
#   - Cada seção radial vira um PERFIL FECHADO (extradorso + intradorso),
#     não duas curvas abertas separadas. Como a espessura parabólica
#     (geometry/airfoil4.py, _espessura_parabolica) é nula em x=0 e x=corda,
#     extradorso e intradorso coincidem exatamente no bordo de ataque (LE)
#     e no bordo de fuga (TE); o laço fecha via
#     extradorso + intradorso_invertido[1:-1] + flag "closed" do DXF,
#     sem duplicar vértice. Pronto para o comando de loft guiado do CAD.
#
#   - Linha de câmber exportada à parte (layer própria, opcional), como
#     referência visual — não faz parte do perfil fechado.
#
#   - NÃO gera curvas-guia (rails de LE/TE entre seções). O loft do CAD
#     deve respeitar a ordem dos vértices (LE é sempre o primeiro ponto
#     em todas as seções), mas em pás muito torcidas (twist grande entre
#     hub e tip) pode ser necessário adicionar rails manualmente no CAD
#     se o loft automático não seguir bem — refinamento futuro, não
#     implementado aqui.
#
#   - $INSUNITS=6 (metros) no header — todo o pipeline trabalha em SI;
#     sem isso, alguns CADs assumem polegadas/sem-unidade por padrão.
# ══════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════
# WRITER DXF R12 — MÍNIMO, SEM DEPENDÊNCIAS
# ══════════════════════════════════════════════════════════════════════════

def _dxf_header() -> str:
    return (
        "0\nSECTION\n2\nHEADER\n"
        "9\n$ACADVER\n1\nAC1009\n"
        "9\n$INSUNITS\n70\n6\n"
        "0\nENDSEC\n"
    )


def _dxf_tables(layers: list) -> str:
    """
    TABLES agora inclui uma tabela LTYPE mínima (define "CONTINUOUS"), já
    que a tabela LAYER referencia esse linetype no grupo 6 — leitores
    estritos podem exigir que ele esteja formalmente declarado, mesmo que
    o AutoCAD assuma um "CONTINUOUS" embutido por padrão.
    """
    partes = [
        "0\nSECTION\n2\nTABLES\n",
        "0\nTABLE\n2\nLTYPE\n70\n1\n",
        "0\nLTYPE\n2\nCONTINUOUS\n70\n0\n3\nSolid line\n72\n65\n73\n0\n40\n0.0\n",
        "0\nENDTAB\n",
        f"0\nTABLE\n2\nLAYER\n70\n{len(layers)}\n",
    ]
    for nome in layers:
        partes.append(
            f"0\nLAYER\n2\n{nome}\n70\n0\n62\n7\n6\nCONTINUOUS\n"
        )
    partes.append("0\nENDTAB\n0\nENDSEC\n")
    return "".join(partes)


def _dxf_blocks_vazio() -> str:
    """
    Seção BLOCKS vazia. Opcional pelo spec R12, mas presente por convenção
    em escritores DXF de referência (ex.: ezdxf); alguns leitores esperam
    encontrá-la entre TABLES e ENTITIES mesmo sem blocos definidos.
    """
    return "0\nSECTION\n2\nBLOCKS\n0\nENDSEC\n"


def _dxf_polyline_3d(pontos: list, layer: str, fechada: bool = False) -> str:
    """
    Cada VERTEX agora carrega o grupo 70=32 (flag "vértice de polyline 3D"),
    que precisa casar com o flag 70=8 ("é 3D") da POLYLINE-pai — sem isso
    o vértice é interpretado como 2D por padrão em alguns leitores,
    descasando com a entidade-pai.

    A POLYLINE também ganhou um ponto-base "dummy" (10/20/30 = 0,0,0),
    convenção comum mesmo quando a geometria real vem só dos VERTEX
    subsequentes.
    """
    flag_polyline = 8 | (1 if fechada else 0)
    flag_vertex = 32
    partes = [
        f"0\nPOLYLINE\n8\n{layer}\n66\n1\n70\n{flag_polyline}\n"
        f"10\n0.0\n20\n0.0\n30\n0.0\n"
    ]
    for (x, y, z) in pontos:
        partes.append(
            f"0\nVERTEX\n8\n{layer}\n70\n{flag_vertex}\n"
            f"10\n{x:.6f}\n20\n{y:.6f}\n30\n{z:.6f}\n"
        )
    partes.append("0\nSEQEND\n")
    return "".join(partes)


def _sanitizar_nome_layer(nome: str) -> str:
    """DXF não aceita espaços/caracteres especiais em nomes de layer."""
    return "".join(c if c.isalnum() else "_" for c in nome).upper()


def _fechar_perfil(extradorso: list, intradorso: list) -> list:
    """
    Monta um laço fechado a partir das curvas abertas extradorso/intradorso
    (ambas ordenadas LE->TE, mesma convenção de geometry/airfoil4.py).

    extradorso[0] == intradorso[0]  (LE, espessura nula)
    extradorso[-1] == intradorso[-1] (TE, espessura nula)

    Laço: extradorso completo (LE->TE) + intradorso invertido, excluindo
    o primeiro e o último ponto (que duplicariam LE e TE). A flag "fechada"
    do DXF conecta o último vértice de volta ao primeiro (extradorso[0]).
    """
    return extradorso + intradorso[-2:0:-1]


def _dxf_polyline_como_linhas(pontos: list, layer: str, fechada: bool = False) -> str:
    """
    Alternativa de fallback ao par POLYLINE/VERTEX/SEQEND: desenha o mesmo
    laço como uma cadeia de entidades LINE independentes. Útil como teste
    de isolamento — se este modo importar e o modo POLYLINE não, o
    problema está especificamente em como o leitor trata a construção
    multi-entidade antiga, não na geometria em si.
    """
    partes = []
    n = len(pontos)
    limite = n if fechada else n - 1
    for i in range(limite):
        x1, y1, z1 = pontos[i]
        x2, y2, z2 = pontos[(i + 1) % n]
        partes.append(
            f"0\nLINE\n8\n{layer}\n"
            f"10\n{x1:.6f}\n20\n{y1:.6f}\n30\n{z1:.6f}\n"
            f"11\n{x2:.6f}\n21\n{y2:.6f}\n31\n{z2:.6f}\n"
        )
    return "".join(partes)


def _escrever_curva(pontos: list, layer: str, fechada: bool, usar_linhas: bool) -> str:
    if usar_linhas:
        return _dxf_polyline_como_linhas(pontos, layer, fechada=fechada)
    return _dxf_polyline_3d(pontos, layer, fechada=fechada)


# ══════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO — UMA PEÇA (rotor OU estator OU bocal, pá única hub->tip)
# ══════════════════════════════════════════════════════════════════════════

def exportar_peca_dxf(peca,
                      caminho: str,
                      incluir_camber: bool = True,
                      nomes_secoes: list = None,
                      usar_linhas:bool = False) -> str:
    """
    Exporta uma única PecaLoftada (engine.geometry.loft.PecaLoftada) para
    um arquivo DXF: um perfil FECHADO por seção radial (layer "<SEC>_PERFIL"),
    mais opcionalmente a linha de câmber de referência (layer "<SEC>_CAMBER").

    PARÂMETROS:
        peca             - Objeto PecaLoftada (de loftar_pa/loftar_compressor/
                           loftar_turbina), já com pa.extradorso_cart,
                           pa.intradorso_cart, pa.camber_cart preenchidos.
        caminho          - Caminho completo do arquivo .dxf de saída.
        incluir_camber   - Se True (padrão), inclui a linha de câmber de
                           cada seção como polyline ABERTA de referência.
        nomes_secoes     - Lista opcional de rótulos (ex.: rad_comp.secoes,
                           ["hub","r1",...,"tip"]) para nomear as layers de
                           forma legível. Se None, usa índices ("S00","S01",...).

    RETORNA: o caminho do arquivo escrito (mesmo valor de "caminho").
    """
    n_secoes = len(peca.pa.r_secoes)

    if nomes_secoes is None:
        nomes_secoes = [f"S{idx:02d}" for idx in range(n_secoes)]
    elif len(nomes_secoes) != n_secoes:
        raise ValueError(
            f"nomes_secoes tem {len(nomes_secoes)} itens, mas a peça tem "
            f"{n_secoes} seções radiais."
        )

    layers = []
    entidades = []

    for idx in range(n_secoes):
        rotulo = _sanitizar_nome_layer(nomes_secoes[idx])
        layer_perfil = f"{rotulo}_PERFIL"
        layers.append(layer_perfil)

        perfil_fechado = _fechar_perfil(
            peca.pa.extradorso_cart[idx], peca.pa.intradorso_cart[idx]
        )
        entidades.append(_escrever_curva(perfil_fechado, layer_perfil, fechada=True, usar_linhas=usar_linhas))

        if incluir_camber:
            layer_camber = f"{rotulo}_CAMBER"
            layers.append(layer_camber)
            entidades.append(
                _escrever_curva(peca.pa.camber_cart[idx], layer_camber, fechada=False, usar_linhas=usar_linhas)
            )

    conteudo = (
        _dxf_header()
        + _dxf_tables(layers)
        + _dxf_blocks_vazio()
        + "0\nSECTION\n2\nENTITIES\n"
        + "".join(entidades)
        + "0\nENDSEC\n0\nEOF\n"
    )

    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w") as f:
        f.write(conteudo)

    return caminho


# ══════════════════════════════════════════════════════════════════════════
# EXPORTAÇÃO EM LOTE — MÁQUINA COMPLETA (todas as peças)
# ══════════════════════════════════════════════════════════════════════════

def exportar_maquina_dxf(maquina,
                          pasta: str,
                          prefixo: str = "",
                          incluir_camber: bool = True,
                          nomes_secoes: list = None,
                          usar_linhas: bool = False) -> list:
    """
    Exporta TODAS as peças de uma MaquinaLofted (engine.geometry.loft.
    MaquinaLofted — saída de loftar_compressor()/loftar_turbina()) para
    arquivos DXF individuais numa pasta, um arquivo por fileira (rotor,
    estator ou bocal), na ordem física da máquina.

    Nomeação: "<prefixo>estagio<NN>_<tipo>.dxf", ex.: "estagio01_rotor.dxf".

    PARÂMETROS:
        maquina         - Objeto MaquinaLofted já montado.
        pasta           - Diretório de saída (criado se não existir).
        prefixo         - Prefixo opcional para os nomes de arquivo.
        incluir_camber, nomes_secoes - repassados a exportar_peca_dxf()
                          para cada peça.

    RETORNA: lista de caminhos de arquivo escritos, na ordem das peças.
    """
    os.makedirs(pasta, exist_ok=True)
    caminhos = []

    for peca in maquina.pecas:
        nome_arquivo = f"{prefixo}estagio{peca.estagio:02d}_{peca.tipo}.dxf"
        caminho = os.path.join(pasta, nome_arquivo)
        exportar_peca_dxf(
            peca, caminho,
            incluir_camber=incluir_camber, nomes_secoes=nomes_secoes,
        )
        caminhos.append(caminho)

    return caminhos


def _rotacionar_curva(pontos: list, angulo_rad: float) -> list:
    cos_a, sin_a = math.cos(angulo_rad), math.sin(angulo_rad)
    return [(x*cos_a - y*sin_a, x*sin_a + y*cos_a, z) for (x, y, z) in pontos]


def exportar_maquina_dxf_completo(maquina,
                                   caminho: str,
                                   usar_linhas: bool = False) -> str:
    """
    Exporta a máquina INTEIRA com todas as peças replicadas (Z pás cada)
    num único arquivo DXF -- equivalente ao macro_compressor_completo do
    FreeCAD, mas em DXF puro. Uma layer por FILEIRA (não por pá individual),
    para manter a tabela de layers pequena (16 layers no compressor, não 924).
    """
    import math
    layers = []
    entidades = []

    for peca in maquina.pecas:
        layer_pa = f"E{peca.estagio:02d}_{peca.tipo.upper()}"
        layers.append(layer_pa)
        n_secoes = len(peca.pa.r_secoes)
        dtheta = 2 * math.pi / peca.Z_pas

        perfis_ref = [
            _fechar_perfil(peca.pa.extradorso_cart[idx], peca.pa.intradorso_cart[idx])
            for idx in range(n_secoes)
        ]

        for k in range(peca.Z_pas):
            ang = k * dtheta
            for perfil in perfis_ref:
                perfil_rot = _rotacionar_curva(perfil, ang)
                entidades.append(_escrever_curva(perfil_rot, layer_pa, fechada=True, usar_linhas=usar_linhas))

    conteudo = (
        _dxf_header() + _dxf_tables(layers) + _dxf_blocks_vazio()
        + "0\nSECTION\n2\nENTITIES\n" + "".join(entidades) + "0\nENDSEC\n0\nEOF\n"
    )
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w") as f:
        f.write(conteudo)
    return caminho