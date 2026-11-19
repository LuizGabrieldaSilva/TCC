"""Verifica importações sem cálculos e criação explícita dos exemplos.

Da pasta NEW: python -m engine.estudos.verificar_importacoes --saida arquivo.json

--comparar-definicoes é uma auditoria estrita da versão do checkpoint de
importações, incluindo textos e docstrings. Não é uma regressão numérica:
revisões autorizadas de apresentação podem divergir desse snapshot histórico.
"""
import argparse
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile


def serializar(valor):
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    if isinstance(valor, (list, tuple)):
        return [serializar(x) for x in valor]
    if isinstance(valor, dict):
        return {str(k):serializar(v) for k,v in valor.items()}
    return {'classe':type(valor).__name__, 'atributos':serializar(vars(valor))}


def executar(comparar_definicoes=False):
    root = Path(__file__).resolve().parents[1]
    checkpoint = root.parents[1]/'checkpoints/importacoes_sem_execucao_2026-11-09'
    sys.path.insert(0, str(root.parent))
    # O app Streamlit é um ponto de entrada, não uma biblioteca. É testado por AppTest.
    arquivos = sorted(p for p in root.rglob('*.py')
                      if p.name not in ('streamlit_app.py', 'verificar_importacoes.py'))
    calculos = {'__init__', 'resolver', 'gerar_perfil_pa', 'loftar_pa',
                'csv_compressor', 'csv_turbina', 'criar_ciclo_exemplo',
                'criar_compressor_exemplo', 'criar_turbina_exemplo'}
    def impedir_calculo(frame, evento, arg):
        if evento == 'call' and frame.f_code.co_name in calculos:
            arquivo = Path(frame.f_code.co_filename)
            if arquivo.is_relative_to(root):
                raise AssertionError(f'Cálculo durante importação: {arquivo.name}:{frame.f_code.co_name}')
    stdout, stderr = io.StringIO(), io.StringIO()
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='tcc_importacoes_') as tmp:
        try:
            os.chdir(tmp)
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                sys.setprofile(impedir_calculo)
                try:
                    for i,p in enumerate(arquivos):
                        # Nome de teste permite também o arquivo histórico *.py.py.
                        nome = f'_tcc_importacao_{i}'
                        spec = importlib.util.spec_from_file_location(nome, p)
                        modulo = importlib.util.module_from_spec(spec)
                        sys.modules[nome] = modulo
                        spec.loader.exec_module(modulo)
                finally:
                    sys.setprofile(None)
            assert stdout.getvalue() == '', stdout.getvalue()
            assert stderr.getvalue() == '', stderr.getvalue()
            assert not list(Path(tmp).rglob('*')), 'Importação gerou arquivos de saída.'
        finally:
            os.chdir(cwd)
    from engine.ciclo import CicloBrayton as ciclo_mod
    from engine.compressor import Compressor_Meanline_main as comp_mod
    from engine.turbina import Turbine_Meanline_main as turb_mod
    for modulo, antigo in ((ciclo_mod,'ciclo1'),(comp_mod,'compr1'),(turb_mod,'turb1')):
        assert antigo not in vars(modulo)
    # Os exemplos explícitos reproduzem os estados completos dos antigos globais.
    with contextlib.redirect_stdout(io.StringIO()):
        c = ciclo_mod.criar_ciclo_exemplo()
        comp = comp_mod.criar_compressor_exemplo()
        turb = turb_mod.criar_turbina_exemplo()
        outro = comp_mod.criar_compressor_exemplo()
    atual = {k:serializar(v) for k,v in dict(ciclo=c,comp=comp,turb=turb).items()}
    anterior = json.loads((checkpoint/'exemplos_antes.json').read_text(encoding='utf-8'))
    if comparar_definicoes:
        assert atual == anterior, 'Estado histórico alterado; não usar esta auditoria entre versões físicas distintas.'
    else:
        from engine.reference_case import montar_caso_referencia
        referencia=montar_caso_referencia()['REF_CICLO']
        assert c.mistura_automatica == referencia['mistura_automatica']
        assert c.cp_gases == c.dados_mistura['cp_J_kg_K']
        assert c.R_gases == c.dados_mistura['R_J_kg_K']
        assert turb.cp == c.cp_gases
    assert comp is not outro
    assert comp._entrada_selecao['ciclo'] is not outro._entrada_selecao['ciclo']
    valor = outro.psi
    comp.psi = -99.
    assert outro.psi == valor
    # As definições pré-existentes de classes e funções físicas não mudaram.
    definicoes = 0 if comparar_definicoes else None
    manifesto = json.loads((checkpoint/'manifesto.json').read_text(encoding='utf-8-sig'))
    for item in manifesto:
        if not comparar_definicoes:
            break
        if not item['arquivo'].endswith('.py'):
            continue
        antes_path = checkpoint/item['arquivo']
        atual_path = root.parents[1]/item['arquivo']
        antes_ast = ast.parse(antes_path.read_text(encoding='utf-8-sig'))
        atual_ast = ast.parse(atual_path.read_text(encoding='utf-8-sig'))
        atuais = {n.name:n for n in ast.walk(atual_ast) if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        for no in antes_ast.body:
            if isinstance(no,(ast.FunctionDef,ast.ClassDef)):
                assert ast.dump(no) == ast.dump(atuais[no.name]), (item['arquivo'],no.name)
                definicoes += 1
    return dict(importacoes=len(arquivos), calculos_ao_importar=0, stdout='', stderr='',
                arquivos_gerados=0, estados_historicos_comparados=comparar_definicoes, exemplos_usam_referencia_atual=True, instancias_independentes=True,
                definicoes_existentes_preservadas=definicoes,
                arquivos=[str(p.relative_to(root)) for p in arquivos])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--saida', type=Path, required=True)
    p.add_argument('--comparar-definicoes', action='store_true',
                   help='Auditoria estrita de código/textos contra a versão histórica do checkpoint de importações.')
    args = p.parse_args()
    resultado = executar(comparar_definicoes=args.comparar_definicoes)
    args.saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{resultado['importacoes']} importações sem cálculos, mensagens ou arquivos de saída; exemplos preservados.")
