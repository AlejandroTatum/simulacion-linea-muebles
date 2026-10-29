import json
from pathlib import Path

from main import main as simular
from vista.graficas import main as graficar

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


def test_chart_is_written_from_summary(tmp_path):
    cfg = json.loads(BASE.read_text())
    cfg.update(replicas=2, duracion_h=300, calentamiento_h=30)
    ruta = tmp_path / "corto.json"
    ruta.write_text(json.dumps(cfg))
    simular(["--config", str(ruta), "--salida", str(tmp_path)])

    png = tmp_path / "g.png"
    assert graficar(["--resumen", str(tmp_path / "resumen-corto.csv"), "--salida", str(png)]) == 0
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_missing_summary_is_reported(tmp_path, capsys):
    assert graficar(["--resumen", str(tmp_path / "no.csv"), "--salida", str(tmp_path / "g.png")]) == 1
    assert "ejecutá primero main.py" in capsys.readouterr().err
    assert not (tmp_path / "g.png").exists()


def _escenario(tmp_path, nombre, **cambios):
    cfg = json.loads(BASE.read_text())
    cfg.update(replicas=2, duracion_h=300, calentamiento_h=30, **cambios)
    ruta = tmp_path / f"{nombre}.json"
    ruta.write_text(json.dumps(cfg))
    return ruta


def test_queue_charts_are_written(tmp_path):
    salida = tmp_path / "out"
    assert simular(["--config", str(_escenario(tmp_path, "corto")),
                    "--salida", str(salida)]) == 0

    for nombre in ("cola-corto.png", "utilizacion-cola-corto.png",
                   "distribucion-cola-corto.png", "flujo-corto.png"):
        png = salida / "graficos" / nombre
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_comparison_chart_is_written_for_several_scenarios(tmp_path):
    salida = tmp_path / "out"
    assert simular(["--config", str(_escenario(tmp_path, "a")),
                    str(_escenario(tmp_path, "b", tasa_llegadas_h=2)),
                    "--salida", str(salida)]) == 0

    png = salida / "graficos" / "escenarios.png"
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
