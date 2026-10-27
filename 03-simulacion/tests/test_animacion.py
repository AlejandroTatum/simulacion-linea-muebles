import json
from pathlib import Path

from animacion import estados_en, main
from linea import cargar_config, simular_replica

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


def _corto(horas=6):
    cfg = cargar_config(BASE)
    cfg.update(duracion_h=horas, calentamiento_h=0)
    return cfg


def test_trace_does_not_change_the_simulation():
    cfg = _corto(50)
    traza = []
    assert simular_replica(cfg, 11, traza=traza) == simular_replica(cfg, 11)
    assert traza, "the trace records state changes"


def test_trace_states_stay_within_station_limits():
    cfg = _corto(50)
    traza = []
    simular_replica(cfg, 3, traza=traza)
    recursos = {e["nombre"]: e["recursos"] for e in cfg["estaciones"]}
    tiempos = [t for t, *_ in traza]
    assert tiempos == sorted(tiempos)
    for t, nombre, cola, ocupados in traza:
        assert cola >= 0 and 0 <= ocupados <= recursos[nombre]


def test_states_at_sample_times_use_the_last_change():
    traza = [(0.0, "A", 1, 0), (2.0, "A", 0, 1), (5.0, "A", 0, 0), (3.0, "B", 2, 1)]
    estados = estados_en(traza, ["A", "B"], [0, 1, 2, 4, 6])
    assert estados["A"] == {"cola": [1, 1, 0, 0, 0], "ocupados": [0, 0, 1, 1, 0]}
    assert estados["B"] == {"cola": [0, 0, 0, 2, 2], "ocupados": [0, 0, 0, 1, 1]}


def test_cli_saves_the_animation_as_gif(tmp_path, capsys):
    cfg = json.loads(BASE.read_text())
    ruta = tmp_path / "base.json"
    ruta.write_text(json.dumps(cfg))
    gif = tmp_path / "linea.gif"

    assert main(["--config", str(ruta), "--horas", "2", "--paso", "10", "--guardar", str(gif)]) == 0

    assert gif.read_bytes()[:6] in (b"GIF87a", b"GIF89a")
    assert f"Animación guardada: {gif}" in capsys.readouterr().out


def test_cli_rejects_non_positive_hours(tmp_path, capsys):
    assert main(["--config", str(BASE), "--horas", "0", "--guardar", str(tmp_path / "x.gif")]) == 1
    assert capsys.readouterr().err == "Error: --horas y --paso deben ser mayores que 0\n"
    assert not (tmp_path / "x.gif").exists()


def test_finished_chairs_are_recorded_with_their_exit_time():
    cfg = _corto(50)
    salidas = []
    resultado = simular_replica(cfg, 5, salidas=salidas)
    assert len(salidas) == resultado["terminadas"] > 0
    assert salidas == sorted(salidas)
    assert all(0 < t <= 50 * 60 for t in salidas)


def _figura(tmp_path=None):
    import matplotlib
    matplotlib.use("Agg")
    from animacion import armar
    return armar(_corto(3) | {"duracion_h": 3}, horas=3, paso_min=30, semilla=7)


def _dentro(interior, exterior, margen=1.0):
    return (interior.x0 >= exterior.x0 - margen and interior.x1 <= exterior.x1 + margen
            and interior.y0 >= exterior.y0 - margen and interior.y1 <= exterior.y1 + margen)


def test_sign_text_fits_when_the_window_shrinks():
    escena = _figura()
    escena.figura.set_size_inches(10.5, 6.4)
    escena.ajustar_texto()
    escena.figura.canvas.draw()
    for cartel, textos in escena.carteles:
        marco = cartel.get_window_extent()
        for texto in textos:
            assert _dentro(texto.get_window_extent(), marco), texto.get_text()


def test_every_text_stays_inside_the_window_at_small_and_large_sizes():
    from matplotlib.text import Text
    escena = _figura()
    for tamano in ((10.5, 6.4), (14, 8.6), (19, 11)):
        escena.figura.set_size_inches(*tamano)
        escena.ajustar_texto()
        escena.dibujar(len(escena.tiempos) - 1)
        escena.figura.canvas.draw()
        ventana = escena.figura.bbox
        dibujado = escena.figura.get_tightbbox().transformed(escena.figura.dpi_scale_trans)
        assert _dentro(dibujado, ventana), tamano  # everything actually drawn fits the window
        # Tick labels outside the axis range exist but are never drawn, so they are
        # covered by the tight box above and skipped here.
        marcas = {t for ax in escena.figura.axes for t in ax.get_xticklabels() + ax.get_yticklabels()}
        for texto in escena.figura.findobj(Text):
            if texto.get_visible() and texto.get_text().strip() and texto not in marcas:
                assert _dentro(texto.get_window_extent(), ventana), (tamano, texto.get_text())


def test_bundled_inter_font_is_used():
    escena = _figura()
    escena.figura.canvas.draw()
    assert escena.carteles[0][1][0].get_fontname() == "Inter"
