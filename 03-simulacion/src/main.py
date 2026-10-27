"""Command-line entry point: run one or more scenarios and write their results.

For each scenario file it writes, inside --salida:
  resultados-<name>.csv  one row per replica and station
  resumen-<name>.csv     per-station mean, deviation, M/M/c theory and % error
  graficos/<name>.png    simulated vs theoretical utilization and waiting time
"""

import argparse
import sys
from pathlib import Path

from graficos import graficar
from linea import cargar_config, cuello_de_botella, ejecutar
from teoria import flujo_teorico_min

RAIZ = Path(__file__).resolve().parents[1]

# Columns shown on screen; the CSV keeps every column.
COLUMNAS_PANTALLA = ["estacion", "capacidad_h", "utilizacion_media", "utilizacion_teorica",
                     "error_utilizacion_pct", "lq_media", "lq_teorico", "wq_min_media",
                     "wq_min_teorico", "error_wq_pct"]


def correr_escenario(ruta, cfg, salida):
    """Simulate one scenario, save its files and print a short report."""
    replicas, resumen = ejecutar(cfg)
    nombre = ruta.stem  # e2.json -> resultados-e2.csv, graficos/e2.png
    ruta_replicas = salida / f"resultados-{nombre}.csv"
    ruta_resumen = salida / f"resumen-{nombre}.csv"
    ruta_grafico = salida / "graficos" / f"{nombre}.png"
    replicas.round(6).to_csv(ruta_replicas, index=False)
    resumen.round(6).to_csv(ruta_resumen, index=False)
    graficar(ruta_resumen, ruta_grafico)

    # Line-level indicators repeat on every station row, so keep one row per replica.
    linea = replicas.drop_duplicates("replica")
    flujo_teo = flujo_teorico_min(cfg["tasa_llegadas_h"], cfg["estaciones"])
    teoria = f"teoría {flujo_teo:.1f} min" if flujo_teo else "sin régimen estable"

    print(f"Escenario: {cfg['nombre']} | {cfg['replicas']} réplicas de {cfg['duracion_h']} h "
          f"({cfg['calentamiento_h']} h de calentamiento)")
    print(resumen[COLUMNAS_PANTALLA].round(3).to_string(index=False))
    print(f"Sillas terminadas por réplica: {linea['sillas_terminadas'].mean():.1f} "
          f"(desv. {linea['sillas_terminadas'].std():.1f})")
    print(f"Throughput: {linea['throughput_h'].mean():.3f} sillas/h | "
          f"tiempo total de flujo: {linea['flujo_min'].mean():.1f} min ({teoria})")
    print(f"Cuello de botella: {cuello_de_botella(resumen)}")
    print(f"Archivos: {ruta_replicas.name}, {ruta_resumen.name}, graficos/{ruta_grafico.name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulate the wooden chair production line.")
    parser.add_argument("--config", type=Path, nargs="+",
                        default=[RAIZ / "escenarios" / "base.json"],
                        help="one or more scenario JSON files (default: escenarios/base.json)")
    parser.add_argument("--salida", type=Path, default=RAIZ,
                        help="output directory (default: 03-simulacion/)")
    args = parser.parse_args(argv)

    # Validate every file first, so a typo in the last one does not waste a long run.
    escenarios = []
    for ruta in args.config:
        try:
            escenarios.append((ruta, cargar_config(ruta)))
        except FileNotFoundError:
            print(f"Error: no existe el escenario {ruta}", file=sys.stderr)
            return 1
        except (OSError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    for i, (ruta, cfg) in enumerate(escenarios):
        if i:
            print()
        correr_escenario(ruta, cfg, args.salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
