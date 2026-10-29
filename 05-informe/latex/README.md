# Informe final en LaTeX

Esta carpeta contiene el código fuente LaTeX del informe final en formato IEEE
(`IEEEtran`, modo conferencia). `main.tex` es equivalente al documento de
[`../documento/`](../documento/): mismo título, secciones I a VII, tablas, ecuaciones,
figuras, referencias y anexos. El entregable es el PDF/DOCX de `documento/`; esta carpeta
permite regenerar el informe desde LaTeX.

```text
05-informe/latex/
├── main.tex          # informe completo (secciones I-VII, referencias y anexos A-C)
├── referencias.bib   # bibliografía del informe (14 entradas)
├── README.md         # estas instrucciones
└── imagenes/         # gráficas usadas por main.tex y copias de las demás
```

## Compilación

Con TeX Live instalado:

```bash
cd 05-informe/latex
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

También se puede usar:

```bash
latexmk -pdf main.tex
```

El resultado es `main.pdf`. Los archivos de compilación (`.aux`, `.bbl`, `.log`, `.pdf`,
etc.) no se guardan en el repositorio.

Si se compila en Overleaf, subir `main.tex`, `referencias.bib` y la carpeta
`imagenes/`. `main.tex` usa esta copia local con `\bibliography{referencias}`, así que no
hay que cambiar ninguna ruta.

## Referencias

`referencias.bib` es la bibliografía del informe: contiene las 10 obras citadas en el texto
(numeradas [1]–[10] por orden de cita) y las 4 de documentación técnica de la sección
Bibliografía. Esta última se escribe a mano en `main.tex` y no se cita, así que no altera la
numeración.

La lista original de la investigación sigue en `01-investigacion/referencias.bib`
(8 entradas); no se mantiene sincronizada con esta. Si se agregan o corrigen referencias del
informe, editar solo `referencias.bib` de esta carpeta.

## Imágenes

Las gráficas de `imagenes/` son una **copia** de `04-experimentos/graficos/` (idénticas a
las de `03-simulacion/salidas/graficos/`), más `escenarios-2x2.png`, que solo existe aquí.
Los originales no se movieron.

Si se vuelven a generar los resultados, copiar de nuevo (no sobrescribe
`escenarios-2x2.png`):

```bash
cp 04-experimentos/graficos/*.png 05-informe/latex/imagenes/
```

Las figuras que usa `main.tex` son:

- `base.png` (Fig. 1): utilización y espera por estación en E1.
- `escenarios-2x2.png` (Fig. 2): comparación de E1, E2 y E3 en ensamblaje y acabado
  (utilización, cola, espera y capacidad frente a producción) en cuatro paneles. Es la
  versión rediseñada del informe; difiere de `escenarios.png`.

Las demás están disponibles para ampliar el informe: `escenarios.png`, `e2.png`, `e3.png`,
`flujo-*.png`, `cola-*.png`, `distribucion-cola-*.png` y `utilizacion-cola-*.png`.

## Requisitos

- `IEEEtran` (incluido en Overleaf; en TeX Live suele estar en `texlive-publishers`).
- `babel` con español (`texlive-lang-spanish`).
- `amsmath`, `array`, `longtable`, `graphicx`, `cite`, `url`, `hyperref`.
