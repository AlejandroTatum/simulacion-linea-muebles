# 03-simulacion — Simulación de la línea de sillas

Modelo de eventos discretos en Python (SimPy) de la línea corte → lijado → ensamblaje → acabado, con los parámetros de las Tablas V–VII del informe de avance. Todos los parámetros viven en archivos JSON dentro de `escenarios/`; el código no tiene datos fijos.

## Requisitos

- Python 3.12 o superior (lo exige NumPy 2.5; probado con 3.13).
- Las bibliotecas de `requirements.txt`: SimPy, NumPy, pandas, Matplotlib y pytest.

## Cómo ejecutar

Desde la raíz del repositorio, una sola vez:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r 03-simulacion/requirements.txt
```

Después, desde `03-simulacion/`:

```bash
cd 03-simulacion
python src/main.py                 # línea base: escenarios/base.json (30 réplicas, ~4 s)
python -m pytest                   # 27 pruebas
```

Cada escenario genera tres archivos (en `03-simulacion/`, o en la carpeta que indique `--salida`):

| Archivo | Contenido |
|---|---|
| `resultados-<escenario>.csv` | Una fila por réplica y estación: `utilizacion`, `lq`, `wq_min`, `sillas_terminadas`, `throughput_h`, `flujo_min`, `semilla`. |
| `resumen-<escenario>.csv` | Una fila por estación: promedio y desviación estándar de las réplicas, valor teórico M/M/c y error porcentual (ecuación 15). |
| `graficos/<escenario>.png` | Utilización y espera en cola por estación, simulada frente a teórica. |

`<escenario>` es el nombre del archivo JSON sin extensión: `e2.json` → `resumen-e2.csv`, `graficos/e2.png`.

En pantalla se ve la tabla por estación, la producción por hora, el tiempo total de flujo (con su valor teórico) y el cuello de botella.

## Cambiar de escenario

Ya están los tres escenarios del informe:

| Archivo | Escenario | Qué cambia respecto de la base |
|---|---|---|
| `escenarios/base.json` | E1 · Línea base | — |
| `escenarios/e2.json` | E2 · Dos ensambladores | Ensamblaje con `"recursos": 2` |
| `escenarios/e3.json` | E3 · Ensamblaje en 10 min | Ensamblaje con `"tiempo_min": 10` |

```bash
python src/main.py --config escenarios/e2.json                      # uno
python src/main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json   # varios seguidos
```

Si se pasan varios archivos, primero se validan todos y recién después se simula; un error en el último no hace perder la corrida de los primeros.

Para un escenario nuevo, copiá `base.json` con otro nombre y cambiá lo que necesites. Campos:

| Campo | Significado |
|---|---|
| `nombre` | Título que aparece en pantalla y en los CSV. |
| `tasa_llegadas_h` | λ, sillas que llegan por hora (llegadas de Poisson). |
| `estaciones` | Lista en orden de proceso. Cada una con `nombre`, `recursos` (operarios en paralelo, ≥ 1) y `tiempo_min` (tiempo medio de proceso, distribución exponencial). |
| `replicas` | Cantidad de corridas independientes. |
| `duracion_h` | Horas simuladas por réplica, **incluido** el calentamiento. |
| `calentamiento_h` | Horas iniciales que se simulan pero no se miden. |
| `semilla` | Semilla base; con la misma semilla los resultados se repiten exactamente. |

Si falta un campo o un valor no tiene sentido (por ejemplo `recursos: 0`), el programa avisa y no escribe nada.

## Cómo está organizado el código

| Archivo | Qué hace |
|---|---|
| `src/main.py` | Lee los escenarios, corre la simulación y escribe CSV y gráfico. Es lo único que hace falta ejecutar. |
| `src/linea.py` | El modelo: llegadas, recorrido de cada silla por las estaciones, medición de indicadores y resumen frente a la teoría. |
| `src/teoria.py` | Fórmulas M/M/c (ecuaciones 7–14) y el tiempo de flujo teórico de la línea. |
| `src/graficos.py` | Gráfico de barras simulado vs. teórico. Se usa desde `main.py`, pero también se puede correr solo: `python src/graficos.py --resumen resumen-e2.csv --salida graficos/e2.png`. |
| `tests/` | Pruebas: teoría frente a las tablas del informe, reproducibilidad con semilla, Ley de Little, escenarios y línea de comandos. |

## Supuestos de implementación

- Unidad interna: minutos. La tasa de llegadas se expresa en sillas/h.
- `duracion_h` es el horizonte total de cada réplica e **incluye** el calentamiento. Con 1 000 h y 100 h de calentamiento, se miden 900 h.
- Cada réplica arranca con la línea vacía y usa su propia semilla, derivada de `semilla` con `numpy.random.SeedSequence`, así que los resultados se pueden reproducir.
- La utilización y `Lq` se calculan como promedios ponderados en el tiempo dentro de la ventana medida. `Wq` promedia las sillas que entraron a la cola de la estación después del calentamiento.
- Las sillas terminadas son las que salen de acabado dentro de la ventana medida. El tiempo de flujo promedia las sillas que llegaron después del calentamiento y terminaron antes del fin.
- Cuello de botella: la estación con mayor utilización simulada.

## Resultados de la línea base

Ver [`resultados-base.md`](resultados-base.md), que trae el texto listo para la sección 7.1 del informe.
