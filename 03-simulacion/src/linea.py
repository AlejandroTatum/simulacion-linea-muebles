"""Discrete-event simulation of the wooden chair production line.

Chairs arrive as a Poisson process and visit every station in order. Each
station has an unlimited FIFO queue and `recursos` servers with exponential
service times. Internal time unit: minutes.

How it fits together:
  _llegadas         creates a new chair every exponential interarrival time
  _silla            walks one chair through the stations (queue -> service)
  Estacion          SimPy resource plus counters for the indicators
  simular_replica   one run of duracion_h hours; returns its indicators
  ejecutar          all replicas, plus the comparison against M/M/c theory

Warm-up: the line starts empty, which is not its usual state, so everything
before calentamiento_h is simulated but left out of the indicators.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import simpy

from teoria import mmc

CAMPOS = ["nombre", "tasa_llegadas_h", "estaciones", "replicas",
          "duracion_h", "calentamiento_h", "semilla"]
CAMPOS_ESTACION = ["nombre", "recursos", "tiempo_min"]


def cargar_config(ruta):
    """Load and validate a scenario file (see escenarios/base.json)."""
    cfg = json.loads(Path(ruta).read_text(encoding="utf-8"))
    faltantes = [c for c in CAMPOS if c not in cfg]
    if faltantes:
        raise ValueError(f"Faltan campos en {ruta}: {', '.join(faltantes)}")
    if not cfg["estaciones"]:
        raise ValueError(f"{ruta}: la línea necesita al menos una estación")
    for i, est in enumerate(cfg["estaciones"]):
        faltantes = [c for c in CAMPOS_ESTACION if c not in est]
        if faltantes:
            raise ValueError(f"Estación {i + 1} sin: {', '.join(faltantes)}")
        if est["recursos"] < 1 or est["tiempo_min"] <= 0:
            raise ValueError(f"Estación {est['nombre']}: recursos >= 1 y tiempo_min > 0")
    if cfg["tasa_llegadas_h"] <= 0 or cfg["replicas"] < 1:
        raise ValueError("tasa_llegadas_h > 0 y replicas >= 1")
    if not 0 <= cfg["calentamiento_h"] < cfg["duracion_h"]:
        raise ValueError("Se requiere 0 <= calentamiento_h < duracion_h")
    return cfg


class Estacion:
    """A station plus time-weighted counters restricted to the measured window.

    Utilization and Lq are time averages: every time the queue or the number of
    busy servers changes, the previous value is multiplied by how long it lasted
    and added to an area. Area / window length gives the average.
    """

    def __init__(self, env, nombre, recursos, tiempo_min, inicio):
        self.nombre = nombre
        self.recursos = recursos
        self.tiempo_min = tiempo_min
        self.recurso = simpy.Resource(env, capacity=recursos)
        self.inicio = inicio
        self.t = 0.0
        self.en_cola = 0
        self.ocupados = 0
        self.area_cola = 0.0
        self.area_ocupados = 0.0
        self.esperas = []

    def acumular(self, ahora):
        """Add the current state's area since the last change (warm-up excluded)."""
        desde = max(self.t, self.inicio)
        if ahora > desde:
            self.area_cola += self.en_cola * (ahora - desde)
            self.area_ocupados += self.ocupados * (ahora - desde)
        self.t = ahora

    def cambio(self, ahora, cola=0, ocupados=0):
        """Record a change: +1/-1 chairs in queue and/or busy servers."""
        self.acumular(ahora)
        self.en_cola += cola
        self.ocupados += ocupados


def _silla(env, estaciones, rng, inicio, registro):
    """Life of one chair: queue and get processed at each station in order."""
    llegada = env.now
    for est in estaciones:
        entrada = env.now
        est.cambio(env.now, cola=1)  # joins the queue
        with est.recurso.request() as turno:
            yield turno  # waits here until a worker is free (FIFO)
            est.cambio(env.now, cola=-1, ocupados=1)
            if entrada >= inicio:  # only chairs that queued after the warm-up count
                est.esperas.append(env.now - entrada)
            yield env.timeout(rng.exponential(est.tiempo_min))  # being processed
            est.cambio(env.now, ocupados=-1)
    # Throughput counts every chair finished in the measured window; flow time
    # only chairs that also arrived after the warm-up, so it is not biased.
    if env.now >= inicio:
        registro["terminadas"] += 1
    if llegada >= inicio:
        registro["flujos"].append(env.now - llegada)


