"""Motor de simulación de la línea de sillas."""

import numpy as np
import pandas as pd
import simpy

from modelo.teoria import (capacidad_linea, cuello_por_capacidad, flujo_teorico_min,
                           mm1)


class Estacion:
    """Estación con su recurso SimPy y los contadores de la ventana medida."""

    def __init__(self, entorno, nombre, recursos, tiempo_min, inicio, traza=None):
        self.nombre = nombre
        self.recursos = recursos
        self.tiempo_min = tiempo_min
        self.recurso = simpy.Resource(entorno, capacity=recursos)
        self.inicio = inicio
        self.traza = traza

        self.ultimo_cambio = 0.0
        self.en_cola = 0
        self.ocupados = 0
        self.area_cola = 0.0
        self.area_ocupados = 0.0
        self.tiempo_con_cola = 0.0
        self.tiempos_por_cola = {}
        self.esperas = []

    def acumular(self, ahora):
        """Acumula el área y el tiempo del estado actual desde el último cambio."""
        desde = max(self.ultimo_cambio, self.inicio)
        if ahora > desde:
            delta = ahora - desde
            self.area_cola += self.en_cola * delta
            self.area_ocupados += self.ocupados * delta
            if self.en_cola > 0:
                self.tiempo_con_cola += delta
            self.tiempos_por_cola[self.en_cola] = (
                self.tiempos_por_cola.get(self.en_cola, 0.0) + delta)
        self.ultimo_cambio = ahora

    def registrar_cambio(self, ahora, cola=0, ocupados=0):
        """Anota una llegada o salida de la cola y de los operarios."""
        self.acumular(ahora)
        self.en_cola += cola
        self.ocupados += ocupados
        if self.traza is not None:
            self.traza.append((ahora, self.nombre, self.en_cola, self.ocupados))

    def metricas(self, ventana):
        """Promedios de utilización, cola y espera durante la ventana medida."""
        return {
            "estacion": self.nombre,
            "recursos": self.recursos,
            "utilizacion": self.area_ocupados / (self.recursos * ventana),
            "lq": self.area_cola / ventana,
            "wq_min": float(np.mean(self.esperas)) if self.esperas else 0.0,
            "cola_utilizacion": self.tiempo_con_cola / ventana,
            "cola_max": float(max(self.tiempos_por_cola, default=0)),
            "cola_p90": self._percentil(0.90),
        }

    def _percentil(self, cuantil):
        """Percentil de la longitud de cola ponderado por tiempo."""
        total = sum(self.tiempos_por_cola.values())
        if total <= 0:
            return 0.0
        objetivo = cuantil * total
        acumulado = 0.0
        for longitud in sorted(self.tiempos_por_cola):
            acumulado += self.tiempos_por_cola[longitud]
            if acumulado >= objetivo:
                return float(longitud)
        return float(max(self.tiempos_por_cola))


