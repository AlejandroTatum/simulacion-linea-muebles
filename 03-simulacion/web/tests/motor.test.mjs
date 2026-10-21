// Run from 03-simulacion: node --test web/tests
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { Linea, mmc, simular, ESCENARIOS } = require("../motor.js");

const cerca = (real, esperado, tolPct) =>
  Math.abs(real - esperado) / esperado * 100 <= tolPct;

test("mmc reproduce los valores teóricos de teoria.py (ensamblaje E1)", () => {
  const r = mmc(3, 4, 1);
  assert.equal(r.utilizacion, 0.75);
  assert.ok(Math.abs(r.lq - 2.25) < 1e-9);
  assert.ok(Math.abs(r.wq_min - 45) < 1e-9);
});

test("mmc con dos servidores coincide con M/M/2", () => {
  const r = mmc(3, 4, 2);
  assert.ok(Math.abs(r.utilizacion - 0.375) < 1e-9);
  assert.ok(Math.abs(r.lq - 0.122727) < 1e-5);
});

test("mmc devuelve null cuando la estación es inestable", () => {
  assert.equal(mmc(4.5, 4, 1), null);
});

test("la misma semilla produce la misma réplica", () => {
  const a = simular(ESCENARIOS.E1, 7, 200 * 60, 20 * 60);
  const b = simular(ESCENARIOS.E1, 7, 200 * 60, 20 * 60);
  assert.deepEqual(a, b);
});

test("la línea conserva sillas: llegadas = terminadas + en proceso", () => {
  const linea = new Linea(ESCENARIOS.E1, 3);
  linea.avanzarHasta(50 * 60);
  const e = linea.estado();
  const enProceso = e.estaciones.reduce(
    (s, est) => s + est.cola.length + est.servidores.filter(Boolean).length, 0);
  assert.equal(e.llegadas, e.terminadas + enProceso);
});

test("una réplica larga de E1 converge a la teoría M/M/1", () => {
  const r = simular(ESCENARIOS.E1, 2026, 20000 * 60, 100 * 60);
  const ens = r.estaciones[2];
  assert.ok(cerca(ens.utilizacion, 0.75, 3), `rho=${ens.utilizacion}`);
  assert.ok(cerca(ens.lq, 2.25, 10), `lq=${ens.lq}`);
  assert.ok(cerca(ens.wq_min, 45, 10), `wq=${ens.wq_min}`);
  assert.ok(cerca(r.throughput_h, 3, 2), `th=${r.throughput_h}`);
});

test("el modo lognormal mantiene rho pero reduce la cola", () => {
  const cfg = { ...ESCENARIOS.E1, distribucion: "lognormal" };
  const r = simular(cfg, 11, 20000 * 60, 100 * 60);
  const ens = r.estaciones[2];
  assert.ok(cerca(ens.utilizacion, 0.75, 3), `rho=${ens.utilizacion}`);
  assert.ok(ens.lq < 2.25 * 0.75, `lq=${ens.lq}`);
});

test("el modo paso a paso procesa un evento y lo anota en la bitácora", () => {
  const linea = new Linea(ESCENARIOS.E1, 5);
  linea.bitacora = [];
  const t = linea.siguienteEvento();
  assert.ok(t > 0);
  assert.equal(linea.ahora, t);
  assert.deepEqual(linea.bitacora.map((e) => e.tipo), ["llegada", "inicio"]);
  assert.equal(linea.bitacora[1].valor, 0);
});
