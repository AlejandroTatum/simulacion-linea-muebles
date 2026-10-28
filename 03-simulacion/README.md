# Simulación de una línea de producción de muebles con SimPy

| Campo | Detalle |
| --- | --- |
| Asignatura | Simulación |
| Ciclo | 5.º ciclo - FEIRNNR, Carrera de Computación |
| Práctica | Trabajo grupal de simulación |
| Docente | José O. Guamán Q. |
| Integrantes | Integrante 1, Integrante 2, Integrante 3, Integrante 4, Integrante 5 |

## 1. Descripción del proyecto

El programa simula una línea de fabricación de sillas con cuatro estaciones en serie:
**corte → lijado → ensamblaje → acabado**. Las sillas llegan al azar, esperan en una cola
FIFO y son atendidas por un operario en cada estación.

**Propósito:** comparar los indicadores de la simulación con los valores teóricos del
modelo M/M/1 y encontrar la estación que limita la producción.

**Supuestos del modelo:**

- Llegadas de Poisson con tasa `λ` sillas por hora.
- Tiempos de servicio exponenciales con media `ti` minutos.
- Cola FIFO sin límite en cada estación.
- Un operario por estación (`c = 1`) en todos los escenarios.
- No hay fallas, turnos, transporte ni retrabajo.

**Parámetros de la línea base:**

| Estación | Operarios `ci` | Tiempo medio `ti` (min/silla) |
| --- | :---: | :---: |
| Corte | 1 | 8 |
| Lijado | 1 | 10 |
| Ensamblaje | 1 | 15 |
| Acabado | 1 | 12 |

Tasa de llegadas: `λ = 3` sillas/h. Cada réplica simula 1 000 h y descarta las primeras
100 h de calentamiento.

| Medida | Significado | Fórmula M/M/1 |
| --- | --- | --- |
| `ρ` | Ocupación de la estación | `λ / μ` |
| `Lq` | Sillas esperando en cola | `ρ² / (1 − ρ)` |
| `Wq` | Espera media en cola | `Lq / λ` |
| `W` | Tiempo en la estación | `Wq + 1/μ` |

## 2. Tecnologías utilizadas

- Python 3.12 o superior
- SimPy (eventos discretos y recursos)
- NumPy (números aleatorios)
- pandas (resultados en CSV)
- Matplotlib (gráficos y animación)
- pytest (pruebas)
- Organización en modelo, vista y controlador (MVC)

## 3. Instalación

Las dependencias están fijadas en `requirements.txt`.

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
cd simulacion-linea-muebles
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 03-simulacion/requirements.txt
```

**macOS:**

```bash
cd simulacion-linea-muebles
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 03-simulacion/requirements.txt
```

**Windows PowerShell:**

```powershell
cd simulacion-linea-muebles
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r 03-simulacion\requirements.txt
```

Si PowerShell bloquea la activación, ejecutar una vez:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

En Windows CMD la activación es `.venv\Scripts\activate.bat`.

Para ver la animación en Linux hace falta Tk (`sudo apt install python3-tk`). En WSL o en
un servidor sin pantalla, usar `--guardar` como se explica en la sección 4.

## 4. Uso

### 4.1 Activar el entorno virtual

Todos los comandos de esta sección se ejecutan con el Python del entorno virtual.
Desde la raíz del repositorio:

**Linux / macOS:**

```bash
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**

```bat
.venv\Scripts\activate.bat
```

Comprobar que quedó activo:

```bash
python --version
```

Debe mostrar Python 3.12 o superior. Si `python` no existe, usá `python3` o directamente
el Python del entorno: `.venv/bin/python` en Linux/macOS y `.venv\Scripts\python.exe` en Windows.

### 4.2 Ejecutar la simulación base

```bash
cd 03-simulacion
python main.py
```

Si no activaste el entorno, desde `03-simulacion/`:

```bash
../.venv/bin/python main.py
```

En Windows:

