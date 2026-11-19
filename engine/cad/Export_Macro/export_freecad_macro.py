import os

#______________________________________________________________________________________________________________
# engine/cad/export_freecad_macro.py
#
# Geração de macro FreeCAD (.FCMacro) que reconstrói a geometria lofted
# como SÓLIDOS REAIS (via Part.makeLoft), usando a API Python nativa do
# FreeCAD -- sem passar pelo importador de DXF.
#
# Motivação: o importador de DXF do FreeCAD 1.0 (testado nesta instalação)
# rejeita nossos arquivos mesmo após confirmação de conformidade por três
# fontes independentes (ezdxf, LibreCAD, inspeção manual da estrutura DXF).
# Em vez de continuar depurando o importador de terceiros, contornamos o
# problema construindo a geometria diretamente dentro do FreeCAD via sua
# própria API Python (Part.makeLoft, Part.Shape.rotate), que não usa o
# caminho de código do importador de arquivo.
#
# O macro é AUTOCONTIDO: as coordenadas já calculadas pelo pipeline
# (engine.geometry.loft) são embutidas como literais Python diretamente no
# arquivo gerado, em vez de o macro tentar importar o pacote `engine`
# dentro do interpretador Python do FreeCAD (que roda separado do Python
# do projeto, sem garantia de ter o mesmo sys.path ou versão).
#
# ══════════════════════════════════════════════════════════════════════════
# AVISO DE DESEMPENHO:
#   Com replicar=True, o número de operações de loft (uma por pá) pode ser
#   muito grande para a máquina inteira (ex.: compressor com Z~56-59 por
#   fileira x 16 fileiras ~ 900 pás). Recomenda-se testar primeiro com uma
#   única peça (gerar_macro_peca) e replicar=False antes de tentar a
#   máquina inteira replicada -- e, se necessário, gerar a máquina completa
#   em partes (um estágio por vez) em vez de tudo de uma vez.
# ══════════════════════════════════════════════════════════════════════════

from engine.cad.export_dxf import _fechar_perfil


def _formatar_lista_pontos(pontos: list) -> str:
    """Converte uma lista de tuplas (x,y,z) em um literal Python de vetores FreeCAD."""
    itens = ", ".join(f"FreeCAD.Vector({x:.6f},{y:.6f},{z:.6f})" for (x, y, z) in pontos)
    return f"[{itens}]"


def _emitir_codigo_peca(peca, indice_peca: int, replicar: bool) -> tuple:
    """
    Igual à versão anterior, mas agora retorna (codigo_str, nomes_objetos)
    -- nomes_objetos é a lista de nomes dos Part::Feature criados por esta
    peça (a pá de referência + as replicadas, se replicar=True), usada
    depois para montar o comando de exportação STEP.
    """
    nome_base = f"E{peca.estagio:02d}_{peca.tipo}"
    n_secoes = len(peca.pa.r_secoes)
    nomes_objetos = [nome_base]

    linhas = [f"\n# ---- Peça {indice_peca}: {nome_base} ({n_secoes} seções, Z={peca.Z_pas} pás) ----"]
    linhas.append("wires = []")
    for idx in range(n_secoes):
        perfil_fechado = _fechar_perfil(
            peca.pa.extradorso_cart[idx], peca.pa.intradorso_cart[idx]
        )
        pontos_fechados = perfil_fechado + [perfil_fechado[0]]
        linhas.append(f"pts_{idx} = {_formatar_lista_pontos(pontos_fechados)}")
        linhas.append(f"wires.append(Part.makePolygon(pts_{idx}))")

    linhas.append("solido = Part.makeLoft(wires, True, False)")
    linhas.append(f'obj = doc.addObject("Part::Feature", "{nome_base}")')
    linhas.append("obj.Shape = solido")

    cor = "(0.3,0.5,0.9)" if peca.tipo == "rotor" else "(0.9,0.6,0.2)"
    linhas.append("try:")
    linhas.append(f"    obj.ViewObject.ShapeColor = {cor}")
    linhas.append("except AttributeError:")
    linhas.append("    pass  # rodando sem GUI (ex.: FreeCADCmd) -- sem ViewObject")

    if replicar and peca.Z_pas > 1:
        linhas.append(f"angulo_passo = 360.0 / {peca.Z_pas}")
        linhas.append(f"for k in range(1, {peca.Z_pas}):")
        linhas.append("    copia = solido.copy()")
        linhas.append("    copia.rotate(FreeCAD.Vector(0,0,0), FreeCAD.Vector(0,0,1), angulo_passo * k)")
        linhas.append(f'    obj_k = doc.addObject("Part::Feature", f"{nome_base}_p{{k:03d}}")')
        linhas.append("    obj_k.Shape = copia")
        linhas.append("    try:")
        linhas.append(f"        obj_k.ViewObject.ShapeColor = {cor}")
        linhas.append("    except AttributeError:")
        linhas.append("        pass")
        nomes_objetos += [f"{nome_base}_p{k:03d}" for k in range(1, peca.Z_pas)]

    return "\n".join(linhas), nomes_objetos


