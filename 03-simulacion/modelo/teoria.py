"""Fórmulas M/M/1 y tiempo de flujo teórico de la línea."""


def mm1(tasa_llegadas, tasa_servicio, servidores=1):
    """Indicadores de una estación M/M/1. Tasas por hora; tiempos en minutos.

    El informe usa M/M/1 porque cada estación tiene una sola persona.
    Cualquier otro número de servidores se rechaza con un error explícito.
    """
    if servidores != 1:
        raise ValueError(
            f"La teoría del informe es M/M/1 y no admite {servidores} servidores; "
            "usá servidores=1")

    lam, mu = tasa_llegadas, tasa_servicio
    if lam <= 0 or mu <= 0:
        raise ValueError(
            f"Las tasas deben ser positivas: lambda = {lam:g}, mu = {mu:g}; "
            "no se puede calcular una estación M/M/1")
    rho = lam / mu
    if rho >= 1:
        raise ValueError(f"Estación inestable: rho = {rho:.3f} >= 1")

    lq = rho ** 2 / (1 - rho)
    wq_min = lq / lam * 60
    w_min = wq_min + 60 / mu
    return {
        "utilizacion": rho,
        "lq": lq,
        "wq_min": wq_min,
        "l": lam * w_min / 60,
        "w_min": w_min,
        "prob_espera": rho,  # P(N >= 1): la silla espera al llegar
        "prob_cola": rho ** 2,  # P(N > 1): ya hay otra silla esperando
    }


def flujo_teorico_min(tasa_llegadas, estaciones):
    """Suma el tiempo medio de cada estación; None si no hay teoría M/M/1."""
    total = 0.0
    for estacion in estaciones:
        mu = 60 / estacion["tiempo_min"]
        try:
            total += mm1(tasa_llegadas, mu, estacion["recursos"])["w_min"]
        except ValueError:
            return None
    return total


def capacidad_estacion(estacion):
    """Sillas por hora que puede atender una estación: c * mu."""
    return estacion["recursos"] * 60 / estacion["tiempo_min"]


def capacidad_linea(estaciones):
    """Producción máxima sostenible de la línea: la estación más lenta."""
    return min(capacidad_estacion(estacion) for estacion in estaciones)


def cuello_por_capacidad(estaciones):
    """Estación que limita la producción: la de menor capacidad."""
    return min(estaciones, key=capacidad_estacion)["nombre"]