class SimulacionLinea:
    """Una línea en serie con llegadas de Poisson y tiempos exponenciales."""

    def __init__(self, escenario):
        self.escenario = escenario

    def correr_replica(self, semilla, traza=None, salidas=None):
        """Simula una réplica y devuelve sus indicadores."""
        rng = np.random.default_rng(semilla)
        entorno = simpy.Environment()
        inicio = self.escenario["calentamiento_h"] * 60
        fin = self.escenario["duracion_h"] * 60
        ventana = fin - inicio

        estaciones = [
            Estacion(entorno, estacion["nombre"], estacion["recursos"],
                     estacion["tiempo_min"], inicio, traza)
            for estacion in self.escenario["estaciones"]
        ]
        registro = {"terminadas": 0, "flujos": [], "salidas": salidas}

        media_llegadas = 60 / self.escenario["tasa_llegadas_h"]
        entorno.process(self._llegadas(entorno, estaciones, rng, inicio, registro, media_llegadas))
        entorno.run(until=fin)

        filas = []
        for estacion in estaciones:
            estacion.acumular(fin)
            filas.append(estacion.metricas(ventana))

        return {
            "estaciones": filas,
            "terminadas": registro["terminadas"],
            "throughput_h": registro["terminadas"] / (ventana / 60),
            "flujo_min": float(np.mean(registro["flujos"])) if registro["flujos"] else 0.0,
        }

    def _silla(self, entorno, estaciones, rng, inicio, registro):
        """Recorre una silla por todas las estaciones."""
        llegada = entorno.now
        for estacion in estaciones:
            entrada = entorno.now
            estacion.registrar_cambio(entorno.now, cola=1)
            with estacion.recurso.request() as turno:
                yield turno
                estacion.registrar_cambio(entorno.now, cola=-1, ocupados=1)
                if entrada >= inicio:
                    estacion.esperas.append(entorno.now - entrada)
                yield entorno.timeout(rng.exponential(estacion.tiempo_min))
                estacion.registrar_cambio(entorno.now, ocupados=-1)

        if entorno.now >= inicio:
            registro["terminadas"] += 1
            if registro["salidas"] is not None:
                registro["salidas"].append(entorno.now)
        if llegada >= inicio:
            registro["flujos"].append(entorno.now - llegada)

    def _llegadas(self, entorno, estaciones, rng, inicio, registro, media_min):
        """Genera una silla nueva cada tiempo exponencial."""
        while True:
            yield entorno.timeout(rng.exponential(media_min))
            entorno.process(self._silla(entorno, estaciones, rng, inicio, registro))

    def correr_todas(self, traza=None):
        """Corre todas las réplicas. Si se pasa `traza`, guarda solo la primera."""
        semillas = np.random.SeedSequence(self.escenario["semilla"]).generate_state(
            self.escenario["replicas"])
        filas = []

        for numero, semilla in enumerate(semillas, start=1):
            resultado = self.correr_replica(
                int(semilla), traza=traza if numero == 1 else None)
            for estacion in resultado["estaciones"]:
                filas.append({
                    "escenario": self.escenario["nombre"],
                    "replica": numero,
                    "semilla": int(semilla),
                    **estacion,
                    "sillas_terminadas": resultado["terminadas"],
                    "throughput_h": resultado["throughput_h"],
                    "flujo_min": resultado["flujo_min"],
                })

        replicas = pd.DataFrame(filas)
        return replicas, self._resumen(replicas)

    def _resumen(self, replicas):
        """Compara cada estación con su valor teórico M/M/1."""
        lam = self.escenario["tasa_llegadas_h"]
        filas = []

        for estacion in self.escenario["estaciones"]:
            datos = replicas[replicas["estacion"] == estacion["nombre"]]
            mu = 60 / estacion["tiempo_min"]
            fila = {
                "estacion": estacion["nombre"],
                "recursos": estacion["recursos"],
                "tiempo_min": estacion["tiempo_min"],
                "capacidad_h": estacion["recursos"] * mu,
                "utilizacion_media": datos["utilizacion"].mean(),
                "utilizacion_desv": datos["utilizacion"].std(),
                "lq_media": datos["lq"].mean(),
                "lq_desv": datos["lq"].std(),
                "wq_min_media": datos["wq_min"].mean(),
                "wq_min_desv": datos["wq_min"].std(),
                "cola_utilizacion_media": datos["cola_utilizacion"].mean(),
                "cola_utilizacion_desv": datos["cola_utilizacion"].std(),
                "cola_max_media": datos["cola_max"].mean(),
                "cola_p90_media": datos["cola_p90"].mean(),
            }
            try:
                teoria = mm1(lam, mu, estacion["recursos"])
                fila.update({
                    "utilizacion_teorica": teoria["utilizacion"],
                    "lq_teorico": teoria["lq"],
                    "wq_min_teorico": teoria["wq_min"],
                    "cola_utilizacion_teorica": teoria["prob_cola"],
                })
            except ValueError:
                fila.update({"utilizacion_teorica": float("nan"),
                             "lq_teorico": float("nan"),
                             "wq_min_teorico": float("nan"),
                             "cola_utilizacion_teorica": float("nan")})

            fila["error_utilizacion_pct"] = _error_pct(
                fila["utilizacion_media"], fila["utilizacion_teorica"])
            fila["error_lq_pct"] = _error_pct(fila["lq_media"], fila["lq_teorico"])
            fila["error_wq_pct"] = _error_pct(fila["wq_min_media"], fila["wq_min_teorico"])
            # Ley de Little (6): Lq = lambda_efectiva * Wq, con la tasa observada.
            fila["lq_little"] = datos["throughput_h"].mean() * fila["wq_min_media"] / 60
            fila["error_little_pct"] = _error_pct(fila["lq_media"], fila["lq_little"])
            filas.append(fila)

        return pd.DataFrame(filas)


def _error_pct(simulado, teorico):
    if simulado is None or teorico is None:
        return float("nan")
    simulado, teorico = float(simulado), float(teorico)
    if np.isnan(simulado) or np.isnan(teorico) or teorico == 0:
        return float("nan")
    return abs(simulado - teorico) / teorico * 100


def resumir_linea(replicas):
    """Promedios de producción y flujo, sin repetir filas por estación."""
    linea = replicas.drop_duplicates("replica")
    return {
        "sillas_terminadas": float(linea["sillas_terminadas"].mean()),
        "sillas_desv": float(linea["sillas_terminadas"].std()),
        "throughput_h": float(linea["throughput_h"].mean()),
        "flujo_min": float(linea["flujo_min"].mean()),
        "flujo_desv": float(linea["flujo_min"].std()),
    }


def cuello_de_botella(resumen):
    """Estación con mayor utilización simulada."""
    return resumen.loc[resumen["utilizacion_media"].idxmax(), "estacion"]


def comparar_linea(replicas, resumen, escenario):
    """Producción, capacidad, flujo y Ley de Little de la línea frente a M/M/1."""
    linea = resumir_linea(replicas)
    lam = escenario["tasa_llegadas_h"]
    flujo_teorico = flujo_teorico_min(lam, escenario["estaciones"])
    capacidad = capacidad_linea(escenario["estaciones"])
    lq_total = float(resumen["lq_media"].sum())
    little_total = linea["throughput_h"] * float(resumen["wq_min_media"].sum()) / 60
    linea.update({
        "escenario": escenario["nombre"],
        "cuello": cuello_de_botella(resumen),
        "throughput_teorico_h": lam,
        "error_throughput_pct": _error_pct(linea["throughput_h"], lam),
        "capacidad_linea_h": capacidad,
        "cuello_capacidad": cuello_por_capacidad(escenario["estaciones"]),
        "holgura_h": capacidad - lam,
        "flujo_teorico_min": flujo_teorico,
        "error_flujo_pct": _error_pct(linea["flujo_min"], flujo_teorico),
        "lq_total": lq_total,
        "lq_little_total": little_total,
        "error_little_total_pct": _error_pct(lq_total, little_total),
    })
    return linea
