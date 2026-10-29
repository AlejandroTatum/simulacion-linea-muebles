import json
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402

from modelo.configuracion import ErrorConfiguracion, cargar_escenario  # noqa: E402
from vista.panel import Panel, escenario_desde_formulario, formulario_desde_escenario  # noqa: E402

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


@pytest.fixture(autouse=True)
def _cerrar_figuras():
    yield
    import matplotlib.pyplot as plt
    plt.close("all")


@pytest.fixture
def base():
    return cargar_escenario(BASE)


def test_el_formulario_arranca_con_los_valores_del_escenario(base):
    valores = formulario_desde_escenario(base)
    assert valores["tasa_llegadas_h"] == "3"
    assert valores["replicas"] == "30"
    assert not any(clave.startswith("recursos_") for clave in valores), "no hay casilla de operarios"
    assert [valores[f"tiempo_min_{i}"] for i in range(4)] == ["8", "10", "15", "12"]


def test_sin_cambios_el_formulario_devuelve_el_mismo_escenario(base):
    escenario = escenario_desde_formulario(formulario_desde_escenario(base), base)
    assert escenario["estaciones"] == base["estaciones"]
    for campo in ("tasa_llegadas_h", "replicas", "duracion_h", "calentamiento_h", "semilla"):
        assert escenario[campo] == base[campo]


def test_los_valores_cambiados_llegan_al_escenario(base):
    valores = formulario_desde_escenario(base)
    valores.update({"tasa_llegadas_h": "4,5", "tiempo_min_3": "9.5"})
    escenario = escenario_desde_formulario(valores, base)
    assert escenario["tasa_llegadas_h"] == 4.5
    assert escenario["estaciones"][3]["tiempo_min"] == 9.5
    assert base["tasa_llegadas_h"] == 3, "el escenario original no se modifica"


