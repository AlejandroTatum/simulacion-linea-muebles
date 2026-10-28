"""Gráfico de utilización y espera: simulación frente a teoría."""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]


def graficar(ruta_resumen, ruta_png):
    """Genera las dos barras comparativas a partir de un resumen CSV."""
    resumen = pd.read_csv(ruta_resumen)
    x = np.arange(len(resumen))
    ancho = 0.38
    figura, (eje_utilizacion, eje_espera) = plt.subplots(1, 2, figsize=(10, 4))

    eje_utilizacion.bar(x - ancho / 2, resumen["utilizacion_media"] * 100, ancho,
                        yerr=resumen["utilizacion_desv"] * 100, capsize=3, label="Simulación")
    eje_utilizacion.bar(x + ancho / 2, resumen["utilizacion_teorica"] * 100, ancho, label="Teoría")
    eje_utilizacion.set_ylabel("Utilización ρ (%)")
    eje_utilizacion.set_title("Utilización por estación")

    eje_espera.bar(x - ancho / 2, resumen["wq_min_media"], ancho,
                   yerr=resumen["wq_min_desv"], capsize=3, label="Simulación")
    eje_espera.bar(x + ancho / 2, resumen["wq_min_teorico"], ancho, label="Teoría")
    eje_espera.set_ylabel("Espera en cola Wq (min)")
    eje_espera.set_title("Tiempo medio de espera por estación")

    for eje in (eje_utilizacion, eje_espera):
        eje.set_xticks(x, resumen["estacion"])
        eje.legend()
        eje.grid(axis="y", alpha=0.3)

    figura.tight_layout()
    ruta_png.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(ruta_png, dpi=200)
    plt.close(figura)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Grafica un resumen de escenario.")
    parser.add_argument("--resumen", type=Path, default=RAIZ / "resumen-base.csv")
    parser.add_argument("--salida", type=Path, default=RAIZ / "graficos" / "base.png")
    args = parser.parse_args(argv)

    if not args.resumen.exists():
        print(f"Error: no existe {args.resumen}; ejecutá primero main.py", file=sys.stderr)
        return 1

    graficar(args.resumen, args.salida)
    print(f"Gráfico: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
