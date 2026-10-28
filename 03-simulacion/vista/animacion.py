"""Vista animada del taller de sillas."""

import argparse
import sys
from bisect import bisect_right
from pathlib import Path

import matplotlib

from modelo.configuracion import ErrorConfiguracion, cargar_escenario
from modelo.simulacion import SimulacionLinea

RAIZ = Path(__file__).resolve().parents[1]
FUENTES = RAIZ / "fuentes"


def estados_en(traza, nombres, tiempos):
    """Estado de cada estación en cada instante de muestra."""
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
    """Ocupación teórica: lambda / (operarios * mu)."""
    return cfg["tasa_llegadas_h"] / (est["recursos"] * 60 / est["tiempo_min"])


# ---------- Colores y medidas del dibujo ----------

PARED = "#efe7da"
PISO = "#d8c19c"
PISO_TABLA = "#cbb187"
MESA = "#8a5a33"
MESA_CANTO = "#6b4226"
TARIMA = "#b48f5e"
MADERA_CRUDA = "#c08a52"
MADERA_CORTADA = "#d6a467"
MADERA_LIJADA = "#ecca95"
MADERA_LAQUEADA = "#6e3816"
VETA = "#5a3a1a"
TRABAJANDO = "#2f6ea5"
LIBRE = "#a5adb5"
PIEL = "#eec39d"
CARTEL = "#2f3e4c"
CUELLO = "#b8322a"
TEXTO = "#2b2622"
TEXTO_SUAVE = "#6d625a"

ANCHO_ESTACION = 3.4
ANCHO_LLEGADA = 2.4
ANCHO_DEPOSITO = 2.6
Y_PISO = 0.55
COLUMNAS_COLA, FILAS_COLA = 3, 2
COLUMNAS_DEPOSITO, FILAS_DEPOSITO = 3, 4


# ---------- Dibujos ----------

def _sombra():
    """Sombra suave para dar volumen."""
    from matplotlib import patheffects
    return [patheffects.SimplePatchShadow(offset=(2, -2), alpha=0.18), patheffects.Normal()]


def _rect(ax, x, y, w, h, color, borde=VETA, visible=False, sombra=False, **kw):
    from matplotlib.patches import Rectangle
    r = ax.add_patch(Rectangle((x, y), w, h, fc=color, ec=borde, lw=0.7, visible=visible, **kw))
    if sombra:
        r.set_path_effects(_sombra())
    return r


def dibujar_tablones(ax, x, y, visible=False):
    """Tres tablones apilados."""
    return [_rect(ax, x, y + k * 0.12, 0.66, 0.1, MADERA_CRUDA, visible=visible) for k in range(3)]


def dibujar_piezas(ax, x, y, color):
    """Asiento, respaldo y dos patas."""
    return [_rect(ax, x, y, 0.36, 0.09, color),
            _rect(ax, x, y + 0.13, 0.36, 0.09, color),
            _rect(ax, x + 0.44, y, 0.08, 0.4, color),
            _rect(ax, x + 0.57, y, 0.08, 0.4, color)]


def dibujar_silla(ax, x, y, color, escala=1.0, visible=False):
    """Silla de perfil."""
    s = escala
    partes = [_rect(ax, x, y, 0.07 * s, 0.32 * s, color, visible=visible),                        # pata delantera
              _rect(ax, x, y + 0.3 * s, 0.5 * s, 0.07 * s, color, visible=visible),               # asiento
              _rect(ax, x + 0.43 * s, y, 0.07 * s, 0.8 * s, color, visible=visible),              # pata trasera
              _rect(ax, x + 0.24 * s, y + 0.66 * s, 0.26 * s, 0.07 * s, color, visible=visible),  # travesaño superior
              _rect(ax, x + 0.24 * s, y + 0.5 * s, 0.26 * s, 0.05 * s, color, visible=visible)]   # travesaño inferior
    return partes


