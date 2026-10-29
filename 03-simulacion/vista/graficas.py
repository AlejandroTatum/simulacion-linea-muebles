"""Gráficos de resultados: utilización, cola, variabilidad y escenarios."""

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]

AZUL = "#2f6ea5"
NARANJA = "#e07b39"
VERDE = "#4f7d5a"
ROJO = "#b8322a"
GRIS = "#6d625a"


def _usar_fuente():
    """Registra la fuente Inter incluida; si falta, usa la de Matplotlib."""
    from matplotlib import font_manager
    archivos = sorted((RAIZ / "fuentes").glob("*.ttf"))
    for archivo in archivos:
        font_manager.fontManager.addfont(str(archivo))
    familia = "Inter" if archivos else "DejaVu Sans"
    plt.rcParams.update({"font.family": familia, "axes.unicode_minus": False})


_usar_fuente()


def _guardar(figura, ruta_png):
    """Guarda la figura y libera la memoria."""
    ruta_png = Path(ruta_png)
    ruta_png.parent.mkdir(parents=True, exist_ok=True)
    figura.savefig(ruta_png, dpi=200, bbox_inches="tight")
    plt.close(figura)


def _cuello(resumen):
    """Estación con mayor utilización simulada."""
    return resumen.loc[resumen["utilizacion_media"].idxmax(), "estacion"]


def _colores(resumen, cuello):
    """Azul para las estaciones normales y rojo para el cuello de botella."""
    return [ROJO if nombre == cuello else AZUL for nombre in resumen["estacion"]]


def _numero(valor, decimales=2):
    """Texto corto para una etiqueta, con guion si el valor no existe."""
    return "—" if pd.isna(valor) else f"{valor:.{decimales}f}"


def _estilo_eje(eje):
    """Grilla horizontal suave y sin bordes superiores."""
    eje.grid(axis="y", alpha=0.3)
    for lado in ("top", "right"):
        eje.spines[lado].set_visible(False)


def _serie_cola(traza, nombre, desde, hasta):
    """Longitud de cola de una estación entre dos instantes (devuelve horas)."""
    cambios = sorted((t, cola) for t, estacion, cola, _ in traza if estacion == nombre)
    cola, i = 0, 0

    # Estado vigente al inicio de la ventana.
    while i < len(cambios) and cambios[i][0] <= desde:
        cola = cambios[i][1]
        i += 1

    tiempos, valores = [desde], [cola]
    while i < len(cambios) and cambios[i][0] <= hasta:
        t, nueva = cambios[i]
        if t > tiempos[-1]:
            tiempos.append(t)
            valores.append(nueva)
        else:
            valores[-1] = nueva  # varios eventos en el mismo instante
        i += 1

    if tiempos[-1] < hasta:
        tiempos.append(hasta)
        valores.append(valores[-1])
    return np.array(tiempos) / 60, np.array(valores)


def _distribucion_cola(traza, nombre, desde, hasta):
    """Fracción del tiempo que la cola pasa en cada longitud."""
    tiempos, valores = _serie_cola(traza, nombre, desde, hasta)
    duraciones = {}
    for i in range(len(tiempos) - 1):
        longitud = int(valores[i])
        duraciones[longitud] = duraciones.get(longitud, 0.0) + (tiempos[i + 1] - tiempos[i])
    total = sum(duraciones.values())
    if total <= 0:
        return {0: 1.0}
    return {longitud: duracion / total for longitud, duracion in duraciones.items()}


# ---------- Gráficos por escenario ----------

