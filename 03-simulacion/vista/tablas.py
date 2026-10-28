"""Tablas y mensajes de resultado en la terminal."""

import math

COLUMNAS = ["estacion", "capacidad_h", "utilizacion_media", "utilizacion_teorica",
            "error_utilizacion_pct", "lq_media", "lq_teorico", "wq_min_media",
            "wq_min_teorico", "error_wq_pct"]


def _numero(valor, decimales=3):
    if valor is None:
        return "—"
    try:
        if math.isnan(float(valor)):
            return "—"
    except (TypeError, ValueError):
        return str(valor)
    return f"{valor:.{decimales}f}"


def mostrar_resumen(escenario, resumen, linea, cuello, flujo_teorico, archivos):
    """Imprime el resumen de un escenario ya simulado."""
    print(f"Escenario: {escenario['nombre']} | {escenario['replicas']} réplicas de "
          f"{escenario['duracion_h']} h ({escenario['calentamiento_h']} h de calentamiento)")

    tabla = resumen[COLUMNAS].copy()
    for columna in COLUMNAS:
        if columna != "estacion":
            tabla[columna] = [_numero(valor) for valor in tabla[columna]]
    print(tabla.to_string(index=False))

    print(f"Sillas terminadas por réplica: {_numero(linea['sillas_terminadas'], 1)} "
          f"(desv. {_numero(linea['sillas_desv'], 1)})")
    teoria = ("sin régimen estable" if flujo_teorico is None
              else f"teoría {flujo_teorico:.1f} min")
    print(f"Throughput: {_numero(linea['throughput_h'])} sillas/h | "
          f"tiempo total de flujo: {_numero(linea['flujo_min'], 1)} min ({teoria})")
    print(f"Cuello de botella: {cuello}")
    print(f"Archivos: {archivos[0]}, {archivos[1]}, {archivos[2]}")