def dibujar_material(ax, etapa, x, y):
    """Aspecto de la pieza antes de la estación indicada."""
    if etapa == 0:
        return dibujar_tablones(ax, x, y)
    if etapa == 1:
        return dibujar_piezas(ax, x, y, MADERA_CORTADA)
    if etapa == 2:
        return dibujar_piezas(ax, x, y, MADERA_LIJADA)
    return dibujar_silla(ax, x, y, MADERA_LIJADA, escala=0.78)


class Operario:
    """Operario del banco: azul si trabaja, gris si espera material."""

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
            if ocupado:
                brazo.set_data([x + lado * 0.2, x + lado * 0.08], [y + 0.55, y + 0.12])
            else:
                brazo.set_data([x + lado * 0.24, x + lado * 0.27], [y + 0.55, y + 0.2])


def mostrar(artistas, visible):
    for a in artistas:
        a.set_visible(visible)


def dibujar_fondo(ax, ancho, alto_min, alto_max):
    """Pared y piso de madera."""
    _rect(ax, 0, Y_PISO, ancho, alto_max - Y_PISO, PARED, borde="none", visible=True, zorder=-10)
    _rect(ax, 0, alto_min, ancho, Y_PISO - alto_min, PISO, borde="none", visible=True, zorder=-10)
    y = Y_PISO - 0.5
    while y > alto_min:
        ax.plot([0, ancho], [y, y], color=PISO_TABLA, lw=0.8, zorder=-9)
        y -= 0.5
    ax.plot([0, ancho], [Y_PISO, Y_PISO], color=MESA_CANTO, lw=1.2, alpha=0.5, zorder=-9)


def dibujar_tarima(ax, cx, y, ancho=2.7):
    """Tarima baja para el material en espera."""
    _rect(ax, cx - ancho / 2, y, ancho, 0.1, TARIMA, visible=True, sombra=True)
    for k in range(3):
        bx = cx - ancho / 2 + 0.05 + k * (ancho - 0.4) / 2
        _rect(ax, bx, y - 0.1, 0.3, 0.1, TARIMA, visible=True)


def dibujar_mesa(ax, cx):
    """Mesa de trabajo con sus patas."""
    _rect(ax, cx - 1.38, 1.06, 2.76, 0.18, MESA, borde=MESA_CANTO, visible=True, sombra=True)
    _rect(ax, cx - 1.38, 1.0, 2.76, 0.07, MESA_CANTO, borde="none", visible=True)
    for lx in (cx - 1.25, cx + 1.11):
        _rect(ax, lx, Y_PISO - 0.05, 0.14, 0.97, MESA_CANTO, borde="none", visible=True)


def dibujar_cartel(ax, cx, texto, color):
    """Cartel con el nombre y los datos de la estación."""
    from matplotlib.patches import FancyBboxPatch
    for dx in (-0.8, 0.8):
        ax.plot([cx + dx, cx + dx], [3.85, 4.4], color=TEXTO_SUAVE, lw=0.8)
    cartel = ax.add_patch(FancyBboxPatch((cx - 1.3, 2.95), 2.6, 0.9,
                                         boxstyle="round,pad=0.02,rounding_size=0.12",
                                         fc=color, ec="none"))
    cartel.set_path_effects(_sombra())
    titulo, detalle = texto
    textos = [ax.text(cx, 3.6, titulo, ha="center", va="center", fontsize=11, weight="semibold",
                      color="white"),
              ax.text(cx, 3.2, detalle, ha="center", va="center", fontsize=8.5, color="#f2ece4")]
    return cartel, textos


# ---------- Animación ----------

TAMANO_DISENO = (14, 8.6)
FONDO = "#faf7f2"


def _usar_fuente():
    """Registra la fuente Inter incluida; si falta, usa la de Matplotlib."""
    from matplotlib import font_manager
    archivos = sorted(FUENTES.glob("*.ttf"))
    for archivo in archivos:
        font_manager.fontManager.addfont(str(archivo))
    familia = "Inter" if archivos else "DejaVu Sans"
    matplotlib.rcParams.update({"font.family": familia, "text.color": TEXTO})