def _cabecalho_macro(nome_doc: str) -> str:
    return (
        "import FreeCAD\n"
        "import Part\n\n"
        f'doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("{nome_doc}")\n'
    )


def _rodape_macro() -> str:
    return (
        "\ndoc.recompute()\n"
        "try:\n"
        "    FreeCADGui.ActiveDocument.ActiveView.fitAll()\n"
        "except (NameError, AttributeError):\n"
        "    pass  # sem GUI ativa\n"
        'print("Macro concluído.")\n'
    )


def _emitir_codigo_export_step(nomes_objetos: list, caminho_step: str) -> str:
    """
    Exporta os objetos indicados para um único arquivo STEP via Part.export().

    Antes de exportar, aplica cura de forma (Shape.fix()) em cada sólido:
    lofts construídos a partir de Part.makePolygon (arestas retas, sem
    suavização) sobre perfis não-planares (cada seção é uma curva sobre um
    cilindro, não um plano) podem gerar geometria com pequenas imperfeições
    de tolerância que passam despercebidas na visualização mas fazem o
    escritor STEP do OpenCascade falhar ("Writing of STEP failed"). fix()
    corrige isso sem alterar a forma visível.
    """
    caminho_norm = caminho_step.replace("\\", "/")
    lista_python = "[" + ", ".join(f'doc.getObject("{n}")' for n in nomes_objetos) + "]"
    return (
        "\n# ---- Exportação STEP ----\n"
        f"objetos_export = {lista_python}\n"
        "for _obj in objetos_export:\n"
        "    _obj.Shape.fix(0.01, 0.01, 0.01)\n"
        f'Part.export(objetos_export, "{caminho_norm}")\n'
        f'print("STEP exportado: {caminho_norm} ({{}} objeto(s))".format(len(objetos_export)))\n'
    )


def gerar_macro_peca(peca,
                      caminho_macro: str,
                      nome_doc: str = "PecaTCC",
                      replicar: bool = False,
                      exportar_step: bool = False,
                      caminho_step: str = None) -> str:
    """
    Gera um .FCMacro para UMA única peça. Se exportar_step=True, o macro
    também exporta a peça (e suas replicações, se replicar=True) para um
    arquivo .step ao final -- caminho_step default: mesmo nome/pasta do
    macro, trocando a extensão para .step.
    """
    codigo_peca, nomes_objetos = _emitir_codigo_peca(peca, indice_peca=1, replicar=replicar)

    conteudo = _cabecalho_macro(nome_doc) + codigo_peca

    if exportar_step:
        if caminho_step is None:
            caminho_step = os.path.splitext(caminho_macro)[0] + ".step"
        conteudo += _emitir_codigo_export_step(nomes_objetos, caminho_step)

    conteudo += _rodape_macro()

    os.makedirs(os.path.dirname(caminho_macro) or ".", exist_ok=True)
    with open(caminho_macro, "w") as f:
        f.write(conteudo)
    return caminho_macro


def gerar_macro_maquina(maquina,
                         caminho_macro: str,
                         nome_doc: str = "MaquinaTCC",
                         replicar: bool = False,
                         exportar_step: bool = False,
                         caminho_step: str = None) -> str:
    """
    Gera um .FCMacro para a MaquinaLofted inteira. Se exportar_step=True,
    exporta TODAS as peças (todas as fileiras, todas replicadas se
    replicar=True) para um ÚNICO arquivo .step ao final.

    AVISO DE DESEMPENHO: com replicar=True numa máquina grande (ex.: o
    compressor completo, ~924 sólidos), o arquivo STEP resultante pode
    ficar grande e a exportação demorar -- mesmo aviso já válido para a
    construção dos sólidos em si (ver cabeçalho do módulo).
    """
    todos_nomes = []
    blocos = []
    for i, peca in enumerate(maquina.pecas):
        codigo, nomes = _emitir_codigo_peca(peca, i + 1, replicar)
        blocos.append(codigo)
        todos_nomes += nomes

    conteudo = _cabecalho_macro(nome_doc) + "".join(blocos)

    if exportar_step:
        if caminho_step is None:
            caminho_step = os.path.splitext(caminho_macro)[0] + ".step"
        conteudo += _emitir_codigo_export_step(todos_nomes, caminho_step)

    conteudo += _rodape_macro()

    os.makedirs(os.path.dirname(caminho_macro) or ".", exist_ok=True)
    with open(caminho_macro, "w") as f:
        f.write(conteudo)
    return caminho_macro

