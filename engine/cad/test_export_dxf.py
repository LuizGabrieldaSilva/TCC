"""Exemplo executável; importar este módulo não roda o projeto."""

def main():
    from engine.compressor.Compressor_Meanline_main import criar_compressor_exemplo
    compr1 = criar_compressor_exemplo()
    from engine.aero.radial_compressor_4_main import RadialCompressor
    from engine.turbina.Turbine_Meanline_main import criar_turbina_exemplo
    turb1 = criar_turbina_exemplo()
    from engine.aero.radial_turbina_3_main import RadialTurbina
    from engine.geometry.loft2 import loftar_compressor, loftar_turbina
    from engine.cad.export_dxf import exportar_peca_dxf, exportar_maquina_dxf, exportar_maquina_dxf_completo

    rad_comp = RadialCompressor(comp=compr1, n_secoes=7)
    rad_comp.resolver()
    rad_turb = RadialTurbina(turb=turb1, n_secoes=7)
    rad_turb.resolver()

    maquina_comp = loftar_compressor(rad_comp, replicar=False)
    maquina_turb = loftar_turbina(rad_turb, replicar=False)

    # # Teste 1: peça única, com nomes de seção legíveis
    # caminho_unico = exportar_peca_dxf(
    #     maquina_comp.pecas[0], "saida_dxf/teste_rotor_e1.dxf",
    #     nomes_secoes=rad_comp.secoes, usar_linhas = True,
    # )
    # print(f"Arquivo único escrito: {caminho_unico}")

    # with open(caminho_unico) as f:
    #     linhas = f.readlines()
    # print(f"Total de linhas no arquivo: {len(linhas)}")
    # print("Primeiras 20 linhas:")
    # print("".join(linhas[:20]))

    # # Teste 2: máquina completa em lote
    # arquivos_comp = exportar_maquina_dxf(
    #     maquina_comp, "saida_dxf/compressor", nomes_secoes=rad_comp.secoes,
    # )
    # arquivos_turb = exportar_maquina_dxf(
    #     maquina_turb, "saida_dxf/turbina", nomes_secoes=rad_turb.secoes,
    # )

    # print(f"\nCompressor: {len(arquivos_comp)} arquivos DXF gerados (esperado {2*compr1.n_estagios})")
    # print(f"Turbina:    {len(arquivos_turb)} arquivos DXF gerados (esperado {2*turb1.n_estagios})")

    # erros = []
    # if len(arquivos_comp) != 2*compr1.n_estagios:
    #     erros.append(f"Compressor: {len(arquivos_comp)} arquivos, esperado {2*compr1.n_estagios}")
    # if len(arquivos_turb) != 2*turb1.n_estagios:
    #     erros.append(f"Turbina: {len(arquivos_turb)} arquivos, esperado {2*turb1.n_estagios}")

    # import os
    # for caminho in arquivos_comp + arquivos_turb:
    #     if not os.path.isfile(caminho):
    #         erros.append(f"Arquivo não encontrado: {caminho}")
    #     elif os.path.getsize(caminho) == 0:
    #         erros.append(f"Arquivo vazio: {caminho}")

    # print("\n" + "=" * 70)
    # if erros:
    #     print(f"{len(erros)} PROBLEMA(S):")
    #     for e in erros:
    #         print(f"  - {e}")
    # else:
    #     print("TODOS OS TESTES DE EXPORTAÇÃO PASSARAM.")
    # print("=" * 70)


    #_______________________________________________________________________________________
    # EM AMBOS OS CASOS, DESCOMENTE A LINHA DO exportar_maquina_dxf_completo()
    # PARA A MÁQUINA DESEJADA.
    #_______________________________________________________________________________________
    # Criar arquivo para exportar turbina completa em dxf
    maquina_turb = loftar_turbina(rad_turb, replicar=False)
    # exportar_maquina_dxf_completo(maquina_turb, "saida_dxf/turbina_completa.dxf")

    #_______________________________________________________________________________________
    # Criar arquivo para exportar compressor completo em dxf
    maquina_comp = loftar_compressor(rad_comp, replicar=False)
    # exportar_maquina_dxf_completo(maquina_comp, "saida_dxf/compressor_completo.dxf")

    #_______________________________________________________________________________________


if __name__ == "__main__":
    main()
