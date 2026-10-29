# Informe final en LaTeX

Esta carpeta contiene la plantilla IEEE del informe final.

```text
05-informe/latex/
├── main.tex          # plantilla del informe
├── referencias.bib   # copia de 01-investigacion/referencias.bib
├── README.md         # estas instrucciones
└── imagenes/         # copias de las gráficas (no se mueven los originales)
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

El resultado es `main.pdf`.

Si se compila en Overleaf, subir `main.tex`, `referencias.bib` y la carpeta
`imagenes/`. La plantilla usa esta copia local con `\bibliography{referencias}`, así
que no hay que cambiar ninguna ruta.

La bibliografía original sigue en `01-investigacion/referencias.bib`; la de esta
carpeta es una copia idéntica. Si se agregan o corrigen referencias, conviene
actualizar ambas.

## Imágenes

Las 19 gráficas de `imagenes/` son una **copia** de
`04-experimentos/graficos/` (idénticas a las de `03-simulacion/graficos/`). Los
originales no se movieron.

Si se vuelven a generar los resultados, copiar de nuevo:

```bash
cp 04-experimentos/graficos/*.png 05-informe/latex/imagenes/
```

Las figuras que ya usa la plantilla son:

- `escenarios.png`: comparación E1, E2 y E3.
- `base.png`: utilización y espera de la línea base.
- `flujo-base.png`: composición del tiempo de flujo.

Las demás están disponibles para agregar las figuras que falten:
`cola-*.png`, `distribucion-cola-*.png`, `utilizacion-cola-*.png`,
`replicas-*.png`, `e2.png`, `e3.png`.

## Qué completar

En `main.tex` están marcados con `% TODO`:

- planteamiento del problema y justificación;
- descripción de la organización del código y del procedimiento experimental;
- discusión con los antecedentes;
- conclusiones, recomendaciones y limitaciones.

También conviene revisar los autores y la afiliación antes de entregar.

## Requisitos

- `IEEEtran` (incluido en Overleaf; en TeX Live suele estar en `texlive-publishers`).
- `babel` con español (`texlive-lang-spanish`).
- `booktabs`, `graphicx`, `amsmath`, `hyperref`, `url`.
