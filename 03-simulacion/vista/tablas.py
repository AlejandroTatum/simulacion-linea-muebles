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


def texto_inestable(linea):
    """Aviso de línea inestable; None si la línea es estable."""
    if linea["estable"]:
        return None
    return (f"Línea inestable: λ = {linea['throughput_teorico_h']:g} muebles/h ≥ capacidad "
            f"{linea['capacidad_linea_h']:g} muebles/h ({linea['cuello_capacidad']}). La cola "
            "crece sin límite: los tiempos dependen de la duración y no hay valor teórico.")


def mostrar_resumen(escenario, resumen, linea, archivos):
    """Imprime el resumen de un escenario ya simulado."""
    print(f"Escenario: {escenario['nombre']} | {escenario['replicas']} réplicas de "
          f"{escenario['duracion_h']} h ({escenario['calentamiento_h']} h de calentamiento)")

    tabla = resumen[[columna for columna in COLUMNAS if columna in resumen.columns]].copy()
    for columna in tabla.columns:
        if columna != "estacion":
            tabla[columna] = [_numero(valor) for valor in tabla[columna]]
    print(tabla.to_string(index=False))

    print(f"Muebles terminados por réplica: {_numero(linea['muebles_terminados'], 1)} "
          f"(desv. {_numero(linea['muebles_desv'], 1)})")
    print(f"Throughput: {_numero(linea['throughput_h'])} muebles/h "
          f"(teoría {_numero(linea['throughput_teorico_h'])}, "
          f"error {_numero(linea['error_throughput_pct'])} %)")
    holgura = linea["holgura_h"]
    if holgura >= 0:
        holgura_texto = f"holgura frente a λ: {_numero(holgura)} muebles/h"
    else:
        holgura_texto = f"déficit frente a λ: {_numero(abs(holgura))} muebles/h"
    print(f"Capacidad de la línea: {_numero(linea['capacidad_linea_h'])} muebles/h "
          f"(la limita {linea['cuello_capacidad']}; {holgura_texto})")
    print(f"Tiempo total de flujo: {_numero(linea['flujo_min'], 1)} min "
          f"({_flujo_teorico_texto(linea['flujo_teorico_min'])}, "
          f"error {_numero(linea['error_flujo_pct'])} %)")
    print(f"Ley de Little: Lq total {_numero(linea['lq_total'])} = "
          f"λ·Wq {_numero(linea['lq_little_total'])} "
          f"(error {_numero(linea['error_little_total_pct'])} %)")
    aviso = texto_inestable(linea)
    if aviso:
        print(aviso)
    print(f"Cuello de botella: {linea['cuello']}")
    print(f"Archivos: {', '.join(archivos)}")
