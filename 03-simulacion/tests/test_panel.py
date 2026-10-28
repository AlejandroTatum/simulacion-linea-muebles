import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

from modelo.configuracion import ErrorConfiguracion, cargar_escenario  # noqa: E402
from vista.panel import Panel, escenario_desde_formulario, formulario_desde_escenario  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


@pytest.fixture
def base():
    return cargar_escenario(BASE)


def test_el_formulario_arranca_con_los_valores_del_escenario(base):
    valores = formulario_desde_escenario(base)
    assert valores["tasa_llegadas_h"] == "3"
    assert valores["replicas"] == "30"
    assert [valores[f"recursos_{i}"] for i in range(4)] == ["1", "1", "1", "1"]
    assert [valores[f"tiempo_min_{i}"] for i in range(4)] == ["8", "10", "15", "12"]


def test_sin_cambios_el_formulario_devuelve_el_mismo_escenario(base):
    escenario = escenario_desde_formulario(formulario_desde_escenario(base), base)
    assert escenario["estaciones"] == base["estaciones"]
    for campo in ("tasa_llegadas_h", "replicas", "duracion_h", "calentamiento_h", "semilla"):
        assert escenario[campo] == base[campo]


def test_los_valores_cambiados_llegan_al_escenario(base):
    valores = formulario_desde_escenario(base)
    valores.update({"tasa_llegadas_h": "4,5", "recursos_2": "2", "tiempo_min_3": "9.5"})
    escenario = escenario_desde_formulario(valores, base)
    assert escenario["tasa_llegadas_h"] == 4.5
    assert escenario["estaciones"][2]["recursos"] == 2
    assert escenario["estaciones"][3]["tiempo_min"] == 9.5
    assert base["tasa_llegadas_h"] == 3, "el escenario original no se modifica"


@pytest.mark.parametrize("campo, texto, mensaje", [
    ("tasa_llegadas_h", "abc", "Llegadas por hora (λ): escribí un número"),
    ("recursos_1", "1.5", "Operarios de Lijado: escribí un número entero"),
    ("tiempo_min_1", "-3", "estación 2: tiempo_min debe ser un número mayor que 0"),
    ("recursos_0", "0", "estación 1: recursos debe ser un entero mayor o igual que 1"),
    ("calentamiento_h", "2000", "calentamiento_h debe ser menor que duracion_h"),
])
def test_un_valor_invalido_se_rechaza_con_un_mensaje_claro(base, campo, texto, mensaje):
    valores = formulario_desde_escenario(base)
    valores[campo] = texto
    with pytest.raises(ErrorConfiguracion, match=re.escape(mensaje)):
        escenario_desde_formulario(valores, base)


def test_simular_desde_el_panel_muestra_resultados(base):
    panel = Panel(base)
    panel.cajas["replicas"].set_val("2")
    panel.cajas["duracion_h"].set_val("200")
    panel.cajas["calentamiento_h"].set_val("20")
    panel.cajas["recursos_2"].set_val("2")
    resultado = panel.simular()
    assert resultado is not None
    resumen, linea = resultado
    assert resumen.loc[resumen["estacion"] == "Ensamblaje", "recursos"].item() == 2
    assert linea["throughput_h"] > 0
    assert "Cuello de botella: Acabado" in panel.estado.get_text()


def test_simular_con_un_error_no_rompe_el_panel(base):
    panel = Panel(base)
    panel.cajas["tiempo_min_0"].set_val("cero")
    assert panel.simular() is None
    assert "Tiempo de Corte" in panel.estado.get_text()


def test_guardar_escribe_un_json_que_main_puede_usar(base, tmp_path):
    destino = tmp_path / "personalizado.json"
    panel = Panel(base, ruta_guardado=destino)
    panel.cajas["tasa_llegadas_h"].set_val("4")
    panel.guardar()
    guardado = cargar_escenario(destino)
    assert guardado["tasa_llegadas_h"] == 4
    assert json.loads(destino.read_text(encoding="utf-8"))["nombre"] == "Personalizado"


def test_restaurar_vuelve_a_los_valores_iniciales(base):
    panel = Panel(base)
    panel.cajas["tasa_llegadas_h"].set_val("9")
    panel.restaurar()
    assert panel.cajas["tasa_llegadas_h"].text == "3"
