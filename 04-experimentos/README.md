# Experimentos E1–E3

Resultados de los tres escenarios de la Tabla VII del informe, generados con:

```bash
cd 03-simulacion
python main.py --config escenarios/base.json escenarios/e2.json escenarios/e3.json \
  --salida ../04-experimentos
```

Todos usan 30 réplicas de 1 000 h, 100 h de calentamiento, semilla base 2026 y
λ = 3 sillas/h. Solo cambia el tiempo de ensamblaje. Todos los escenarios tienen **un
operario por estación**, así que la teoría aplicable es **M/M/1**.

## Resumen en ensamblaje y en la línea

| Indicador | E1 Base | E2 (t₃ = 12 min) | E3 (t₃ = 10 min) |
| --- | :---: | :---: | :---: |
| ρ ensamblaje (sim. / teór.) | 75,1 % / 75,0 % | 59,8 % / 60,0 % | 49,7 % / 50,0 % |
| Lq ensamblaje (sim. / teór.) | 2,27 / 2,25 | 0,86 / 0,90 | 0,48 / 0,50 |
| Wq ensamblaje en min (sim. / teór.) | 45,4 / 45,0 | 17,3 / 18,0 | 9,71 / 10,0 |
| Tiempo total de flujo en min (sim. / teór.) | 124,0 / 123,3 | 92,2 / 93,3 | 82,2 / 83,3 |
| Sillas terminadas por réplica (900 h) | 2 698,4 ± 52,7 | 2 699,4 ± 56,9 | 2 689,3 ± 40,6 |
| Producción (sillas/h) | 2,998 | 2,999 | 2,988 |
| Cuello de botella simulado | Ensamblaje | Ensamblaje | Acabado |
| Capacidad máxima de la línea (sillas/h) | 4,00 | 5,00 | 5,00 |
| Holgura frente a λ = 3 (sillas/h) | 1,00 | 2,00 | 2,00 |
| Error máximo frente a la teoría (ρ, Lq, Wq) | 1,3 % | 4,1 % | 3,2 % |
| Error máximo de la Ley de Little (Lq frente a λ·Wq) | 0,17 % | 0,15 % | 0,13 % |

La capacidad de la línea es `min(cᵢ · μᵢ)`, la estación más lenta. Sube de 4,00 a
5,00 sillas/h al pasar ensamblaje de 15 a 12 min, pero no vuelve a subir con 10 min porque
el nuevo cuello es acabado (5,00 sillas/h). La producción simulada se queda en ~3
sillas/h porque la demanda es λ = 3: las mejoras aumentan el techo de producción, no lo
que llega. Para superar 5 sillas/h habría que mejorar también acabado.

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
| `graficos/flujo-*.png` | Tiempo total de flujo por estación |