@pytest.mark.parametrize("campo, texto, mensaje", [
    ("tasa_llegadas_h", "abc", "Llegadas por hora (λ): escribí un número"),
    ("tiempo_min_1", "-3", "estación 2: tiempo_min debe ser un número mayor que 0"),
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
    panel.cajas["tiempo_min_2"].set_val("10")
    resultado = panel.simular()
    assert resultado is not None
    resumen, linea = resultado
    assert resumen.loc[resumen["estacion"] == "Ensamblaje", "tiempo_min"].item() == 10
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


def test_el_panel_es_solo_m_m_1_con_un_operario_por_estacion(base):
    panel = Panel(base)
    assert not any(clave.startswith("recursos_") for clave in panel.cajas)
    con_dos = dict(base, estaciones=[dict(e, recursos=2) for e in base["estaciones"]])
    escenario = escenario_desde_formulario(formulario_desde_escenario(con_dos), con_dos)
    assert [e["recursos"] for e in escenario["estaciones"]] == [1, 1, 1, 1]


def test_la_animacion_redibuja_solo_el_taller(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    animacion = panel.animar()
    assert animacion._blit, "cada cuadro redibuja solo lo que cambia (blit)"
    cambiados = panel.escena.dibujar(1)
    assert cambiados and all(artista.get_animated() for artista in cambiados)


def test_un_redibujado_completo_vuelve_a_pintar_el_taller(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("1")
    panel.animar()
    pintados = []
    panel._pintar_taller = lambda _evento=None: pintados.append(True)
    panel.figura.canvas.mpl_disconnect(panel._id_repintar)
    panel._id_repintar = panel.figura.canvas.mpl_connect("draw_event", panel._pintar_taller)
    panel.figura.canvas.draw()
    assert pintados


def test_simular_en_segundo_plano_no_bloquea_y_muestra_los_resultados(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "2", "duracion_h": "100", "calentamiento_h": "10",
                         "horas_animacion": "1"}.items():
        panel.cajas[clave].set_val(valor)
    assert panel.simular(en_segundo_plano=True) is None, "vuelve enseguida"
    assert "Simulando" in panel.estado.get_text()
    panel._calculo.join(timeout=60)
    assert panel._revisar_calculo() is True
    assert "Cuello de botella" in panel.estado.get_text()


@pytest.mark.parametrize("animar_de_nuevo", [False, True])
def test_el_blit_no_deja_restos_de_cuadros_anteriores(base, animar_de_nuevo):
    import numpy as np
    panel = Panel(base)
    lienzo = panel.figura.canvas
    lienzo.draw()
    if animar_de_nuevo:
        panel.cajas["tiempo_min_2"].set_val("10")
        panel.animar()
        lienzo.draw()
    animacion = panel._animacion
    animacion._init_draw()
    for k in range(1, 25):
        animacion._draw_next_frame(k, blit=True)
    con_blit = np.asarray(lienzo.buffer_rgba()).copy()
    lienzo.draw()  # redibujado completo del mismo cuadro, sin restos
    completo = np.asarray(lienzo.buffer_rgba())
    distintos = np.any(con_blit != completo, axis=2).mean()
    assert distintos < 0.001, f"{distintos:.2%} de píxeles distintos"


def test_el_panel_avisa_que_la_linea_es_inestable(base):
    panel = Panel(base)
    for clave, valor in {"tasa_llegadas_h": "10", "replicas": "2", "duracion_h": "200",
                         "calentamiento_h": "20"}.items():
        panel.cajas[clave].set_val(valor)
    assert panel.simular() is not None
    texto = panel.estado.get_text().replace("\n", " ")
    assert "Línea inestable: λ = 10 muebles/h ≥ capacidad 4 muebles/h (Ensamblaje)." in texto
    assert "Cuello de botella: Ensamblaje" in texto


def test_el_panel_muestra_sin_datos_en_vez_de_cero(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "2", "duracion_h": "0.01",
                         "calentamiento_h": "0"}.items():
        panel.cajas[clave].set_val(valor)
    assert panel.simular() is not None
    texto = panel.estado.get_text()
    assert "Tiempo total de flujo: — min" in texto
    assert "nan" not in texto.lower()


def test_el_panel_rechaza_un_escenario_exagerado(base):
    panel = Panel(base)
    panel.cajas["tasa_llegadas_h"].set_val("100000")
    assert panel.simular() is None
    assert "el máximo es 200000" in panel.estado.get_text().replace("\n", " ")


def test_horas_a_animar_tiene_un_maximo(base):
    panel = Panel(base)
    panel.cajas["horas_animacion"].set_val("73")
    assert panel.animar() is None
    assert panel.estado.get_text() == "Error: Horas a animar: debe ser como máximo 72"
    panel.cajas["horas_animacion"].set_val("72")
    assert panel.animar() is not None


# Casillas sin lag: un redibujado completo de la ventana cuesta ~175 ms, así que las casillas
# deben repintarse solas (blit) al escribir, hacer clic, pasar el mouse o cambiar su valor.

@pytest.fixture
def conteo(base, monkeypatch):
    """Panel ya dibujado cuyo canvas cuenta los redibujados completos y los blit."""
    panel = Panel(base)
    lienzo = panel.figura.canvas
    lienzo.draw()
    cuenta = {"draw": 0, "idle": 0, "blit": []}
    dibujar = lienzo.draw

    def draw(*args, **kwargs):
        cuenta["draw"] += 1
        return dibujar(*args, **kwargs)

    # En Agg draw_idle llama a draw; en una ventana real se junta en un solo redibujado.
    monkeypatch.setattr(lienzo, "draw", draw)
    monkeypatch.setattr(lienzo, "draw_idle",
                        lambda *a, **k: cuenta.__setitem__("idle", cuenta["idle"] + 1))
    monkeypatch.setattr(lienzo, "blit", lambda bbox=None: cuenta["blit"].append(bbox))
    assert lienzo.supports_blit
    return panel, cuenta


def _centro(eje):
    caja = eje.get_window_extent()
    return (caja.x0 + caja.x1) / 2, (caja.y0 + caja.y1) / 2


def _mouse(panel, nombre, x, y):
    from matplotlib.backend_bases import MouseEvent
    lienzo = panel.figura.canvas
    lienzo.callbacks.process(nombre, MouseEvent(nombre, lienzo, x, y, button=1))


def _clic(panel, eje):
    x, y = _centro(eje)
    _mouse(panel, "button_press_event", x, y)
    _mouse(panel, "button_release_event", x, y)


def _tecla(panel, tecla):
    from matplotlib.backend_bases import KeyEvent
    lienzo = panel.figura.canvas
    lienzo.callbacks.process("key_press_event", KeyEvent("key_press_event", lienzo, tecla))


def test_escribir_en_una_casilla_no_redibuja_toda_la_ventana(conteo):
    panel, cuenta = conteo
    caja = panel.cajas["tasa_llegadas_h"]
    _clic(panel, caja.ax)
    _tecla(panel, "backspace")
    _tecla(panel, "4")
    assert caja.text == "4"
    assert cuenta["draw"] == 0
    assert cuenta["blit"] and all(bbox is caja.ax.bbox for bbox in cuenta["blit"])


def test_salir_de_una_casilla_la_repinta_sola(conteo):
    panel, cuenta = conteo
    caja, otra = panel.cajas["tasa_llegadas_h"], panel.cajas["replicas"]
    _clic(panel, caja.ax)
    cuenta["blit"].clear()
    _clic(panel, otra.ax)  # el clic fuera termina de escribir en la primera
    assert not caja.cursor.get_visible()
    assert cuenta["draw"] == 0
    assert caja.ax.bbox in cuenta["blit"]


def test_un_clic_fuera_de_las_casillas_no_las_repinta_si_no_se_escribe(conteo):
    panel, cuenta = conteo
    _mouse(panel, "button_press_event", 5, 5)
    assert cuenta["draw"] == 0
    assert cuenta["blit"] == []


def test_pasar_el_mouse_por_las_casillas_no_redibuja_nada(conteo):
    panel, cuenta = conteo
    for caja in panel.cajas.values():
        x, y = _centro(caja.ax)
        _mouse(panel, "motion_notify_event", x, y)
        _mouse(panel, "motion_notify_event", 5, y)
    assert cuenta["draw"] == 0
    assert cuenta["idle"] == 0
    assert cuenta["blit"] == []


def test_cambiar_el_valor_de_una_casilla_la_repinta_sola(conteo):
    panel, cuenta = conteo
    caja = panel.cajas["replicas"]
    caja.set_val("7")
    assert caja.text == "7"
    assert cuenta["draw"] == 0
    assert cuenta["blit"] == [caja.ax.bbox]


def test_restaurar_redibuja_la_ventana_a_lo_sumo_una_vez(conteo):
    panel, cuenta = conteo
    for clave in ("tasa_llegadas_h", "tiempo_min_0", "replicas", "duracion_h", "semilla"):
        panel.cajas[clave].set_val("9")
    cuenta["draw"] = 0
    panel.restaurar()
    assert panel.valores() == panel.iniciales
    assert cuenta["draw"] <= 1


def test_sin_blit_la_casilla_pide_un_redibujado_diferido(conteo, monkeypatch):
    panel, cuenta = conteo
    monkeypatch.setattr(type(panel.figura.canvas), "supports_blit", False)
    panel.cajas["replicas"].set_val("7")
    assert cuenta["draw"] == 0
    assert cuenta["blit"] == []
    assert cuenta["idle"] >= 1


def test_simular_dos_veces_seguidas_no_deja_un_temporizador_vivo(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "1", "duracion_h": "20", "calentamiento_h": "2",
                         "horas_animacion": "1"}.items():
        panel.cajas[clave].set_val(valor)
    panel.simular(en_segundo_plano=True)
    primero = panel._temporizador_calculo
    detenidos = []
    primero.stop = lambda: detenidos.append(primero)
    panel._calculo.join(timeout=60)  # terminó, pero el temporizador todavía no lo notó
    panel.simular(en_segundo_plano=True)
    assert primero in detenidos
    assert panel._temporizador_calculo is not primero
    panel._calculo.join(timeout=60)
    assert panel._revisar_calculo() is True
    assert panel._temporizador_calculo is None


def test_simular_calcula_en_otro_proceso_y_el_temporizador_sigue_revisando(base):
    panel = Panel(base)
    for clave, valor in {"replicas": "30", "duracion_h": "1000", "calentamiento_h": "50",
                         "horas_animacion": "1"}.items():
        panel.cajas[clave].set_val(valor)
    panel.simular(en_segundo_plano=True)
    assert panel._calculo.pid != os.getpid(), "las réplicas no compiten por el GIL de la ventana"
    # Mientras calcula devuelve True: si devolviera False Matplotlib quitaría el callback
    # del temporizador y los resultados nunca se dibujarían.
    assert panel._revisar_calculo() is True
    assert panel._calculo is not None
    assert "Cuello de botella" not in panel.estado.get_text()
    panel._calculo.join(timeout=120)
    assert panel._revisar_calculo() is True
    assert "Cuello de botella" in panel.estado.get_text()


def test_si_el_proceso_de_simular_muere_el_panel_avisa_y_no_se_cuelga(base):
    panel = Panel(base)
    panel.simular(en_segundo_plano=True)
    panel._calculo.terminate()
    panel._calculo.join(timeout=60)
    assert panel._revisar_calculo() is True
    assert "Error al simular: el proceso terminó sin resultado" in panel.estado.get_text()
    assert panel._calculo is None and panel._temporizador_calculo is None
