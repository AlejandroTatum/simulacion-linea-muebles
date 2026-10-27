"""Animated view of the chair workshop over a few hours.

It runs one replica of the same model as main.py (linea.py), records every
change in the queues and workers, and plays it back as a workshop drawing:
a workbench per station with its workers, the material waiting in front of
it, and the finished chairs piling up in the warehouse.

  python src/animacion.py                                  # base scenario, 8 h
  python src/animacion.py --config escenarios/e2.json --horas 12
  python src/animacion.py --guardar graficos/base.gif      # save instead of showing
"""

import argparse
import sys
from bisect import bisect_right
from pathlib import Path

import matplotlib

from linea import cargar_config, simular_replica

RAIZ = Path(__file__).resolve().parents[1]

# Layout in drawing units (the axes keep a 1:1 aspect so shapes look real).
ANCHO_ESTACION = 3.4  # horizontal space per station
COLUMNAS_COLA, FILAS_COLA = 3, 2  # material drawn in front of each bench; the rest is "+n"
COLUMNAS_DEPOSITO, FILAS_DEPOSITO = 3, 4  # finished chairs drawn in the warehouse

# Wood colours, from raw plank to lacquered chair.
MADERA_CRUDA = "#c8955c"
MADERA_CORTADA = "#d9a66b"
MADERA_LIJADA = "#efcf9c"
MADERA_LAQUEADA = "#7a3f17"
BORDE = "#5a3a1a"
PISO = "#f3ece2"


def estados_en(traza, nombres, tiempos):
    """State of each station at each sample time.

    `traza` holds (time, station, queue, busy) changes. At a sample time the
    state is the one left by the last change at or before it (0 before any).
    Returns {station: {"cola": [...], "ocupados": [...]}}, one value per time.
    """
    estados = {}
    for nombre in nombres:
        cambios = sorted((c for c in traza if c[1] == nombre), key=lambda c: c[0])
        cola, ocupados, i = 0, 0, 0
        serie = {"cola": [], "ocupados": []}
        for t in tiempos:
            while i < len(cambios) and cambios[i][0] <= t:
                _, _, cola, ocupados = cambios[i]
                i += 1
            serie["cola"].append(cola)
            serie["ocupados"].append(ocupados)
        estados[nombre] = serie
    return estados


def utilizacion_teorica(cfg, est):
    """rho = lambda / (servers * mu); above 1 the station cannot keep up."""
    return cfg["tasa_llegadas_h"] / (est["recursos"] * 60 / est["tiempo_min"])


# ---------- Drawings. Each returns the patches it added, hidden until shown. ----------

def _rect(ax, x, y, w, h, color, borde=BORDE, visible=False, **kw):
    from matplotlib.patches import Rectangle
    return ax.add_patch(Rectangle((x, y), w, h, fc=color, ec=borde, lw=0.8,
                                  visible=visible, **kw))


def dibujar_tablones(ax, x, y):
    """Three raw planks stacked: the material that arrives with an order."""
    return [_rect(ax, x, y + k * 0.11, 0.62, 0.09, MADERA_CRUDA) for k in range(3)]


def dibujar_piezas(ax, x, y, color):
    """Cut parts of a chair: seat and backrest boards plus two legs."""
    return [_rect(ax, x, y, 0.34, 0.08, color),
            _rect(ax, x, y + 0.12, 0.34, 0.08, color),
            _rect(ax, x + 0.42, y, 0.07, 0.36, color),
            _rect(ax, x + 0.54, y, 0.07, 0.36, color)]


def dibujar_silla(ax, x, y, color, escala=1.0):
    """A chair seen from the side: front leg, seat, tall back post and backrest rail."""
    s = escala
    return [_rect(ax, x, y, 0.07 * s, 0.3 * s, color),                       # front leg
            _rect(ax, x, y + 0.28 * s, 0.48 * s, 0.07 * s, color),            # seat
            _rect(ax, x + 0.41 * s, y, 0.07 * s, 0.75 * s, color),            # back post
            _rect(ax, x + 0.22 * s, y + 0.62 * s, 0.26 * s, 0.07 * s, color),  # backrest rail
            _rect(ax, x + 0.22 * s, y + 0.46 * s, 0.26 * s, 0.05 * s, color)]  # lower rail


def dibujar_material(ax, etapa, x, y):
    """What a chair looks like before station number `etapa` (0 = first)."""
    if etapa == 0:
        return dibujar_tablones(ax, x, y)
    if etapa == 1:
        return dibujar_piezas(ax, x, y, MADERA_CORTADA)
    if etapa == 2:
        return dibujar_piezas(ax, x, y, MADERA_LIJADA)
    # From the fourth station on the piece is already a chair waiting for its finish.
    return dibujar_silla(ax, x, y, MADERA_LIJADA, escala=0.8)


