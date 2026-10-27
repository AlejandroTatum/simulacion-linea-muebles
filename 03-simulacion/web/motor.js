/*
 * Discrete-event engine for the chair line, mirroring src/linea.py.
 *
 * Same model: Poisson arrivals (rate in chairs/h), stations in series with an
 * unlimited FIFO queue and `recursos` servers. Internal time unit: minutes.
 * Works in the browser (window.Motor) and in Node (module.exports).
 */
(function (raiz) {
  "use strict";

  /** Coefficient of variation of the "more regular" lognormal service times. */
  const CV_LOGNORMAL = 0.3;

  const ESCENARIOS = {
    E1: {
      nombre: "E1 · Línea base",
      tasa_llegadas_h: 3,
      distribucion: "exponencial",
      estaciones: [
        { nombre: "Corte", recursos: 1, tiempo_min: 8 },
        { nombre: "Lijado", recursos: 1, tiempo_min: 10 },
        { nombre: "Ensamblaje", recursos: 1, tiempo_min: 15 },
        { nombre: "Acabado", recursos: 1, tiempo_min: 12 },
      ],
    },
  };
  ESCENARIOS.E2 = clonar(ESCENARIOS.E1, "E2 · Segundo ensamblador", (c) => { c.estaciones[2].recursos = 2; });
  ESCENARIOS.E3 = clonar(ESCENARIOS.E1, "E3 · Ensamblaje en 10 min", (c) => { c.estaciones[2].tiempo_min = 10; });
  ESCENARIOS.SAT = clonar(ESCENARIOS.E1, "Saturada · λ = 4,5 sillas/h", (c) => { c.tasa_llegadas_h = 4.5; });

  function clonar(base, nombre, cambio) {
    const c = JSON.parse(JSON.stringify(base));
    c.nombre = nombre;
    cambio(c);
    return c;
  }

  // Seeded PRNG (mulberry32) so every run is reproducible.
  function generador(semilla) {
    let s = semilla >>> 0;
    const u = () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const uniforme = () => 1 - u(); // (0, 1]
    return {
      exponencial: (media) => -Math.log(uniforme()) * media,
      // Lognormal with the same mean and a coefficient of variation `cv`.
      lognormal: (media, cv) => {
        const s2 = Math.log(1 + cv * cv);
        const z = Math.sqrt(-2 * Math.log(uniforme())) * Math.cos(2 * Math.PI * u());
        return Math.exp(Math.log(media) - s2 / 2 + Math.sqrt(s2) * z);
      },
    };
  }

  // Binary min-heap ordered by (time, insertion order).
  class Agenda {
    constructor() { this.h = []; this.n = 0; }
    get size() { return this.h.length; }
    peek() { return this.h[0]; }
    push(ev) {
      ev.orden = this.n++;
      const h = this.h;
      h.push(ev);
      let i = h.length - 1;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (menor(h[p], h[i])) break;
        [h[p], h[i]] = [h[i], h[p]];
        i = p;
      }
    }
    pop() {
      const h = this.h;
      const top = h[0];
      const last = h.pop();
      if (h.length) {
        h[0] = last;
        let i = 0;
        for (;;) {
          const l = 2 * i + 1, r = l + 1;
          let m = i;
          if (l < h.length && menor(h[l], h[m])) m = l;
          if (r < h.length && menor(h[r], h[m])) m = r;
          if (m === i) break;
          [h[m], h[i]] = [h[i], h[m]];
          i = m;
        }
      }
      return top;
    }
  }
  const menor = (a, b) => a.t < b.t || (a.t === b.t && a.orden < b.orden);

  class Linea {
    /**
     * @param cfg scenario (see ESCENARIOS)
     * @param semilla integer seed
     * @param calentamientoMin statistics ignore everything before this time
     */
    constructor(cfg, semilla, calentamientoMin = 0) {
      this.cfg = cfg;
      this.rng = generador(semilla);
      this.finCalentamiento = calentamientoMin;
      this.ahora = 0;
      this.agenda = new Agenda();
      this.siguienteId = 1;
      this.llegadas = 0;
      this.terminadas = 0;
      this.terminadasMedidas = 0;
      this.flujos = { suma: 0, n: 0 };
      this.salidas = []; // chairs that just left the line (drained by the UI)
      this.bitacora = null; // set to [] to record every event (UI event log)
      this.estaciones = cfg.estaciones.map((e) => ({
        nombre: e.nombre,
        recursos: e.recursos,
        tiempo_min: e.tiempo_min,
        cola: [],
        servidores: new Array(e.recursos).fill(null),
        t: 0, areaCola: 0, areaOcupados: 0,
        esperas: { suma: 0, n: 0 },
        atendidas: 0,
      }));
      this.agenda.push({ t: this.muestraLlegada(), tipo: "llegada" });
    }

    muestraLlegada() {
      return this.ahora + this.rng.exponencial(60 / this.cfg.tasa_llegadas_h);
    }

    muestraServicio(est) {
      return this.cfg.distribucion === "lognormal"
        ? this.rng.lognormal(est.tiempo_min, CV_LOGNORMAL)
        : this.rng.exponencial(est.tiempo_min);
    }

    acumular(est, t) {
      const desde = Math.max(est.t, this.finCalentamiento);
      if (t > desde) {
        const ocupados = est.servidores.reduce((s, x) => s + (x ? 1 : 0), 0);
        est.areaCola += est.cola.length * (t - desde);
        est.areaOcupados += ocupados * (t - desde);
      }
      est.t = t;
    }

    entrar(silla, i) {
      const est = this.estaciones[i];
      this.acumular(est, this.ahora);
      silla.etapa = i;
      silla.entradaCola = this.ahora;
      const libre = est.servidores.indexOf(null);
      if (libre >= 0) this.atender(silla, i, libre);
      else est.cola.push(silla);
    }

    atender(silla, i, servidor) {
      const est = this.estaciones[i];
      const espera = this.ahora - silla.entradaCola;
      if (silla.entradaCola >= this.finCalentamiento) {
        est.esperas.suma += espera;
        est.esperas.n += 1;
      }
      this.anotar("inicio", silla.id, i, espera);
      const fin = this.ahora + this.muestraServicio(est);
      est.servidores[servidor] = { silla, inicio: this.ahora, fin };
      this.agenda.push({ t: fin, tipo: "fin", estacion: i, servidor });
    }

    procesar(ev) {
      this.ahora = ev.t;
      if (ev.tipo === "llegada") {
        this.llegadas += 1;
        const silla = { id: this.siguienteId++, llegada: this.ahora, etapa: 0 };
        this.anotar("llegada", silla.id, 0, 0);
        this.entrar(silla, 0);
        this.agenda.push({ t: this.muestraLlegada(), tipo: "llegada" });
        return;
      }
      const est = this.estaciones[ev.estacion];
      this.acumular(est, this.ahora);
      const { silla } = est.servidores[ev.servidor];
      est.servidores[ev.servidor] = null;
      est.atendidas += 1;
      this.anotar("fin", silla.id, ev.estacion, 0);
      if (est.cola.length) this.atender(est.cola.shift(), ev.estacion, ev.servidor);
      if (ev.estacion + 1 < this.estaciones.length) {
        this.entrar(silla, ev.estacion + 1);
      } else {
        this.terminadas += 1;
        if (this.ahora >= this.finCalentamiento) this.terminadasMedidas += 1;
        if (silla.llegada >= this.finCalentamiento) {
          this.flujos.suma += this.ahora - silla.llegada;
          this.flujos.n += 1;
        }
        this.salidas.push(silla);
        this.anotar("salida", silla.id, ev.estacion, this.ahora - silla.llegada);
      }
    }

    anotar(tipo, id, estacion, valor) {
      if (this.bitacora) this.bitacora.push({ t: this.ahora, tipo, id, estacion, valor });
    }

    /** Process exactly one event (step mode). Returns its time, or null. */
    siguienteEvento() {
      if (!this.agenda.size) return null;
      this.procesar(this.agenda.pop());
      return this.ahora;
    }

    /** Advance the clock to t; never rewinds when step mode already moved past t. */
    avanzarHasta(t) {
      while (this.agenda.size && this.agenda.peek().t <= t) this.procesar(this.agenda.pop());
      this.ahora = Math.max(this.ahora, t);
    }

    estado() {
      return {
        ahora: this.ahora,
        llegadas: this.llegadas,
        terminadas: this.terminadas,
        estaciones: this.estaciones,
      };
    }

    metricas() {
      const ventana = this.ahora - this.finCalentamiento;
      const filas = this.estaciones.map((est) => {
        this.acumular(est, this.ahora);
        return {
          estacion: est.nombre,
          recursos: est.recursos,
          utilizacion: ventana > 0 ? est.areaOcupados / (est.recursos * ventana) : 0,
          lq: ventana > 0 ? est.areaCola / ventana : 0,
          wq_min: est.esperas.n ? est.esperas.suma / est.esperas.n : 0,
        };
      });
      return {
        estaciones: filas,
        terminadas: this.terminadasMedidas,
        throughput_h: ventana > 0 ? this.terminadasMedidas / (ventana / 60) : 0,
        flujo_min: this.flujos.n ? this.flujos.suma / this.flujos.n : 0,
      };
    }
  }

  /** Run one full replica; mirrors simular_replica in src/linea.py. */
  function simular(cfg, semilla, duracionMin, calentamientoMin) {
    const linea = new Linea(cfg, semilla, calentamientoMin);
    linea.salidas = { push() {} }; // nobody drains it in batch mode
    linea.avanzarHasta(duracionMin);
    return linea.metricas();
  }

  function factorial(n) { let f = 1; for (let k = 2; k <= n; k++) f *= k; return f; }

  /** M/M/c steady state (report equations 7-14). Rates in chairs/h. Null if unstable. */
  function mmc(lam, mu, c) {
    const rho = lam / (c * mu);
    if (rho >= 1) return null;
    const a = lam / mu;
    let suma = 0;
    for (let k = 0; k < c; k++) suma += a ** k / factorial(k);
    const p0 = 1 / (suma + a ** c / (factorial(c) * (1 - rho)));
    const lq = (p0 * a ** c * rho) / (factorial(c) * (1 - rho) ** 2);
    const wq = lq / lam;
    const w = wq + 1 / mu;
    return { utilizacion: rho, p0, lq, wq_min: wq * 60, l: lam * w, w_min: w * 60 };
  }

  /** Kingman (G/G/1) approximation of the queue wait, in minutes, with Poisson arrivals. */
  function kingmanWq(rho, tiempoMin, cvServicio) {
    return ((1 + cvServicio ** 2) / 2) * (rho / (1 - rho)) * tiempoMin;
  }

  /**
   * First sample time at or after the clock; step mode can leave older ones behind.
   * Samples sit on the grid k * paso anchored at 0, computed from the index so
   * fractional steps do not accumulate rounding error.
   */
  function siguienteMuestra(prox, ahora, paso) {
    if (prox >= ahora) return prox;
    let k = Math.ceil(ahora / paso);
    if (k * paso < ahora) k += 1;
    else if ((k - 1) * paso >= ahora) k -= 1;
    return k * paso;
  }

  const api = { Linea, simular, mmc, ESCENARIOS, generador, CV_LOGNORMAL, kingmanWq, siguienteMuestra };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Motor = api;
})(typeof window !== "undefined" ? window : globalThis);
