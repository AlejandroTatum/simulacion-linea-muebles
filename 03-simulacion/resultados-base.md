# Resultados de la línea base (E1)

Fuente: `resumen-base.csv` y `resultados-base.csv`, generados con `python main.py` (semilla 2026, 30 réplicas de 1 000 h con 100 h de calentamiento). Gráficos: `graficos/base.png` y las figuras complementarias del final.

Este documento contiene el texto listo para pegar en el informe del grupo (Google Docs). Las tablas y la figura siguen la numeración del informe de avance.

> **Estado:** ya integrado en el informe (secciones 6.3, 6.4.6 y 7.1). Los resultados de E2 y E3 para la sección 7.2 están en [`../04-experimentos/`](../04-experimentos/).

---

## Ajustes a secciones existentes

**6.3, Tabla II (Bibliotecas).** Reemplazar "por confirmar al implementar" por:

> SimPy 4.1 (eventos y recursos), NumPy 2.5, pandas 3.0 y Matplotlib 3.11 (datos y gráficos).

**6.3, Tabla II (Software).** Reemplazar "por definir" por:

> Python 3 en un entorno virtual; código y resultados en el repositorio del grupo (`03-simulacion/`).

**6.4.6, al final.** Reemplazar "(valores iniciales: 30 réplicas de 1 000 h con 100 h de calentamiento, ajustables al implementar el código)" por:

> Se ejecutaron 30 réplicas independientes de 1 000 h cada una; las primeras 100 h de cada réplica se descartan como calentamiento, por lo que los indicadores se miden sobre 900 h. Cada réplica usa una semilla distinta derivada de una semilla base (2026), de modo que los resultados son reproducibles. La utilización y la longitud de cola se calculan como promedios ponderados en el tiempo, y el tiempo de espera como el promedio de las sillas que ingresaron a cada estación después del calentamiento.

**6.4.10 y 6.5.** El error porcentual se cita como "ecuación (8)", pero corresponde a la **ecuación (15)**.

---

## 7.1 Resultados del objetivo específico 1

Se implementó en Python un modelo de eventos discretos de la línea de producción de sillas con las cuatro estaciones en serie y los parámetros de la Tabla V. En la línea base (E1) se completaron en promedio 2 698,4 sillas por réplica (desviación estándar de 52,7) durante las 900 h medidas, lo que equivale a una producción de 2,998 sillas/h. Este valor coincide con la tasa de llegadas (λ = 3 sillas/h): la línea es estable y entrega todo lo que recibe, porque ninguna estación supera su capacidad. La Tabla VIII resume los indicadores de cada estación.

Tabla VIII. Resultados simulados de la línea base frente a los valores teóricos (promedio ± desviación estándar de 30 réplicas)

| Estación | Ci (sillas/h) | ρi simulado | ρi teórico | Error ρ (%) | Lq simulado | Lq teórico | Error Lq (%) | Wq simulado (min) | Wq teórico (min) | Error Wq (%) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Corte | 7,50 | 39,8 % ± 0,9 | 40,0 % | 0,52 | 0,27 ± 0,03 | 0,27 | 0,13 | 5,3 ± 0,6 | 5,3 | 0,18 |
| Lijado | 6,00 | 49,8 % ± 1,4 | 50,0 % | 0,36 | 0,50 ± 0,06 | 0,50 | 0,18 | 10,0 ± 1,1 | 10,0 | 0,13 |
| Ensamblaje | 4,00 | 75,1 % ± 2,3 | 75,0 % | 0,14 | 2,27 ± 0,42 | 2,25 | 1,06 | 45,4 ± 7,9 | 45,0 | 0,95 |
| Acabado | 5,00 | 60,0 % ± 1,9 | 60,0 % | 0,01 | 0,91 ± 0,13 | 0,90 | 1,26 | 18,2 ± 2,5 | 18,0 | 1,11 |

La estación de ensamblaje es el cuello de botella de la línea. Tiene la menor capacidad (4 sillas/h, ecuación (4)) y la mayor utilización simulada (75,1 %), y además acumula la cola más larga (2,27 sillas en promedio) y la mayor espera (45,4 min por silla). Esa espera es 2,5 veces la de acabado, que es la segunda estación más cargada. Del tiempo total de flujo de una silla (124,0 ± 10,3 min, frente a 123,3 min teóricos), cerca de 60 min (45,4 min de espera y 15 min de proceso), es decir casi la mitad, transcurren en ensamblaje. La simulación confirma así el cuello de botella nominal de la sección 6.4.5: la estación que limita la producción es la misma que predice el cálculo de capacidad.

