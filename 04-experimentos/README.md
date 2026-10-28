# Experimentos E1–E3

Resultados de los tres escenarios de la Tabla VII del informe, generados con:

```bash
cd 03-simulacion
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json \
  --salida ../04-experimentos
```

Todos usan 30 réplicas de 1 000 h, 100 h de calentamiento, semilla base 2026 y
λ = 3 sillas/h. Solo cambia la estación de ensamblaje.

## Resumen en ensamblaje y en la línea

| Indicador | E1 Base | E2 (c₃ = 2) | E3 (t₃ = 10 min) |
| --- | :---: | :---: | :---: |
| ρ ensamblaje (sim. / teór.) | 75,1 % / 75,0 % | 37,3 % / 37,5 % | 49,7 % / 50,0 % |
| Lq ensamblaje (sim. / teór.) | 2,27 / 2,25 | 0,12 / 0,12 | 0,48 / 0,50 |
| Wq ensamblaje en min (sim. / teór.) | 45,4 / 45,0 | 2,47 / 2,45 | 9,71 / 10,0 |
| Tiempo total de flujo en min (sim. / teór.) | 124,0 / 123,3 | 81,1 / 80,8 | 82,2 / 83,3 |
| Sillas terminadas por réplica (900 h) | 2 698,4 ± 52,7 | 2 702,1 ± 48,6 | 2 689,3 ± 40,6 |
| Producción (sillas/h) | 2,998 | 3,002 | 2,988 |
| Cuello de botella simulado | Ensamblaje | Acabado | Acabado |
| Error máximo frente a la teoría (ρ, Lq, Wq) | 1,3 % | 1,6 % | 3,2 % |
| Error máximo de la Ley de Little (Lq frente a λ·Wq) | 0,20 % | 0,12 % | 0,20 % |

El detalle por estación (media, desviación estándar, valor teórico, error porcentual con la
ecuación (15) y la comprobación de la Ley de Little (6) en `lq_little` y `error_little_pct`)
está en `resumen-<escenario>.csv`. Los valores por réplica están en
`resultados-<escenario>.csv`.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `resumen-base.csv`, `resumen-e2.csv`, `resumen-e3.csv` | Indicadores por estación promediados en las 30 réplicas |
| `resultados-base.csv`, `resultados-e2.csv`, `resultados-e3.csv` | Indicadores de cada réplica |
| `graficos/escenarios.png` | Comparación de los tres escenarios |
| `graficos/<escenario>.png` | Utilización y espera simuladas frente a las teóricas |
| `graficos/cola-*.png`, `utilizacion-cola-*.png`, `distribucion-cola-*.png` | Colas por estación |
| `graficos/flujo-*.png`, `replicas-*.png` | Tiempo total de flujo y variación entre réplicas |