def graficar(ruta_resumen, ruta_png):
    """Utilización, espera y cola media: simulación frente a teoría."""
    resumen = pd.read_csv(ruta_resumen)
    cuello = _cuello(resumen)
    colores = _colores(resumen, cuello)
    x = np.arange(len(resumen))
    ancho = 0.38
    figura, (eje_utilizacion, eje_espera) = plt.subplots(1, 2, figsize=(11, 4.2))

    eje_utilizacion.bar(x - ancho / 2, resumen["utilizacion_media"] * 100, ancho,
                        yerr=resumen["utilizacion_desv"] * 100, capsize=3,
                        color=colores, label="Simulación")
    eje_utilizacion.bar(x + ancho / 2, resumen["utilizacion_teorica"] * 100, ancho,
                        color=NARANJA, label="Teoría")
    eje_utilizacion.set_ylabel("Utilización ρ (%)")
    eje_utilizacion.set_title("Utilización por estación", fontsize=11, weight="semibold")

    eje_espera.bar(x - ancho / 2, resumen["wq_min_media"], ancho,
                   yerr=resumen["wq_min_desv"], capsize=3, color=colores, label="Simulación")
    eje_espera.bar(x + ancho / 2, resumen["wq_min_teorico"], ancho, color=NARANJA, label="Teoría")
    eje_espera.set_ylabel("Espera en cola Wq (min)")
    eje_espera.set_title("Tiempo medio de espera", fontsize=11, weight="semibold")

    for eje in (eje_utilizacion, eje_espera):
        eje.set_xticks(x, resumen["estacion"])
        eje.legend(frameon=False, fontsize=9)
        _estilo_eje(eje)

    figura.suptitle("Indicadores de la línea", fontsize=13, weight="semibold")
    figura.text(0.5, 0.01, f"El rojo marca el cuello de botella ({cuello}).",
                ha="center", fontsize=8.5, color=GRIS)
    figura.tight_layout(rect=(0, 0.04, 1, 1))
    _guardar(figura, ruta_png)


def graficar_cola(traza, resumen, escenario, ruta_png):
    """Evolución temporal de la cola en la primera réplica."""
    nombres = list(resumen["estacion"])
    cuello = _cuello(resumen)
    inicio_h = float(escenario["calentamiento_h"])
    fin_h = float(escenario["duracion_h"])
    filas = math.ceil(len(nombres) / 2)
    figura, ejes = plt.subplots(filas, 2, figsize=(12, 3.4 * filas), squeeze=False)

    for i, nombre in enumerate(nombres):
        eje = ejes.flat[i]
        tiempos, cola = _serie_cola(traza, nombre, 0.0, fin_h * 60)
        fila = resumen.loc[resumen["estacion"] == nombre].iloc[0]

        eje.step(tiempos, cola, where="post", color=ROJO if nombre == cuello else AZUL,
                 lw=1.1, label="Cola observada")
        if inicio_h > 0:
            eje.axvspan(0, inicio_h, color="#d9d0c3", alpha=0.45, lw=0,
                        label="Calentamiento")
        eje.axhline(fila["lq_media"], color=NARANJA, ls="--", lw=1.2,
                    label=f"Lq medio {_numero(fila['lq_media'])}")
        eje.axhline(fila["lq_teorico"], color=VERDE, ls=":", lw=1.3,
                    label=f"Lq teórico {_numero(fila['lq_teorico'])}")

        eje.set_title(nombre + (" · cuello de botella" if nombre == cuello else ""),
                      loc="left", fontsize=11, weight="semibold",
                      color=ROJO if nombre == cuello else "#2b2622")
        eje.set_xlim(0, fin_h)
        eje.set_ylim(bottom=0)
        eje.set_xlabel("Tiempo (h)")
        eje.set_ylabel("Sillas en cola")
        eje.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        eje.legend(frameon=False, fontsize=7.5, loc="upper right")
        _estilo_eje(eje)

    for eje in ejes.flat[len(nombres):]:
        eje.set_visible(False)

    figura.suptitle(f"Evolución de la cola · {escenario['nombre']} · réplica 1",
                    fontsize=13, weight="semibold")
    figura.tight_layout()
    _guardar(figura, ruta_png)


