# Modelo matemático de la línea de producción de muebles

| Campo | Detalle |
| --- | --- |
| Asignatura | Simulación |
| Ciclo | 5.º ciclo - FEIRNNR, Carrera de Computación |
| Práctica | Trabajo grupal de simulación |
| Docente | José O. Guamán Q. |
| Integrantes | Victor Roa, Francis Valdiviezo, Cael Soto, Jimmy Ontaneda, Alejandro Padilla |
| Implementación | [`../03-simulacion/`](../03-simulacion/) |

## 1. Descripción del sistema

Se modela una línea de fabricación de sillas con cuatro estaciones en serie:

**Corte → Lijado → Ensamblaje → Acabado**

Cada silla recorre las estaciones en ese orden. En cada una espera en una cola FIFO
sin límite y es atendida por un operario. El objetivo es estimar la utilización, la
cola, la espera y el tiempo total de flujo, identificar el cuello de botella y comparar
los resultados con la teoría de colas M/M/1.

## 2. Entidades, recursos y eventos

| Elemento | Descripción |
| --- | --- |
| Entidad | Silla que llega al sistema y recorre las cuatro estaciones. |
| Recurso | Operario de cada estación (`c_i` operarios en paralelo). |
| Evento de llegada | Llegada de una silla con tiempo entre llegadas exponencial. |
| Evento de servicio | Inicio y fin del procesamiento en una estación. |
| Cola | Espera FIFO de las sillas que no encuentran un operario libre. |
| Variables de estado | Sillas en cola, operarios ocupados, sillas terminadas y tiempos de espera. |

En todos los escenarios del informe se usa **un operario por estación** (`c_i = 1`).
El simulador admite más operarios, pero la comparación teórica implementada es M/M/1.

## 3. Supuestos

- Las llegadas siguen un proceso de Poisson con tasa `λ` sillas por hora.
- Los tiempos de servicio son exponenciales con media `t_i` minutos.
- La disciplina de cola es FIFO y no tiene límite de capacidad.
- Cada operario atiende una sola silla a la vez.
- No hay fallas, turnos, transporte, retrabajo ni tiempos de preparación.
- La línea comienza vacía y se descarta un periodo de calentamiento.
- Los parámetros son supuestos académicos; no provienen de datos reales.

## 4. Parámetros

### Línea base (E1)

| Estación | Operarios `c_i` | Tiempo medio `t_i` (min/silla) |
| --- | :---: | :---: |
| Corte | 1 | 8 |
| Lijado | 1 | 10 |
| Ensamblaje | 1 | 15 |
| Acabado | 1 | 12 |

Tasa de llegadas: `λ = 3` sillas/h.

Configuración de la corrida: **30 réplicas independientes** de **1 000 h**, con
**100 h de calentamiento** descartadas y semilla base **2026**. La ventana medida es
de 900 h por réplica.

### Escenarios

| Escenario | Cambio respecto de E1 |
| --- | --- |
| E1 - Base | Ensamblaje con `t_3 = 15` min. |
| E2 | Ensamblaje con `t_3 = 12` min. |
| E3 | Ensamblaje con `t_3 = 10` min. |

Todos los escenarios mantienen `c_i = 1`, `λ = 3` sillas/h y los mismos tiempos de
corte, lijado y acabado.

## 5. Modelo matemático

### 5.1 Capacidad y utilización

Para cada estación `i`:

```text
μ_i = 60 / t_i              (sillas/h que atiende un operario)
C_i = c_i · μ_i             (capacidad de la estación, sillas/h)
ρ_i = λ / (c_i · μ_i)       (utilización)
```

Con `c_i = 1`, la utilización teórica es `ρ_i = λ / μ_i`. Para que la estación sea
estable se requiere `ρ_i < 1`.

### 5.2 Modelo M/M/1

Cada estación se aproxima como una cola M/M/1. Con `ρ = λ/μ`:

