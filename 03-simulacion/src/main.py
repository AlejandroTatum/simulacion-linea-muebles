"""Command-line entry point: run one scenario and write its CSV results."""

import argparse
import sys
from pathlib import Path

from linea import cargar_config, cuello_de_botella, ejecutar

RAIZ = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simulate the wooden chair production line.")
    parser.add_argument("--config", type=Path, default=RAIZ / "escenarios" / "base.json",
                        help="scenario JSON file (default: escenarios/base.json)")
    parser.add_argument("--salida", type=Path, default=RAIZ,
                        help="output directory (default: 03-simulacion/)")
    args = parser.parse_args(argv)

    try:
        cfg = cargar_config(args.config)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    replicas, resumen = ejecutar(cfg)
    args.salida.mkdir(parents=True, exist_ok=True)
    sufijo = args.config.stem
    ruta_replicas = args.salida / f"resultados-{sufijo}.csv"
    ruta_resumen = args.salida / f"resumen-{sufijo}.csv"
    replicas.round(6).to_csv(ruta_replicas, index=False)
    resumen.round(6).to_csv(ruta_resumen, index=False)

    linea = replicas.drop_duplicates("replica")
    print(f"Escenario: {cfg['nombre']} | {cfg['replicas']} réplicas de {cfg['duracion_h']} h "
          f"({cfg['calentamiento_h']} h de calentamiento)")
    columnas = ["estacion", "capacidad_h", "utilizacion_media", "utilizacion_teorica",
                "error_utilizacion_pct", "lq_media", "lq_teorico", "wq_min_media",
                "wq_min_teorico", "error_wq_pct"]
    print(resumen[columnas].round(3).to_string(index=False))
    print(f"Sillas terminadas por réplica: {linea['sillas_terminadas'].mean():.1f} "
          f"(desv. {linea['sillas_terminadas'].std():.1f})")
    print(f"Throughput: {linea['throughput_h'].mean():.3f} sillas/h | "
          f"tiempo total de flujo: {linea['flujo_min'].mean():.1f} min")
    print(f"Cuello de botella: {cuello_de_botella(resumen)}")
    print(f"Archivos: {ruta_replicas.name}, {ruta_resumen.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
