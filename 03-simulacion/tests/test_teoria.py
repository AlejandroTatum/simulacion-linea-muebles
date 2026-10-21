import pytest

from teoria import mmc


def test_mm1_matches_assembly_reference_values():
    r = mmc(tasa_llegadas=3, tasa_servicio=4, servidores=1)
    assert r["utilizacion"] == pytest.approx(0.75)
    assert r["lq"] == pytest.approx(2.25)
    assert r["wq_min"] == pytest.approx(45.0)
    assert r["l"] == pytest.approx(3.0)
    assert r["w_min"] == pytest.approx(60.0)


@pytest.mark.parametrize(
    "mu, lq, wq_min",
    [(7.5, 0.2667, 5.33), (6.0, 0.50, 10.0), (5.0, 0.90, 18.0)],
)
def test_mm1_matches_table_vi(mu, lq, wq_min):
    r = mmc(tasa_llegadas=3, tasa_servicio=mu, servidores=1)
    assert r["lq"] == pytest.approx(lq, abs=0.001)
    assert r["wq_min"] == pytest.approx(wq_min, abs=0.01)


def test_mmc_two_servers_matches_scenario_e2():
    r = mmc(tasa_llegadas=3, tasa_servicio=4, servidores=2)
    assert r["utilizacion"] == pytest.approx(0.375)
    assert r["wq_min"] == pytest.approx(2.45, abs=0.01)


def test_unstable_station_is_rejected():
    with pytest.raises(ValueError, match="inestable"):
        mmc(tasa_llegadas=4, tasa_servicio=4, servidores=1)