```powershell
..\.venv\Scripts\python.exe main.py
```

Esto ejecuta `escenarios/base.json` y escribe:

| Archivo | Contenido |
| --- | --- |
| `resultados-base.csv` | Una fila por réplica y estación. |
| `resumen-base.csv` | Promedios, desviación, teoría M/M/1 y error porcentual. |
| `linea-base.csv` | Producción, flujo total y Ley de Little de la línea. |
| `graficos/base.png` | Utilización y espera: simulación frente a teoría. |
| `graficos/cola-base.png` | Evolución de la cola en el tiempo (réplica 1). |
| `graficos/utilizacion-cola-base.png` | Tiempo con cola y longitud media de la cola. |
| `graficos/distribucion-cola-base.png` | Distribución de la longitud de la cola. |
| `graficos/replicas-base.png` | Variabilidad de ρ, Lq y Wq entre réplicas. |
| `graficos/flujo-base.png` | Composición del tiempo de flujo por estación. |
| `graficos/escenarios.png` | Comparación de escenarios (solo si se simulan varios). |

**Qué muestra cada gráfico:**

- **`base.png`**: utilización de cada estación y espera media `Wq`, con la teoría M/M/1 al lado.
- **`cola-base.png`**: cómo cambia la longitud de la cola durante una réplica. La franja gris es el
  calentamiento y las líneas punteadas marcan `Lq` simulado y teórico.
- **`utilizacion-cola-base.png`**: porcentaje del tiempo con al menos una silla esperando
  (utilización de la cola) y longitud media `Lq`.
- **`distribucion-cola-base.png`**: porcentaje del tiempo que la cola pasa con 0, 1, 2, … sillas.
- **`replicas-base.png`**: cajas de `ρ`, `Lq` y `Wq` para ver cuánto varían las 30 réplicas.
- **`flujo-base.png`**: cuánto del tiempo total de una silla es servicio y cuánto es espera.
- **`escenarios.png`**: utilización, `Lq` y `Wq` de ensamblaje y acabado en E1, E2 y E3,
  con el valor teórico marcado con un rombo.

**Indicadores de cola:**

| Métrica | Significado |
| --- | --- |
| `cola_utilizacion` | Fracción del tiempo con al menos una silla esperando (`N > 1`). |
| `cola_p90` | Percentil 90 de la longitud de la cola, ponderado por tiempo. |
| `cola_max` | Longitud máxima observada durante la ventana medida. |
| `cola_utilizacion_teorica` | `P(N > 1) = ρ²` del modelo M/M/1. |
| `lq_little` | `λ_efectiva · Wq` para comprobar la Ley de Little. |
| `error_little_pct` | Error porcentual entre `Lq` medido y el de la Ley de Little. |

En la terminal se muestra el resumen por estación, la producción por hora, el tiempo de
flujo, la Ley de Little y el cuello de botella.

### 4.3 Ejecutar otros escenarios

```bash
python main.py --config escenarios/e2.json
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json
python main.py --config escenarios/e2.json --salida ../04-experimentos
```

| Archivo | Escenario | Diferencia con E1 |
| --- | --- | --- |
| `escenarios/base.json` | E1 (base) | — |
| `escenarios/e2.json` | E2 | Ensamblaje en 12 min |
| `escenarios/e3.json` | E3 | Ensamblaje en 10 min |

Los tres usan un solo operario por estación (`c = 1`), `λ = 3` sillas/h y los mismos
corte, lijado y acabado de E1. Los resultados llevan el nombre del archivo:
`resumen-e2.csv`, `linea-e2.csv`, `graficos/e2.png`, etc.

`--salida` cambia la carpeta de resultados y gráficos. Los escenarios se validan todos
antes de simular; si uno tiene un error, no se escribe nada. Cuando se simulan varios
escenarios en la misma corrida también se genera `graficos/escenarios.png`.

### 4.4 Ejecutar las pruebas

