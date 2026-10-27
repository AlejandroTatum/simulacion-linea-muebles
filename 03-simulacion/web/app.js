/* UI for the chair-line simulator: floor plan, live indicators and study panels. */
(function () {
  "use strict";

  const M = window.Motor;
  const $ = (sel) => document.querySelector(sel);
  const calma = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const VELOCIDADES = [5, 15, 30, 60, 120, 300, 900]; // simulated minutes per real second
  const PASO_MUESTRA = 10; // minutes between chart samples
  const MAX_MUESTRAS = 720; // last 120 h on the charts
  const MIN_VENTANA = 72; // the x axis spans at least 12 h so early curves are readable
  const K_SILLA = 1.6; // chair size on the floor plan
  const COLORES = ["#e3c08d", "#8fb8de", "#e0533d", "#6fb58a", "#c39bd3", "#f4c430"];
  const ETAPAS = [
    "Tablones sin cortar: esperan en corte.",
    "Piezas cortadas, todavía ásperas: van a lijado.",
    "Piezas lijadas: esperan ser ensambladas.",
    "Silla armada en madera cruda: va a acabado.",
    "Silla laqueada: lista para despacho.",
  ];
  // resumen-base.csv (Python, 30 replicas, seed 2026)
  const PYTHON_E1 = {
    estaciones: [
      { utilizacion: 0.397913, lq: 0.266318, wq_min: 5.324018 },
      { utilizacion: 0.498205, lq: 0.500891, wq_min: 10.012641 },
      { utilizacion: 0.751032, lq: 2.273949, wq_min: 45.425165 },
      { utilizacion: 0.599941, lq: 0.911325, wq_min: 18.200311 },
    ],
    throughput_h: 2.998, flujo_min: 124.0,
  };

  const S = {
    cfg: copiar(M.ESCENARIOS.E1),
    escenario: "E1",
    semilla: 2026,
    velocidad: VELOCIDADES[2],
    pausado: false,
    linea: null,
    muestras: [],
    proxMuestra: 0,
    wip: { suma: 0, n: 0 },
    visual: new Map(),
    salientes: [],
    log: [],
    ultimo: 0,
    ultimoPanel: 0,
    teoria: null,
  };

  function copiar(o) { return JSON.parse(JSON.stringify(o)); }

  const nf = {};
  function fmt(x, d = 2) {
    if (x === null || x === undefined || !Number.isFinite(x)) return "—";
    nf[d] = nf[d] || new Intl.NumberFormat("es", { minimumFractionDigits: d, maximumFractionDigits: d });
    return nf[d].format(x);
  }
  const pct = (x, d = 1) => (Number.isFinite(x) ? fmt(x * 100, d) + " %" : "—");
  function reloj(min) {
    const h = Math.floor(min / 60), m = Math.floor(min % 60);
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

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

  /* ---------- Simulation control ---------- */

  function reiniciar() {
    S.linea = new M.Linea(S.cfg, S.semilla);
    S.linea.bitacora = [];
    S.muestras = [];
    S.proxMuestra = 0;
    S.wip = { suma: 0, n: 0 };
    S.visual.clear();
    S.salientes = [];
    S.log = [];
    S.teoria = calcularTeoria(S.cfg);
    construirTarjetas();
    actualizarPaneles();
  }

  function avanzar(hasta) {
    const L = S.linea;
    // Step mode can move the clock past pending samples; skip them instead of
    // recording the current state under a stale time.
    while (S.proxMuestra < L.ahora) S.proxMuestra += PASO_MUESTRA;
    while (S.proxMuestra <= hasta) {
      L.avanzarHasta(S.proxMuestra);
      muestrear();
      S.proxMuestra += PASO_MUESTRA;
    }
    L.avanzarHasta(hasta);
  }

  function muestrear() {
    const e = S.linea.estado();
    const wip = e.llegadas - e.terminadas;
    S.wip.suma += wip;
    S.wip.n += 1;
    S.muestras.push({ wip, colas: e.estaciones.map((x) => x.cola.length) });
    if (S.muestras.length > MAX_MUESTRAS) S.muestras.shift();
  }

  function drenarEventos() {
    const b = S.linea.bitacora;
    if (b.length) {
      S.log = S.log.concat(b.slice(-9)).slice(-9);
      b.length = 0;
    }
    const sal = S.linea.salidas;
    for (const silla of sal) {
      const v = S.visual.get(silla.id);
      S.salientes.push({ id: silla.id, x: v ? v.x : 0, y: v ? v.y : 0 });
      S.visual.delete(silla.id);
    }
    sal.length = 0;
    if (S.salientes.length > 30) S.salientes.splice(0, S.salientes.length - 30);
  }

  function cuadro(ts) {
    const dt = Math.min(0.1, (ts - S.ultimo) / 1000 || 0);
    S.ultimo = ts;
    if (!S.pausado) avanzar(S.linea.ahora + dt * S.velocidad);
    drenarEventos();
    dibujarPlanta(dt);
    if (ts - S.ultimoPanel > 250) {
      S.ultimoPanel = ts;
      actualizarPaneles();
    }
    requestAnimationFrame(cuadro);
  }

  /* ---------- Canvas helpers ---------- */

  function ajustarCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, w, h };
  }

  // A chair drawn as the product it is at that point of the line.
  function dibujarSilla(ctx, x, y, etapa, k = 1) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(k, k);
    ctx.strokeStyle = "rgba(0,0,0,.5)";
    ctx.lineWidth = 0.8;
    if (etapa === 0) {
      ctx.fillStyle = "#d6b07a";
      for (let i = 0; i < 3; i++) { ctx.fillRect(-8, -6 + i * 4.2, 16, 3.2); ctx.strokeRect(-8, -6 + i * 4.2, 16, 3.2); }
    } else if (etapa <= 2) {
      ctx.fillStyle = etapa === 1 ? "#c39a62" : "#f2d9ab";
      ctx.fillRect(-8, -6, 9, 9); ctx.strokeRect(-8, -6, 9, 9);
      for (let i = 0; i < 4; i++) { ctx.fillRect(2.5 + i * 2.2, -7, 1.6, 12); }
      if (etapa === 1) {
        ctx.fillStyle = "rgba(90,60,30,.7)";
        for (const [a, b] of [[-6, -4], [-3, 0], [-5, 1], [-2, -3]]) ctx.fillRect(a, b, 1, 1);
      }
    } else {
      ctx.fillStyle = etapa === 3 ? "#e3c08d" : "#7a4a2a";
      ctx.fillRect(-6, -9, 2.6, 17);
      ctx.fillRect(-6, -1, 12, 2.6);
      ctx.fillRect(3.4, 1, 2.6, 7);
      ctx.strokeRect(-6, -9, 2.6, 17);
      ctx.strokeRect(-6, -1, 12, 2.6);
      if (etapa === 4) {
        ctx.fillStyle = "rgba(255,220,180,.55)";
        ctx.fillRect(-5.4, -8, 0.8, 7);
      }
    }
    ctx.restore();
  }

  /* ---------- Floor plan ---------- */

  function geometria(w, h) {
    const n = S.cfg.estaciones.length, izq = 110, der = 120;
    const slot = (w - izq - der) / n;
    const yc = h / 2 + 16;
    const est = S.cfg.estaciones.map((e, i) => {
      const ancho = 100, x1 = izq + slot * (i + 1) - 14, x0 = x1 - ancho;
      const alto = 58, sep = 8, total = e.recursos * alto + (e.recursos - 1) * sep;
      const bahias = Array.from({ length: e.recursos }, (_, k) => ({
        x: x0, y: yc - total / 2 + k * (alto + sep), w: ancho, h: alto,
      }));
      return { x0, x1, colaX: x0 - 20, colaMin: izq + slot * i + 12, bahias, arriba: yc - total / 2 };
    });
    return { w, h, yc, est, entrada: { x: 34, y: yc }, despacho: { x: w - 62, y: yc } };
  }

  const FILAS = [0, -30, 30, -60, 60, -90, 90];
  const PASO_COLA = 28;
  function posCola(g, i, k) {
    const e = g.est[i];
    const porFila = Math.max(1, Math.floor((e.colaX - e.colaMin) / PASO_COLA) + 1);
    const fila = Math.floor(k / porFila);
    if (fila >= FILAS.length) return null;
    return { x: e.colaX - (k % porFila) * PASO_COLA, y: g.yc + FILAS[fila] };
  }

  let rodillos = 0;
  function dibujarPlanta(dt) {
    const { ctx, w, h } = ajustarCanvas($("#planta"));
    const g = geometria(w, h);
    const L = S.linea;
    const T = S.teoria;

    // Floor and grid
    ctx.fillStyle = "#181d21";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#20262b";
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 24) { ctx.beginPath(); ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, h); ctx.stroke(); }
    for (let y = 0; y < h; y += 24) { ctx.beginPath(); ctx.moveTo(0, y + 0.5); ctx.lineTo(w, y + 0.5); ctx.stroke(); }

    // Conveyor with moving rollers
    if (!S.pausado && !calma) rodillos = (rodillos + dt * Math.min(40, S.velocidad)) % 12;
    ctx.fillStyle = "#2b3238";
    ctx.fillRect(0, g.yc - 7, w, 14);
    ctx.strokeStyle = "#3c464f";
    for (let x = -12 + rodillos; x < w; x += 12) { ctx.beginPath(); ctx.moveTo(x, g.yc - 7); ctx.lineTo(x, g.yc + 7); ctx.stroke(); }

    // Intake and dispatch
    rotulo(ctx, "INGRESO", g.entrada.x, 26, "#a3a9ad");
    ctx.fillStyle = "#2a3137";
    ctx.fillRect(g.entrada.x - 28, g.yc - 44, 56, 88);
    for (let i = 0; i < 6; i++) dibujarSilla(ctx, g.entrada.x - 1, g.yc - 32 + i * 13, 0, K_SILLA);
    rotulo(ctx, `λ = ${fmt(S.cfg.tasa_llegadas_h, 1)} sillas/h`, g.entrada.x, h - 16, "#a3a9ad", 11);

    rotulo(ctx, "DESPACHO", g.despacho.x, 26, "#6fb58a");
    ctx.fillStyle = "#5a4330";
    ctx.fillRect(g.despacho.x - 44, g.yc - 60, 88, 120);
    ctx.strokeStyle = "#3d2d20";
    for (let y = g.yc - 60; y < g.yc + 60; y += 12) { ctx.beginPath(); ctx.moveTo(g.despacho.x - 44, y); ctx.lineTo(g.despacho.x + 44, y); ctx.stroke(); }
    const apiladas = Math.min(12, L.terminadas);
    for (let i = 0; i < apiladas; i++) {
      dibujarSilla(ctx, g.despacho.x - 27 + (i % 4) * 19, g.yc + 42 - Math.floor(i / 4) * 34, 4, K_SILLA);
    }
    rotulo(ctx, `${L.terminadas} sillas`, g.despacho.x, h - 16, "#6fb58a", 13);

    // Stations
    const presentes = new Set();
    const k = calma ? 1 : 1 - Math.exp(-dt * 14);
    const mover = (id, tx, ty, etapa, origen) => {
      presentes.add(id);
      let v = S.visual.get(id);
      if (!v) { v = origen ? { x: origen.x, y: origen.y } : { x: tx, y: ty }; S.visual.set(id, v); }
      v.x += (tx - v.x) * k;
      v.y += (ty - v.y) * k;
      v.etapa = etapa;
    };

    L.estaciones.forEach((est, i) => {
      const ge = g.est[i];
      const cuello = i === T.cuello;
      const x = (ge.x0 + ge.x1) / 2;

      // Safety marking around the work cell
      ctx.save();
      ctx.setLineDash([6, 5]);
      ctx.strokeStyle = cuello ? "#e0533d" : "#f4c430";
      ctx.globalAlpha = cuello ? 0.9 : 0.45;
      ctx.lineWidth = cuello ? 2 : 1;
      const yTop = ge.arriba - 10, yBot = ge.bahias[ge.bahias.length - 1].y + 56;
      ctx.strokeRect(ge.x0 - 8, yTop, ge.x1 - ge.x0 + 16, yBot - yTop);
      ctx.restore();

      rotulo(ctx, est.nombre.toUpperCase(), x, yTop - 26, "#ece4d6", 15, true);
      rotulo(ctx, `c = ${est.recursos} · t = ${fmt(est.tiempo_min, est.tiempo_min % 1 ? 1 : 0)} min`, x, yTop - 10, "#a3a9ad", 11);
      if (cuello) rotulo(ctx, "CUELLO DE BOTELLA", x, yBot + 16, "#e0533d", 11, true);

      est.servidores.forEach((srv, b) => {
        const bay = ge.bahias[b];
        ctx.fillStyle = "#2f3940";
        ctx.fillRect(bay.x, bay.y, bay.w, bay.h);
        ctx.strokeStyle = "#46525c";
        ctx.strokeRect(bay.x + 0.5, bay.y + 0.5, bay.w - 1, bay.h - 1);
        // Operator: hard hat when working, grey when idle
        ctx.beginPath();
        ctx.arc(bay.x + bay.w - 18, bay.y + 18, 8, 0, Math.PI * 2);
        ctx.fillStyle = srv ? "#f4c430" : "#5b656d";
        ctx.fill();
        if (srv) {
          const avance = Math.min(1, (L.ahora - srv.inicio) / (srv.fin - srv.inicio));
          ctx.fillStyle = "#1b2025";
          ctx.fillRect(bay.x + 6, bay.y + bay.h - 8, bay.w - 12, 4);
          ctx.fillStyle = cuello ? "#e0533d" : "#e3c08d";
          ctx.fillRect(bay.x + 6, bay.y + bay.h - 8, (bay.w - 12) * avance, 4);
          const etapa = avance > 0.6 ? i + 1 : i;
          mover(srv.silla.id, bay.x + 32, bay.y + bay.h / 2 - 3, etapa, i === 0 ? g.entrada : null);
        }
      });

      est.cola.forEach((silla, q) => {
        const p = posCola(g, i, q);
        if (p) mover(silla.id, p.x, p.y, i, i === 0 ? g.entrada : null);
      });
      const n = est.cola.length;
      const tono = n >= 8 ? "#e0533d" : n >= 3 ? "#f4c430" : "#a3a9ad";
      rotulo(ctx, `cola ${n}`, ge.colaX - 30, h - 16, tono, 12);
    });

    for (const id of S.visual.keys()) if (!presentes.has(id)) S.visual.delete(id);
    for (const [id, v] of S.visual) dibujarSilla(ctx, v.x, v.y, v.etapa, K_SILLA);

    // Finished chairs rolling to dispatch
    S.salientes = S.salientes.filter((s) => {
      s.x += (g.despacho.x - s.x) * k;
      s.y += (g.despacho.y - s.y) * k;
      dibujarSilla(ctx, s.x, s.y, 4, K_SILLA);
      return Math.hypot(g.despacho.x - s.x, g.despacho.y - s.y) > 6;
    });

    if (S.pausado) {
      ctx.fillStyle = "rgba(24,29,33,.75)";
      ctx.fillRect(w / 2 - 70, 8, 140, 26);
      rotulo(ctx, "EN PAUSA", w / 2, 26, "#f4c430", 14, true);
    }
  }

  function rotulo(ctx, texto, x, y, color, size = 12, display = false) {
    ctx.fillStyle = color;
    ctx.font = display ? `700 ${size}px "Barlow Condensed", sans-serif` : `${size}px "IBM Plex Mono", monospace`;
    ctx.textAlign = "center";
    ctx.fillText(texto, x, y);
  }

  /* ---------- Charts ---------- */

  function grafico(canvas, series, referencia) {
    const { ctx, w, h } = ajustarCanvas(canvas);
    const m = { i: 36, d: 10, a: 8, b: 22 };
    ctx.clearRect(0, 0, w, h);
    const n = S.muestras.length;
    let ymax = 1;
    for (const s of series) for (const v of s.valores) ymax = Math.max(ymax, v);
    if (referencia) ymax = Math.max(ymax, referencia.valor * 1.3);
    ymax = Math.ceil((ymax * 1.1) / 4) * 4; // four integer ticks
    const X = (i) => m.i + (i / Math.max(MIN_VENTANA - 1, n - 1)) * (w - m.i - m.d);
    const Y = (v) => h - m.b - (v / ymax) * (h - m.a - m.b);

    ctx.font = '10px "IBM Plex Mono", monospace';
    ctx.fillStyle = "#a3a9ad";
    ctx.strokeStyle = "#3a444d";
    ctx.textAlign = "right";
    for (let t = 0; t <= 4; t++) {
      const v = (ymax * t) / 4;
      ctx.beginPath(); ctx.moveTo(m.i, Y(v) + 0.5); ctx.lineTo(w - m.d, Y(v) + 0.5); ctx.stroke();
      ctx.fillText(fmt(v, 0), m.i - 4, Y(v) + 3);
    }
    if (n > 1) {
      const t0 = (S.proxMuestra - PASO_MUESTRA * n) / 60;
      const t1 = t0 + (Math.max(MIN_VENTANA, n) - 1) * PASO_MUESTRA / 60;
      ctx.textAlign = "left"; ctx.fillText(`${fmt(Math.max(0, t0), 0)} h`, m.i, h - 6);
      ctx.textAlign = "right"; ctx.fillText(`${fmt(t1, 0)} h`, w - m.d, h - 6);
    }
    if (referencia) {
      ctx.save();
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = "#ece4d6";
      ctx.beginPath(); ctx.moveTo(m.i, Y(referencia.valor)); ctx.lineTo(w - m.d, Y(referencia.valor)); ctx.stroke();
      ctx.restore();
    }
    for (const s of series) {
      ctx.strokeStyle = s.color;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      s.valores.forEach((v, i) => (i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v))));
      ctx.stroke();
    }
    ctx.lineWidth = 1;
  }

  /* ---------- DOM panels ---------- */

  function construirTarjetas() {
    $("#tarjetas").innerHTML = S.cfg.estaciones.map((e, i) => `
      <article class="tarjeta${i === S.teoria.cuello ? " cuello" : ""}">
        <header><h3 style="color:${COLORES[i]}">${e.nombre}</h3>
          ${i === S.teoria.cuello ? '<span class="etiqueta">Cuello de botella</span>' : ""}</header>
        <div class="barra" title="Utilización simulada; la marca es el valor teórico"><i id="b-${i}"></i><b id="m-${i}"></b></div>
        <dl id="d-${i}"></dl>
      </article>`).join("");
    $("#leyenda-colas").innerHTML = S.cfg.estaciones
      .map((e, i) => `<span><i style="background:${COLORES[i]}"></i>${e.nombre}</span>`).join("");
    $("#leyenda-wip").innerHTML = '<span><i style="background:#e3c08d"></i>simulado</span>'
      + (S.teoria.L ? `<span><i style="background:#ece4d6"></i>L teórico = ${fmt(S.teoria.L)}</span>` : "");
  }

  function actualizarPaneles() {
    const L = S.linea, T = S.teoria;
    const met = L.metricas();
    const horas = L.ahora / 60;
    const wipAhora = L.llegadas - L.terminadas;
    const wipMedio = S.wip.n ? S.wip.suma / S.wip.n : 0;
    const flujoBajo = T.W && met.flujo_min;

    $("#indicadores").innerHTML = [
      kpi(reloj(L.ahora), "reloj de simulación (h:min)"),
      kpi(L.terminadas, "sillas terminadas"),
      kpi(wipAhora, `en la línea ahora · promedio ${fmt(wipMedio, 1)}${T.L ? ` (teo ${fmt(T.L, 1)})` : ""}`, !T.estables),
      kpi(fmt(met.throughput_h), `sillas/h producidas · máx. ${fmt(T.throughput)}`),
      kpi(flujoBajo ? `${fmt(met.flujo_min, 0)} min` : "—", `tiempo en la línea${T.W ? ` · teo ${fmt(T.W, 0)} min` : " · sin valor estable"}`),
    ].join("");

    met.estaciones.forEach((r, i) => {
      const t = T.estaciones[i];
      const est = L.estaciones[i];
      const barra = $(`#b-${i}`);
      if (!barra) return;
      barra.style.width = `${Math.min(1, r.utilizacion) * 100}%`;
      barra.className = r.utilizacion > 0.85 ? "alta" : "";
      $(`#m-${i}`).style.left = `calc(${Math.min(1, t.rho) * 100}% - 1px)`;
      $(`#d-${i}`).innerHTML = `
        <dt>Capacidad Cᵢ</dt><dd>${fmt(t.C)} sillas/h</dd>
        <dt>ρ sim / teo</dt><dd>${pct(r.utilizacion)} / ${pct(t.rho)}</dd>
        <dt>Lq sim / teo</dt><dd>${fmt(r.lq)} / ${t.teo ? fmt(t.teo.lq) : "∞"}</dd>
        <dt>Wq sim / teo</dt><dd>${fmt(r.wq_min, 1)} / ${t.teo ? fmt(t.teo.wq_min, 1) : "∞"} min</dd>
        <dt>En cola ahora</dt><dd>${est.cola.length}</dd>
        <dt>Atendidas</dt><dd>${est.atendidas}</dd>`;
    });

    $("#bitacora").innerHTML = S.log.slice().reverse().map(textoEvento).join("");

    grafico($("#graf-wip"), [{ valores: S.muestras.map((x) => x.wip), color: "#e3c08d" }],
      T.L ? { valor: T.L } : null);
    grafico($("#graf-colas"), S.cfg.estaciones.map((_, i) => ({
      valores: S.muestras.map((x) => x.colas[i]), color: COLORES[i],
    })));

    if (!$("#tab-formulas").hidden) actualizarFormulas(met, wipMedio);
  }

  function kpi(valor, texto, alerta = false) {
    return `<div class="kpi${alerta ? " alerta" : ""}"><b>${valor}</b><span>${texto}</span></div>`;
  }

  function textoEvento(e) {
    const est = S.cfg.estaciones[e.estacion]?.nombre;
    let txt;
    if (e.tipo === "llegada") txt = `Silla #${e.id} llega a la línea`;
    else if (e.tipo === "inicio") txt = `#${e.id} entra a ${est} ${e.valor > 0.05 ? `tras esperar ${fmt(e.valor, 1)} min` : "sin esperar"}`;
    else if (e.tipo === "fin") txt = `#${e.id} termina ${est}`;
    else txt = `#${e.id} sale terminada · ${fmt(e.valor, 0)} min en la línea`;
    return `<li class="${e.tipo}"><time>${reloj(e.t)}</time>${txt}</li>`;
  }

  function actualizarFormulas(met, wipMedio) {
    const T = S.teoria, lam = S.cfg.tasa_llegadas_h;
    const filas = S.cfg.estaciones.map((e, i) => {
      const t = T.estaciones[i], r = met.estaciones[i];
      const c = i === T.cuello ? ' class="cuello"' : "";
      return `<tr><td${c}>${e.nombre}</td><td>${fmt(t.lam)}</td><td>${fmt(t.mu)}</td><td>${e.recursos}</td>
        <td>${fmt(t.C)}</td><td${c}>${fmt(t.rho, 3)}</td><td>${t.teo ? fmt(t.teo.lq) : "∞"}</td><td>${fmt(r.lq)}</td>
        <td>${t.teo ? fmt(t.teo.wq_min, 1) : "∞"}</td><td>${fmt(r.wq_min, 1)}</td></tr>`;
    }).join("");
    $("#tabla-formulas").innerHTML = `<thead><tr><th>Estación</th><th>λᵢ (sillas/h)</th><th>μᵢ = 60/tᵢ</th><th>cᵢ</th>
      <th>Cᵢ = cᵢ·μᵢ</th><th>ρᵢ = λᵢ/Cᵢ</th><th>Lq teo</th><th>Lq sim</th><th>Wq teo (min)</th><th>Wq sim (min)</th></tr></thead><tbody>${filas}</tbody>`;

    const b = T.estaciones[T.cuello], be = S.cfg.estaciones[T.cuello];
    const mm1 = be.recursos === 1 && b.teo
      ? `<p>Lq = ρ² / (1 − ρ) = ${fmt(b.rho, 3)}² / ${fmt(1 - b.rho, 3)} = ${fmt(b.teo.lq)} sillas</p>
         <p>Wq = Lq / λ = ${fmt(b.teo.lq)} / ${fmt(b.lam)} h = ${fmt(b.teo.wq_min, 1)} min</p>
         <p class="nota">Si ρ pasa de 0,75 a 0,90, Lq salta de 2,25 a 8,1: la cola crece mucho más rápido que la carga.</p>`
      : b.teo
        ? `<p>Con c = ${be.recursos} se usa M/M/c (Erlang C): Lq = ${fmt(b.teo.lq, 3)}, Wq = ${fmt(b.teo.wq_min, 1)} min.</p>`
        : `<p>ρ = ${fmt(b.rho, 3)} ≥ 1: no hay régimen estable. La cola crece a razón de λ − C = ${fmt(b.lam - b.C)} sillas/h.</p>`;
    const littleSim = met.throughput_h * met.flujo_min / 60;
    $("#formulas-linea").innerHTML = `
      <div class="formula"><h3>Capacidad y cuello de botella</h3>
        <p>Cᵢ = cᵢ · 60 / tᵢ (ecuación 4)</p>
        <p>min Cᵢ = ${fmt(T.Cmin)} sillas/h en ${be.nombre}</p>
        <p>λ = ${fmt(lam, 1)} ${lam < T.Cmin ? "&lt;" : "≥"} ${fmt(T.Cmin)} → ${lam < T.Cmin ? "la línea es estable y produce λ" : "la línea se satura y produce como máximo min Cᵢ"}</p>
      </div>
      <div class="formula"><h3>${be.nombre}: ${be.recursos === 1 ? "M/M/1" : "M/M/c"}</h3>${mm1}</div>
      <div class="formula"><h3>Ley de Little: L = λ · W</h3>
        ${T.W ? `<p>Teoría: ${fmt(lam, 1)} × ${fmt(T.W, 1)} / 60 = ${fmt(T.L)} sillas</p>` : "<p>Teoría: sin régimen estable.</p>"}
        <p>Simulación: ${fmt(met.throughput_h)} × ${fmt(met.flujo_min, 1)} / 60 = ${fmt(littleSim)} sillas</p>
        <p>WIP promedio observado: ${fmt(wipMedio)} sillas</p>
        <p class="nota">Las tres cifras se acercan a medida que corre el reloj: eso es estado estacionario.</p>
      </div>`;
  }

  /* ---------- Parameters ---------- */

  function construirAjustes() {
    $("#lambda").value = S.cfg.tasa_llegadas_h;
    $("#lambda-txt").textContent = `${fmt(S.cfg.tasa_llegadas_h, 1)} sillas/h`;
    document.querySelectorAll('input[name="dist"]').forEach((r) => { r.checked = r.value === S.cfg.distribucion; });
    $("#ajuste-estaciones").innerHTML = S.cfg.estaciones.map((e, i) => `
      <fieldset><legend style="color:${COLORES[i]}">${e.nombre}</legend>
        <label>Operarios cᵢ <input type="number" min="1" max="4" step="1" value="${e.recursos}" data-i="${i}" data-campo="recursos"></label>
        <label>Tiempo medio tᵢ (min) <input type="number" min="1" max="40" step="0.5" value="${e.tiempo_min}" data-i="${i}" data-campo="tiempo_min"></label>
      </fieldset>`).join("");
    document.querySelectorAll("[data-escenario]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.escenario === S.escenario));
  }

  function cargarEscenario(clave, distribucion = "exponencial") {
    S.cfg = copiar(M.ESCENARIOS[clave]);
    S.cfg.distribucion = distribucion;
    S.escenario = distribucion === "exponencial" ? clave : null;
    construirAjustes();
    reiniciar();
  }

  function personalizar() {
    S.escenario = null;
    S.cfg.nombre = "Personalizado";
    construirAjustes();
    reiniciar();
  }

  /* ---------- Learning content ---------- */

  function construirEtapas() {
    $("#etapas").innerHTML = ETAPAS.map((t, i) => `<li><canvas data-etapa="${i}"></canvas>${t}</li>`).join("");
    document.querySelectorAll("#etapas canvas").forEach((c) => {
      const { ctx, w, h } = ajustarCanvas(c);
      dibujarSilla(ctx, w / 2, h / 2, Number(c.dataset.etapa), 1.4);
    });
  }

  function construirExperimentos() {
    const t = (clave) => calcularTeoria(M.ESCENARIOS[clave]);
    const e1 = t("E1"), e2 = t("E2"), e3 = t("E3"), sat = t("SAT");
    const nombre = (T) => M.ESCENARIOS.E1.estaciones[T.cuello].nombre;
    const kingman = ((1 + 0.3 ** 2) / 2) * (0.75 / 0.25) * 15;
    const lista = [
      { clave: "E1", titulo: "E1 · ¿Dónde se forma la cola?",
        texto: "Corré la línea base y mirá las cuatro colas. Todas las estaciones tienen la misma λ; cambia solo el tiempo de proceso.",
        espera: `Ensamblaje trabaja al ${pct(e1.estaciones[2].rho, 0)} y cada silla espera ~${fmt(e1.estaciones[2].teo.wq_min, 0)} min ahí. Corte espera ~${fmt(e1.estaciones[0].teo.wq_min, 0)} min.` },
      { clave: "E2", titulo: "E2 · Sumar un ensamblador",
        texto: "Duplicamos el recurso del cuello de botella. ¿Baja la producción de sillas por hora o solo la espera?",
        espera: `La espera en ensamblaje cae a ${fmt(e2.estaciones[2].teo.wq_min, 1)} min y el tiempo en la línea baja de ${fmt(e1.W, 0)} a ${fmt(e2.W, 0)} min. La producción sigue en ${fmt(e2.throughput, 0)} sillas/h y el nuevo cuello es ${nombre(e2)}.` },
      { clave: "E3", titulo: "E3 · Ensamblaje más rápido",
        texto: "En vez de contratar, mejoramos el método: ensamblar en 10 min en lugar de 15.",
        espera: `ρ de ensamblaje pasa a ${pct(e3.estaciones[2].rho, 0)} y su espera a ${fmt(e3.estaciones[2].teo.wq_min, 0)} min. Tiempo en la línea: ${fmt(e3.W, 0)} min. Compará con E2: ¿cuál conviene?` },
      { clave: "SAT", titulo: "Saturación · λ = 4,5 sillas/h",
        texto: "Llegan más pedidos de los que ensamblaje puede hacer. Mirá el gráfico de WIP durante varias horas.",
        espera: `Ensamblaje queda con ρ = ${fmt(sat.estaciones[2].rho, 3)} &gt; 1: su cola crece sin límite (~${fmt(4.5 - sat.estaciones[2].C, 1)} sillas más por hora) y la producción se clava en ${fmt(sat.throughput, 0)} sillas/h.` },
      { clave: "E1", dist: "lognormal", titulo: "Variabilidad · mismo ρ, menos cola",
        texto: "Mismos tiempos medios, pero procesos más regulares (CV = 0,3), como en un taller con métodos estandarizados.",
        espera: `ρ no cambia (75 %), pero la espera en ensamblaje baja hacia ~${fmt(kingman, 0)} min (aproximación de Kingman) en lugar de 45. La cola nace de la variabilidad, no solo de la carga.` },
    ];
    $("#experimentos").innerHTML = lista.map((x, i) => `
      <article class="experimento"><h3>${x.titulo}</h3><p>${x.texto}</p>
        <p class="espera"><strong>Qué deberías ver:</strong> ${x.espera}</p>
        <button data-exp="${i}">Probar en la planta</button></article>`).join("");
    $("#experimentos").addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-exp]");
      if (!b) return;
      const x = lista[Number(b.dataset.exp)];
      cargarEscenario(x.clave, x.dist || "exponencial");
      S.pausado = false;
      sincronizarPausa();
      $(".planta-zona").scrollIntoView({ behavior: calma ? "auto" : "smooth" });
    });
  }

  function construirPreguntas() {
    const p = [
      ["Si el corte trabajara el doble de rápido, ¿cuántas sillas por hora más saldrían?",
        "Ninguna. Con la línea estable la producción es igual a λ = 3 sillas/h. Acelerar una estación que no es el cuello solo reduce su propia espera (de 5,3 a ~1,1 min)."],
      ["Ensamblaje está ocupado el 75 % del tiempo. ¿Por qué hay 2,25 sillas en cola y no algo cercano a 0,75?",
        "Porque en M/M/1 Lq = ρ²/(1 − ρ): la cola crece de forma no lineal y explota cuando ρ se acerca a 1. Entre ρ = 0,75 y ρ = 0,90 la cola se multiplica por 3,6."],
      ["En E2 la producción no aumenta. Entonces, ¿qué gana la empresa con el segundo ensamblador?",
        "Menos tiempo de flujo y menos inventario en proceso (Ley de Little: L = λW). Las sillas salen antes y hay menos material parado, aunque el ritmo de salida siga siendo λ."],
      ["¿Por qué se descartan las primeras 100 h de cada réplica?",
        "Porque la línea arranca vacía y las primeras horas tienen colas más cortas que en régimen. Si se incluyeran, subestimaríamos Lq y Wq (sesgo de inicialización)."],
      ["¿Por qué se corren 30 réplicas y no una sola muy larga?",
        "Cada réplica es una observación independiente; con 30 se puede estimar la media y su desviación estándar y construir intervalos de confianza. La Tabla VIII reporta promedio ± desviación de esas 30 réplicas."],
    ];
    $("#preguntas").innerHTML = p.map(([q, r]) => `<details><summary>${q}</summary><p>${r}</p></details>`).join("");
  }

  /* ---------- Validation: the report's 30 replicas, in the browser ---------- */

  function esE1() {
    const a = M.ESCENARIOS.E1, b = S.cfg;
    return b.distribucion === "exponencial" && b.tasa_llegadas_h === a.tasa_llegadas_h
      && JSON.stringify(b.estaciones) === JSON.stringify(a.estaciones);
  }

  async function correrReplicas() {
    const boton = $("#btn-replicas"), prog = $("#progreso");
    const cfg = copiar(S.cfg), T = calcularTeoria(cfg), conPython = esE1();
    boton.disabled = true;
    prog.hidden = false;
    const res = [];
    const rng = M.generador(S.semilla);
    for (let i = 0; i < 30; i++) {
      res.push(M.simular(cfg, Math.floor(rng.exponencial(1) * 1e9), 1000 * 60, 100 * 60));
      prog.value = i + 1;
      await new Promise((r) => setTimeout(r, 0));
    }
    const media = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length;
    const desv = (xs) => { const m = media(xs); return Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / (xs.length - 1)); };
    const err = (s, t) => (t ? `${fmt(Math.abs(s - t) / t * 100)} %` : "—");
    const filas = cfg.estaciones.map((e, i) => {
      const col = (k) => res.map((r) => r.estaciones[i][k]);
      const [u, lq, wq] = ["utilizacion", "lq", "wq_min"].map(col);
      const teo = T.estaciones[i].teo, py = PYTHON_E1.estaciones[i];
      return `<tr><td${i === T.cuello ? ' class="cuello"' : ""}>${e.nombre}</td>
        <td>${pct(media(u))} ± ${fmt(desv(u) * 100, 1)}</td><td>${teo ? pct(teo.utilizacion) : "≥ 100 %"}</td><td>${err(media(u), teo?.utilizacion)}</td>
        <td>${fmt(media(lq))} ± ${fmt(desv(lq))}</td><td>${teo ? fmt(teo.lq) : "∞"}</td><td>${err(media(lq), teo?.lq)}</td>
        <td>${fmt(media(wq), 1)} ± ${fmt(desv(wq), 1)}</td><td>${teo ? fmt(teo.wq_min, 1) : "∞"}</td><td>${err(media(wq), teo?.wq_min)}</td>
        ${conPython ? `<td>${pct(py.utilizacion)}</td><td>${fmt(py.lq)}</td><td>${fmt(py.wq_min, 1)}</td>` : ""}</tr>`;
    }).join("");
    $("#tabla-validacion").innerHTML = `<thead><tr><th>Estación</th><th>ρ web</th><th>ρ teo</th><th>Error</th>
      <th>Lq web</th><th>Lq teo</th><th>Error</th><th>Wq web (min)</th><th>Wq teo</th><th>Error</th>
      ${conPython ? "<th>ρ Python</th><th>Lq Python</th><th>Wq Python</th>" : ""}</tr></thead><tbody>${filas}</tbody>`;
    const th = res.map((r) => r.throughput_h), fl = res.map((r) => r.flujo_min);
    $("#nota-validacion").innerHTML = `Producción: ${fmt(media(th), 3)} sillas/h (teoría ${fmt(T.throughput, 3)}${conPython ? `, Python ${fmt(PYTHON_E1.throughput_h, 3)}` : ""}).
      Tiempo en la línea: ${fmt(media(fl), 1)} ± ${fmt(desv(fl), 1)} min (teoría ${T.W ? fmt(T.W, 1) : "sin régimen estable"}${conPython ? `, Python ${fmt(PYTHON_E1.flujo_min, 1)}` : ""}).
      Los valores web y Python no son idénticos porque cada generador produce otra secuencia aleatoria; ambos deben quedar cerca de la teoría y dentro de la variación entre réplicas.`;
    boton.disabled = false;
  }

  /* ---------- Wiring ---------- */

  function sincronizarPausa() {
    $("#btn-pausa").textContent = S.pausado ? "Reanudar" : "Pausar";
    $("#btn-paso").disabled = !S.pausado;
  }

  function conectar() {
    $("#btn-pausa").addEventListener("click", () => { S.pausado = !S.pausado; sincronizarPausa(); });
    $("#btn-paso").addEventListener("click", () => {
      S.linea.siguienteEvento();
      drenarEventos();
      actualizarPaneles();
    });
    $("#btn-reiniciar").addEventListener("click", reiniciar);
    $("#btn-semilla").addEventListener("click", () => { S.semilla += 1; reiniciar(); });
    const vel = $("#velocidad");
    const mostrarVel = () => {
      S.velocidad = VELOCIDADES[Number(vel.value)];
      $("#velocidad-txt").textContent = S.velocidad >= 60 ? `1 s = ${fmt(S.velocidad / 60, 0)} h` : `1 s = ${S.velocidad} min`;
    };
    vel.addEventListener("input", mostrarVel);
    mostrarVel();

    document.querySelectorAll("[data-escenario]").forEach((b) =>
      b.addEventListener("click", () => cargarEscenario(b.dataset.escenario)));
    $("#lambda").addEventListener("input", (ev) => {
      S.cfg.tasa_llegadas_h = Number(ev.target.value);
      $("#lambda-txt").textContent = `${fmt(S.cfg.tasa_llegadas_h, 1)} sillas/h`;
    });
    $("#lambda").addEventListener("change", personalizar);
    document.querySelectorAll('input[name="dist"]').forEach((r) => r.addEventListener("change", () => {
      S.cfg.distribucion = r.value;
      personalizar();
    }));
    $("#ajuste-estaciones").addEventListener("change", (ev) => {
      const inp = ev.target;
      const v = Number(inp.value);
      const min = Number(inp.min), max = Number(inp.max);
      if (!Number.isFinite(v) || v < min || v > max) { construirAjustes(); return; }
      S.cfg.estaciones[Number(inp.dataset.i)][inp.dataset.campo] = inp.dataset.campo === "recursos" ? Math.round(v) : v;
      personalizar();
    });

    document.querySelectorAll('[role="tab"]').forEach((t) => t.addEventListener("click", () => {
      document.querySelectorAll('[role="tab"]').forEach((x) => x.setAttribute("aria-selected", x === t));
      document.querySelectorAll('[role="tabpanel"]').forEach((p) => { p.hidden = p.id !== `tab-${t.dataset.tab}`; });
      actualizarPaneles();
    }));
    $("#btn-replicas").addEventListener("click", correrReplicas);
  }

  conectar();
  construirAjustes();
  construirEtapas();
  construirExperimentos();
  construirPreguntas();
  reiniciar();
  requestAnimationFrame(cuadro);
})();
