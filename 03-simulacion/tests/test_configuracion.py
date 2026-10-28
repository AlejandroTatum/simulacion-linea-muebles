import copy
import json
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
