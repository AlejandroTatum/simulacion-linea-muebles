import copy
import json
import re
from pathlib import Path

import pytest

from modelo.configuracion import ErrorConfiguracion, cargar_escenario

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


def _guardar(tmp_path, datos, nombre="escenario.json"):
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos), encoding="utf-8")
    return ruta


def _base():
    return copy.deepcopy(json.loads(BASE.read_text()))


def test_un_escenario_valido_se_carga(tmp_path):
    cfg = cargar_escenario(_guardar(tmp_path, _base()))
    assert cfg["nombre"] == "E1 - Base"


def test_un_campo_desconocido_se_rechaza(tmp_path):
    cfg = _base()
    cfg["tasa_llegada"] = 3
    with pytest.raises(ErrorConfiguracion, match="desconocidos"):
        cargar_escenario(_guardar(tmp_path, cfg))


@pytest.mark.parametrize("campo, valor", [
    ("replicas", 2.5),
    ("duracion_h", "1000"),
    ("semilla", -1),
    ("nombre", "   "),
])
def test_valores_invalidos_del_escenario_se_rechazan(tmp_path, campo, valor):
    cfg = _base()
    cfg[campo] = valor
    with pytest.raises(ErrorConfiguracion):
        cargar_escenario(_guardar(tmp_path, cfg))


@pytest.mark.parametrize("campo, valor", [
    ("recursos", "1"),
    ("recursos", 0),
    ("tiempo_min", "8"),
    ("nombre", ""),
])
def test_valores_invalidos_de_una_estacion_se_rechazan(tmp_path, campo, valor):
    cfg = _base()
    cfg["estaciones"][0][campo] = valor
    with pytest.raises(ErrorConfiguracion):
        cargar_escenario(_guardar(tmp_path, cfg))


def test_dos_estaciones_con_el_mismo_nombre_se_rechazan(tmp_path):
    cfg = _base()
    cfg["estaciones"][1]["nombre"] = cfg["estaciones"][0]["nombre"]
    with pytest.raises(ErrorConfiguracion, match="duplicada"):
        cargar_escenario(_guardar(tmp_path, cfg))


def test_las_estaciones_deben_ser_una_lista(tmp_path):
    cfg = _base()
    cfg["estaciones"] = {"nombre": "Corte"}
    with pytest.raises(ErrorConfiguracion, match="al menos una estación"):
        cargar_escenario(_guardar(tmp_path, cfg))


def test_el_calentamiento_debe_ser_menor_que_la_duracion(tmp_path):
    cfg = _base()
    cfg["calentamiento_h"] = cfg["duracion_h"]
    with pytest.raises(ErrorConfiguracion, match="calentamiento_h"):
        cargar_escenario(_guardar(tmp_path, cfg))


def test_un_json_invalido_se_rechaza(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{", encoding="utf-8")
    with pytest.raises(ErrorConfiguracion, match="JSON inválido"):
        cargar_escenario(ruta)


@pytest.mark.parametrize("campo", ["tasa_llegadas_h", "duracion_h", "calentamiento_h"])
@pytest.mark.parametrize("valor", [float("nan"), float("inf")])
def test_nan_e_infinito_del_escenario_se_rechazan(tmp_path, campo, valor):
    cfg = _base()
    cfg[campo] = valor
    with pytest.raises(ErrorConfiguracion, match=campo):
        cargar_escenario(_guardar(tmp_path, cfg))


@pytest.mark.parametrize("valor", [float("nan"), float("inf")])
def test_nan_e_infinito_de_una_estacion_se_rechazan(tmp_path, valor):
    cfg = _base()
    cfg["estaciones"][0]["tiempo_min"] = valor
    with pytest.raises(ErrorConfiguracion, match="tiempo_min"):
        cargar_escenario(_guardar(tmp_path, cfg))


@pytest.mark.parametrize("archivo", ["base.json", "e2.json", "e3.json"])
def test_los_escenarios_del_informe_quedan_dentro_de_los_limites(archivo):
    cargar_escenario(BASE.parent / archivo)


@pytest.mark.parametrize("cambios, mensaje", [
    ({"replicas": 201},
     "replicas debe ser como máximo 200 (se pidió 201)"),
    ({"tasa_llegadas_h": 1000, "replicas": 1},
     "tasa_llegadas_h × duracion_h da 1000000 muebles por réplica; el máximo es 200000. "
     "Bajá λ o la duración"),
    ({"tasa_llegadas_h": 100, "replicas": 30},
     "tasa_llegadas_h × duracion_h × replicas da 3000000 muebles en total; el máximo es "
     "1000000. Bajá λ, la duración o las réplicas"),
])
def test_un_escenario_exagerado_se_rechaza_antes_de_simular(tmp_path, cambios, mensaje):
    cfg = _base()
    cfg.update(cambios)
    with pytest.raises(ErrorConfiguracion, match=re.escape(f"{tmp_path / 'escenario.json'}: "
                                                            f"{mensaje}")):
        cargar_escenario(_guardar(tmp_path, cfg))


def test_los_limites_admiten_el_valor_exacto(tmp_path):
    cfg = _base()
    cfg.update(tasa_llegadas_h=200, duracion_h=1000, calentamiento_h=100, replicas=5)
    assert cargar_escenario(_guardar(tmp_path, cfg))["replicas"] == 5
    cfg.update(tasa_llegadas_h=3, replicas=200)
    assert cargar_escenario(_guardar(tmp_path, cfg))["replicas"] == 200
