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


# ---------- Palette: one meaning per colour ----------

PARED = "#efe7da"            # workshop wall
PISO = "#d8c19c"             # wooden floor
PISO_TABLA = "#cbb187"       # floorboard joints
MESA = "#8a5a33"             # workbench top
MESA_CANTO = "#6b4226"       # bench edge and legs
TARIMA = "#b48f5e"           # pallet under waiting material
MADERA_CRUDA = "#c08a52"     # raw plank
MADERA_CORTADA = "#d6a467"   # cut parts
MADERA_LIJADA = "#ecca95"    # sanded parts and unfinished chair
MADERA_LAQUEADA = "#6e3816"  # lacquered chair
VETA = "#5a3a1a"             # wood outline
TRABAJANDO = "#2f6ea5"       # worker busy
LIBRE = "#a5adb5"            # worker idle
PIEL = "#eec39d"
CARTEL = "#2f3e4c"           # station sign
CUELLO = "#b8322a"           # bottleneck: the only red on screen
TEXTO = "#2b2622"
TEXTO_SUAVE = "#6d625a"

# Layout in drawing units (the axes keep a 1:1 aspect so shapes look real).
ANCHO_ESTACION = 3.4         # horizontal space per station
ANCHO_LLEGADA = 2.4          # arrival area on the left
ANCHO_DEPOSITO = 2.6         # warehouse on the right
Y_PISO = 0.55                # where the wall meets the floor
COLUMNAS_COLA, FILAS_COLA = 3, 2           # material drawn on each pallet; the rest is "+n"
COLUMNAS_DEPOSITO, FILAS_DEPOSITO = 3, 4   # finished chairs drawn in the warehouse


# ---------- Drawings. Each returns the artists it added, hidden until shown. ----------

def _sombra():
    """Soft drop shadow: offset down-right, translucent."""
    from matplotlib import patheffects
    return [patheffects.SimplePatchShadow(offset=(2, -2), alpha=0.18), patheffects.Normal()]


def _rect(ax, x, y, w, h, color, borde=VETA, visible=False, sombra=False, **kw):
    from matplotlib.patches import Rectangle
    r = ax.add_patch(Rectangle((x, y), w, h, fc=color, ec=borde, lw=0.7, visible=visible, **kw))
    if sombra:
        r.set_path_effects(_sombra())
    return r


def dibujar_tablones(ax, x, y, visible=False):
    """Three raw planks stacked: the material that arrives with an order."""
    return [_rect(ax, x, y + k * 0.12, 0.66, 0.1, MADERA_CRUDA, visible=visible) for k in range(3)]


def dibujar_piezas(ax, x, y, color):
    """Cut parts of one chair: seat and backrest boards plus two legs."""
    return [_rect(ax, x, y, 0.36, 0.09, color),
            _rect(ax, x, y + 0.13, 0.36, 0.09, color),
            _rect(ax, x + 0.44, y, 0.08, 0.4, color),
            _rect(ax, x + 0.57, y, 0.08, 0.4, color)]


def dibujar_silla(ax, x, y, color, escala=1.0, visible=False):
    """A chair seen from the side: front leg, seat, tall back post and two backrest rails."""
    s = escala
    partes = [_rect(ax, x, y, 0.07 * s, 0.32 * s, color, visible=visible),                       # front leg
              _rect(ax, x, y + 0.3 * s, 0.5 * s, 0.07 * s, color, visible=visible),              # seat
              _rect(ax, x + 0.43 * s, y, 0.07 * s, 0.8 * s, color, visible=visible),             # back post
              _rect(ax, x + 0.24 * s, y + 0.66 * s, 0.26 * s, 0.07 * s, color, visible=visible),  # top rail
              _rect(ax, x + 0.24 * s, y + 0.5 * s, 0.26 * s, 0.05 * s, color, visible=visible)]   # lower rail
    return partes


