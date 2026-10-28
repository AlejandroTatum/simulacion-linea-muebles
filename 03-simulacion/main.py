"""Punto de entrada: simula uno o varios escenarios."""

import argparse
import sys
from pathlib import Path

from controlador.controlador import ControladorSimulacion, RAIZ
from modelo.configuracion import ErrorConfiguracion


def main(argv=None):
    parser = argparse.ArgumentParser(description="Simula la línea de producción de sillas.")
    parser.add_argument("--config", type=Path, nargs="+",
                        default=[RAIZ / "escenarios" / "base.json"],
                        help="uno o varios escenarios JSON (por defecto: escenarios/base.json)")
    parser.add_argument("--salida", type=Path, default=RAIZ,
                        help="carpeta donde se guardan CSV y gráficos")
    args = parser.parse_args(argv)

    try:
        ControladorSimulacion(args.salida).ejecutar(args.config)
    except FileNotFoundError as error:
        print(f"Error: no existe el escenario {error.filename}", file=sys.stderr)
        return 1
    except ErrorConfiguracion as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Error: no se pudo escribir en {args.salida}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
