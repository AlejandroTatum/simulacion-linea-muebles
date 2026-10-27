// Run from 03-simulacion: node --test web/tests
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { Linea, mmc, simular, ESCENARIOS, CV_LOGNORMAL, kingmanWq, siguienteMuestra } = require("../motor.js");

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

test("avanzar a un tiempo pasado después de un paso no retrocede el reloj", () => {
  const linea = new Linea(ESCENARIOS.E1, 5);
  linea.siguienteEvento();
  linea.siguienteEvento();
  const t = linea.ahora;
  assert.ok(t > 0, "two steps must move the clock past zero");
  linea.avanzarHasta(t / 2);
  assert.equal(linea.ahora, t);
  linea.avanzarHasta(t + 60);
  assert.equal(linea.ahora, t + 60);
});

test("kingmanWq aproxima la espera con el CV lognormal compartido", () => {
  assert.equal(CV_LOGNORMAL, 0.3);
  // Assembly in E1: rho = 0.75, 15 min -> (1 + 0.09) / 2 * 3 * 15
  assert.ok(Math.abs(kingmanWq(0.75, 15, CV_LOGNORMAL) - 24.525) < 1e-9);
  // CV = 1 recovers M/M/1 (45 min)
  assert.ok(Math.abs(kingmanWq(0.75, 15, 1) - mmc(3, 4, 1).wq_min) < 1e-9);
});

test("siguienteMuestra salta los puntos de muestreo que el reloj ya pasó", () => {
  assert.equal(siguienteMuestra(0, 0, 10), 0);
  assert.equal(siguienteMuestra(20, 5, 10), 20);
  assert.equal(siguienteMuestra(10, 10, 10), 10);
  assert.equal(siguienteMuestra(10, 37.5, 10), 40);
});

test("el calentamiento se expone como finCalentamiento", () => {
  const linea = new Linea(ESCENARIOS.E1, 1, 120);
  assert.equal(linea.finCalentamiento, 120);
  assert.equal(linea.inicio, undefined);
});
