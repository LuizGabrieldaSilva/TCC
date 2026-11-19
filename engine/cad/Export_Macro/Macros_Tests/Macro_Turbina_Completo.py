"""Exemplo executável; importar este módulo não roda o projeto."""

def main():
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.geometry.loft2 import loftar_turbina
    from engine.cad.Export_Macro.export_freecad_macro import gerar_macro_maquina

    rad_turb = RadialTurbina(turb=turb1, n_secoes=7)
    rad_turb.resolver()

    maquina_turb = loftar_turbina(rad_turb, replicar=False)

    gerar_macro_maquina(
        maquina_turb,
        "saida_dxf/macro_turbina_replicada.FCMacro",
        nome_doc="TurbinaCompleta",
        replicar=True,
    )


if __name__ == "__main__":
    main()
