import pytest

from modelo.teoria import (capacidad_estacion, capacidad_linea, cuello_por_capacidad,
                           flujo_teorico_min, mm1)

# (tiempo medio en minutos, rho, Lq, Wq en minutos) de la Tabla IV del informe.
TABLA_E1 = [
    (8.0, 0.40, 0.2667, 5.33),
    (10.0, 0.50, 0.50, 10.0),
    (15.0, 0.75, 2.25, 45.0),
    (12.0, 0.60, 0.90, 18.0),
]


@pytest.mark.parametrize("tiempo_min, rho, lq, wq_min", TABLA_E1)
def test_mm1_coincide_con_la_tabla_vi(tiempo_min, rho, lq, wq_min):
    r = mm1(tasa_llegadas=3, tasa_servicio=60 / tiempo_min)
    assert r["utilizacion"] == pytest.approx(rho)
    assert r["lq"] == pytest.approx(lq, abs=0.001)
    assert r["wq_min"] == pytest.approx(wq_min, abs=0.01)


def test_mm1_calcula_l_y_w():
    r = mm1(tasa_llegadas=3, tasa_servicio=4)
    assert r["l"] == pytest.approx(3.0)
    assert r["w_min"] == pytest.approx(60.0)


@pytest.mark.parametrize(
    "tiempo_min, rho, lq, wq_min",
    [(12.0, 0.60, 0.90, 18.0), (10.0, 0.50, 0.50, 10.0)],
)
def test_mm1_de_ensamblaje_en_e2_y_e3(tiempo_min, rho, lq, wq_min):
    r = mm1(tasa_llegadas=3, tasa_servicio=60 / tiempo_min)
    assert r["utilizacion"] == pytest.approx(rho)
    assert r["lq"] == pytest.approx(lq)
    assert r["wq_min"] == pytest.approx(wq_min)


def test_probabilidad_de_espera_y_de_cola_mm1():
    r = mm1(tasa_llegadas=3, tasa_servicio=7.5)
    assert r["prob_espera"] == pytest.approx(0.4)
    assert r["prob_cola"] == pytest.approx(0.16)


def test_ley_de_little_en_la_teoria():
    r = mm1(tasa_llegadas=3, tasa_servicio=4)
    assert r["lq"] == pytest.approx(3 * r["wq_min"] / 60)
    assert r["l"] == pytest.approx(3 * r["w_min"] / 60)


def test_la_teoria_rechaza_mas_de_un_servidor():
    with pytest.raises(ValueError, match="M/M/1"):
        mm1(tasa_llegadas=3, tasa_servicio=4, servidores=2)


@pytest.mark.parametrize("lam, mu", [(0, 4), (-1, 4), (3, 0), (3, -1)])
def test_la_teoria_rechaza_tasas_no_positivas(lam, mu):
    with pytest.raises(ValueError, match="positivas"):
        mm1(lam, mu)


def test_unstable_station_is_rejected():
    with pytest.raises(ValueError, match="inestable"):
        mm1(tasa_llegadas=4, tasa_servicio=4, servidores=1)


def test_line_flow_time_sums_station_times():
    estaciones = [{"recursos": 1, "tiempo_min": t} for t in (8, 10, 15, 12)]
    # W = 1 / (mu - lambda): 13.33 + 20 + 60 + 30 minutes
    assert abs(flujo_teorico_min(3, estaciones) - 123.333333) < 1e-5


def test_line_flow_time_is_none_when_a_station_is_unstable():
    assert flujo_teorico_min(5, [{"recursos": 1, "tiempo_min": 15}]) is None


def test_line_flow_time_is_none_without_mm1_theory():
    assert flujo_teorico_min(3, [{"recursos": 2, "tiempo_min": 15}]) is None


def test_capacidad_de_una_estacion_es_c_por_mu():
    assert capacidad_estacion({"recursos": 1, "tiempo_min": 8}) == pytest.approx(7.5)
    assert capacidad_estacion({"recursos": 2, "tiempo_min": 15}) == pytest.approx(8.0)


def test_capacidad_de_la_linea_la_marca_la_estacion_mas_lenta():
    estaciones = [
        {"nombre": "Corte", "recursos": 1, "tiempo_min": 8},
        {"nombre": "Lijado", "recursos": 1, "tiempo_min": 10},
        {"nombre": "Ensamblaje", "recursos": 1, "tiempo_min": 15},
        {"nombre": "Acabado", "recursos": 1, "tiempo_min": 12},
    ]
    assert capacidad_linea(estaciones) == pytest.approx(4.0)
    assert cuello_por_capacidad(estaciones) == "Ensamblaje"


def test_la_capacidad_sube_al_reducir_el_tiempo_de_ensamblaje():
    def capacidad(t3):
        return capacidad_linea([
            {"recursos": 1, "tiempo_min": 8},
            {"recursos": 1, "tiempo_min": 10},
            {"recursos": 1, "tiempo_min": t3},
            {"recursos": 1, "tiempo_min": 12},
        ])

    assert capacidad(15) == pytest.approx(4.0)
    assert capacidad(12) == pytest.approx(5.0)
    assert capacidad(10) == pytest.approx(5.0)
