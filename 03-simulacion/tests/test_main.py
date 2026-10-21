import json
from pathlib import Path

import pandas as pd

from main import main

BASE = Path(__file__).resolve().parents[1] / "escenarios" / "base.json"


def test_cli_writes_csv_files_and_reports_bottleneck(tmp_path, capsys):
    cfg = json.loads(BASE.read_text())
    cfg.update(replicas=2, duracion_h=500, calentamiento_h=50)
    ruta = tmp_path / "corto.json"
    ruta.write_text(json.dumps(cfg))

    assert main(["--config", str(ruta), "--salida", str(tmp_path / "out")]) == 0

    salida = capsys.readouterr().out
    assert "Cuello de botella: Ensamblaje" in salida
    assert len(pd.read_csv(tmp_path / "out" / "resultados-corto.csv")) == 2 * 4
    assert len(pd.read_csv(tmp_path / "out" / "resumen-corto.csv")) == 4


def test_cli_reports_invalid_config_without_writing(tmp_path, capsys):
    ruta = tmp_path / "malo.json"
    ruta.write_text(json.dumps({"nombre": "x"}))

    assert main(["--config", str(ruta), "--salida", str(tmp_path / "out")]) == 1

    captura = capsys.readouterr()
    assert captura.out == ""
    assert captura.err.startswith("Error: Faltan campos")
    assert not (tmp_path / "out").exists()
