"""Fórmulas M/M/c y tiempo de flujo teórico de la línea."""

from math import factorial


def mmc(tasa_llegadas, tasa_servicio, servidores):
    """Indicadores de una estación M/M/c. Tasas por hora; tiempos en minutos."""
    lam, mu, c = tasa_llegadas, tasa_servicio, servidores
    rho = lam / (c * mu)
    if rho >= 1:
        raise ValueError(f"Estación inestable: rho = {rho:.3f} >= 1")

    a = lam / mu
    suma = sum(a**k / factorial(k) for k in range(c))
    p0 = 1 / (suma + a**c / (factorial(c) * (1 - rho)))
    lq = p0 * a**c * rho / (factorial(c) * (1 - rho) ** 2)
    wq = lq / lam
    w = wq + 1 / mu
    return {
        "utilizacion": rho,
        "p0": p0,
        "lq": lq,
        "wq_min": wq * 60,
        "l": lam * w,
        "w_min": w * 60,
    }


def flujo_teorico_min(tasa_llegadas, estaciones):
    """Suma el tiempo medio de cada estación; None si alguna es inestable."""
    total = 0.0
    for estacion in estaciones:
        mu = 60 / estacion["tiempo_min"]
        try:
            total += mmc(tasa_llegadas, mu, estacion["recursos"])["w_min"]
        except ValueError:
            return None
    return total
