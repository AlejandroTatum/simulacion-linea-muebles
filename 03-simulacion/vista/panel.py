"""Pantalla única: parámetros, taller animado y resultados en la misma ventana."""

import argparse
import copy
import json
import sys
from pathlib import Path

import matplotlib

from modelo.configuracion import ErrorConfiguracion, cargar_escenario, validar_escenario
from modelo.simulacion import SimulacionLinea, comparar_linea, cuello_de_botella
from modelo.teoria import flujo_teorico_min

RAIZ = Path(__file__).resolve().parents[1]
GUARDADO = RAIZ / "escenarios" / "personalizado.json"

AZUL = "#2f6ea5"
GRIS = "#9b8f85"
ROJO = "#b8322a"
TEXTO = "#2b2622"

# Zona del taller animado (x, y, ancho, alto en fracciones de la ventana).
ZONA_TALLER = (0.25, 0.33, 0.745, 0.67)

# Campos generales del formulario: clave del JSON, etiqueta y si es entero.
CAMPOS_GENERALES = [
    ("replicas", "Réplicas", True),
    ("duracion_h", "Duración de cada réplica (h)", False),
    ("calentamiento_h", "Calentamiento (h)", False),
    ("semilla", "Semilla", True),
]


def _texto(valor):
    """Número sin decimales sobrantes: 8 y no 8.0."""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _numero(texto, etiqueta, entero=False):
    """Convierte el texto de una casilla; acepta coma decimal."""
    limpio = texto.strip().replace(",", ".")
    try:
        if entero:
            return int(limpio)
        valor = float(limpio)
    except ValueError:
        tipo = "un número entero" if entero else "un número"
        raise ErrorConfiguracion(f"{etiqueta}: escribí {tipo}") from None
    return int(valor) if valor.is_integer() else valor


def formulario_desde_escenario(escenario):
    """Textos iniciales de cada casilla a partir de un escenario."""
    valores = {"tasa_llegadas_h": _texto(escenario["tasa_llegadas_h"])}
    for clave, _, _ in CAMPOS_GENERALES:
        valores[clave] = _texto(escenario[clave])
    for i, estacion in enumerate(escenario["estaciones"]):
        valores[f"recursos_{i}"] = _texto(estacion["recursos"])
        valores[f"tiempo_min_{i}"] = _texto(estacion["tiempo_min"])
    return valores


def escenario_desde_formulario(valores, base):
    """Arma y valida un escenario nuevo con los textos del formulario."""
    escenario = copy.deepcopy(base)
    escenario["tasa_llegadas_h"] = _numero(valores["tasa_llegadas_h"], "Llegadas por hora (λ)")
    for clave, etiqueta, entero in CAMPOS_GENERALES:
        escenario[clave] = _numero(valores[clave], etiqueta, entero)
    for i, estacion in enumerate(escenario["estaciones"]):
        nombre = estacion["nombre"]
        estacion["recursos"] = _numero(valores[f"recursos_{i}"], f"Operarios de {nombre}",
                                       entero=True)
        estacion["tiempo_min"] = _numero(valores[f"tiempo_min_{i}"],
                                         f"Tiempo de {nombre} (min)")
    if escenario != base:
        escenario["nombre"] = "Personalizado"
    return validar_escenario(escenario, "panel")


def _formato(valor, decimales=2):
    return "—" if valor != valor else f"{valor:.{decimales}f}"  # NaN != NaN