```bash
python -m pytest
```

Desde la raíz del repositorio:

```bash
python -m pytest 03-simulacion
```

### 4.5 Ver la animación del taller

```bash
python animacion.py
python animacion.py --config escenarios/e2.json --horas 24
python animacion.py --guardar graficos/base.gif
```

La animación usa una sola réplica y sirve para explicar la dinámica; los números del
informe salen de `main.py`. Las opciones principales son:

- `--horas`: horas simuladas a mostrar (por defecto 8).
- `--paso`: minutos simulados por cuadro (por defecto 5).
- `--semilla`: semilla de la réplica.
- `--guardar`: guarda un GIF en vez de abrir una ventana.

Para una prueba rápida sin abrir ventana:

```bash
python animacion.py --horas 2 --paso 10 --guardar graficos/prueba.gif
```

En Linux, para abrir la ventana hace falta Tk (`sudo apt install python3-tk`). En WSL,
SSH o servidores sin pantalla, usá siempre `--guardar`.

### 4.6 Solución de problemas

| Problema | Causa probable | Solución |
| --- | --- | --- |
| `python: command not found` | El entorno virtual no está activado | `source .venv/bin/activate` o usá `../.venv/bin/python` |
| `No module named 'simpy'` o `'matplotlib'` | Estás usando el Python del sistema | Activá el venv o usá el Python de `.venv` |
| `No module named 'vista'` o `No such file: animacion.py` | Estás en la carpeta equivocada | `cd 03-simulacion` |
| `TclError: no display name and no $DISPLAY` | No hay entorno gráfico | Usá `--guardar graficos/base.gif` |
| La ventana se abre y la terminal queda ocupada | La animación sigue en ejecución | Cerrá la ventana para terminar |
| El GIF tarda mucho | Son muchos cuadros | Probá `--horas 2 --paso 10` |
| `No such file: escenarios/e2.json` | Ruta relativa desde otra carpeta | Ejecutá desde `03-simulacion` o pasá la ruta completa |

Si el error persiste, copiá el mensaje completo y el comando que ejecutaste.

## 5. Configuración

Los escenarios están en `escenarios/`. No hay parámetros de la línea escritos dentro del
código.

| Campo | Significado |
| --- | --- |
| `nombre` | Nombre que aparece en la terminal y en los resultados. |
| `tasa_llegadas_h` | `λ`, sillas que llegan por hora. |
| `estaciones` | Lista ordenada de estaciones. |
| `replicas` | Cantidad de réplicas independientes. |
| `duracion_h` | Horas simuladas por réplica, incluido el calentamiento. |
| `calentamiento_h` | Horas iniciales que no se miden. |
| `semilla` | Semilla base para repetir los resultados. |

Cada estación tiene:

| Campo | Significado |
| --- | --- |
| `nombre` | Nombre de la estación. |
| `recursos` | Operarios en paralelo. En los escenarios del informe siempre es 1. |
| `tiempo_min` | Tiempo medio de servicio, en minutos. |

Para crear un escenario, copiar `escenarios/base.json`, cambiar los valores y pasar el
archivo con `--config`. El programa rechaza campos faltantes, tipos incorrectos, nombres
repetidos, valores negativos y estaciones sin operarios.

## 6. Estructura del proyecto

```text
03-simulacion/
├── main.py                  # entrada: simula uno o varios escenarios
├── animacion.py             # entrada de la animación
├── requirements.txt
├── modelo/
│   ├── configuracion.py     # lee y valida los JSON
│   ├── simulacion.py        # Estacion y SimulacionLinea (SimPy)
│   └── teoria.py            # fórmulas M/M/1
├── vista/
│   ├── tablas.py            # salida de la terminal
│   ├── graficas.py          # gráficos PNG
│   └── animacion.py         # dibujo del taller
├── controlador/
│   └── controlador.py       # une modelo y vista
├── escenarios/
│   ├── base.json
│   ├── e2.json
│   └── e3.json
├── tests/
├── fuentes/                 # fuente Inter y su licencia
├── graficos/
├── resultados-base.csv
├── resumen-base.csv
└── resultados-base.md
```

