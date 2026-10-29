"""Regresión: E1 debe seguir dando los mismos números que antes de pasar a M/M/1."""

from pathlib import Path

import pandas as pd

from modelo.configuracion import cargar_escenario
from modelo.simulacion import SimulacionLinea

RAIZ = Path(__file__).resolve().parents[1]
BASE = RAIZ / "escenarios" / "base.json"
REFERENCIA = Path(__file__).resolve().parent / "referencia-e1.csv"


def test_e1_reproduce_el_resumen_anterior():
    """referencia-e1.csv es la copia de resumen-base.csv previa al ajuste."""
    _, resumen = SimulacionLinea(cargar_escenario(BASE)).correr_todas()
    referencia = pd.read_csv(REFERENCIA)
    columnas = [columna for columna in referencia.columns if columna in resumen.columns]

    pd.testing.assert_frame_equal(
        resumen[columnas].round(6).reset_index(drop=True),
        referencia[columnas].reset_index(drop=True))


def test_dos_corridas_con_la_misma_semilla_son_identicas():
    cfg = cargar_escenario(BASE)
    cfg.update(replicas=2, duracion_h=300, calentamiento_h=30)

    primera, resumen_primero = SimulacionLinea(cfg).correr_todas()
    segunda, resumen_segundo = SimulacionLinea(cfg).correr_todas()

    pd.testing.assert_frame_equal(primera, segunda)
    pd.testing.assert_frame_equal(resumen_primero, resumen_segundo)
