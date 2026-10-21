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