def _llegadas(env, estaciones, rng, inicio, registro, media_min):
    """Poisson arrivals: exponential gaps with mean 60 / tasa_llegadas_h minutes."""
    while True:
        yield env.timeout(rng.exponential(media_min))
        env.process(_silla(env, estaciones, rng, inicio, registro))


def simular_replica(cfg, semilla):
    """Run one replica and return per-station and line-level indicators."""
    rng = np.random.default_rng(semilla)
    env = simpy.Environment()
    inicio = cfg["calentamiento_h"] * 60
    fin = cfg["duracion_h"] * 60
    ventana = fin - inicio
    estaciones = [Estacion(env, e["nombre"], e["recursos"], e["tiempo_min"], inicio)
                  for e in cfg["estaciones"]]
    registro = {"terminadas": 0, "flujos": []}
    env.process(_llegadas(env, estaciones, rng, inicio, registro,
                          60 / cfg["tasa_llegadas_h"]))
    env.run(until=fin)

    filas = []
    for est in estaciones:
        est.acumular(fin)  # close the last open interval before averaging
        filas.append({
            "estacion": est.nombre,
            "recursos": est.recursos,
            "utilizacion": est.area_ocupados / (est.recursos * ventana),
            "lq": est.area_cola / ventana,
            "wq_min": float(np.mean(est.esperas)) if est.esperas else 0.0,
        })
    return {
        "estaciones": filas,
        "terminadas": registro["terminadas"],
        "throughput_h": registro["terminadas"] / (ventana / 60),
        "flujo_min": float(np.mean(registro["flujos"])) if registro["flujos"] else 0.0,
    }


def _error_pct(simulado, teorico):
    return abs(simulado - teorico) / teorico * 100 if teorico else float("nan")


def ejecutar(cfg):
    """Run every replica; return (per-replica rows, per-station summary)."""
    # One independent, reproducible seed per replica, derived from the base seed.
    semillas = np.random.SeedSequence(cfg["semilla"]).generate_state(cfg["replicas"])
    filas = []
    for i, semilla in enumerate(semillas, start=1):
        r = simular_replica(cfg, int(semilla))
        for est in r["estaciones"]:
            filas.append({
                "escenario": cfg["nombre"],
                "replica": i,
                "semilla": int(semilla),
                **est,
                "sillas_terminadas": r["terminadas"],
                "throughput_h": r["throughput_h"],
                "flujo_min": r["flujo_min"],
            })
    replicas = pd.DataFrame(filas)

    lam = cfg["tasa_llegadas_h"]
    resumen = []
    for e in cfg["estaciones"]:
        datos = replicas[replicas["estacion"] == e["nombre"]]
        mu = 60 / e["tiempo_min"]
        capacidad = e["recursos"] * mu
        fila = {
            "estacion": e["nombre"],
            "recursos": e["recursos"],
            "tiempo_min": e["tiempo_min"],
            "capacidad_h": capacidad,
            "utilizacion_media": datos["utilizacion"].mean(),
            "utilizacion_desv": datos["utilizacion"].std(),
            "lq_media": datos["lq"].mean(),
            "lq_desv": datos["lq"].std(),
            "wq_min_media": datos["wq_min"].mean(),
            "wq_min_desv": datos["wq_min"].std(),
        }
        # Theory assumes every station receives lambda, which holds while the
        # stations before it are stable. An unstable station (rho >= 1) has no
        # steady state, so its theory is left as NaN.
        try:
            teo = mmc(lam, mu, e["recursos"])
            fila.update({
                "utilizacion_teorica": teo["utilizacion"],
                "lq_teorico": teo["lq"],
                "wq_min_teorico": teo["wq_min"],
            })
        except ValueError:
            fila.update({"utilizacion_teorica": float("nan"), "lq_teorico": float("nan"),
                         "wq_min_teorico": float("nan")})
        fila["error_utilizacion_pct"] = _error_pct(fila["utilizacion_media"], fila["utilizacion_teorica"])
        fila["error_lq_pct"] = _error_pct(fila["lq_media"], fila["lq_teorico"])
        fila["error_wq_pct"] = _error_pct(fila["wq_min_media"], fila["wq_min_teorico"])
        resumen.append(fila)
    return replicas, pd.DataFrame(resumen)


def cuello_de_botella(resumen):
    """Station that limits the line: highest simulated utilization."""
    return resumen.loc[resumen["utilizacion_media"].idxmax(), "estacion"]
