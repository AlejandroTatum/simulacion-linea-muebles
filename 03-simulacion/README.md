# 03-simulacion — Simulación de la línea de sillas

Modelo de eventos discretos en Python (SimPy) de la línea corte → lijado → ensamblaje → acabado, con los parámetros de las Tablas V–VII del informe de avance.

## Cómo ejecutar

Desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r 03-simulacion/requirements.txt

cd 03-simulacion
python src/main.py                 # corre escenarios/base.json (30 réplicas, ~4 s)
python src/graficos.py             # genera graficos/base.png
python -m pytest                   # 19 pruebas
```

`main.py` escribe dos archivos junto a esta carpeta:

| Archivo | Contenido |
|---|---|
| `resultados-<escenario>.csv` | Una fila por réplica y estación: `utilizacion`, `lq`, `wq_min`, `sillas_terminadas`, `throughput_h`, `flujo_min`, `semilla`. |
| `resumen-<escenario>.csv` | Una fila por estación: promedio y desviación estándar de las réplicas, valor teórico M/M/c y error porcentual (ecuación 15). |

Opciones: `--config <archivo.json>` elige el escenario y `--salida <carpeta>` cambia dónde se guardan los CSV. El nombre del JSON se usa como sufijo (`e2.json` → `resultados-e2.csv`).

## Simulador web interactivo

`web/index.html` es una versión visual del mismo modelo para exponer y estudiar. Se abre con doble clic (no necesita servidor ni instalación; sin internet usa fuentes del sistema).

| Sección | Para qué sirve |
|---|---|
| Planta | Vista en planta de la línea: cada silla cambia de aspecto según la etapa (tablones → piezas cortadas → lijadas → silla armada → laqueada). Muestra colas, operarios ocupados y el cuello de botella. |
| Bitácora y *Siguiente evento* | En pausa, avanza de un evento a otro para ver cómo salta el reloj de una simulación de eventos discretos. |
| Indicadores por estación | ρ, Lq y Wq simulados frente a los teóricos M/M/c, actualizados en vivo. |
| Parámetros | λ, operarios y tiempo medio por estación, y tiempos exponenciales (modelo del informe) o más regulares (CV = 0,3). |
| Fórmulas en vivo | Capacidad, M/M/1 del cuello de botella y Ley de Little con los números actuales. |
| Experimentos guiados | E1, E2, E3, saturación y variabilidad, cada uno con lo que se debería observar. |
| Validación | Corre en el navegador las 30 réplicas de 1 000 h del informe y las compara con la teoría y con `resumen-base.csv`. |

El motor (`web/motor.js`) replica `src/linea.py`: mismas llegadas, colas FIFO, calentamiento y forma de medir. Usa otro generador aleatorio, así que sus números no son idénticos a los de Python, pero caen dentro de la misma variación (por ejemplo, ensamblaje: ρ 75,2 % web, 75,1 % Python, 75,0 % teórico). La teoría de la línea y los textos de los experimentos guiados viven en `web/experimentos.js`, calculados a partir de los escenarios del motor. Pruebas del motor y de esos textos, desde esta carpeta:

```bash
node --test web/tests              # 18 pruebas, requiere Node 18+
```

## Escenarios (para el integrante 4)

Los parámetros están en `escenarios/*.json`, así que no hace falta tocar el código. Para E2 o E3 copiá `base.json` y cambiá solo el ensamblaje:

- **E2:** `"recursos": 2`
- **E3:** `"tiempo_min": 10`

Después corré `python src/main.py --config escenarios/e2.json` y `python src/graficos.py --resumen resumen-e2.csv --salida graficos/e2.png`.

## Supuestos de implementación

- Unidad interna: minutos. La tasa de llegadas se expresa en sillas/h.
- `duracion_h` es el horizonte total de cada réplica e **incluye** el calentamiento. Con 1 000 h y 100 h de calentamiento, se miden 900 h.
- Cada réplica arranca con la línea vacía y usa su propia semilla, derivada de `semilla` con `numpy.random.SeedSequence`, así que los resultados se pueden reproducir.
- La utilización y `Lq` se calculan como promedios ponderados en el tiempo dentro de la ventana medida. `Wq` promedia las sillas que entraron a la cola de la estación después del calentamiento.
- Las sillas terminadas son las que salen de acabado dentro de la ventana medida. El tiempo de flujo promedia las sillas que llegaron después del calentamiento y terminaron antes del fin.
- Cuello de botella: la estación con mayor utilización simulada.

## Resultados de la línea base

Ver [`resultados-base.md`](resultados-base.md), que trae el texto listo para la sección 7.1 del informe.
