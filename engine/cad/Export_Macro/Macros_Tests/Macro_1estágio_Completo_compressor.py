"""Exemplo executável; importar este módulo não roda o projeto."""

def main():
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.geometry.loft2 import loftar_compressor, MaquinaLofted
    from engine.cad.Export_Macro.export_freecad_macro import gerar_macro_maquina

    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()

    maquina_comp = loftar_compressor(rad_comp, replicar=False)

    # Isola só as 2 primeiras peças (rotor E1 + estator E1) numa "mini-máquina"s
    estagio1 = MaquinaLofted(
        pecas=maquina_comp.pecas[:2],
        z_total=maquina_comp.pecas[1].z_final,
    )

    gerar_macro_maquina(
        estagio1,
        "saida_dxf/macro_compressor_estagio1.FCMacro",
        nome_doc="CompressorEstagio1",
        replicar=True,
    )


if __name__ == "__main__":
    main()