El modelo reproduce los valores teóricos de colas. El error porcentual (ecuación (15)) es menor a 0,6 % en la utilización y menor a 1,3 % en Lq y Wq en todas las estaciones. Las diferencias más grandes aparecen en ensamblaje y acabado, donde la alta utilización vuelve más variables las colas (la desviación estándar de Wq en ensamblaje es de 7,9 min). La Ley de Little (ecuación (6)) también se cumple: por ejemplo, en ensamblaje λWq = 2,998 × 45,4/60 = 2,27 sillas, igual al Lq medido. Esto indica que el modelo es internamente coherente y puede usarse para evaluar los escenarios de mejora del objetivo 2. La Figura 1 compara la utilización y la espera simuladas con las teóricas.

Figura 1. Utilización y tiempo medio de espera por estación en la línea base: simulación (promedio y desviación estándar de 30 réplicas) frente al modelo teórico. *(Insertar `03-simulacion/graficos/base.png`.)*

La cola también se analiza como porcentaje del tiempo en que está ocupada, es decir, con al menos una silla esperando. Los valores simulados fueron 15,9 % en corte, 24,9 % en lijado, 56,4 % en ensamblaje y 36,1 % en acabado; los teóricos `P(N > 1) = ρ²` son 16,0 %, 25,0 %, 56,3 % y 36,0 %, respectivamente. En ensamblaje, el percentil 90 de la longitud de la cola fue 6,7 sillas: durante el 10 % del tiempo hubo siete o más sillas esperando. Esto confirma que el cuello de botella no solo tiene la espera media más alta, sino también la cola más persistente y variable.

## Escenarios E2 y E3

Los dos escenarios de mejora cambian solo el ensamblaje, siempre con un operario: E2 lo
lleva a 12 min y E3 a 10 min. La producción se mantiene en 3 sillas/h en ambos porque la
línea sigue entregando todo lo que llega. La Tabla compara el ensamblaje con el acabado,
que es la estación que queda como límite cuando el ensamblaje deja de serlo.

| Escenario | Ensamblaje: ρ / Lq / Wq | Acabado: ρ / Lq / Wq | Flujo simulado (teórico) |
| --- | :---: | :---: | :---: |
| E2 (12 min) | 59,8 % / 0,87 / 17,3 min | 59,8 % / 0,89 / 17,7 min | 92,2 min (93,3 min) |
| E3 (10 min) | 49,7 % / 0,48 / 9,7 min | 59,6 % / 0,87 / 17,5 min | 82,2 min (83,3 min) |

En E2, ensamblaje y acabado empatan en 60 % de utilización y 18,0 min de espera teórica.
En E3 el cuello de botella pasa a acabado (60 %), mientras ensamblaje baja al 50 %. El
error mayor es 4,07 % (`Wq` de ensamblaje en E2); todas las demás estaciones quedan por
debajo del 3,3 %. La Ley de Little se cumple en los tres escenarios con un error menor al
0,2 % sobre el total de la línea.

## Figuras complementarias

El código genera, además de la Figura 1, las siguientes figuras de apoyo:

- `graficos/cola-base.png`: evolución de la longitud de la cola durante la primera réplica, con el calentamiento sombreado y los valores medio y teórico de `Lq`.
- `graficos/utilizacion-cola-base.png`: porcentaje del tiempo con cola y longitud media `Lq`, comparados con la teoría M/M/1.
- `graficos/distribucion-cola-base.png`: distribución del tiempo según la cantidad de sillas esperando.
- `graficos/replicas-base.png`: cajas de `ρ`, `Lq` y `Wq` para las 30 réplicas.
- `graficos/flujo-base.png`: composición del tiempo total de flujo (servicio más espera) por estación.
- `graficos/escenarios.png`: comparación de ensamblaje y acabado (ρ, `Lq` y `Wq`) en E1, E2 y E3, con el valor teórico de cada uno.