class Escena:
    """Figura, dibujo por cuadro y ajuste de textos."""

    def __init__(self, figura, dibujar, tiempos, carteles, ajustar_texto):
        self.figura = figura
        self.dibujar = dibujar
        self.tiempos = tiempos
        self.carteles = carteles
        self.ajustar_texto = ajustar_texto


def armar(cfg, horas, paso_min, semilla):
    """Simula desde un taller vacío y prepara la escena."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator

    # La animación arranca con el taller vacío, sin calentamiento.
    corrida = dict(cfg, duracion_h=horas, calentamiento_h=0)
    traza, salidas = [], []
    SimulacionLinea(corrida).correr_replica(semilla, traza=traza, salidas=salidas)

    estaciones = cfg["estaciones"]
    n = len(estaciones)
    nombres = [e["nombre"] for e in estaciones]
    tiempos = [k * paso_min for k in range(int(horas * 60 / paso_min) + 1)]
    estados = estados_en(traza, nombres, tiempos)
    terminadas = [bisect_right(salidas, t) for t in tiempos]
    rhos = [utilizacion_teorica(cfg, e) for e in estaciones]
    cuello = max(range(n), key=lambda i: rhos[i])

    _usar_fuente()
    fig = plt.figure(figsize=TAMANO_DISENO, facecolor=FONDO)
    taller = fig.add_axes((0.02, 0.31, 0.96, 0.57))
    curvas = fig.add_axes((0.06, 0.07, 0.78, 0.17), facecolor=FONDO)

    # Taller: pedidos a la izquierda y depósito a la derecha.
    x_deposito = ANCHO_LLEGADA + n * ANCHO_ESTACION
    ancho = x_deposito + ANCHO_DEPOSITO
    y_min, y_max = -2.45, 4.4
    taller.set_xlim(0, ancho)
    taller.set_ylim(y_min, y_max)
    taller.set_aspect("equal")
    taller.axis("off")
    dibujar_fondo(taller, ancho, y_min, y_max)

    taller.text(1.2, 3.55, "Pedidos", ha="center", fontsize=11, weight="semibold")
    taller.text(1.2, 3.18, f"llegan {cfg['tasa_llegadas_h']:g} sillas/h\nen promedio", ha="center",
                va="top", fontsize=8.5, color=TEXTO_SUAVE)
    dibujar_tarima(taller, 1.2, -1.75, ancho=1.6)
    mostrar(dibujar_tablones(taller, 0.87, -1.65), True)
    mostrar(dibujar_tablones(taller, 0.87, -1.29), True)

    operarios, en_banco, en_cola, esperando, carteles = [], [], [], [], []
    for i, est in enumerate(estaciones):
        cx = ANCHO_LLEGADA + i * ANCHO_ESTACION + ANCHO_ESTACION / 2
        es_cuello = i == cuello
        plural = "s" if est["recursos"] > 1 else ""
        carteles.append(dibujar_cartel(
            taller, cx,
            (est["nombre"], f"{est['recursos']} operario{plural} · {est['tiempo_min']:g} min/silla"
                            f"\nocupación ρ = {rhos[i]:.0%}"),
            CUELLO if es_cuello else CARTEL))
        if es_cuello:
            taller.text(cx, 2.72, "cuello de botella", ha="center", fontsize=9, weight="semibold",
                        color=CUELLO)

        # Los operarios van detrás de la mesa y la pieza descansa sobre ella.
        separacion = 2.4 / est["recursos"]
        personas, piezas = [], []
        for s in range(est["recursos"]):
            px = cx - 1.2 + separacion * (s + 0.5)
            personas.append(Operario(taller, px, 1.28))
            piezas.append(dibujar_material(taller, i, px - 0.32, 1.25))
        dibujar_mesa(taller, cx)
        for pieza in piezas:
            for parte in pieza:
                parte.set_zorder(3)
        operarios.append(personas)
        en_banco.append(piezas)

        # Material esperando en la tarima.
        dibujar_tarima(taller, cx, -1.75)
        espera = []
        for k in range(COLUMNAS_COLA * FILAS_COLA):
            fila, col = divmod(k, COLUMNAS_COLA)
            espera.append(dibujar_material(taller, i, cx - 1.22 + col * 0.86, -1.62 + fila * 0.72))
        en_cola.append(espera)
        esperando.append(taller.text(cx, -2.2, "", ha="center", fontsize=9, color=TEXTO_SUAVE))

        # Flecha hacia la siguiente estación o el depósito.
        fx = cx + ANCHO_ESTACION / 2
        taller.annotate("", xy=(fx + 0.22, 1.9), xytext=(fx - 0.22, 1.9),
                        arrowprops={"arrowstyle": "-|>", "color": TEXTO_SUAVE, "lw": 1.4})
    taller.annotate("", xy=(ANCHO_LLEGADA + 0.22, 1.9), xytext=(ANCHO_LLEGADA - 0.22, 1.9),
                    arrowprops={"arrowstyle": "-|>", "color": TEXTO_SUAVE, "lw": 1.4})

    # Depósito con las sillas terminadas.
    xd = x_deposito + ANCHO_DEPOSITO / 2
    taller.text(xd, 3.55, "Depósito", ha="center", fontsize=11, weight="semibold")
    contador = taller.text(xd, 3.18, "", ha="center", va="top", fontsize=8.5, color=TEXTO_SUAVE)
    deposito = []
    for k in range(COLUMNAS_DEPOSITO * FILAS_DEPOSITO):
        fila, col = divmod(k, COLUMNAS_DEPOSITO)
        deposito.append(dibujar_silla(taller, x_deposito + 0.25 + col * 0.78, 1.75 - fila * 1.05,
                                      MADERA_LAQUEADA, escala=0.85))

    # Encabezado: escenario, leyenda, reloj y totales.
    fig.text(0.03, 0.952, "Taller de sillas", fontsize=17, weight="semibold")
    fig.text(0.03, 0.915, cfg["nombre"], fontsize=10.5, color=TEXTO_SUAVE)
    reloj = fig.text(0.97, 0.952, "", ha="right", fontsize=17, weight="semibold")
    totales = fig.text(0.97, 0.915, "", ha="right", fontsize=10.5, color=TEXTO_SUAVE)
    claves = [Patch(color=TRABAJANDO, label="operario trabajando"),
              Patch(color=LIBRE, label="operario esperando material"),
              Patch(color=CUELLO, label="cuello de botella")]
    fig.legend(handles=claves, loc="center", bbox_to_anchor=(0.5, 0.93), ncol=3, frameon=False,
               fontsize=9.5, handlelength=1.1, handleheight=1.1, columnspacing=1.8)

    # Abajo: sillas esperando en cada estación. La cola es entera, por eso escalones.
    colores = ["#4f6d7a", "#a08455", "#6f8f5a", "#7a5c8c", "#5c7a8c", "#8c5c6a"]
    horas_eje = [t / 60 for t in tiempos]
    lineas = []
    for i, nombre in enumerate(nombres):
        es_cuello = i == cuello
        lineas.append(curvas.plot([], [], drawstyle="steps-post", label=nombre,
                                  color=CUELLO if es_cuello else colores[i % len(colores)],
                                  lw=2.4 if es_cuello else 1.5, zorder=3 if es_cuello else 2)[0])
    relleno = [None]
    curvas.set_xlim(0, horas)
    curvas.set_ylim(0, max(max(estados[nb]["cola"]) for nb in nombres) + 1)
    curvas.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    if horas <= 24:
        curvas.xaxis.set_major_locator(MultipleLocator(1 if horas <= 12 else 2))
    curvas.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g} h"))
    curvas.set_title("Sillas esperando en cada estación", loc="left", fontsize=11, weight="semibold",
                     pad=10)
    curvas.tick_params(colors=TEXTO_SUAVE, length=0, labelsize=8.5)
    for lado in ("top", "right", "left"):
        curvas.spines[lado].set_visible(False)
    curvas.spines["bottom"].set_color("#d9d0c3")
    curvas.grid(axis="y", color="#ebe3d7", lw=0.8)
    curvas.set_axisbelow(True)
    curvas.legend(loc="upper left", bbox_to_anchor=(1.02, 1.05), fontsize=9, frameon=False,
                  title="Estación", title_fontsize=9, alignment="left")

    # El texto conserva su tamaño de diseño y se escala con la ventana.
    bases = [(t, t.get_fontsize()) for t in fig.findobj(Text)]

    def ajustar_texto(_evento=None):
        ancho_pulg, alto_pulg = fig.get_size_inches()
        factor = min(ancho_pulg / TAMANO_DISENO[0], alto_pulg / TAMANO_DISENO[1])
        for texto, base in bases:
            texto.set_fontsize(base * factor)
        curvas.tick_params(labelsize=8.5 * factor)

    fig.canvas.mpl_connect("resize_event", ajustar_texto)

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
            esperando[i].set_text(texto + (f" (+{sobra} fuera)" if sobra > 0 else ""))
            lineas[i].set_data(horas_eje[:k + 1], estados[nombre]["cola"][:k + 1])
        if relleno[0] is not None:
            relleno[0].remove()
        relleno[0] = curvas.fill_between(horas_eje[:k + 1], estados[nombres[cuello]]["cola"][:k + 1],
                                         step="post", color=CUELLO, alpha=0.1, lw=0, zorder=1)
        for j, silla in enumerate(deposito):
            mostrar(silla, j < terminadas[k])
        contador.set_text(f"{terminadas[k]} sillas terminadas")
        h, m = divmod(int(tiempos[k]), 60)
        reloj.set_text(f"hora {h:02d}:{m:02d}")
        totales.set_text(f"{en_proceso} sillas en proceso · {terminadas[k]} terminadas")

    return Escena(fig, dibujar, tiempos, carteles, ajustar_texto)


def animar(cfg, horas, paso_min, semilla, guardar=None):
    """Anima el taller cada `paso_min` minutos y abre una ventana o guarda un GIF."""
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    escena = armar(cfg, horas, paso_min, semilla)
    animacion = FuncAnimation(escena.figura, escena.dibujar, frames=len(escena.tiempos),
                              interval=150, repeat=False)
    if guardar:
        guardar.parent.mkdir(parents=True, exist_ok=True)
        animacion.save(guardar, writer=PillowWriter(fps=8))
        plt.close(escena.figura)
    else:
        plt.show()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Anima el taller de sillas.")
    parser.add_argument("--config", type=Path, default=RAIZ / "escenarios" / "base.json",
                        help="escenario JSON (por defecto: escenarios/base.json)")
    parser.add_argument("--horas", type=float, default=8,
                        help="horas simuladas a mostrar (por defecto: 8)")
    parser.add_argument("--paso", type=float, default=5,
                        help="minutos simulados por cuadro (por defecto: 5)")
    parser.add_argument("--semilla", type=int, help="semilla (por defecto: la del escenario)")
    parser.add_argument("--guardar", type=Path, help="guarda un GIF en vez de abrir la ventana")
    args = parser.parse_args(argv)

    if args.horas <= 0 or args.paso <= 0:
        print("Error: --horas y --paso deben ser mayores que 0", file=sys.stderr)
        return 1
    if args.semilla is not None and args.semilla < 0:
        print("Error: --semilla debe ser mayor o igual que 0", file=sys.stderr)
        return 1
    try:
        cfg = cargar_escenario(args.config)
    except FileNotFoundError:
        print(f"Error: no existe el escenario {args.config}", file=sys.stderr)
        return 1
    except (ErrorConfiguracion, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.guardar:
        matplotlib.use("Agg")
    semilla = cfg["semilla"] if args.semilla is None else args.semilla
    animar(cfg, args.horas, args.paso, semilla, args.guardar)
    if args.guardar:
        print(f"Animación guardada: {args.guardar}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
