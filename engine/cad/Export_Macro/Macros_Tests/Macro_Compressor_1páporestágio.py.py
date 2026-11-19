"""Exemplo executável; importar este módulo não roda o projeto."""

def main():
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.geometry.loft2 import loftar_compressor
    from engine.cad.Export_Macro.export_freecad_macro import gerar_macro_maquina

    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()
    maquina_comp = loftar_compressor(rad_comp, replicar=False)

    gerar_macro_maquina(maquina_comp, "saida_dxf/macro_compressor_leve.FCMacro", replicar=False)


if __name__ == "__main__":
    main()
