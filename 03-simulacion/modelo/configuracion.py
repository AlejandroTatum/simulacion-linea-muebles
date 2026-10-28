"""Carga y validación de los escenarios JSON.

Los valores de la línea (λ, operarios y tiempos de cada estación, réplicas, duración,
calentamiento y semilla) no se cambian aquí: están en escenarios/*.json o se escriben en
la ventana de python panel.py. Este módulo solo los lee y revisa que sean válidos.
"""

import json
import math
from numbers import Real
from pathlib import Path

CAMPOS_ESCENARIO = ("nombre", "tasa_llegadas_h", "estaciones", "replicas",
                    "duracion_h", "calentamiento_h", "semilla")
CAMPOS_ESTACION = ("nombre", "recursos", "tiempo_min")


class ErrorConfiguracion(ValueError):
    """El escenario no tiene el formato esperado."""


def _es_numero(valor):
    """Finite real number; JSON accepts NaN and Infinity, which no parameter can take."""
    return isinstance(valor, Real) and not isinstance(valor, bool) and math.isfinite(valor)


def _es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


def _revisar_campos(datos, esperados, origen):
    if not isinstance(datos, dict):
        raise ErrorConfiguracion(f"{origen}: se esperaba un objeto JSON")

    faltantes = [campo for campo in esperados if campo not in datos]
    if faltantes:
        raise ErrorConfiguracion(f"Faltan campos en {origen}: {', '.join(faltantes)}")

    sobrantes = sorted(set(datos) - set(esperados))
    if sobrantes:
        raise ErrorConfiguracion(f"Campos desconocidos en {origen}: {', '.join(sobrantes)}")


def validar_escenario(datos, origen="escenario"):
    """Revisa tipos, rangos y nombres antes de simular."""
    _revisar_campos(datos, CAMPOS_ESCENARIO, origen)

    if not isinstance(datos["nombre"], str) or not datos["nombre"].strip():
        raise ErrorConfiguracion(f"{origen}: el nombre no puede estar vacío")

    if not _es_numero(datos["tasa_llegadas_h"]) or datos["tasa_llegadas_h"] <= 0:
        raise ErrorConfiguracion(f"{origen}: tasa_llegadas_h debe ser un número mayor que 0")

    if not _es_entero(datos["replicas"]) or datos["replicas"] < 1:
        raise ErrorConfiguracion(f"{origen}: replicas debe ser un entero mayor o igual que 1")

    if not _es_numero(datos["duracion_h"]) or datos["duracion_h"] <= 0:
        raise ErrorConfiguracion(f"{origen}: duracion_h debe ser un número mayor que 0")

    if not _es_numero(datos["calentamiento_h"]) or datos["calentamiento_h"] < 0:
        raise ErrorConfiguracion(f"{origen}: calentamiento_h debe ser un número mayor o igual que 0")

    if datos["calentamiento_h"] >= datos["duracion_h"]:
        raise ErrorConfiguracion(f"{origen}: calentamiento_h debe ser menor que duracion_h")

    if not _es_entero(datos["semilla"]) or datos["semilla"] < 0:
        raise ErrorConfiguracion(f"{origen}: semilla debe ser un entero mayor o igual que 0")

    estaciones = datos["estaciones"]
    if not isinstance(estaciones, list) or not estaciones:
        raise ErrorConfiguracion(f"{origen}: la línea necesita al menos una estación")

    nombres = set()
    for numero, estacion in enumerate(estaciones, start=1):
        lugar = f"{origen}, estación {numero}"
        _revisar_campos(estacion, CAMPOS_ESTACION, lugar)

        nombre = estacion["nombre"]
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorConfiguracion(f"{lugar}: el nombre no puede estar vacío")
        if nombre in nombres:
            raise ErrorConfiguracion(f"{origen}: estación duplicada '{nombre}'")
        nombres.add(nombre)

        if not _es_entero(estacion["recursos"]) or estacion["recursos"] < 1:
            raise ErrorConfiguracion(f"{lugar}: recursos debe ser un entero mayor o igual que 1")

        if not _es_numero(estacion["tiempo_min"]) or estacion["tiempo_min"] <= 0:
            raise ErrorConfiguracion(f"{lugar}: tiempo_min debe ser un número mayor que 0")

    return datos


def cargar_escenario(ruta):
    """Lee un archivo JSON y devuelve el escenario ya validado."""
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise
    except UnicodeDecodeError as error:
        raise ErrorConfiguracion(f"{ruta}: el archivo no está en UTF-8") from error
    except OSError as error:
        raise ErrorConfiguracion(f"{ruta}: no se pudo leer ({error})") from error

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorConfiguracion(f"{ruta}: JSON inválido en la línea {error.lineno}") from error

    return validar_escenario(datos, str(ruta))
