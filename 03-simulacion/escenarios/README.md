# Escenarios: aquí se cambian los valores

Todos los parámetros de la línea están en estos archivos JSON. El código Python no tiene
ningún valor de la línea escrito adentro.

| Archivo | Escenario |
| --- | --- |
| `base.json` | E1: línea base del informe (Tabla III). |
| `e2.json` | E2: ensamblaje en 12 min, un operario (`t3 = 12`). |
| `e3.json` | E3: ensamblaje en 10 min (`t3 = 10`). |

Todos los escenarios usan **un operario por estación** (`cᵢ = 1`), que es el supuesto del
modelo M/M/1. Si se pone `recursos > 1`, la simulación corre y la animación dibuja varios
operarios, pero la comparación teórica aparece como `—` porque M/M/1 no aplica.

## Qué significa cada valor

| Campo | Símbolo | Significado | Regla |
| --- | :---: | --- | --- |
| `tasa_llegadas_h` | λ | Muebles que llegan por hora. | Número mayor que 0. |
| `estaciones[i].recursos` | cᵢ | Operarios en paralelo de la estación. | Entero ≥ 1. |
| `estaciones[i].tiempo_min` | tᵢ | Tiempo medio de un mueble en la estación (min). | Número mayor que 0. |
| `replicas` | — | Réplicas independientes. | Entero ≥ 1. |
| `duracion_h` | — | Horas simuladas por réplica, con el calentamiento incluido. | Número mayor que 0. |
| `calentamiento_h` | — | Horas iniciales que no se miden. | ≥ 0 y menor que `duracion_h`. |
| `semilla` | — | Semilla base; la misma semilla repite los resultados. | Entero ≥ 0. |
| `nombre` | — | Nombre que aparece en la terminal. | Texto no vacío. |

Además de la columna "Regla", hay tres topes de carga que protegen al equipo de valores
exagerados. Si se superan, `main.py` y el panel rechazan el escenario antes de simular, con
un mensaje que nombra el campo, el valor y el límite:

| Tope | Límite | Base (E1, E2, E3) |
| --- | :---: | :---: |
| `replicas` | 200 | 30 |
| `tasa_llegadas_h × duracion_h` (muebles por réplica) | 200 000 | 3 000 |
| `tasa_llegadas_h × duracion_h × replicas` (muebles en total) | 1 000 000 | 90 000 |

Están en las constantes `MAX_REPLICAS`, `MAX_MUEBLES_POR_REPLICA` y `MAX_MUEBLES_TOTALES` de
`modelo/configuracion.py`. En el panel, "Horas a animar" tiene su propio tope de 72 horas.

## Qué pasa con valores extremos

- **Línea inestable** (`tasa_llegadas_h` mayor o igual que la capacidad de la estación más
  lenta): el escenario no se rechaza. Se simula, se avisa con `Línea inestable: λ = ...` y
  el cuello de botella es la estación de menor capacidad. La cola crece sin límite, así que
  los tiempos dependen de `duracion_h` y no hay valor teórico (`—`).
- **Sin datos**: si no se mide ninguna espera ni ningún flujo (por ejemplo, `duracion_h`
  muy corta), el resultado es "sin datos" y se muestra `—`, no `0`. El error porcentual de
  esa fila también es `—`.

Las estaciones se recorren en el orden de la lista. Se pueden agregar o quitar estaciones;
cada una necesita `nombre`, `recursos` y `tiempo_min`.

## Cómo probar un caso nuevo

1. Copiá `base.json` con otro nombre, por ejemplo `mi_caso.json`.
2. Cambiá los valores.
3. Desde `03-simulacion/`, corré `python main.py --config escenarios/mi_caso.json`.

Para cambiar los valores sin editar archivos, usá la ventana: `python panel.py`. Su botón
**Guardar escenario** escribe `personalizado.json` en esta carpeta.
