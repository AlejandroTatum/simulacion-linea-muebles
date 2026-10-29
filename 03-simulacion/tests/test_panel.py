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


def test_el_taller_se_anima_en_la_misma_ventana_del_panel(base):
    import matplotlib.pyplot as plt
    plt.close("all")
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    assert panel.animar() is not None
    assert plt.get_fignums() == [panel.figura.number], "no se abre otra ventana"
    assert panel.escena.figura is panel.figura


def test_animar_de_nuevo_reemplaza_el_taller_anterior(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    panel.animar()
    ejes_antes = len(panel.figura.axes)
    textos_antes = len(panel.figura.texts)
    panel.cajas["tiempo_min_2"].set_val("10")
    panel.animar()
    assert len(panel.figura.axes) == ejes_antes
    assert len(panel.figura.texts) == textos_antes
    assert any("10 min/mueble" in t.get_text() for t in panel.escena.carteles_texto())


def test_pausa_detiene_y_reanuda_la_animacion(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    panel.animar()
    assert panel.pausar() is True
    assert panel.botones["pausa"].label.get_text() == "Seguir"
    assert panel.pausar() is False
    assert panel.botones["pausa"].label.get_text() == "Pausa"


def test_el_panel_abre_con_el_taller_dibujado(base):
    panel = Panel(base)
    assert panel.escena is not None
    assert panel.escena.figura is panel.figura


def test_sin_cambios_el_escenario_conserva_su_nombre(base):
    assert escenario_desde_formulario(formulario_desde_escenario(base), base)["nombre"] == base["nombre"]
    valores = formulario_desde_escenario(base)
    valores["tasa_llegadas_h"] = "4"
    assert escenario_desde_formulario(valores, base)["nombre"] == "Personalizado"


def test_los_textos_del_panel_no_se_pisan_en_una_pantalla_chica(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "2", "duracion_h": "100", "calentamiento_h": "10"}.items():
        panel.cajas[clave].set_val(valor)
    panel.simular()
    panel.figura.set_size_inches(13.66, 7.68)
    panel._ajustar_taller()
    panel.figura.canvas.draw()
    estado = panel.estado.get_window_extent()
    titulo = panel.eje_barras.title.get_window_extent()
    leyenda = panel.eje_barras.get_legend().get_window_extent()
    assert not estado.overlaps(titulo)
    assert not titulo.overlaps(leyenda)
    separador_x = 0.235 * panel.figura.bbox.width
    for texto in panel.figura.texts:
        caja = texto.get_window_extent()
        if caja.x0 < separador_x and texto.get_text().strip():
            assert caja.x1 <= separador_x, texto.get_text()


def _terminar_animacion(panel):
    """Matplotlib deja event_source en None cuando la animación muestra el último cuadro."""
    panel._animacion.event_source = None


def test_animar_de_nuevo_funciona_cuando_la_animacion_ya_termino(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    panel.animar()
    _terminar_animacion(panel)
    assert panel.animar() is not None
    assert panel._animacion.event_source is not None


def test_pausa_con_la_animacion_terminada_avisa_y_no_falla(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    panel.animar()
    _terminar_animacion(panel)
    assert panel.pausar() is None
    assert "Animar de nuevo" in panel.estado.get_text()


def test_restaurar_funciona_cuando_la_animacion_ya_termino(base):
    panel = Panel(base)
    panel.animar()
    _terminar_animacion(panel)
    panel.cajas["tasa_llegadas_h"].set_val("9")
    panel.restaurar()
    assert panel.cajas["tasa_llegadas_h"].text == "3"
    assert panel._animacion.event_source is not None


def test_cerrar_la_ventana_detiene_la_animacion(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    animacion = panel.animar()
    temporizador = animacion.event_source
    detenido = []
    temporizador.stop = lambda: detenido.append(True)
    panel.figura.canvas.callbacks.process("close_event", None)
    assert detenido, "al cerrar, la animación deja de pedir cuadros"


@pytest.mark.parametrize("tamano", [(13.66, 7.68), (19.2, 10.2)])
def test_el_resumen_largo_no_pisa_los_resultados(base, tamano):
    panel = Panel(base)
    for clave, valor in {"replicas": "2", "duracion_h": "100", "calentamiento_h": "10",
                         "tasa_llegadas_h": "5"}.items():
        panel.cajas[clave].set_val(valor)
    panel.simular()
    panel.figura.set_size_inches(*tamano)
    panel._ajustar_taller()
    panel.figura.canvas.draw()
    estado = panel.estado.get_window_extent()
    separacion = 6  # píxeles libres entre el resumen y lo que tiene debajo
    for otro in (panel.eje_tabla.title, panel.eje_barras.title):
        assert estado.y0 - otro.get_window_extent().y1 >= separacion, otro.get_text()
    assert estado.x1 <= panel.figura.bbox.width


def test_simular_actualiza_tambien_el_taller(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "2", "duracion_h": "100", "calentamiento_h": "10",
                         "horas_animacion": "1", "tiempo_min_2": "10"}.items():
        panel.cajas[clave].set_val(valor)
    panel.simular()
    _, (titulo, detalle) = panel.escena.carteles[2]
    assert titulo.get_text() == "Ensamblaje"
    assert "10 min/mueble" in detalle.get_text() and "ρ = 50%" in detalle.get_text()
