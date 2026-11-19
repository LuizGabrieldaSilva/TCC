"""Exemplo executável; importar este módulo não roda o projeto."""

def main():
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.estudos.export_csv import csv_compressor, csv_turbina

    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()
    rad_turb = RadialTurbina(turb=turb1, n_secoes=7)
    rad_turb.resolver()

    c1 = csv_compressor(compr1, rad_comp, "saida_dxf/parametros_compressor.csv")
    c2 = csv_turbina(turb1, rad_turb, "saida_dxf/parametros_turbina.csv")

    print(f"Compressor: {c1} ({compr1.n_estagios * len(rad_comp.secoes)} linhas de dados esperadas; cabeçalho à parte)")
    print(f"Turbina: {c2} ({turb1.n_estagios * len(rad_turb.secoes)} linhas de dados esperadas; cabeçalho à parte)")

    with open(c1) as f:
        linhas = f.readlines()
    print(f"\nCabeçalho: {linhas[0].strip()}")
    print(f"Primeira linha de dado: {linhas[1].strip()}")
    print(f"Total de linhas (com cabeçalho): {len(linhas)}")


if __name__ == "__main__":
    main()