class Panel:
    """Parámetros a la izquierda; a la derecha, el taller animado arriba y los resultados abajo."""

    def __init__(self, base, ruta_guardado=GUARDADO):
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
        from matplotlib.widgets import Button, TextBox

        self.base = base
        self.ruta_guardado = Path(ruta_guardado)
        self.iniciales = formulario_desde_escenario(base)
        self.iniciales["horas_animacion"] = "8"
        self._animacion = None
        self._pausado = False
        self.escena = None

        self.figura = plt.figure(figsize=(16, 9), facecolor="#faf7f2")
        self.figura.canvas.manager and self.figura.canvas.manager.set_window_title(
            "Simulación de la línea de muebles")
        fig = self.figura
        fig.text(0.02, 0.95, "Parámetros de la línea", fontsize=15, weight="semibold",
                 color=TEXTO)
        fig.text(0.02, 0.925, "Cambiá los valores. Animar muestra el taller;\nSimular corre las "
                 "réplicas.", fontsize=9.5, color=GRIS, va="top")

        self.cajas = {}

        def caja(clave, x, y, ancho=0.06):
            eje = fig.add_axes([x, y, ancho, 0.036])
            self.cajas[clave] = TextBox(eje, "", initial=self.iniciales[clave])

        y = 0.83
        fig.text(0.02, y + 0.012, "Llegadas por hora (λ)", fontsize=11, color=TEXTO)
        caja("tasa_llegadas_h", 0.17, y)

        y -= 0.06
        fig.text(0.02, y, "Estación", fontsize=9.5, weight="semibold", color=TEXTO)
        fig.text(0.10, y, "Operarios", fontsize=9.5, weight="semibold", color=TEXTO)
        fig.text(0.17, y, "t (min)", fontsize=9.5, weight="semibold", color=TEXTO)
        for i, estacion in enumerate(base["estaciones"]):
            y -= 0.05
            fig.text(0.02, y + 0.011, estacion["nombre"], fontsize=10.5, color=TEXTO)
            caja(f"recursos_{i}", 0.10, y, ancho=0.05)
            caja(f"tiempo_min_{i}", 0.17, y)

        y -= 0.025
        for clave, etiqueta, _ in CAMPOS_GENERALES + [("horas_animacion",
                                                        "Horas a animar", False)]:
            y -= 0.047
            fig.text(0.02, y + 0.011, etiqueta, fontsize=10, color=TEXTO)
            caja(clave, 0.17, y)

        self.botones = {}
        for (clave, texto, accion), (x, yb) in zip(
                [("animar", "Animar de nuevo", self.animar), ("pausa", "Pausa", self.pausar),
                 ("simular", "Simular", self.simular), ("guardar", "Guardar", self.guardar),
                 ("restaurar", "Restaurar", self.restaurar)],
                [(0.02, 0.135), (0.125, 0.135), (0.02, 0.08), (0.125, 0.08), (0.02, 0.025)]):
            boton = Button(fig.add_axes([x, yb, 0.10, 0.045]), texto,
                           color="#e8eef5" if clave in ("simular", "animar") else "0.92",
                           hovercolor="#cddbea")
            boton.on_clicked(lambda _evento, accion=accion: accion())
            self.botones[clave] = boton

        # Separador vertical entre el formulario y el resto de la pantalla.
        fig.add_artist(Line2D([0.235, 0.235], [0.02, 0.98], color="#e2d9cc",
                                               lw=1, transform=fig.transFigure))
        self.eje_barras = fig.add_axes([0.285, 0.05, 0.23, 0.18])
        self.eje_tabla = fig.add_axes([0.55, 0.03, 0.44, 0.22])
        self.eje_tabla.axis("off")
        self.estado = fig.text(0.255, 0.322, "", fontsize=9.5, color=TEXTO, va="top")
        self._bases = {}
        self._limpiar_resultados()
        fig.canvas.mpl_connect("resize_event", self._ajustar_taller)
        self.animar()

    # Lectura del formulario -------------------------------------------------

    def valores(self):
        return {clave: caja.text for clave, caja in self.cajas.items()}

    def escenario(self):
        return escenario_desde_formulario(self.valores(), self.base)

    def _avisar(self, texto, error=False):
        self.estado.set_text(texto)
        self.estado.set_color(ROJO if error else TEXTO)
        self.figura.canvas.draw_idle()

    # Acciones de los botones ------------------------------------------------

    def simular(self):
        """Simula con los valores del formulario y dibuja los resultados."""
        try:
            escenario = self.escenario()
        except ErrorConfiguracion as error:
            self._avisar(f"Error: {error}", error=True)
            return None

        self._avisar(f"Simulando {escenario['replicas']} réplicas de "
                     f"{_texto(escenario['duracion_h'])} h…")
        self.figura.canvas.draw()
        self.figura.canvas.flush_events()

        replicas, resumen = SimulacionLinea(escenario).correr_todas()
        linea = comparar_linea(replicas, resumen, escenario)
        cuello = cuello_de_botella(resumen)
        self._dibujar_resultados(escenario, resumen, linea, cuello)
        return resumen, linea

    def animar(self):
        """Anima el taller en esta misma ventana; si ya había uno, lo reemplaza."""
        from matplotlib.animation import FuncAnimation

        from vista.animacion import armar

        try:
            escenario = self.escenario()
            horas = _numero(self.cajas["horas_animacion"].text, "Horas a animar")
            if horas <= 0:
                raise ErrorConfiguracion("Horas a animar: debe ser mayor que 0")
        except ErrorConfiguracion as error:
            self._avisar(f"Error: {error}", error=True)
            return None

        if self._animacion is not None:
            self._animacion.event_source.stop()
        if self.escena is not None:
            self.escena.quitar()
        self.escena = armar(escenario, horas, 5, escenario["semilla"], figura=self.figura,
                            zona=ZONA_TALLER)
        self.escena.dibujar(0)
        # Se guarda la referencia: sin ella Matplotlib detiene la animación.
        self._animacion = FuncAnimation(self.figura, self.escena.dibujar,
                                        frames=len(self.escena.tiempos), interval=150,
                                        repeat=False)
        self._pausado = False
        self.botones["pausa"].label.set_text("Pausa")
        self.figura.canvas.draw_idle()
        return self._animacion

    def pausar(self):
        """Detiene o reanuda la animación; devuelve True si quedó en pausa."""
        if self._animacion is None:
            return None
        if self._pausado:
            self._animacion.resume()
        else:
            self._animacion.pause()
        self._pausado = not self._pausado
        self.botones["pausa"].label.set_text("Seguir" if self._pausado else "Pausa")
        self.figura.canvas.draw_idle()
        return self._pausado

    def _ajustar_taller(self, _evento=None):
        if self.escena is not None:
            self.escena.ajustar_texto()
        self._escalar_textos()

    def _escalar_textos(self):
        """Escala los textos del panel con la ventana (el taller escala los suyos)."""
        from matplotlib.text import Text

        ancho, alto = self.figura.get_size_inches()
        factor = min(ancho / 16, alto / 9)
        del_taller = set()
        if self.escena is not None:
            for artista in self.escena.artistas:
                del_taller.update(artista.findobj(Text))
        for texto in self.figura.findobj(Text):
            if texto not in del_taller:
                base = self._bases.setdefault(texto, texto.get_fontsize())
                texto.set_fontsize(base * factor)

    def guardar(self):
        """Guarda el formulario como JSON para repetirlo con main.py."""
        try:
            escenario = self.escenario()
        except ErrorConfiguracion as error:
            self._avisar(f"Error: {error}", error=True)
            return None

        self.ruta_guardado.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_guardado.write_text(
            json.dumps(escenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            ruta = self.ruta_guardado.relative_to(RAIZ).as_posix()
        except ValueError:
            ruta = str(self.ruta_guardado)
        self._avisar(f"Guardado en {ruta}. Para repetirlo: python main.py --config {ruta}")
        return self.ruta_guardado

    def restaurar(self):
        """Vuelve a los valores del escenario con el que se abrió el panel."""
        for clave, caja in self.cajas.items():
            caja.set_val(self.iniciales[clave])
        self._limpiar_resultados()
        self.animar()
        self._avisar("Valores restaurados.")

    # Dibujo de resultados ---------------------------------------------------

    def _limpiar_resultados(self):
        self.eje_barras.clear()
        self.eje_barras.set_title("Utilización por estación", loc="left", fontsize=11,
                                  color=TEXTO)
        self.eje_barras.text(0.5, 0.5, "Presioná Simular para ver los resultados",
                             ha="center", va="center", color=GRIS,
                             transform=self.eje_barras.transAxes)
        self.eje_barras.set_xticks([])
        self.eje_barras.set_yticks([])
        self.eje_tabla.clear()
        self.eje_tabla.axis("off")
        self._escalar_textos()

    def _dibujar_resultados(self, escenario, resumen, linea, cuello):
        nombres = list(resumen["estacion"])
        x = range(len(nombres))
        ancho = 0.38

        eje = self.eje_barras
        eje.clear()
        colores = [ROJO if nombre == cuello else AZUL for nombre in nombres]
        eje.bar([i - ancho / 2 for i in x], resumen["utilizacion_media"] * 100, ancho,
                color=colores, label="Simulación")
        teoria = resumen["utilizacion_teorica"].fillna(0) * 100
        eje.bar([i + ancho / 2 for i in x], teoria, ancho, color=GRIS, alpha=0.6,
                label="Teoría M/M/1")
        eje.axhline(100, color=ROJO, lw=1, ls="--")
        eje.set_yticks([0, 25, 50, 75, 100])
        eje.set_xticks(list(x), nombres)
        eje.set_ylabel("ρ (%)")
        eje.set_ylim(0, 135)
        eje.set_title(f"Utilización (λ = {_texto(escenario['tasa_llegadas_h'])} muebles/h)",
                      loc="left", fontsize=11, color=TEXTO)
        # La leyenda va dentro del gráfico, por encima de la línea del 100 %.
        eje.legend(loc="upper left", frameon=False, fontsize=8, ncol=2, borderaxespad=0.2)
        eje.grid(axis="y", alpha=0.3)
        for lado in ("top", "right"):
            eje.spines[lado].set_visible(False)

        filas = []
        for _, fila in resumen.iterrows():
            filas.append([
                fila["estacion"], f"{fila['recursos']:.0f}", _texto(fila["tiempo_min"]),
                _formato(fila["utilizacion_media"] * 100, 1),
                _formato(fila["utilizacion_teorica"] * 100, 1),
                _formato(fila["lq_media"]), _formato(fila["lq_teorico"]),
                _formato(fila["wq_min_media"], 1), _formato(fila["wq_min_teorico"], 1),
                _formato(fila["error_wq_pct"]),
            ])
        self.eje_tabla.clear()
        self.eje_tabla.axis("off")
        self.eje_tabla.set_title("Resultados por estación (Wq en minutos; rojo: cuello de "
                                 "botella)", loc="left", fontsize=11, color=TEXTO)
        tabla = self.eje_tabla.table(
            cellText=filas, loc="upper center", cellLoc="center",
            colWidths=[0.14, 0.05, 0.08] + [0.104] * 7,
            colLabels=["Estación", "c", "t (min)", "ρ sim %", "ρ teo %", "Lq sim", "Lq teo",
                       "Wq sim", "Wq teo", "Error Wq %"])
        tabla.auto_set_font_size(False)
        tabla.set_fontsize(8.5)
        tabla.scale(1, 1.35)
        for columna in range(10):
            tabla[0, columna].set_facecolor("#e8eef5")
            fila_cuello = nombres.index(cuello) + 1
            tabla[fila_cuello, columna].set_facecolor("#f6dcd9")

        flujo_teorico = flujo_teorico_min(escenario["tasa_llegadas_h"], escenario["estaciones"])
        flujo = (f"{linea['flujo_min']:.1f} min (teoría {flujo_teorico:.1f} min)"
                 if flujo_teorico is not None else f"{linea['flujo_min']:.1f} min")
        lineas = [f"Cuello de botella: {cuello}   ·   Producción: "
                  f"{linea['throughput_h']:.3f} muebles/h   ·   Tiempo total de flujo: {flujo}",
                  f"Capacidad máxima de la línea: {linea['capacidad_linea_h']:.2f} muebles/h "
                  f"(la limita {linea['cuello_capacidad']})"]
        sin_teoria = list(resumen.loc[resumen["utilizacion_teorica"].isna(), "estacion"])
        if sin_teoria:
            varios = [f"{fila['estacion']} ({fila['recursos']:.0f} operarios)"
                      for _, fila in resumen.iterrows()
                      if fila["estacion"] in sin_teoria and fila["recursos"] > 1]
            inestables = [fila["estacion"] for _, fila in resumen.iterrows()
                          if fila["estacion"] in sin_teoria and fila["recursos"] == 1]
            if varios:
                lineas.append(f"Sin comparación teórica M/M/1: {', '.join(varios)}. "
                              "La simulación corre igual, pero la teoría del informe "
                              "supone un operario por estación.")
            if inestables:
                lineas.append(f"Atención: {', '.join(inestables)} recibe más muebles de los "
                              "que puede atender (λ ≥ c·μ). Su cola crece sin límite y no "
                              "hay valor teórico.")
        self._avisar("\n".join(lineas), error=bool(sin_teoria))
        self._escalar_textos()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Panel para cambiar parámetros y simular.")
    parser.add_argument("--config", type=Path, default=RAIZ / "escenarios" / "base.json",
                        help="escenario con los valores iniciales (por defecto: base.json)")
    args = parser.parse_args(argv)
    try:
        base = cargar_escenario(args.config)
    except FileNotFoundError:
        print(f"Error: no existe el escenario {args.config}", file=sys.stderr)
        return 1
    except (ErrorConfiguracion, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    import matplotlib.pyplot as plt

    from vista.animacion import _usar_fuente
    _usar_fuente()
    panel = Panel(base)  # noqa: F841 - la referencia mantiene vivos los botones
    if matplotlib.get_backend().lower() == "agg":
        print("Error: no hay pantalla disponible para abrir la ventana", file=sys.stderr)
        return 1
    plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
