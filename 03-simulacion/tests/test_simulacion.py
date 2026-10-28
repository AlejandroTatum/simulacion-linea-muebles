import copy
import json
from pathlib import Path

import pytest

from modelo.configuracion import ErrorConfiguracion, cargar_escenario
from modelo.simulacion import SimulacionLinea, cuello_de_botella

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


@pytest.fixture
def config():
    cfg = cargar_escenario(BASE)
    cfg["replicas"] = 3
    cfg["duracion_h"] = 2000
    cfg["calentamiento_h"] = 100
    return cfg


def estacion(resultado, nombre):
    return next(e for e in resultado["estaciones"] if e["estacion"] == nombre)


def test_configuracion_base_coincide_con_tabla_v():
    cfg = cargar_escenario(BASE)
    assert cfg["tasa_llegadas_h"] == 3
    assert [(e["nombre"], e["recursos"], e["tiempo_min"]) for e in cfg["estaciones"]] == [
        ("Corte", 1, 8),
        ("Lijado", 1, 10),
        ("Ensamblaje", 1, 15),
        ("Acabado", 1, 12),
    ]
    assert (cfg["replicas"], cfg["duracion_h"], cfg["calentamiento_h"]) == (30, 1000, 100)


def test_misma_semilla_repite_la_replica(config):
    assert (SimulacionLinea(config).correr_replica(7)
            == SimulacionLinea(config).correr_replica(7))


def test_semillas_distintas_cambian_la_replica(config):
    assert (SimulacionLinea(config).correr_replica(7)
            != SimulacionLinea(config).correr_replica(8))


def test_linea_base_se_acerca_a_la_teoria(config):
    resultado = SimulacionLinea(config).correr_replica(11)
    ensamblaje = estacion(resultado, "Ensamblaje")
    assert ensamblaje["utilizacion"] == pytest.approx(0.75, abs=0.05)
    assert estacion(resultado, "Corte")["utilizacion"] == pytest.approx(0.40, abs=0.05)
    assert resultado["throughput_h"] == pytest.approx(3.0, abs=0.2)


def test_ley_de_little_por_estacion(config):
    resultado = SimulacionLinea(config).correr_replica(13)
    for estacion_actual in resultado["estaciones"]:
        lam = resultado["throughput_h"]
        assert estacion_actual["lq"] == pytest.approx(
            lam * estacion_actual["wq_min"] / 60, rel=0.1)


def test_tiempo_de_flujo_suma_esperas_y_servicio(config):
    resultado = SimulacionLinea(config).correr_replica(17)
    servicio = sum(e["tiempo_min"] for e in config["estaciones"])
    esperas = sum(e["wq_min"] for e in resultado["estaciones"])
    assert resultado["flujo_min"] == pytest.approx(servicio + esperas, rel=0.1)


def test_segundo_ensamblador_se_configura_sin_tocar_codigo(config):
    cfg = copy.deepcopy(config)
    next(e for e in cfg["estaciones"] if e["nombre"] == "Ensamblaje")["recursos"] = 2
    resultado = SimulacionLinea(cfg).correr_replica(11)
    assert estacion(resultado, "Ensamblaje")["utilizacion"] == pytest.approx(0.375, abs=0.04)


def test_resumen_compara_con_teoria_y_encuentra_cuello(config):
    replicas, resumen = SimulacionLinea(config).correr_todas()
    assert len(replicas) == 3 * 4
    assert list(resumen["estacion"]) == ["Corte", "Lijado", "Ensamblaje", "Acabado"]
    for columna in ["utilizacion_media", "utilizacion_teorica", "error_utilizacion_pct",
                    "wq_min_media", "wq_min_teorico", "error_wq_pct", "capacidad_h"]:
        assert columna in resumen.columns
    assert cuello_de_botella(resumen) == "Ensamblaje"


def test_falta_un_campo_y_se_rechaza(tmp_path):
    cfg = json.loads(BASE.read_text())
    del cfg["tasa_llegadas_h"]
    ruta = tmp_path / "malo.json"
    ruta.write_text(json.dumps(cfg))
    with pytest.raises(ErrorConfiguracion, match="tasa_llegadas_h"):
        cargar_escenario(ruta)


@pytest.mark.parametrize("archivo, recursos, tiempo", [("e2.json", 2, 15), ("e3.json", 1, 10)])
def test_escenarios_del_informe_solo_cambian_ensamblaje(archivo, recursos, tiempo):
    base = cargar_escenario(BASE)
    cfg = cargar_escenario(BASE.parent / archivo)
    ensamblaje = cfg["estaciones"][2]
    assert (ensamblaje["nombre"], ensamblaje["recursos"], ensamblaje["tiempo_min"]) == (
        "Ensamblaje", recursos, tiempo)
    resto = {k: v for k, v in cfg.items() if k not in ("nombre", "estaciones")}
    assert resto == {k: v for k, v in base.items() if k not in ("nombre", "estaciones")}
    assert [e for i, e in enumerate(cfg["estaciones"]) if i != 2] == \
        [e for i, e in enumerate(base["estaciones"]) if i != 2]
