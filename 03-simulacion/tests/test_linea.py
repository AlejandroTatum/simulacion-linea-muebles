import copy
import json
from pathlib import Path

import pytest

from linea import cargar_config, cuello_de_botella, ejecutar, simular_replica

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


@pytest.fixture
def config():
    cfg = cargar_config(BASE)
    cfg["replicas"] = 3
    cfg["duracion_h"] = 2000
    cfg["calentamiento_h"] = 100
    return cfg


def estacion(resultado, nombre):
    return next(e for e in resultado["estaciones"] if e["estacion"] == nombre)


def test_base_config_matches_report_table_v():
    cfg = cargar_config(BASE)
    assert cfg["tasa_llegadas_h"] == 3
    assert [(e["nombre"], e["recursos"], e["tiempo_min"]) for e in cfg["estaciones"]] == [
        ("Corte", 1, 8),
        ("Lijado", 1, 10),
        ("Ensamblaje", 1, 15),
        ("Acabado", 1, 12),
    ]
    assert (cfg["replicas"], cfg["duracion_h"], cfg["calentamiento_h"]) == (30, 1000, 100)


def test_same_seed_gives_identical_replica(config):
    assert simular_replica(config, 7) == simular_replica(config, 7)


def test_different_seeds_give_different_replicas(config):
    assert simular_replica(config, 7) != simular_replica(config, 8)


def test_base_line_approximates_queueing_theory(config):
    r = simular_replica(config, 11)
    ens = estacion(r, "Ensamblaje")
    assert ens["utilizacion"] == pytest.approx(0.75, abs=0.05)
    assert estacion(r, "Corte")["utilizacion"] == pytest.approx(0.40, abs=0.05)
    assert r["throughput_h"] == pytest.approx(3.0, abs=0.2)


def test_littles_law_holds_per_station(config):
    r = simular_replica(config, 13)
    for e in r["estaciones"]:
        lam = r["throughput_h"]
        assert e["lq"] == pytest.approx(lam * e["wq_min"] / 60, rel=0.1)


def test_flow_time_covers_waits_and_service(config):
    r = simular_replica(config, 17)
    servicio = sum(e["tiempo_min"] for e in config["estaciones"])
    esperas = sum(e["wq_min"] for e in r["estaciones"])
    assert r["flujo_min"] == pytest.approx(servicio + esperas, rel=0.1)


def test_extra_assembly_resource_is_configurable_without_code(config):
    cfg = copy.deepcopy(config)
    next(e for e in cfg["estaciones"] if e["nombre"] == "Ensamblaje")["recursos"] = 2
    r = simular_replica(cfg, 11)
    assert estacion(r, "Ensamblaje")["utilizacion"] == pytest.approx(0.375, abs=0.04)


def test_summary_compares_against_theory_and_finds_bottleneck(config):
    replicas, resumen = ejecutar(config)
    assert len(replicas) == 3 * 4
    assert list(resumen["estacion"]) == ["Corte", "Lijado", "Ensamblaje", "Acabado"]
    for col in ["utilizacion_media", "utilizacion_teorica", "error_utilizacion_pct",
                "wq_min_media", "wq_min_teorico", "error_wq_pct", "capacidad_h"]:
        assert col in resumen.columns
    assert cuello_de_botella(resumen) == "Ensamblaje"


def test_config_missing_field_is_rejected(tmp_path):
    cfg = json.loads(BASE.read_text())
    del cfg["tasa_llegadas_h"]
    ruta = tmp_path / "malo.json"
    ruta.write_text(json.dumps(cfg))
    with pytest.raises(ValueError, match="tasa_llegadas_h"):
        cargar_config(ruta)


@pytest.mark.parametrize("archivo, recursos, tiempo", [("e2.json", 2, 15), ("e3.json", 1, 10)])
def test_report_scenarios_change_only_assembly(archivo, recursos, tiempo):
    base = cargar_config(BASE)
    cfg = cargar_config(BASE.parent / archivo)
    ensamblaje = cfg["estaciones"][2]
    assert (ensamblaje["nombre"], ensamblaje["recursos"], ensamblaje["tiempo_min"]) == ("Ensamblaje", recursos, tiempo)
    resto = {k: v for k, v in cfg.items() if k not in ("nombre", "estaciones")}
    assert resto == {k: v for k, v in base.items() if k not in ("nombre", "estaciones")}
    assert [e for i, e in enumerate(cfg["estaciones"]) if i != 2] == \
        [e for i, e in enumerate(base["estaciones"]) if i != 2]
