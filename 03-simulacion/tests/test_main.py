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


def _corto(tmp_path, nombre, **cambios):
    cfg = json.loads(BASE.read_text())
    cfg.update(replicas=2, duracion_h=300, calentamiento_h=30, **cambios)
    ruta = tmp_path / f"{nombre}.json"
    ruta.write_text(json.dumps(cfg))
    return ruta


def test_cli_runs_several_scenarios_and_writes_a_chart_for_each(tmp_path, capsys):
    a, b = _corto(tmp_path, "a"), _corto(tmp_path, "b", tasa_llegadas_h=2)
    out = tmp_path / "out"

    assert main(["--config", str(a), str(b), "--salida", str(out)]) == 0

    for nombre in ("a", "b"):
        assert (out / f"resultados-{nombre}.csv").exists()
        assert (out / f"resumen-{nombre}.csv").exists()
        assert (out / f"linea-{nombre}.csv").exists()
        assert (out / "graficos" / f"{nombre}.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert capsys.readouterr().out.count("Cuello de botella:") == 2


def test_cli_prints_theoretical_flow_time_and_little_law(tmp_path, capsys):
    assert main(["--config", str(_corto(tmp_path, "a")), "--salida", str(tmp_path / "out")]) == 0
    salida = capsys.readouterr().out
    assert "teoría 123.3 min" in salida
    assert "Ley de Little" in salida


def test_cli_validates_every_scenario_before_running_any(tmp_path, capsys):
    bueno = _corto(tmp_path, "bueno")
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps({"nombre": "x"}))

    assert main(["--config", str(bueno), str(malo), "--salida", str(tmp_path / "out")]) == 1

    captura = capsys.readouterr()
    assert captura.out == ""
    assert captura.err.startswith("Error: Faltan campos")
    assert not (tmp_path / "out").exists()


def test_cli_reports_missing_scenario_file(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "nada.json"), "--salida", str(tmp_path / "out")]) == 1
    assert capsys.readouterr().err == f"Error: no existe el escenario {tmp_path / 'nada.json'}\n"
    assert not (tmp_path / "out").exists()


def test_cli_rejects_two_scenarios_that_would_overwrite_each_other(tmp_path, capsys):
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    a = _corto(tmp_path / "x", "base")
    b = _corto(tmp_path / "y", "base")

    assert main(["--config", str(a), str(b), "--salida", str(tmp_path / "out")]) == 1

    captura = capsys.readouterr()
    assert captura.out == ""
    assert captura.err == "Error: dos escenarios se llaman 'base'; sus resultados se pisarían\n"
    assert not (tmp_path / "out").exists()


def test_cli_reports_unwritable_output_folder(tmp_path, capsys):
    ocupado = tmp_path / "archivo"
    ocupado.write_text("not a folder")

    assert main(["--config", str(_corto(tmp_path, "a")), "--salida", str(ocupado)]) == 1

    assert capsys.readouterr().err.startswith(f"Error: no se pudo escribir en {ocupado}")
