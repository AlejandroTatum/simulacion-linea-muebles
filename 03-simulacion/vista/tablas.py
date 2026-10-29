"""Tablas y mensajes de resultado en la terminal."""

import math

COLUMNAS = ["estacion", "capacidad_h", "utilizacion_media", "utilizacion_teorica",
            "error_utilizacion_pct", "lq_media", "lq_teorico", "error_lq_pct",
            "wq_min_media", "wq_min_teorico", "error_wq_pct", "error_little_pct"]


def _numero(valor, decimales=3):
    if valor is None:
        return "—"
    try:
        if math.isnan(float(valor)):
            return "—"
    except (TypeError, ValueError):
        return str(valor)
    return f"{valor:.{decimales}f}"


def _flujo_teorico_texto(valor):
    if valor is None or math.isnan(float(valor)):
        return "sin teoría M/M/1"
    return f"teoría {valor:.1f} min"


def mostrar_resumen(escenario, resumen, linea, archivos):
    """Imprime el resumen de un escenario ya simulado."""
    print(f"Escenario: {escenario['nombre']} | {escenario['replicas']} réplicas de "
          f"{escenario['duracion_h']} h ({escenario['calentamiento_h']} h de calentamiento)")

    tabla = resumen[[columna for columna in COLUMNAS if columna in resumen.columns]].copy()
    for columna in tabla.columns:
        if columna != "estacion":
            tabla[columna] = [_numero(valor) for valor in tabla[columna]]
    print(tabla.to_string(index=False))

    print(f"Sillas terminadas por réplica: {_numero(linea['sillas_terminadas'], 1)} "
          f"(desv. {_numero(linea['sillas_desv'], 1)})")
    print(f"Throughput: {_numero(linea['throughput_h'])} sillas/h "
          f"(teoría {_numero(linea['throughput_teorico_h'])}, "
          f"error {_numero(linea['error_throughput_pct'])} %)")
    print(f"Tiempo total de flujo: {_numero(linea['flujo_min'], 1)} min "
          f"({_flujo_teorico_texto(linea['flujo_teorico_min'])}, "
          f"error {_numero(linea['error_flujo_pct'])} %)")
    print(f"Ley de Little: Lq total {_numero(linea['lq_total'])} = "
          f"λ·Wq {_numero(linea['lq_little_total'])} "
          f"(error {_numero(linea['error_little_total_pct'])} %)")
    print(f"Cuello de botella: {linea['cuello']}")
    print(f"Archivos: {', '.join(archivos)}")
