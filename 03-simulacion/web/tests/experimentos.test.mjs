// Run from 03-simulacion: node --test web/tests
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { listaExperimentos, calcularTeoria, fmt } = require("../experimentos.js");

const lista = listaExperimentos();
const porTitulo = (inicio) => lista.find((x) => x.titulo.startsWith(inicio));

test("ningún texto de experimento deja un placeholder sin interpolar", () => {
  for (const x of lista) {
    for (const campo of ["titulo", "texto", "espera"]) {
      assert.ok(!/\$\{|undefined|NaN/.test(x[campo]), `${x.titulo} · ${campo}: ${x[campo]}`);
    }
  }
});

test("cada experimento apunta a un escenario del motor", () => {
  assert.deepEqual(lista.map((x) => x.clave), ["E1", "E2", "E3", "SAT", "E1"]);
  assert.equal(lista[4].dist, "lognormal");
});

test("el experimento de variabilidad muestra CV, ρ, Kingman y la espera M/M/1", () => {
  const v = porTitulo("Variabilidad");
  assert.match(v.texto, /\(CV = 0,3\)/);
  assert.match(v.espera, /ρ no cambia \(75 %\)/);
  assert.match(v.espera, /baja hacia ~25 min \(aproximación de Kingman\) en lugar de 45\./);
});

test("el experimento de saturación usa la λ del escenario SAT", () => {
  const s = porTitulo("Saturación");
  assert.equal(s.titulo, "Saturación · λ = 4,5 sillas/h");
  assert.match(s.espera, /\(~0,5 sillas más por hora\)/);
  assert.match(s.espera, /se clava en 4 sillas\/h/);
});

test("E2 reporta la nueva espera y el nuevo cuello de botella", () => {
  const e2 = porTitulo("E2");
  const T = calcularTeoria(require("../motor.js").ESCENARIOS.E2);
  assert.ok(e2.espera.includes(`cae a ${fmt(T.estaciones[2].teo.wq_min, 1)} min`));
  assert.match(e2.espera, /el nuevo cuello es Acabado\./);
});
