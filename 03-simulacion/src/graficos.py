"""Bar chart of simulated vs theoretical utilization and waiting time."""

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
    resumen = pd.read_csv(ruta_resumen)
    x = np.arange(len(resumen))
    ancho = 0.38
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    ax1.bar(x - ancho / 2, resumen["utilizacion_media"] * 100, ancho,
            yerr=resumen["utilizacion_desv"] * 100, capsize=3, label="Simulación")
    ax1.bar(x + ancho / 2, resumen["utilizacion_teorica"] * 100, ancho, label="Teoría")
    ax1.set_ylabel("Utilización ρ (%)")
    ax1.set_title("Utilización por estación")

    ax2.bar(x - ancho / 2, resumen["wq_min_media"], ancho,
            yerr=resumen["wq_min_desv"], capsize=3, label="Simulación")
    ax2.bar(x + ancho / 2, resumen["wq_min_teorico"], ancho, label="Teoría")
    ax2.set_ylabel("Espera en cola Wq (min)")
    ax2.set_title("Tiempo medio de espera por estación")

    for ax in (ax1, ax2):
        ax.set_xticks(x, resumen["estacion"])
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    ruta_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta_png, dpi=200)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot a scenario summary CSV.")
    parser.add_argument("--resumen", type=Path, default=RAIZ / "resumen-base.csv")
    parser.add_argument("--salida", type=Path, default=RAIZ / "graficos" / "base.png")
    args = parser.parse_args(argv)
    if not args.resumen.exists():
        print(f"Error: no existe {args.resumen}; ejecutá primero src/main.py", file=sys.stderr)
        return 1
    graficar(args.resumen, args.salida)
    print(f"Gráfico: {args.salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
