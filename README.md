# Simulación de una línea de producción de muebles

Proyecto grupal: simulación de eventos discretos de una línea de fabricación de sillas (corte → lijado → ensamblaje → acabado), con modelo matemático, programa en Python, experimentos y un informe académico en formato IEEE.

---

## Inicio rápido

Requiere Python 3.12 o superior. Las instrucciones completas, la explicación de cada gráfica
y la solución de problemas están en [`03-simulacion/README.md`](03-simulacion/README.md).

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r 03-simulacion/requirements.txt
cd 03-simulacion
python main.py
python -m pytest
```

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r 03-simulacion\requirements.txt
cd 03-simulacion
python main.py
python -m pytest
```

Si `python` no existe, usá `python3` o el Python del entorno virtual:
`.venv/bin/python` en Linux/macOS y `.venv\Scripts\python.exe` en Windows.

Para generar la animación como GIF, sin abrir ventana:

```bash
cd 03-simulacion
python animacion.py --guardar graficos/base.gif
```

> **Nota:** si el comando `python` falla, casi siempre es porque el entorno virtual no está
> activado. Los comandos de esta guía suponen que estás dentro de `03-simulacion/`.

---

## Estado del proyecto

| Parte | Carpeta | Estado |
|---|---|:---:|
| Investigación y marco teórico | [`01-investigacion/`](01-investigacion/) | Pendiente de subir |
| Modelo matemático | [`02-modelo/`](02-modelo/) | Pendiente de subir |
| Programación y simulación | [`03-simulacion/`](03-simulacion/) | ✅ Terminado |
| Experimentos y análisis (E1, E2, E3) | [`04-experimentos/`](04-experimentos/) | Pendiente |
| Informe final (formato IEEE) | [`05-informe/`](05-informe/) | Pendiente de subir |

La coordinación del grupo se hizo fuera de GitHub; este repositorio guarda solo el código,
los datos y los documentos finales.

---

## Simulación

Línea de fabricación de sillas con cuatro estaciones en serie, cada una con su cola FIFO
sin límite y `ci` operarios que atienden una silla a la vez. Llegadas de Poisson con
λ = 3 sillas/h y tiempos de servicio exponenciales con media `ti`.

**Parámetros de la línea base (Tabla V del informe):**

| Estación | ci | ti (min/silla) |
|---|:---:|:---:|
| Corte | 1 | 8 |
| Lijado | 1 | 10 |
| Ensamblaje | 1 | 15 |
| Acabado | 1 | 12 |

**Configuración de la corrida:** línea vacía al inicio, 30 réplicas independientes con
semillas distintas, 1 000 h por réplica y 100 h de calentamiento descartadas.

**Control:** el promedio de la simulación base se acerca a la Tabla VI del informe
(por ejemplo, ensamblaje con ρ ≈ 75 % y Wq ≈ 45 min).

### Escenarios experimentales

`ci` y `ti` se cambian sin tocar el código, con los archivos JSON de `03-simulacion/escenarios/`:

| Escenario | Archivo | Cambio frente a la base |
|---|---|---|
| E1 · Línea base | `base.json` | — |
| E2 · Más recursos | `e2.json` | `c3 = 2` (dos operarios en ensamblaje) |
| E3 · Mejora de tiempos | `e3.json` | `t3 = 10` min en ensamblaje |

Para correr los tres y dejar los resultados en `04-experimentos/`:

```bash
cd 03-simulacion
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json \
  --salida ../04-experimentos
```

---

## Estructura del repositorio

```
simulacion-linea-muebles/
├── 01-investigacion/   # artículos, introducción, referencias IEEE
├── 02-modelo/          # diagrama del proceso, parámetros, ecuaciones
├── 03-simulacion/      # código Python y resultados base
│   ├── modelo/         # configuración, simulación y teoría
│   ├── vista/          # tablas, gráficos y animación
│   ├── controlador/    # une modelo y vista
│   ├── escenarios/     # archivos JSON de parámetros
│   ├── tests/          # pruebas automáticas
│   └── graficos/       # gráficas de la línea base
├── 04-experimentos/    # resultados de E1–E3, tablas y gráficos comparativos
│   └── graficos/
└── 05-informe/         # informe final (DOCX/PDF)
```