def dibujar_material(ax, etapa, x, y):
    """What a chair looks like before station number `etapa` (0 = first)."""
    if etapa == 0:
        return dibujar_tablones(ax, x, y)
    if etapa == 1:
        return dibujar_piezas(ax, x, y, MADERA_CORTADA)
    if etapa == 2:
        return dibujar_piezas(ax, x, y, MADERA_LIJADA)
    # From the fourth station on the piece is already a chair waiting for its finish.
    return dibujar_silla(ax, x, y, MADERA_LIJADA, escala=0.78)


class Operario:
    """A worker behind the bench: blue and reaching for the piece when busy, grey and idle otherwise."""

    def __init__(self, ax, x, y):
        from matplotlib.patches import Circle, FancyBboxPatch
        self.x, self.y = x, y
        self.cuerpo = ax.add_patch(FancyBboxPatch((x - 0.21, y), 0.42, 0.66,
                                                  boxstyle="round,pad=0.05,rounding_size=0.14",
                                                  fc=LIBRE, ec="none"))
        self.cabeza = ax.add_patch(Circle((x, y + 0.92), 0.18, fc=PIEL, ec="none"))
        self.brazos = [ax.plot([], [], color=LIBRE, lw=5, solid_capstyle="round")[0] for _ in range(2)]
        self.trabajar(False)

    def trabajar(self, ocupado):
        x, y = self.x, self.y
        color = TRABAJANDO if ocupado else LIBRE
        self.cuerpo.set_facecolor(color)
        for brazo, lado in zip(self.brazos, (-1, 1)):
            brazo.set_color(color)
            if ocupado:  # both hands down on the piece in front of the body
                brazo.set_data([x + lado * 0.2, x + lado * 0.08], [y + 0.55, y + 0.12])
            else:        # arms hanging at the sides
                brazo.set_data([x + lado * 0.24, x + lado * 0.27], [y + 0.55, y + 0.2])


def mostrar(artistas, visible):
    for a in artistas:
        a.set_visible(visible)


def dibujar_fondo(ax, ancho, alto_min, alto_max):
    """Wall and wooden floor: the only texture is the floorboards."""
    _rect(ax, 0, Y_PISO, ancho, alto_max - Y_PISO, PARED, borde="none", visible=True, zorder=-10)
    _rect(ax, 0, alto_min, ancho, Y_PISO - alto_min, PISO, borde="none", visible=True, zorder=-10)
    y = Y_PISO - 0.5
    while y > alto_min:
        ax.plot([0, ancho], [y, y], color=PISO_TABLA, lw=0.8, zorder=-9)
        y -= 0.5
    ax.plot([0, ancho], [Y_PISO, Y_PISO], color=MESA_CANTO, lw=1.2, alpha=0.5, zorder=-9)


def dibujar_tarima(ax, cx, y, ancho=2.7):
    """Low pallet on the floor where material waits its turn."""
    _rect(ax, cx - ancho / 2, y, ancho, 0.1, TARIMA, visible=True, sombra=True)
    for k in range(3):  # three blocks underneath: both ends and the middle
        bx = cx - ancho / 2 + 0.05 + k * (ancho - 0.4) / 2
        _rect(ax, bx, y - 0.1, 0.3, 0.1, TARIMA, visible=True)


def dibujar_mesa(ax, cx):
    """Workbench: thick top with a darker front edge, two legs."""
    _rect(ax, cx - 1.38, 1.06, 2.76, 0.18, MESA, borde=MESA_CANTO, visible=True, sombra=True)
    _rect(ax, cx - 1.38, 1.0, 2.76, 0.07, MESA_CANTO, borde="none", visible=True)
    for lx in (cx - 1.25, cx + 1.11):
        _rect(ax, lx, Y_PISO - 0.05, 0.14, 0.97, MESA_CANTO, borde="none", visible=True)


