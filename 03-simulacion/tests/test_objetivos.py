"""Comprueba que los escenarios cubren los objetivos 5.1 y 5.2 del informe."""

import copy
from pathlib import Path

import pytest

from modelo.configuracion import cargar_escenario
from modelo.simulacion import SimulacionLinea, comparar_linea
from modelo.teoria import capacidad_linea

ESCENARIOS = Path(__file__).resolve().parents[1] / "escenarios"
BASE = ESCENARIOS / "base.json"
E2 = ESCENARIOS / "e2.json"
E3 = ESCENARIOS / "e3.json"


def _estaciones(cfg):
    return [(e["nombre"], e["recursos"], e["tiempo_min"]) for e in cfg["estaciones"]]


def _corto(cfg):
    cfg = copy.deepcopy(cfg)
    cfg.update(replicas=2, duracion_h=600, calentamiento_h=60)
    return cfg


def test_la_linea_base_tiene_las_cuatro_estaciones_del_informe():
    cfg = cargar_escenario(BASE)
    assert _estaciones(cfg) == [
        ("Corte", 1, 8),
        ("Lijado", 1, 10),
        ("Ensamblaje", 1, 15),
        ("Acabado", 1, 12),
    ]
    assert cfg["tasa_llegadas_h"] == 3


def test_todos_los_escenarios_usan_un_operario_por_estacion():
    for ruta in (BASE, E2, E3):
        cfg = cargar_escenario(ruta)
        assert all(e["recursos"] == 1 for e in cfg["estaciones"]), ruta.name


def test_e2_solo_cambia_el_tiempo_de_ensamblaje_a_12_min():
    base, e2 = cargar_escenario(BASE), cargar_escenario(E2)
    esperado = _estaciones(base)
    esperado[2] = ("Ensamblaje", 1, 12)
    assert _estaciones(e2) == esperado


def test_e3_solo_cambia_el_tiempo_de_ensamblaje_a_10_min():
    base, e3 = cargar_escenario(BASE), cargar_escenario(E3)
    esperado = _estaciones(base)
    esperado[2] = ("Ensamblaje", 1, 10)
    assert _estaciones(e3) == esperado


def test_los_escenarios_conservan_la_configuracion_de_la_corrida():
    base = cargar_escenario(BASE)
    for ruta in (E2, E3):
        cfg = cargar_escenario(ruta)
        for campo in ("tasa_llegadas_h", "replicas", "duracion_h",
                      "calentamiento_h", "semilla"):
            assert cfg[campo] == base[campo], f"{ruta.name}: cambió {campo}"


def test_las_mejoras_aumentan_la_capacidad_pero_no_la_produccion_actual():
    resultados = {}
    for ruta in (BASE, E2, E3):
        cfg = _corto(cargar_escenario(ruta))
        replicas, resumen = SimulacionLinea(cfg).correr_todas()
        resultados[ruta.stem] = comparar_linea(replicas, resumen, cfg)

    # La capacidad máxima de la línea sube de 4 a 5 muebles/h.
    assert capacidad_linea(cargar_escenario(BASE)["estaciones"]) == pytest.approx(4.0)
    assert resultados["base"]["capacidad_linea_h"] == pytest.approx(4.0)
    assert resultados["e2"]["capacidad_linea_h"] == pytest.approx(5.0)
    assert resultados["e3"]["capacidad_linea_h"] == pytest.approx(5.0)

    # La producción observada sigue limitada por la demanda λ = 3 muebles/h.
    for nombre, linea in resultados.items():
        assert linea["throughput_h"] == pytest.approx(3.0, rel=0.05), nombre
