/*
 * Number formatting, line theory and guided-experiment copy for the simulator.
 * Pure functions on top of motor.js, so the copy can be tested in Node.
 * Works in the browser (window.Experimentos) and in Node (module.exports).
 */
(function (raiz) {
  "use strict";

  const M = typeof module !== "undefined" && module.exports ? require("./motor.js") : raiz.Motor;

  const nf = {};
  function fmt(x, d = 2) {
    if (x === null || x === undefined || !Number.isFinite(x)) return "—";
    nf[d] = nf[d] || new Intl.NumberFormat("es", { minimumFractionDigits: d, maximumFractionDigits: d });
    return nf[d].format(x);
  }
  const pct = (x, d = 1) => (Number.isFinite(x) ? fmt(x * 100, d) + " %" : "—");

  /* ---------- Theory for the current configuration ---------- */

  // In series, a saturated station only passes on its capacity downstream.
  function calcularTeoria(cfg) {
    let lam = cfg.tasa_llegadas_h;
    const estaciones = cfg.estaciones.map((e) => {
      const mu = 60 / e.tiempo_min;
      const C = e.recursos * mu;
      const fila = { lam, mu, C, rho: lam / C, teo: M.mmc(lam, mu, e.recursos) };
      lam = Math.min(lam, C);
      return fila;
    });
    const estables = estaciones.every((e) => e.teo);
    const W = estables ? estaciones.reduce((s, e) => s + e.teo.w_min, 0) : null;
    const cuello = estaciones.reduce((m, e, i) => (e.rho > estaciones[m].rho ? i : m), 0);
    const Cmin = Math.min(...estaciones.map((e) => e.C));
    return {
      estaciones, estables, W, cuello,
      L: estables ? cfg.tasa_llegadas_h * W / 60 : null,
      throughput: Math.min(cfg.tasa_llegadas_h, Cmin),
      Cmin,
    };
  }

  /** Guided experiments: scenario key, title, prompt and the expected outcome. */
  function listaExperimentos() {
    const t = (clave) => calcularTeoria(M.ESCENARIOS[clave]);
    const e1 = t("E1"), e2 = t("E2"), e3 = t("E3"), sat = t("SAT");
    const nombre = (T) => M.ESCENARIOS.E1.estaciones[T.cuello].nombre;
    const ens = M.ESCENARIOS.E1.estaciones[2], ensE1 = e1.estaciones[2];
    const kingman = M.kingmanWq(ensE1.rho, ens.tiempo_min, M.CV_LOGNORMAL);
    const lamSat = M.ESCENARIOS.SAT.tasa_llegadas_h;
    return [
      { clave: "E1", titulo: "E1 · ¿Dónde se forma la cola?",
        texto: "Corré la línea base y mirá las cuatro colas. Todas las estaciones tienen la misma λ; cambia solo el tiempo de proceso.",
        espera: `Ensamblaje trabaja al ${pct(e1.estaciones[2].rho, 0)} y cada silla espera ~${fmt(e1.estaciones[2].teo.wq_min, 0)} min ahí. Corte espera ~${fmt(e1.estaciones[0].teo.wq_min, 0)} min.` },
      { clave: "E2", titulo: "E2 · Sumar un ensamblador",
        texto: "Duplicamos el recurso del cuello de botella. ¿Baja la producción de sillas por hora o solo la espera?",
        espera: `La espera en ensamblaje cae a ${fmt(e2.estaciones[2].teo.wq_min, 1)} min y el tiempo en la línea baja de ${fmt(e1.W, 0)} a ${fmt(e2.W, 0)} min. La producción sigue en ${fmt(e2.throughput, 0)} sillas/h y el nuevo cuello es ${nombre(e2)}.` },
      { clave: "E3", titulo: "E3 · Ensamblaje más rápido",
        texto: "En vez de contratar, mejoramos el método: ensamblar en 10 min en lugar de 15.",
        espera: `ρ de ensamblaje pasa a ${pct(e3.estaciones[2].rho, 0)} y su espera a ${fmt(e3.estaciones[2].teo.wq_min, 0)} min. Tiempo en la línea: ${fmt(e3.W, 0)} min. Compará con E2: ¿cuál conviene?` },
      { clave: "SAT", titulo: `Saturación · λ = ${fmt(lamSat, 1)} sillas/h`,
        texto: "Llegan más pedidos de los que ensamblaje puede hacer. Mirá el gráfico de WIP durante varias horas.",
        espera: `Ensamblaje queda con ρ = ${fmt(sat.estaciones[2].rho, 3)} &gt; 1: su cola crece sin límite (~${fmt(lamSat - sat.estaciones[2].C, 1)} sillas más por hora) y la producción se clava en ${fmt(sat.throughput, 0)} sillas/h.` },
      { clave: "E1", dist: "lognormal", titulo: "Variabilidad · mismo ρ, menos cola",
        texto: `Mismos tiempos medios, pero procesos más regulares (CV = ${fmt(M.CV_LOGNORMAL, 1)}), como en un taller con métodos estandarizados.`,
        espera: `ρ no cambia (${pct(ensE1.rho, 0)}), pero la espera en ensamblaje baja hacia ~${fmt(kingman, 0)} min (aproximación de Kingman) en lugar de ${fmt(ensE1.teo.wq_min, 0)}. La cola nace de la variabilidad, no solo de la carga.` },
    ];
  }

  const api = { fmt, pct, calcularTeoria, listaExperimentos };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Experimentos = api;
})(typeof window !== "undefined" ? window : globalThis);
