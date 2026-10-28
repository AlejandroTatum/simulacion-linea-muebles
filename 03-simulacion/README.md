# Simulación de una línea de producción de muebles con SimPy

| Campo | Detalle |
| --- | --- |
| Asignatura | Simulación |
| Ciclo | 5.º ciclo - FEIRNNR, Carrera de Computación |
| Práctica | Trabajo grupal de simulación |
| Docente | José O. Guamán Q. |
| Integrantes | Victor Roa, Francis Valdiviezo, Cael Soto, Jimmy Ontaneda, Alejandro Padilla |

## 1. Descripción del proyecto

El programa simula una línea de fabricación de sillas con cuatro estaciones en serie:
**corte → lijado → ensamblaje → acabado**. Las sillas llegan al azar, esperan en una cola
FIFO y son atendidas por uno o más operarios en cada estación.

**Propósito:** comparar los indicadores de la simulación con los valores teóricos del
modelo M/M/c y encontrar la estación que limita la producción.

**Supuestos del modelo:**

- Llegadas de Poisson con tasa `λ` sillas por hora.
- Tiempos de servicio exponenciales con media `ti` minutos.
- Cola FIFO sin límite en cada estación.
- Cada operario atiende una silla a la vez.
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

| Medida | Significado | Fórmula |
| --- | --- | --- |
| `ρ` | Ocupación de la estación | `λ / (c · μ)` |
| `Lq` | Sillas esperando en cola | M/M/c |
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
| `resumen-base.csv` | Promedios, desviación, teoría M/M/c, error porcentual y Ley de Little. |
| `graficos/base.png` | Utilización y espera: simulación frente a teoría. |
| `graficos/cola-base.png` | Evolución de la cola en el tiempo (réplica 1). |
| `graficos/utilizacion-cola-base.png` | Tiempo con cola y longitud media de la cola. |
| `graficos/distribucion-cola-base.png` | Distribución de la longitud de la cola. |
| `graficos/replicas-base.png` | Variabilidad de ρ, Lq y Wq entre réplicas. |
| `graficos/flujo-base.png` | Composición del tiempo de flujo por estación. |
| `graficos/escenarios.png` | Comparación de escenarios (solo si se simulan varios). |

**Qué muestra cada gráfico:**

- **`base.png`**: utilización de cada estación y espera media `Wq`, con la teoría M/M/c al lado.
- **`cola-base.png`**: cómo cambia la longitud de la cola durante una réplica. La franja gris es el
  calentamiento y las líneas punteadas marcan `Lq` simulado y teórico.
- **`utilizacion-cola-base.png`**: porcentaje del tiempo con al menos una silla esperando
  (utilización de la cola) y longitud media `Lq`.
- **`distribucion-cola-base.png`**: porcentaje del tiempo que la cola pasa con 0, 1, 2, … sillas.
- **`replicas-base.png`**: cajas de `ρ`, `Lq` y `Wq` para ver cuánto varían las 30 réplicas.
- **`flujo-base.png`**: cuánto del tiempo total de una silla es servicio y cuánto es espera.
- **`escenarios.png`**: producción, tiempo de flujo y utilización del cuello de botella en cada
  escenario ejecutado en la misma corrida.

**Indicadores de cola:**

| Métrica | Significado |
| --- | --- |
| `cola_utilizacion` | Fracción del tiempo con al menos una silla esperando (`N > c`). |
| `cola_p90` | Percentil 90 de la longitud de la cola, ponderado por tiempo. |
| `cola_max` | Longitud máxima observada durante la ventana medida. |
| `cola_utilizacion_teorica` | `P(N > c)` del modelo M/M/c: Erlang C multiplicado por `ρ`. |
| `lq_little` | `λ · Wq` con la producción observada; es el `Lq` que predice la Ley de Little (6). |
| `error_little_pct` | Diferencia entre `Lq` medido y `lq_little` con la ecuación (15). |

En la terminal se muestra el resumen por estación, la producción por hora, el tiempo de
flujo y el cuello de botella.

### 4.3 Ejecutar otros escenarios

```bash
python main.py --config escenarios/e2.json
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json
python main.py --config escenarios/e2.json --salida ../04-experimentos
```

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
| `recursos` | Operarios en paralelo. Entero mayor o igual que 1. |
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
│   └── teoria.py            # fórmulas M/M/c
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
└── resultados-base.md       # texto de la sección 7.1 (ya integrado en el informe)
```

Los resultados de los tres escenarios (E1, E2 y E3) están en
[`../04-experimentos/`](../04-experimentos/README.md).

- **modelo:** calcula. No imprime ni dibuja.
- **vista:** muestra tablas, gráficos y animación. No simula.
- **controlador:** lee escenarios, llama al modelo y pasa los resultados a la vista.

## 7. Información adicional

**Funcionalidades:**

- Simulación de la línea con estaciones, colas FIFO y varios operarios.
- Comparación automática con la teoría M/M/c y verificación de la Ley de Little.
- Detección del cuello de botella por utilización.
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

| Archivo | Cambio respecto de la base |
| --- | --- |
| `escenarios/base.json` | Línea base. |
| `escenarios/e2.json` | Ensamblaje con 2 operarios. |
| `escenarios/e3.json` | Ensamblaje con tiempo medio de 10 min. |