def graficar_utilizacion_cola(resumen, ruta_png):
    """Porcentaje del tiempo con cola y longitud media de la cola."""
    nombres = list(resumen["estacion"])
    cuello = _cuello(resumen)
    colores = _colores(resumen, cuello)
    x = np.arange(len(nombres))
    ancho = 0.38
    figura, (eje_tiempo, eje_lq) = plt.subplots(1, 2, figsize=(11.5, 4.2))

    eje_tiempo.bar(x - ancho / 2, resumen["cola_utilizacion_media"] * 100, ancho,
                   yerr=resumen["cola_utilizacion_desv"] * 100, capsize=3,
                   color=colores, label="Simulación")
    if "cola_utilizacion_teorica" in resumen:
        eje_tiempo.bar(x + ancho / 2, resumen["cola_utilizacion_teorica"] * 100, ancho,
                       color=NARANJA, label="Teoría M/M/1")
    eje_tiempo.set_ylabel("Tiempo con cola (%)")
    eje_tiempo.set_title("Utilización de la cola", fontsize=11, weight="semibold")
    eje_tiempo.set_ylim(0, 105)

    eje_lq.bar(x - ancho / 2, resumen["lq_media"], ancho, yerr=resumen["lq_desv"],
               capsize=3, color=colores, label="Simulación")
    eje_lq.bar(x + ancho / 2, resumen["lq_teorico"], ancho, color=NARANJA, label="Teoría")
    eje_lq.set_ylabel("Sillas esperando Lq")
    eje_lq.set_title("Longitud media de la cola", fontsize=11, weight="semibold")

    for eje in (eje_tiempo, eje_lq):
        eje.set_xticks(x, nombres)
        eje.legend(frameon=False, fontsize=9)
        _estilo_eje(eje)

    figura.suptitle("Indicadores de cola", fontsize=13, weight="semibold")
    figura.text(0.5, 0.01,
                "Cola utilizada: porcentaje del tiempo con al menos una silla esperando.",
                ha="center", fontsize=8.5, color=GRIS)
    figura.tight_layout(rect=(0, 0.04, 1, 1))
    _guardar(figura, ruta_png)


