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

Desde `03-simulacion/`:

```bash
python main.py
```

Esto ejecuta `escenarios/base.json` y escribe:

| Archivo | Contenido |
| --- | --- |
| `resultados-base.csv` | Una fila por réplica y estación. |
| `resumen-base.csv` | Promedios, desviación, teoría M/M/c y error porcentual. |
| `graficos/base.png` | Utilización y espera: simulación frente a teoría. |

En la terminal se muestra el resumen por estación, la producción por hora, el tiempo de
flujo y el cuello de botella.

**Otros escenarios:**

```bash
python main.py --config escenarios/e2.json
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json
python main.py --config escenarios/e2.json --salida ../04-experimentos
```

`--salida` cambia la carpeta de resultados y gráficos. Los escenarios se validan todos
antes de simular; si uno tiene un error, no se escribe nada.

**Pruebas:**

```bash
python -m pytest
```

También se pueden ejecutar desde la raíz del repositorio con el mismo comando.

**Animación del taller:**

```bash
python animacion.py
python animacion.py --config escenarios/e2.json --horas 24
python animacion.py --guardar graficos/base.gif
```

La animación usa una sola réplica y sirve para explicar la dinámica; los números del
informe salen de `main.py`. `--guardar` funciona sin entorno gráfico.

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
└── resultados-base.md
```

- **modelo:** calcula. No imprime ni dibuja.
- **vista:** muestra tablas, gráficos y animación. No simula.
- **controlador:** lee escenarios, llama al modelo y pasa los resultados a la vista.

## 7. Información adicional

**Funcionalidades:**

- Simulación de la línea con estaciones, colas FIFO y varios operarios.
- Comparación automática con la teoría M/M/c.
- Detección del cuello de botella por utilización.
- Resultados en CSV y gráficos PNG.
- Validación de escenarios antes de ejecutar.
- Animación del taller para una réplica.

**Resultados de la línea base:**

| Estación | ρ simulado | ρ teórico | Wq simulado (min) | Wq teórico (min) |
| --- | :---: | :---: | :---: | :---: |
| Corte | 39,8 % | 40,0 % | 5,3 | 5,3 |
| Lijado | 49,8 % | 50,0 % | 10,0 | 10,0 |
| Ensamblaje | 75,1 % | 75,0 % | 45,4 | 45,0 |
| Acabado | 60,0 % | 60,0 % | 18,2 | 18,0 |

El cuello de botella es **Ensamblaje**. El detalle y el texto de apoyo están en
[`resultados-base.md`](resultados-base.md).

![Utilización y espera por estación](graficos/base.png)

**Escenarios:**

| Archivo | Cambio respecto de la base |
| --- | --- |
| `escenarios/base.json` | Línea base. |
| `escenarios/e2.json` | Ensamblaje con 2 operarios. |
| `escenarios/e3.json` | Ensamblaje con tiempo medio de 10 min. |
