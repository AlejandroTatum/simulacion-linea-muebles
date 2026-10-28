# Escenarios: aquí se cambian los valores

Todos los parámetros de la línea están en estos archivos JSON. El código Python no tiene
ningún valor de la línea escrito adentro.

| Archivo | Escenario |
| --- | --- |
| `base.json` | E1: línea base del informe (Tabla V). |
| `e2.json` | E2: dos operarios en ensamblaje (`c3 = 2`). |
| `e3.json` | E3: ensamblaje en 10 min (`t3 = 10`). |

## Qué significa cada valor

| Campo | Símbolo | Significado | Regla |
| --- | :---: | --- | --- |
| `tasa_llegadas_h` | λ | Sillas que llegan por hora. | Número mayor que 0. |
| `estaciones[i].recursos` | cᵢ | Operarios en paralelo de la estación. | Entero ≥ 1. |
| `estaciones[i].tiempo_min` | tᵢ | Tiempo medio de una silla en la estación (min). | Número mayor que 0. |
| `replicas` | — | Réplicas independientes. | Entero ≥ 1. |
| `duracion_h` | — | Horas simuladas por réplica, con el calentamiento incluido. | Número mayor que 0. |
| `calentamiento_h` | — | Horas iniciales que no se miden. | ≥ 0 y menor que `duracion_h`. |
| `semilla` | — | Semilla base; la misma semilla repite los resultados. | Entero ≥ 0. |
| `nombre` | — | Nombre que aparece en la terminal. | Texto no vacío. |

Las estaciones se recorren en el orden de la lista. Se pueden agregar o quitar estaciones;
cada una necesita `nombre`, `recursos` y `tiempo_min`.

## Cómo probar un caso nuevo

1. Copiá `base.json` con otro nombre, por ejemplo `mi_caso.json`.
2. Cambiá los valores.
3. Desde `03-simulacion/`, corré `python main.py --config escenarios/mi_caso.json`.

Para cambiar los valores sin editar archivos, usá la ventana: `python panel.py`. Su botón
**Guardar escenario** escribe `personalizado.json` en esta carpeta.