def graficar_distribucion_cola(traza, resumen, escenario, ruta_png):
    """Distribución de la longitud de la cola durante la ventana medida."""
    nombres = list(resumen["estacion"])
    inicio = float(escenario["calentamiento_h"]) * 60
    fin = float(escenario["duracion_h"]) * 60
    distribuciones = [_distribucion_cola(traza, nombre, inicio, fin) for nombre in nombres]
    maximo = max((max(dist) for dist in distribuciones), default=0)

    if maximo <= 6:
        categorias = list(range(maximo + 1))
    else:
        categorias = list(range(6)) + ["6+"]

    filas = []
    for dist in distribuciones:
        if maximo <= 6:
            filas.append([dist.get(k, 0.0) * 100 for k in range(maximo + 1)])
        else:
            filas.append([dist.get(k, 0.0) * 100 for k in range(6)]
                         + [sum(v for k, v in dist.items() if k >= 6) * 100])

    colores = plt.cm.Blues(np.linspace(0.18, 0.95, len(categorias)))
    y = np.arange(len(nombres))
    figura, eje = plt.subplots(figsize=(10.5, 1.4 + 0.7 * len(nombres)))
    izquierda = np.zeros(len(nombres))

    for j, categoria in enumerate(categorias):
        valores = np.array([fila[j] for fila in filas])
        eje.barh(y, valores, left=izquierda, color=colores[j], height=0.62,
                 edgecolor="white", linewidth=0.8, label=str(categoria))
        for yi, valor, inicio_barra in zip(y, valores, izquierda):
            if valor >= 6:
                eje.text(inicio_barra + valor / 2, yi, f"{valor:.0f}%",
                         ha="center", va="center", fontsize=8,
                         color="white" if j >= len(categorias) // 2 else "#1f2d3d")
        izquierda += valores

    eje.set_yticks(y, nombres)
    eje.invert_yaxis()
    eje.set_xlim(0, 100)
    eje.set_xlabel("Porcentaje del tiempo medido (%)")
    eje.set_title("¿Cuánto tiempo pasa la cola en cada longitud?",
                  loc="left", fontsize=11, weight="semibold")
    eje.legend(title="Sillas esperando", bbox_to_anchor=(1.02, 1), loc="upper left",
               frameon=False, fontsize=8, title_fontsize=8)
    _estilo_eje(eje)
    figura.suptitle(f"Distribución de la cola · {escenario['nombre']} · réplica 1",
                    fontsize=13, weight="semibold")
    figura.text(0.01, 0.01,
                "Se excluye el calentamiento. El color más oscuro indica colas más largas.",
                fontsize=8.5, color=GRIS)
    figura.tight_layout(rect=(0, 0.05, 0.88, 0.95))
    _guardar(figura, ruta_png)


def graficar_replicas(replicas, resumen, ruta_png):
    """Cajas de utilización, Lq y Wq para ver la variabilidad entre réplicas."""
    nombres = list(resumen["estacion"])
    cuello = _cuello(resumen)
    figura, ejes = plt.subplots(1, 3, figsize=(13, 4.2))
    metricas = [
        ("utilizacion", "Utilización ρ", 100.0, "ρ (%)"),
        ("lq", "Longitud de cola Lq", 1.0, "Sillas"),
        ("wq_min", "Espera en cola Wq", 1.0, "Minutos"),
    ]

    for eje, (columna, titulo, factor, etiqueta) in zip(ejes, metricas):
        datos = [replicas.loc[replicas["estacion"] == nombre, columna].dropna() * factor
                 for nombre in nombres]
        cajas = eje.boxplot(datos, tick_labels=nombres, patch_artist=True, widths=0.55,
                            showmeans=True, meanprops={"marker": "D", "markerfacecolor": "white",
                                                       "markeredgecolor": "#2b2622",
                                                       "markersize": 4})
        for caja, nombre in zip(cajas["boxes"], nombres):
            caja.set_facecolor(ROJO if nombre == cuello else AZUL)
            caja.set_alpha(0.75)
        eje.set_title(titulo, fontsize=11, weight="semibold")
        eje.set_ylabel(etiqueta)
        eje.tick_params(axis="x", rotation=15)
        _estilo_eje(eje)

    figura.suptitle("Variabilidad entre réplicas", fontsize=13, weight="semibold")
    figura.text(0.5, 0.01, "Caja: cuartiles; línea: mediana; rombo: media.",
                ha="center", fontsize=8.5, color=GRIS)
    figura.tight_layout(rect=(0, 0.05, 1, 1))
    _guardar(figura, ruta_png)


def graficar_flujo(resumen, escenario, ruta_png):
    """Tiempo de servicio y espera que componen el flujo de una silla."""
    nombres = list(resumen["estacion"])
    cuello = _cuello(resumen)
    x = np.arange(len(nombres))
    servicio = resumen["tiempo_min"].to_numpy(dtype=float)
    espera = resumen["wq_min_media"].to_numpy(dtype=float)
    teorico = servicio + resumen["wq_min_teorico"].to_numpy(dtype=float)
    figura, eje = plt.subplots(figsize=(10, 4.4))

    eje.bar(x, servicio, color=AZUL, width=0.6, label="Servicio (ti)")
    eje.bar(x, espera, bottom=servicio, color=NARANJA, width=0.6,
            edgecolor=[ROJO if nombre == cuello else "none" for nombre in nombres],
            linewidth=1.5, label="Espera media (Wq)")
    for xi, total in zip(x, servicio + espera):
        eje.text(xi, total + 2, f"{total:.1f} min", ha="center", va="bottom", fontsize=9)

    eje.plot(x, teorico, "D", color=VERDE, markersize=7, label="W teórico")
    eje.set_xticks(x, nombres)
    eje.set_ylabel("Minutos por silla")
    eje.set_title(f"Composición del tiempo de flujo · {escenario['nombre']}",
                  loc="left", fontsize=12, weight="semibold")
    eje.legend(frameon=False, fontsize=9)
    _estilo_eje(eje)
    figura.tight_layout()
    _guardar(figura, ruta_png)


def graficar_escenarios(resultados, ruta_png):
    """Compara ensamblaje y acabado entre escenarios: simulación frente a teoría."""
    etiquetas = [resultado["escenario"]["nombre"].split(" - ")[0]
                 for resultado in resultados]
    estaciones = [nombre for nombre in ("Ensamblaje", "Acabado")
                  if all(nombre in set(resultado["resumen"]["estacion"])
                         for resultado in resultados)]
    if not estaciones:
        estaciones = list(resultados[0]["resumen"]["estacion"])

    metricas = [
        ("utilizacion_media", "utilizacion_teorica", 100.0,
         "ρ (%)", "Utilización"),
        ("lq_media", "lq_teorico", 1.0, "Lq (sillas)", "Longitud de la cola"),
        ("wq_min_media", "wq_min_teorico", 1.0, "Wq (min)", "Tiempo de espera"),
    ]
    colores = [AZUL, VERDE, NARANJA, ROJO, "#7a5c8c", "#5c7a8c"]
    figura, ejes = plt.subplots(1, 4, figsize=(17.5, 4.6))
    x = np.arange(len(estaciones))
    ancho = 0.8 / max(len(resultados), 1)

    for eje, (columna_sim, columna_teo, factor, etiqueta, titulo) in zip(ejes[:3],
                                                                        metricas):
        for i, resultado in enumerate(resultados):
            datos = (resultado["resumen"].set_index("estacion")
                     .reindex(estaciones))
            posicion = x + (i - (len(resultados) - 1) / 2) * ancho
            eje.bar(posicion, datos[columna_sim] * factor, ancho * 0.92,
                    color=colores[i % len(colores)], label=etiquetas[i])
            eje.plot(posicion, datos[columna_teo] * factor, "D", color="#2b2622",
                     markersize=4.5, linestyle="none", zorder=3,
                     label="Teoría M/M/1" if i == 0 else None)

        eje.set_xticks(x, estaciones)
        eje.set_title(titulo, fontsize=11, weight="semibold")
        eje.set_ylabel(etiqueta)
        _estilo_eje(eje)

    # Cuarto panel: capacidad máxima de la línea frente a la producción observada.
    eje_capacidad = ejes[3]
    posiciones = np.arange(len(resultados))
    capacidades = [resultado["linea"]["capacidad_linea_h"] for resultado in resultados]
    producciones = [resultado["linea"]["throughput_h"] for resultado in resultados]
    eje_capacidad.bar(posiciones - 0.2, capacidades, 0.38, color=GRIS,
                      label="Capacidad (cuello)")
    eje_capacidad.bar(posiciones + 0.2, producciones, 0.38, color=AZUL,
                      label="Producción simulada")
    for posicion, capacidad, produccion in zip(posiciones, capacidades, producciones):
        eje_capacidad.text(posicion - 0.2, capacidad, f"{capacidad:.2f}", ha="center",
                           va="bottom", fontsize=8, color="#2b2622")
        eje_capacidad.text(posicion + 0.2, produccion, f"{produccion:.2f}", ha="center",
                           va="bottom", fontsize=8, color="#2b2622")
    eje_capacidad.set_xticks(posiciones, etiquetas)
    eje_capacidad.set_title("Producción por hora", fontsize=11, weight="semibold")
    eje_capacidad.set_ylabel("sillas/h")
    eje_capacidad.legend(loc="upper left", frameon=False, fontsize=8.5)
    _estilo_eje(eje_capacidad)

    ejes[0].legend(frameon=False, fontsize=8.5)
    figura.suptitle("Escenarios: estaciones críticas y capacidad de la línea",
                    fontsize=13, weight="semibold")
    cuellos = [resultado["cuello"] for resultado in resultados]
    nota = "Cuello de botella: " + ", ".join(
        f"{etiqueta} = {cuello}" for etiqueta, cuello in zip(etiquetas, cuellos))
    nota += "   ·   Capacidad: " + ", ".join(
        f"{etiqueta} = {capacidad:.2f}" for etiqueta, capacidad
        in zip(etiquetas, capacidades)) + " sillas/h"
    figura.text(0.5, 0.01, nota, ha="center", fontsize=8.5, color=GRIS)
    figura.tight_layout(rect=(0, 0.05, 1, 1))
    _guardar(figura, ruta_png)


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