- **modelo:** calcula. No imprime ni dibuja.
- **vista:** muestra tablas, gráficos y animación. No simula.
- **controlador:** lee escenarios, llama al modelo y pasa los resultados a la vista.

## 7. Información adicional

**Funcionalidades:**

- Simulación de la línea con estaciones, colas FIFO y un operario por estación.
- Comparación automática con la teoría M/M/1.
- Detección del cuello de botella por utilización.
- Verificación de la Ley de Little y del tiempo total de flujo por escenario.
- Indicadores de cola: utilización, percentil 90 y máximo.
- Resultados en CSV y gráficos PNG.
- Gráficos de evolución, distribución, variabilidad, flujo y comparación de escenarios.
- Validación de escenarios antes de ejecutar.
- Animación del taller para una réplica.

**Resultados de la línea base:**

| Estación | ρ simulado | ρ teórico | Cola ocupada | Wq simulado (min) | Wq teórico (min) |
| --- | :---: | :---: | :---: | :---: | :---: |
| Corte | 39,8 % | 40,0 % | 15,9 % | 5,3 | 5,3 |
| Lijado | 49,8 % | 50,0 % | 24,9 % | 10,0 | 10,0 |
| Ensamblaje | 75,1 % | 75,0 % | 56,4 % | 45,4 | 45,0 |
| Acabado | 60,0 % | 60,0 % | 36,1 % | 18,2 | 18,0 |

El cuello de botella es **Ensamblaje**. Su cola permanece ocupada el 56,4 % del tiempo y es la que
más se acerca a su valor teórico (56,3 %). El detalle y el texto de apoyo están en
[`resultados-base.md`](resultados-base.md).

![Utilización y espera por estación](graficos/base.png)

![Evolución de la cola en la réplica 1](graficos/cola-base.png)

![Utilización y longitud media de la cola](graficos/utilizacion-cola-base.png)

![Distribución de la longitud de la cola](graficos/distribucion-cola-base.png)

![Variabilidad entre réplicas](graficos/replicas-base.png)

![Composición del tiempo de flujo](graficos/flujo-base.png)

**Escenarios:**

| Archivo | Escenario | Cambio respecto de E1 | Flujo teórico |
| --- | --- | --- | :---: |
| `escenarios/base.json` | E1 | Línea base. | 123,3 min |
| `escenarios/e2.json` | E2 | Ensamblaje en 12 min. | 93,3 min |
| `escenarios/e3.json` | E3 | Ensamblaje en 10 min. | 83,3 min |

En E1 el cuello de botella es ensamblaje (75 %). En E2, ensamblaje y acabado empatan
al 60 %; en E3 el cuello pasa a acabado (60 %) porque ensamblaje baja al 50 %. La
producción se mantiene en 3 sillas/h en los tres escenarios porque la línea entrega
todo lo que llega.

![Ensamblaje y acabado en cada escenario](graficos/escenarios.png)

**Resumen numérico por escenario:**

| Escenario | ρ ensamblaje | Lq ensamblaje | Wq ensamblaje (min) | Error máx. ρ/Lq/Wq |
| --- | :---: | :---: | :---: | :---: |
| E1 | 75,1 % | 2,27 | 45,4 | 1,26 % |
| E2 | 59,8 % | 0,87 | 17,3 | 4,07 % |
| E3 | 49,7 % | 0,48 | 9,7 | 3,22 % |

El error máximo de E2 (4,07 % en `Wq` de ensamblaje) está dentro del 5 %; el resto de
las estaciones queda por debajo del 3,3 %. Los valores por estación están en
`resumen-e2.csv` y `resumen-e3.csv`, y la Ley de Little en `linea-e2.csv` y `linea-e3.csv`.
