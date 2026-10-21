import json
from pathlib import Path

from graficos import main as graficar
from main import main as simular

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
    assert "ejecutá primero src/main.py" in capsys.readouterr().err
    assert not (tmp_path / "g.png").exists()
