import sys

from engine.estudos.export_csv import csv_compressor, csv_turbina
from engine.estudos.verificar_acoplamento import montar_caso


def main():
    sufixo = sys.argv[1] if len(sys.argv) > 1 else "ANTES"

    # Mesmas propriedades, combustível e parâmetros do caso vigente.
    # Não manter um segundo caso fixo com cp único e ψ antigo neste script.
    ciclo, comp, turb, rad_comp, rad_turb = montar_caso()

    csv_compressor(comp, rad_comp, f"saida_dxf/regressao_compressor_{sufixo}.csv")
    csv_turbina(turb, rad_turb, f"saida_dxf/regressao_turbina_{sufixo}.csv")
    print("CSVs de regressão gerados:", sufixo)


if __name__ == "__main__":
    main()
