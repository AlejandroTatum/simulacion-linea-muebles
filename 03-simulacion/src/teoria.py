"""Theoretical M/M/c reference values (report equations (7)-(14))."""

from math import factorial


def mmc(tasa_llegadas, tasa_servicio, servidores):
    """Steady-state metrics of an M/M/c station.

    Rates are in chairs per hour; times are returned in minutes.
    With servidores=1 the result equals the M/M/1 formulas.
    """
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
    """Theoretical time a chair spends in the whole line, in minutes.

    In a stable series line every station receives the same arrival rate, so
    the total time is the sum of each station's W (queue wait + service).
    Returns None when any station is unstable (its queue grows without bound).
    """
    total = 0.0
    for est in estaciones:
        mu = 60 / est["tiempo_min"]
        try:
            total += mmc(tasa_llegadas, mu, est["recursos"])["w_min"]
        except ValueError:
            return None
    return total