```text
Lq = ρ² / (1 − ρ)           (sillas esperando en cola)
Wq = Lq / λ                 (espera media en cola, en horas)
W  = Wq + 1/μ               (tiempo total en la estación, en horas)
L  = λ · W                  (sillas en el sistema)
P(N > 1) = ρ²               (fracción del tiempo con al menos una silla esperando)
```

El tiempo de flujo teórico de una silla es la suma de los tiempos `W` de las cuatro
estaciones.

### 5.3 Ley de Little

La Ley de Little se comprueba con la tasa efectiva observada:

```text
Lq ≈ λ_efectiva · Wq
```

En el código se usa `lq_little = throughput · Wq / 60` por estación y también para
toda la línea, sumando las esperas de las estaciones.

### 5.4 Error porcentual

La separación entre el valor simulado y el teórico se calcula como:

```text
error (%) = |valor_simulado − valor_teórico| / valor_teórico × 100
```

### 5.5 Cuello de botella

Se identifica como la estación con mayor utilización media simulada. En caso de
empate, se conserva la primera estación en el orden de la línea.

## 6. Indicadores de salida

| Indicador | Descripción |
| --- | --- |
| `ρ_i` | Utilización media de cada estación. |
| `Lq_i` | Longitud media de la cola. |
| `Wq_i` | Espera media en cola, en minutos. |
| `W_i` | Tiempo medio en la estación, en minutos. |
| `cola_utilizacion` | Porcentaje del tiempo con al menos una silla esperando. |
| `cola_p90` | Percentil 90 de la longitud de la cola, ponderado por tiempo. |
| `throughput_h` | Sillas terminadas por hora. |
| `flujo_min` | Tiempo total medio de una silla en la línea. |
| `cuello` | Estación con mayor utilización. |

## 7. Resultados esperados de la línea base

| Estación | ρ simulado | ρ teórico | Lq simulado | Lq teórico | Wq simulado (min) | Wq teórico (min) |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| Corte | 39,8 % | 40,0 % | 0,27 | 0,27 | 5,3 | 5,3 |
| Lijado | 49,8 % | 50,0 % | 0,50 | 0,50 | 10,0 | 10,0 |
| Ensamblaje | 75,1 % | 75,0 % | 2,27 | 2,25 | 45,4 | 45,0 |
| Acabado | 60,0 % | 60,0 % | 0,91 | 0,90 | 18,2 | 18,0 |

El cuello de botella de E1 es **Ensamblaje**. La producción simulada es
**2,998 sillas/h** y el tiempo total de flujo es **124,0 min** frente a **123,3 min**
teóricos.

## 8. Implementación

El modelo está implementado en Python con SimPy y se organiza en modelo, vista y
controlador:

| Archivo | Función |
| --- | --- |
| [`../03-simulacion/modelo/teoria.py`](../03-simulacion/modelo/teoria.py) | Fórmulas M/M/1 y flujo teórico. |
| [`../03-simulacion/modelo/simulacion.py`](../03-simulacion/modelo/simulacion.py) | Estaciones, recursos, colas y réplicas. |
| [`../03-simulacion/modelo/configuracion.py`](../03-simulacion/modelo/configuracion.py) | Lectura y validación de escenarios JSON. |
| [`../03-simulacion/escenarios/`](../03-simulacion/escenarios/) | Parámetros de E1, E2 y E3. |

Los resultados experimentales están en
[`../04-experimentos/`](../04-experimentos/), y la explicación completa del programa
en [`../03-simulacion/README.md`](../03-simulacion/README.md).

## 9. Reproducibilidad

La misma semilla produce los mismos resultados. Cada réplica deriva su semilla de la
semilla base del escenario. Los resultados del informe se generan con:

```bash
cd 03-simulacion
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json \
  --salida ../04-experimentos
```

## 10. Relación con el informe

Este documento resume el modelo que se describe en la metodología y en el modelo
matemático del informe. Las ecuaciones de capacidad, utilización, M/M/1, Ley de Little
y error porcentual son las que utiliza el programa para comparar la simulación con la
teoría. No se utiliza M/M/c ni Erlang C.