def dibujar_operario(ax, x, y):
    """A worker standing behind the bench. Returns (body, head) to recolour."""
    from matplotlib.patches import Circle, FancyBboxPatch
    cuerpo = ax.add_patch(FancyBboxPatch((x - 0.2, y), 0.4, 0.62, boxstyle="round,pad=0.04",
                                         fc="#9aa3ab", ec="#3d4a55", lw=1))
    cabeza = ax.add_patch(Circle((x, y + 0.86), 0.17, fc="#f1c9a5", ec="#7a5a40", lw=1))
    return cuerpo, cabeza


def mostrar(patches, visible):
    for p in patches:
        p.set_visible(visible)


# ---------- Animation ----------

def animar(cfg, horas, paso_min, semilla, guardar=None):
    """Simulate `horas` hours from an empty workshop and animate it every `paso_min` minutes."""
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    # The animation shows the workshop from opening time, so no warm-up is discarded.
    corrida = dict(cfg, duracion_h=horas, calentamiento_h=0)
    traza, salidas = [], []
    simular_replica(corrida, semilla, traza=traza, salidas=salidas)

    estaciones = cfg["estaciones"]
    n = len(estaciones)
    nombres = [e["nombre"] for e in estaciones]
    tiempos = [k * paso_min for k in range(int(horas * 60 / paso_min) + 1)]
    estados = estados_en(traza, nombres, tiempos)
    terminadas = [bisect_right(salidas, t) for t in tiempos]  # chairs finished by each time
    rhos = [utilizacion_teorica(cfg, e) for e in estaciones]
    cuello = max(range(n), key=lambda i: rhos[i])

    fig, (taller, curvas) = plt.subplots(2, 1, figsize=(14, 8.5), height_ratios=[3, 1.3])
    fig.patch.set_facecolor("white")

    # --- Workshop floor: orders arrive on the left, warehouse on the right.
    x_deposito = 2.4 + n * ANCHO_ESTACION
    taller.set_xlim(-0.2, x_deposito + 2.6)
    taller.set_ylim(-2.3, 4.1)
    taller.set_aspect("equal")
    taller.axis("off")
    taller.add_patch(matplotlib.patches.Rectangle((-0.2, -2.3), x_deposito + 2.8, 6.4,
                                                  fc=PISO, ec="none", zorder=-5))
    taller.text(1.0, 3.4, "Llegan pedidos", ha="center", fontsize=10, weight="bold")
    taller.text(1.0, 3.0, f"{cfg['tasa_llegadas_h']:g} sillas/h en promedio",
                ha="center", fontsize=8, color="#555555")
    mostrar(dibujar_tablones(taller, 0.7, 1.4), True)
    taller.annotate("", xy=(2.3, 1.6), xytext=(1.5, 1.6),
                    arrowprops={"arrowstyle": "-|>", "color": "#888888", "lw": 1.5})

    operarios, en_banco, en_cola, sobrantes = [], [], [], []
    for i, est in enumerate(estaciones):
        cx = 2.4 + i * ANCHO_ESTACION + ANCHO_ESTACION / 2
        es_cuello = i == cuello
        color_cartel = "#c0392b" if es_cuello else "#34495e"

        # Sign with the station data, taken from the scenario file.
        cartel = f"{est['nombre']}\n{est['recursos']} operario{'s' if est['recursos'] > 1 else ''}"
        cartel += f" · {est['tiempo_min']:g} min/silla\nocupación ρ = {rhos[i]:.0%}"
        taller.text(cx, 3.15, cartel, ha="center", va="center", fontsize=9, color="white",
                    bbox={"boxstyle": "round,pad=0.4", "fc": color_cartel, "ec": "none"})
        if es_cuello:
            taller.text(cx, 3.95, "cuello de botella", ha="center", fontsize=8,
                        color=color_cartel, weight="bold")

        # Workbench: top and two legs.
        _rect(taller, cx - 1.35, 1.05, 2.7, 0.22, "#8d5b2f", visible=True)
        _rect(taller, cx - 1.25, 0.45, 0.12, 0.6, "#6e4523", visible=True)
        _rect(taller, cx + 1.13, 0.45, 0.12, 0.6, "#6e4523", visible=True)

        # Workers behind the bench, each with the piece they are working on.
        separacion = 2.4 / est["recursos"]
        personas, piezas = [], []
        for s in range(est["recursos"]):
            px = cx - 1.2 + separacion * (s + 0.5)
            personas.append(dibujar_operario(taller, px, 1.3))
            piezas.append(dibujar_material(taller, i, px - 0.3, 1.3))
        operarios.append(personas)
        en_banco.append(piezas)

        # Material waiting on the floor in front of the bench.
        espera = []
        for k in range(COLUMNAS_COLA * FILAS_COLA):
            fila, col = divmod(k, COLUMNAS_COLA)
            espera.append(dibujar_material(taller, i, cx - 1.2 + col * 0.85, -0.2 - fila * 0.9))
        en_cola.append(espera)
        sobrantes.append(taller.text(cx, -2.15, "", ha="center", fontsize=9, color="#555555"))

        flecha_x = cx + ANCHO_ESTACION / 2
        taller.annotate("", xy=(flecha_x + 0.15, 1.6), xytext=(flecha_x - 0.15, 1.6),
                        arrowprops={"arrowstyle": "-|>", "color": "#888888", "lw": 1.5})

    # --- Warehouse with finished, lacquered chairs.
    taller.text(x_deposito + 1.2, 3.4, "Depósito", ha="center", fontsize=10, weight="bold")
    contador = taller.text(x_deposito + 1.2, 3.0, "", ha="center", fontsize=9, color="#555555")
    deposito = []
    for k in range(COLUMNAS_DEPOSITO * FILAS_DEPOSITO):
        fila, col = divmod(k, COLUMNAS_DEPOSITO)
        deposito.append(dibujar_silla(taller, x_deposito + col * 0.8, 1.9 - fila * 1.0,
                                      MADERA_LAQUEADA, escala=0.85))

    titulo = fig.suptitle("", fontsize=13, weight="bold")

    # --- Below: how many chairs wait at each station over time.
    horas_eje = [t / 60 for t in tiempos]
    lineas = [curvas.plot([], [], label=nombre, lw=2.6 if i == cuello else 1.4)[0]
              for i, nombre in enumerate(nombres)]
    curvas.set_xlim(0, horas)
    curvas.set_ylim(0, max(max(estados[nb]["cola"]) for nb in nombres) + 1)
    curvas.set_xlabel("Horas desde que abre el taller")
    curvas.set_ylabel("Sillas esperando")
    curvas.grid(alpha=0.3)
    curvas.legend(loc="upper left", fontsize=8, ncol=n)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    def dibujar(k):
        en_proceso = 0
        for i, nombre in enumerate(nombres):
            cola = estados[nombre]["cola"][k]
            ocupados = estados[nombre]["ocupados"][k]
            en_proceso += cola + ocupados
            for s, ((cuerpo, _), pieza) in enumerate(zip(operarios[i], en_banco[i])):
                trabajando = s < ocupados
                cuerpo.set_facecolor("#2e6da4" if trabajando else "#9aa3ab")  # blue = working
                mostrar(pieza, trabajando)
            for j, material in enumerate(en_cola[i]):
                mostrar(material, j < cola)
            sobra = cola - len(en_cola[i])
            sobrantes[i].set_text(f"esperando: {cola}" + (f" (+{sobra} sin dibujar)" if sobra > 0 else ""))
            lineas[i].set_data(horas_eje[:k + 1], estados[nombre]["cola"][:k + 1])
        for j, silla in enumerate(deposito):
            mostrar(silla, j < terminadas[k])
        contador.set_text(f"{terminadas[k]} sillas terminadas")
        h, m = divmod(int(tiempos[k]), 60)
        titulo.set_text(f"Taller de sillas · {cfg['nombre']} · hora {h:02d}:{m:02d} · "
                        f"{en_proceso} sillas en proceso")

    animacion = FuncAnimation(fig, dibujar, frames=len(tiempos), interval=150, repeat=False)
    if guardar:
        guardar.parent.mkdir(parents=True, exist_ok=True)
        animacion.save(guardar, writer=PillowWriter(fps=8))
        plt.close(fig)
    else:
        plt.show()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Animate the chair workshop.")
    parser.add_argument("--config", type=Path, default=RAIZ / "escenarios" / "base.json",
                        help="scenario JSON file (default: escenarios/base.json)")
    parser.add_argument("--horas", type=float, default=8,
                        help="simulated hours to show (default: 8)")
    parser.add_argument("--paso", type=float, default=5,
                        help="simulated minutes per frame (default: 5)")
    parser.add_argument("--semilla", type=int, help="seed (default: the scenario's)")
    parser.add_argument("--guardar", type=Path, help="save as GIF instead of opening a window")
    args = parser.parse_args(argv)

    if args.horas <= 0 or args.paso <= 0:
        print("Error: --horas y --paso deben ser mayores que 0", file=sys.stderr)
        return 1
    try:
        cfg = cargar_config(args.config)
    except FileNotFoundError:
        print(f"Error: no existe el escenario {args.config}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.guardar:
        matplotlib.use("Agg")  # no window needed to write the file
    semilla = cfg["semilla"] if args.semilla is None else args.semilla
    animar(cfg, args.horas, args.paso, semilla, args.guardar)
    if args.guardar:
        print(f"Animación guardada: {args.guardar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