def dibujar_cartel(ax, cx, texto, color):
    """Sign hanging from the ceiling with the station data."""
    from matplotlib.patches import FancyBboxPatch
    for dx in (-0.8, 0.8):
        ax.plot([cx + dx, cx + dx], [3.85, 4.4], color=TEXTO_SUAVE, lw=0.8)
    cartel = ax.add_patch(FancyBboxPatch((cx - 1.3, 2.95), 2.6, 0.9,
                                         boxstyle="round,pad=0.02,rounding_size=0.12",
                                         fc=color, ec="none"))
    cartel.set_path_effects(_sombra())
    titulo, detalle = texto
    ax.text(cx, 3.6, titulo, ha="center", va="center", fontsize=11, weight="bold", color="white")
    ax.text(cx, 3.2, detalle, ha="center", va="center", fontsize=8.5, color="#f2ece4")


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

    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TEXTO})
    fig = plt.figure(figsize=(14, 8.6), facecolor="white")
    taller = fig.add_axes((0.02, 0.33, 0.96, 0.58))
    curvas = fig.add_axes((0.06, 0.06, 0.9, 0.2))

    # --- Workshop: orders arrive on the left, warehouse on the right.
    x_deposito = ANCHO_LLEGADA + n * ANCHO_ESTACION
    ancho = x_deposito + ANCHO_DEPOSITO
    y_min, y_max = -2.45, 4.4
    taller.set_xlim(0, ancho)
    taller.set_ylim(y_min, y_max)
    taller.set_aspect("equal")
    taller.axis("off")
    dibujar_fondo(taller, ancho, y_min, y_max)

    taller.text(1.2, 3.55, "Pedidos", ha="center", fontsize=11, weight="bold")
    taller.text(1.2, 3.18, f"llegan {cfg['tasa_llegadas_h']:g} sillas/h\nen promedio", ha="center",
                va="top", fontsize=8.5, color=TEXTO_SUAVE)
    dibujar_tarima(taller, 1.2, -1.75, ancho=1.6)  # same floor line as the stations' pallets
    mostrar(dibujar_tablones(taller, 0.87, -1.65), True)
    mostrar(dibujar_tablones(taller, 0.87, -1.29), True)

    operarios, en_banco, en_cola, esperando = [], [], [], []
    for i, est in enumerate(estaciones):
        cx = ANCHO_LLEGADA + i * ANCHO_ESTACION + ANCHO_ESTACION / 2
        es_cuello = i == cuello
        plural = "s" if est["recursos"] > 1 else ""
        dibujar_cartel(taller, cx, (est["nombre"],
                                    f"{est['recursos']} operario{plural} · {est['tiempo_min']:g} min por silla"
                                    f"\nocupación ρ = {rhos[i]:.0%}"),
                       CUELLO if es_cuello else CARTEL)
        if es_cuello:
            taller.text(cx, 2.72, "cuello de botella", ha="center", fontsize=9, weight="bold",
                        color=CUELLO)

        # Workers stand behind the bench; the piece they work on rests on it.
        separacion = 2.4 / est["recursos"]
        personas, piezas = [], []
        for s in range(est["recursos"]):
            px = cx - 1.2 + separacion * (s + 0.5)
            personas.append(Operario(taller, px, 1.28))
            piezas.append(dibujar_material(taller, i, px - 0.32, 1.25))
        dibujar_mesa(taller, cx)
        for pieza in piezas:  # keep the piece in front of the bench top
            for parte in pieza:
                parte.set_zorder(3)
        operarios.append(personas)
        en_banco.append(piezas)

        # Material waiting on a pallet in front of the bench.
        dibujar_tarima(taller, cx, -1.75)
        espera = []
        for k in range(COLUMNAS_COLA * FILAS_COLA):
            fila, col = divmod(k, COLUMNAS_COLA)
            espera.append(dibujar_material(taller, i, cx - 1.22 + col * 0.86, -1.62 + fila * 0.72))
        en_cola.append(espera)
        esperando.append(taller.text(cx, -2.2, "", ha="center", fontsize=9, color=TEXTO_SUAVE))

        # Flow arrow towards the next bench (or the warehouse).
        fx = cx + ANCHO_ESTACION / 2
        taller.annotate("", xy=(fx + 0.22, 1.9), xytext=(fx - 0.22, 1.9),
                        arrowprops={"arrowstyle": "-|>", "color": TEXTO_SUAVE, "lw": 1.4})
    taller.annotate("", xy=(ANCHO_LLEGADA + 0.22, 1.9), xytext=(ANCHO_LLEGADA - 0.22, 1.9),
                    arrowprops={"arrowstyle": "-|>", "color": TEXTO_SUAVE, "lw": 1.4})

    # --- Warehouse with finished, lacquered chairs.
    xd = x_deposito + ANCHO_DEPOSITO / 2
    taller.text(xd, 3.55, "Depósito", ha="center", fontsize=11, weight="bold")
    contador = taller.text(xd, 3.18, "", ha="center", va="top", fontsize=8.5, color=TEXTO_SUAVE)
    deposito = []
    for k in range(COLUMNAS_DEPOSITO * FILAS_DEPOSITO):
        fila, col = divmod(k, COLUMNAS_DEPOSITO)
        deposito.append(dibujar_silla(taller, x_deposito + 0.25 + col * 0.78, 1.75 - fila * 1.05,
                                      MADERA_LAQUEADA, escala=0.85))

    # --- Header: scenario on the left, clock and totals on the right.
    fig.text(0.03, 0.955, "Taller de sillas", fontsize=17, weight="bold")
    fig.text(0.03, 0.925, cfg["nombre"], fontsize=10.5, color=TEXTO_SUAVE)
    reloj = fig.text(0.97, 0.952, "", ha="right", fontsize=17, weight="bold")
    totales = fig.text(0.97, 0.925, "", ha="right", fontsize=10.5, color=TEXTO_SUAVE)

    # --- Below: how many chairs wait at each station over time.
    colores = ["#4f6d7a", "#8c7a5b", "#6f8f5a", "#7a5c8c", "#5c7a8c", "#8c5c6a"]
    horas_eje = [t / 60 for t in tiempos]
    lineas = []
    for i, nombre in enumerate(nombres):
        color = CUELLO if i == cuello else colores[i % len(colores)]
        lineas.append(curvas.plot([], [], color=color, lw=2.4 if i == cuello else 1.4,
                                  label=nombre)[0])
    curvas.set_xlim(0, horas)
    curvas.set_ylim(0, max(max(estados[nb]["cola"]) for nb in nombres) + 1)
    curvas.set_title("Sillas esperando en cada estación", loc="left", fontsize=10.5,
                     weight="bold", pad=8)
    curvas.set_xlabel("horas desde que abre el taller", fontsize=9, color=TEXTO_SUAVE)
    curvas.tick_params(colors=TEXTO_SUAVE, labelsize=8.5)
    for lado in ("top", "right"):
        curvas.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        curvas.spines[lado].set_color("#c9c1b6")
    curvas.grid(axis="y", color="#ece6dd")
    curvas.legend(loc="upper left", fontsize=8.5, ncol=n, frameon=False)

    def dibujar(k):
        en_proceso = 0
        for i, nombre in enumerate(nombres):
            cola = estados[nombre]["cola"][k]
            ocupados = estados[nombre]["ocupados"][k]
            en_proceso += cola + ocupados
            for s, (persona, pieza) in enumerate(zip(operarios[i], en_banco[i])):
                persona.trabajar(s < ocupados)
                mostrar(pieza, s < ocupados)
            for j, material in enumerate(en_cola[i]):
                mostrar(material, j < cola)
            sobra = cola - len(en_cola[i])
            texto = "nadie esperando" if cola == 0 else f"{cola} esperando"
            esperando[i].set_text(texto + (f"  (+{sobra} fuera de la tarima)" if sobra > 0 else ""))
            lineas[i].set_data(horas_eje[:k + 1], estados[nombre]["cola"][:k + 1])
        for j, silla in enumerate(deposito):
            mostrar(silla, j < terminadas[k])
        contador.set_text(f"{terminadas[k]} sillas terminadas")
        h, m = divmod(int(tiempos[k]), 60)
        reloj.set_text(f"hora {h:02d}:{m:02d}")
        totales.set_text(f"{en_proceso} sillas en proceso · {terminadas[k]} terminadas")

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
