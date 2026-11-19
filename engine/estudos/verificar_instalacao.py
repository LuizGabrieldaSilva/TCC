"""Teste local de instalação; não substitui a validação física do projeto.

De NEW: python -m engine.estudos.verificar_instalacao --interface
Saídas transitórias ficam em diretório temporário. --saida grava só o resumo.
"""

import argparse
import contextlib
import importlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import platform
import sys
import tempfile


def verificar(interface=False):
    pacotes={'streamlit':'streamlit','pandas':'pandas','numpy':'numpy',
             'matplotlib':'matplotlib','altair':'altair','plotly':'plotly','Jinja2':'jinja2'}
    versoes={}
    for pacote,modulo in pacotes.items():
        importlib.import_module(modulo)
        versoes[pacote]=importlib.metadata.version(pacote)
    import matplotlib
    matplotlib.use('Agg')
    from engine.estudos.verificar_acoplamento import montar_caso,conferir
    from engine.geometry.airfoil4 import gerar_perfis_compressor,gerar_perfis_turbina
    from engine.geometry.loft2 import loftar_compressor,loftar_turbina
    from engine.cad.export_dxf import exportar_peca_dxf
    from engine.estudos.export_csv import csv_compressor,csv_turbina
    from engine.webapp.assembly_3d import figura_montagem
    from engine.webapp.number_format import tabela_br
    import matplotlib.pyplot as plt
    import pandas as pd

    with contextlib.redirect_stdout(io.StringIO()):
        ciclo,comp,turb,rc,rt=montar_caso()
        conferir(comp,rc,'Compressor');conferir(turb,rt,'Turbina')
        pc=gerar_perfis_compressor(rc);pt=gerar_perfis_turbina(rt)
        mc=loftar_compressor(rc,perfis=pc,replicar=False)
        mt=loftar_turbina(rt,perfis=pt,replicar=False)
    assert math.isfinite(ciclo.W_líq) and ciclo.W_líq>0
    with tempfile.TemporaryDirectory(prefix='tcc_instalacao_') as pasta:
        pasta=Path(pasta)
        dxf=pasta/'pa.dxf';exportar_peca_dxf(mc.pecas[0],str(dxf))
        assert dxf.exists() and 'EOF' in dxf.read_text()
        csv_compressor(comp,rc,str(pasta/'compressor.csv'))
        csv_turbina(turb,rt,str(pasta/'turbina.csv'))
        assert (pasta/'compressor.csv').stat().st_size>0
        assert (pasta/'turbina.csv').stat().st_size>0
        assert '<table' in tabela_br(pd.DataFrame({'Valor':[.35]})).to_html()
        fig=plt.figure();ax=fig.add_subplot();ax.plot([0,1],[0,1])
        fig.savefig(pasta/'grafico.png');plt.close(fig)
        assert (pasta/'grafico.png').stat().st_size>0
        fig,_=figura_montagem(mt.pecas,replicar=True,limite=4,pontos=12,cubo=True)
        fig.write_html(pasta/'montagem.html',include_plotlyjs=True)
        assert len(fig.data)==len(mt.pecas)+1

    resultado={'python':platform.python_version(),'plataforma':platform.platform(),
               'ambiente_virtual':sys.prefix!=sys.base_prefix,'executavel':sys.executable,
               'raiz_codigo':str(Path(__file__).resolve().parents[2]),
               'dependencias':versoes,'potencia_liquida_W':ciclo.W_líq,
               'estagios':{'compressor':comp.n_estagios,'turbina':turb.n_estagios},
               'testes':{'imports':True,'caso_referencia':True,'identidades_numericas':True,
                        'csv_dxf':True,'tabelas_jinja2':True,'matplotlib':True,'montagem_plotly':True}}
    if interface:
        from streamlit.testing.v1 import AppTest
        app=Path(__file__).resolve().parents[1]/'webapp'/'streamlit_app.py'
        at=AppTest.from_file(str(app),default_timeout=240).run()
        assert not at.exception,[x.message for x in at.exception]
        botao=next(b for b in at.button if b.label=='Calcular e atualizar gráficos')
        botao.click().run(timeout=240)
        assert not at.exception,[x.message for x in at.exception]
        assert at.session_state['erro'] is None,at.session_state['erro']
        assert at.session_state['erro_sensibilidade'] is None,at.session_state['erro_sensibilidade']
        r=at.session_state['resultados']
        assert math.isclose(r['ciclo'].W_líq,ciclo.W_líq,rel_tol=1e-10)
        assert len(at.tabs)>=9
        at.radio(key='montagem_nivel').set_value('Componente completo').run()
        at.checkbox(key='montagem_cubo').check().run()
        at.button(key='montagem_gerar').click().run()
        assert not at.exception,[x.message for x in at.exception]
        assert len(at.get('plotly_chart'))>=1
        resultado['testes']['streamlit_apptest_calculo_sensibilidade_3d']=True
        resultado['avisos_referencia']=len(r.get('avisos_detalhados',[]))
        resultado['testes']['sem_erro_sensibilidade']=True
    return resultado


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface',action='store_true',help='Também executa o Streamlit em AppTest, calcula o caso e prepara o 3D.')
    parser.add_argument('--saida',type=Path,help='Arquivo JSON opcional com o resumo da verificação.')
    args=parser.parse_args()
    try:
        resultado=verificar(args.interface)
    except ImportError as erro:
        parser.exit(1,f'Dependência ausente/incompatível: {erro}\nInstale com: python -m pip install -r requirements.txt\n')
    texto=json.dumps(resultado,ensure_ascii=False,indent=2)
    if args.saida:args.saida.write_text(texto,encoding='utf-8')
    print(texto)
    print('Instalação conferida no escopo acima. Avisos físicos podem permanecer; consulte a interface.')


if __name__=='__main__':main()
