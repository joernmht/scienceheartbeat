/*
 * science heartbeat — dashboard engine.
 *
 * The document (nodes, edges, pulses, palette, time bounds) is produced
 * deterministically by the Python pipeline. This script is a *pure function*
 * of that document and the timeline cursor: the visual state at any cursor
 * position is reproducible. Real wall-clock time is used only to animate the
 * cursor smoothly and for idle twinkle; any randomness is seeded so even the
 * starfield is identical across runs.
 */
(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("hb-data").textContent);

  var stage = document.getElementById("stage");
  var ctx = stage.getContext("2d");
  var ecg = document.getElementById("ecg");
  var ectx = ecg.getContext("2d");
  var tooltip = document.getElementById("tooltip");
  var clockEl = document.getElementById("clock");
  var legendEl = document.getElementById("legend");
  var nowEl = document.getElementById("nowplaying");
  var emptyEl = document.getElementById("empty");
  var playBtn = document.getElementById("playpause");
  var speedsEl = document.getElementById("speeds");
  var scrub = document.getElementById("scrub");
  var eventListEl = document.getElementById("eventlist");
  var filtersEl = document.getElementById("filters");
  var rangesEl = document.getElementById("ranges");
  var legendToggle = document.getElementById("legendToggle");
  var listToggle = document.getElementById("listToggle");
  var drawerHandle = document.getElementById("drawerHandle");

  // --- theme tokens (read from CSS so the canvas follows the device theme) -
  // The TUD Chair design lives in style.css; the Canvas engine reads the same
  // custom properties here so the glow / starfield / ECG recolour with the
  // light/dark appearance instead of carrying hard-coded hex.
  function parseRgb(s, fallback) {
    var p = String(s).split(",");
    if (p.length < 3) return fallback;
    return [parseInt(p[0], 10) || 0, parseInt(p[1], 10) || 0, parseInt(p[2], 10) || 0];
  }
  var THEME;
  function readTheme() {
    var cs = getComputedStyle(document.documentElement);
    function v(name, fallback) {
      var got = cs.getPropertyValue(name).trim();
      return got || fallback;
    }
    THEME = {
      bg0: v("--canvas-bg-0", "#0b2a63"),
      bg1: v("--canvas-bg-1", "#00103a"),
      star: parseRgb(v("--star-rgb", "130,175,225"), [130, 175, 225]),
      edge: parseRgb(v("--edge-rgb", "90,150,185"), [90, 150, 185]),
      node: parseRgb(v("--node-rgb", "140,170,215"), [140, 170, 215]),
      accent: parseRgb(v("--accent-rgb", "54,184,191"), [54, 184, 191]),
    };
  }
  readTheme();
  var darkMq = window.matchMedia("(prefers-color-scheme: dark)");
  if (darkMq.addEventListener) darkMq.addEventListener("change", readTheme);
  else if (darkMq.addListener) darkMq.addListener(readTheme);

  // --- event-type metadata (label + sidebar filter group) ----------------
  var EVENT_META = {
    commit: { label: "commit", group: "commits" },
    sync: { label: "sync", group: "syncs" },
    loop_run: { label: "loop", group: "loops" },
    message: { label: "message", group: "messages" },
    session: { label: "session", group: "sessions" },
    access: { label: "access", group: "sessions" },
  };
  // Filter chips: id -> matching event kinds (null = all).
  var FILTERS = [
    { id: "all", label: "all", kinds: null },
    { id: "commits", label: "commits", kinds: ["commit"] },
    { id: "syncs", label: "syncs", kinds: ["sync"] },
    { id: "loops", label: "loops", kinds: ["loop_run"] },
    { id: "messages", label: "msgs", kinds: ["message"] },
    { id: "sessions", label: "sessions", kinds: ["session", "access"] },
  ];

  // --- deterministic PRNG (mulberry32) for purely-cosmetic twinkle -------
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // --- indexes -----------------------------------------------------------
  var nodeById = {};
  DATA.nodes.forEach(function (n) { nodeById[n.id] = n; });
  var pulses = DATA.pulses; // sorted by (t, id)
  var pulseTimes = pulses.map(function (p) { return p.t; });

  // Absolute bounds of the data; the *view* bounds below can be narrowed to a
  // trailing range (e.g. the last week) without rescanning.
  var FULL_T0 = DATA.t_min, FULL_T1 = DATA.t_max;
  var DAY = 86400;

  // View bounds + derived animation constants — all (re)set by applyRange().
  var T0, T1, span, TAU, RISE, WINDOW, TRAVEL, TAIL, DOMAIN_END;
  var rangeDays = null;                            // null = all time

  var hasPulses = pulses.length > 0;
  if (!hasPulses) {
    emptyEl.style.display = "flex";
    emptyEl.textContent = "No activity found in the scanned sources yet.";
    var sb = document.getElementById("sidebar");
    if (sb) sb.style.display = "none";
  }

  // playback state (cursor / baseSpeed are initialised by applyRange below)
  var cursor = FULL_T0;
  var playing = hasPulses;
  var multiplier = 1;
  var baseSpeed = 1; // recomputed per range: play the whole window in ~26s at 1x
  var lastFrame = 0;

  // view transform (world -> screen)
  var view = { scale: 1, ox: 0, oy: 0, fit: 1, cx: 0, cy: 0 };
  var userScale = 1, userOX = 0, userOY = 0;

  // --- sizing ------------------------------------------------------------
  function resize() {
    readTheme();   // appearance / token changes are cheap to re-read here
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    stage.width = Math.floor(window.innerWidth * dpr);
    stage.height = Math.floor(window.innerHeight * dpr);
    stage.style.width = window.innerWidth + "px";
    stage.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var er = ecg.getBoundingClientRect();
    ecg.width = Math.floor(er.width * dpr);
    ecg.height = Math.floor(er.height * dpr);
    ectx.setTransform(dpr, 0, 0, dpr, 0, 0);

    fitView();
  }

  function fitView() {
    var w = window.innerWidth, h = window.innerHeight;
    var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    DATA.nodes.forEach(function (n) {
      if (n.x < minX) minX = n.x; if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y; if (n.y > maxY) maxY = n.y;
    });
    if (!isFinite(minX)) { minX = -1; maxX = 1; minY = -1; maxY = 1; }
    var bw = Math.max(maxX - minX, 1), bh = Math.max(maxY - minY, 1);
    var pad = 150;
    var fit = Math.min((w - pad * 2) / bw, (h - 220) / bh);
    view.fit = isFinite(fit) && fit > 0 ? fit : 1;
    view.cx = (minX + maxX) / 2;
    view.cy = (minY + maxY) / 2;
  }

  function toScreen(x, y) {
    var s = view.fit * userScale;
    return [
      (x - view.cx) * s + window.innerWidth / 2 + userOX,
      (y - view.cy) * s + (window.innerHeight - 70) / 2 + userOY,
    ];
  }
  function toWorld(sx, sy) {
    var s = view.fit * userScale;
    return [
      (sx - window.innerWidth / 2 - userOX) / s + view.cx,
      (sy - (window.innerHeight - 70) / 2 - userOY) / s + view.cy,
    ];
  }

  // --- colour helpers ----------------------------------------------------
  function hexToRgb(hex) {
    var h = hex.replace("#", "");
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  var rgbCache = {};
  function rgb(hex) { return rgbCache[hex] || (rgbCache[hex] = hexToRgb(hex)); }
  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }

  // --- pulse window lookup (binary search on sorted times) ---------------
  function lowerBound(arr, target) {
    var lo = 0, hi = arr.length;
    while (lo < hi) { var mid = (lo + hi) >> 1; if (arr[mid] < target) lo = mid + 1; else hi = mid; }
    return lo;
  }

  function envelope(dt) {
    if (dt < 0) return 0;
    if (dt < RISE) return dt / RISE;
    return Math.exp(-(dt - RISE) / TAU);
  }

  // Per-node weight along a pulse path: source dim, destination bright, any
  // waypoint brightest. Works for any path length (commits travel 3 nodes,
  // activity events 1-2).
  function pathWeight(k, n) {
    if (n <= 1) return 1.0;
    if (k === 0) return 0.6;
    if (k === n - 1) return 0.9;
    return 1.0;
  }

  // accumulate per-node glow + blended colour; collect travelling pulses
  function computeState() {
    var glow = {};      // id -> intensity
    var col = {};       // id -> [r,g,b] weighted accumulation
    var weight = {};    // id -> total weight
    var travels = [];
    var fresh = null, freshDt = Infinity;

    var start = lowerBound(pulseTimes, cursor - WINDOW);
    var end = lowerBound(pulseTimes, cursor + 1e-6);
    for (var i = start; i < end; i++) {
      var p = pulses[i];
      if (p.t < T0) continue; // narrowed range: ignore pulses before the window
      var dt = cursor - p.t;
      if (dt < 0) continue;
      var env = envelope(dt);
      var act = p.intensity * env;
      if (act < 0.001) continue;
      var c = rgb(p.color);
      var nodes = p.path;
      for (var k = 0; k < nodes.length; k++) {
        var id = nodes[k];
        var a = act * pathWeight(k, nodes.length);
        glow[id] = (glow[id] || 0) + a;
        weight[id] = (weight[id] || 0) + a;
        var acc = col[id] || (col[id] = [0, 0, 0]);
        acc[0] += c[0] * a; acc[1] += c[1] * a; acc[2] += c[2] * a;
      }
      if (dt <= TRAVEL) travels.push({ p: p, prog: dt / TRAVEL });
      if (dt < freshDt) { freshDt = dt; fresh = p; }
    }
    return { glow: glow, col: col, weight: weight, travels: travels, fresh: fresh, freshDt: freshDt };
  }

  function nodeColor(id, state, fallback) {
    var w = state.weight[id];
    if (!w) return fallback;
    var c = state.col[id];
    return [c[0] / w, c[1] / w, c[2] / w];
  }

  // --- background --------------------------------------------------------
  var stars = [];
  (function () {
    var rnd = mulberry32(0x9e3779b9);
    for (var i = 0; i < 140; i++) {
      stars.push({ x: rnd(), y: rnd(), r: 0.4 + rnd() * 1.3, ph: rnd() * 6.28, sp: 0.4 + rnd() * 1.2 });
    }
  })();

  function drawBackground(now) {
    var w = window.innerWidth, h = window.innerHeight;
    var g = ctx.createRadialGradient(w / 2, h * 0.42, 40, w / 2, h * 0.42, Math.max(w, h) * 0.8);
    g.addColorStop(0, THEME.bg0);
    g.addColorStop(1, THEME.bg1);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "lighter";
    for (var i = 0; i < stars.length; i++) {
      var s = stars[i];
      var tw = 0.35 + 0.35 * (0.5 + 0.5 * Math.sin(now * 0.0008 * s.sp + s.ph));
      ctx.fillStyle = rgba(THEME.star, tw * 0.5);
      ctx.beginPath();
      ctx.arc(s.x * w, s.y * h, s.r, 0, 6.2832);
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";
  }

  // --- main render -------------------------------------------------------
  // Idle core tint by node kind, so machine nodes read distinctly even when
  // they are not glowing.
  var KIND_TINT = {
    server: [255, 209, 102],
    loop: [126, 231, 135],
    bot: [92, 200, 255],
    agent: [229, 140, 255],
    repo: [200, 215, 240],
    branch: [160, 190, 230],
    committer: [196, 210, 235],
  };
  // Kinds whose labels are always drawn (the rest only when active/hovered).
  var ALWAYS_LABEL = { server: 1, repo: 1, branch: 1, loop: 1, bot: 1 };

  function nodeRadius(node) {
    switch (node.kind) {
      case "server": return 16;
      case "repo": return 13;
      case "loop": case "bot": case "agent": return 9;
      case "branch": return 8;
      default: return 6; // committer
    }
  }

  function render(now) {
    drawBackground(now);

    var state = computeState();

    // edges
    ctx.lineWidth = 1;
    for (var e = 0; e < DATA.edges.length; e++) {
      var ed = DATA.edges[e];
      var a = nodeById[ed.source], b = nodeById[ed.target];
      if (!a || !b) continue;
      var pa = toScreen(a.x, a.y), pb = toScreen(b.x, b.y);
      var lit = Math.min(1, (state.glow[ed.source] || 0) + (state.glow[ed.target] || 0));
      ctx.strokeStyle = rgba(THEME.edge, 0.06 + lit * 0.18);
      ctx.beginPath();
      ctx.moveTo(pa[0], pa[1]);
      ctx.lineTo(pb[0], pb[1]);
      ctx.stroke();
    }

    // node glow (additive)
    ctx.globalCompositeOperation = "lighter";
    for (var i = 0; i < DATA.nodes.length; i++) {
      var n = DATA.nodes[i];
      var g = Math.min(1.6, state.glow[n.id] || 0);
      if (g <= 0.002) continue;
      var pos = toScreen(n.x, n.y);
      var c = nodeColor(n.id, state, THEME.node);
      var R = nodeRadius(n) + 8 + g * 46;
      var grad = ctx.createRadialGradient(pos[0], pos[1], 0, pos[0], pos[1], R);
      grad.addColorStop(0, rgba(c, Math.min(0.9, 0.25 + g * 0.6)));
      grad.addColorStop(0.5, rgba(c, Math.min(0.45, g * 0.35)));
      grad.addColorStop(1, rgba(c, 0));
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(pos[0], pos[1], R, 0, 6.2832);
      ctx.fill();
    }

    // travelling light along the pulse path (any number of segments)
    for (var t = 0; t < state.travels.length; t++) {
      var tr = state.travels[t];
      var path = tr.p.path;
      var segs = path.length - 1;
      if (segs <= 0) continue; // single-node path: glow only, no travel
      var fseg = tr.prog * segs;
      var seg = Math.min(segs - 1, Math.floor(fseg));
      var local = fseg - seg;
      var from = nodeById[path[seg]], to = nodeById[path[seg + 1]];
      if (!from || !to) continue;
      var pf = toScreen(from.x, from.y), pt = toScreen(to.x, to.y);
      var x = pf[0] + (pt[0] - pf[0]) * local;
      var y = pf[1] + (pt[1] - pf[1]) * local;
      var cc = rgb(tr.p.color);
      var fade = (1 - tr.prog) * 0.9 + 0.1;
      var rr = 8 + tr.p.intensity * 8;
      var gr = ctx.createRadialGradient(x, y, 0, x, y, rr);
      gr.addColorStop(0, rgba(cc, 0.95 * fade));
      gr.addColorStop(1, rgba(cc, 0));
      ctx.fillStyle = gr;
      ctx.beginPath();
      ctx.arc(x, y, rr, 0, 6.2832);
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";

    // node cores + labels
    for (var j = 0; j < DATA.nodes.length; j++) {
      var nd = DATA.nodes[j];
      var p2 = toScreen(nd.x, nd.y);
      var gg = state.glow[nd.id] || 0;
      var cc2 = nodeColor(nd.id, state, THEME.node);
      var rad = nodeRadius(nd);
      // core
      var tint = KIND_TINT[nd.kind] || [200, 215, 240];
      ctx.beginPath();
      ctx.arc(p2[0], p2[1], rad, 0, 6.2832);
      ctx.fillStyle = gg > 0.02 ? rgba(cc2, 0.95) : rgba(tint, 0.55);
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = rgba([255, 255, 255], 0.35 + Math.min(0.5, gg * 0.5));
      ctx.stroke();
      // labels: structural + machine nodes always; committers/agents on demand
      var showLabel = ALWAYS_LABEL[nd.kind] || gg > 0.05 || hovered === nd.id;
      if (showLabel) {
        var bigLabel = nd.kind === "repo" || nd.kind === "server";
        ctx.font = (bigLabel ? "600 13px " : "12px ") + "ui-sans-serif, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillStyle = rgba([232, 238, 252], (nd.kind === "committer" || nd.kind === "agent") ? 0.65 : 0.9);
        ctx.shadowColor = "rgba(0,0,0,0.8)";
        ctx.shadowBlur = 6;
        ctx.fillText(nd.label, p2[0], p2[1] + rad + 15);
        ctx.shadowBlur = 0;
      }
    }

    drawECG();
    updatePanels(state);
  }

  // --- ECG waveform ------------------------------------------------------
  function drawECG() {
    var w = ecg.clientWidth, h = ecg.clientHeight;
    ectx.clearRect(0, 0, w, h);
    if (!hasPulses) return;
    var mid = h * 0.62;
    var kernel = WINDOW; // time radius contributing to each x
    var dom = DOMAIN_END - T0;
    var vals = new Float32Array(w);
    var domKind = new Array(w);
    var max = 0.0001;

    // accumulate (deterministic; pure function of pulses in the view window)
    for (var i = 0; i < pulses.length; i++) {
      var p = pulses[i];
      if (p.t < T0) continue; // narrowed range: ignore pulses before the window
      var px = ((p.t - T0) / dom) * w;
      var rad = (kernel / dom) * w;
      var x0 = Math.max(0, Math.floor(px - rad));
      var x1 = Math.min(w - 1, Math.ceil(px + rad));
      for (var x = x0; x <= x1; x++) {
        var dx = (x - px) / Math.max(rad, 1);
        var contrib = p.intensity * Math.exp(-dx * dx * 4);
        vals[x] += contrib;
        if (!domKind[x] || contrib > domKind[x].v) domKind[x] = { k: p.color, v: contrib };
      }
    }
    for (var m = 0; m < w; m++) if (vals[m] > max) max = vals[m];

    // baseline
    ectx.strokeStyle = rgba(THEME.edge, 0.18);
    ectx.lineWidth = 1;
    ectx.beginPath(); ectx.moveTo(0, mid); ectx.lineTo(w, mid); ectx.stroke();

    // filled waveform
    ectx.beginPath();
    ectx.moveTo(0, mid);
    for (var xx = 0; xx < w; xx++) {
      var v = vals[xx] / max;
      ectx.lineTo(xx, mid - v * (mid - 6));
    }
    ectx.lineTo(w, mid);
    var fg = ectx.createLinearGradient(0, 0, 0, mid);
    fg.addColorStop(0, rgba(THEME.accent, 0.3));
    fg.addColorStop(1, rgba(THEME.accent, 0.02));
    ectx.fillStyle = fg;
    ectx.fill();

    // coloured stroke by dominant kind
    ectx.lineWidth = 1.6;
    for (var s = 1; s < w; s++) {
      var dk = domKind[s];
      if (!dk) continue;
      ectx.strokeStyle = dk.k;
      ectx.globalAlpha = 0.85;
      ectx.beginPath();
      ectx.moveTo(s - 1, mid - (vals[s - 1] / max) * (mid - 6));
      ectx.lineTo(s, mid - (vals[s] / max) * (mid - 6));
      ectx.stroke();
    }
    ectx.globalAlpha = 1;

    // playhead
    var phx = ((cursor - T0) / dom) * w;
    ectx.strokeStyle = "rgba(255,255,255,0.85)";
    ectx.lineWidth = 1.5;
    ectx.beginPath(); ectx.moveTo(phx, 2); ectx.lineTo(phx, h - 2); ectx.stroke();
    ectx.fillStyle = "#fff";
    ectx.beginPath(); ectx.arc(phx, 6, 3, 0, 6.2832); ectx.fill();
  }

  // --- panels ------------------------------------------------------------
  var lastFreshId = null;
  function updatePanels(state) {
    // clock
    var d = new Date(cursor * 1000);
    clockEl.innerHTML = hasPulses
      ? "<b>" + d.toISOString().slice(0, 10) + "</b> " + d.toISOString().slice(11, 19) + " UTC"
      : "";
    // scrub position
    scrub.value = String(Math.round(((cursor - T0) / Math.max(1, DOMAIN_END - T0)) * 1000));

    // now playing
    var f = state.fresh;
    if (f && state.freshDt < TAU * 1.5) {
      if (f.id !== lastFreshId) {
        lastFreshId = f.id;
        var catColor = DATA.palette[f.category] || "#9fb0c0";
        nowEl.innerHTML =
          '<span class="np-kind" style="background:' + catColor + '">' + escapeHtml(f.category) +
          "</span>" +
          '<div class="np-title">' + escapeHtml(f.title) + "</div>" +
          '<div class="np-meta">' + metaLine(f) + "</div>";
        setActiveRow(f.id);
      }
      nowEl.classList.remove("idle");
    } else {
      nowEl.classList.add("idle");
      lastFreshId = null;
    }
  }

  // The detail line for a pulse — commit churn for commits, the event's own
  // redacted detail for everything else.
  function metaLine(p) {
    var source = "<b>" + escapeHtml(p.source) + "</b>";
    if (p.event === "commit") {
      var repoL = nodeById[p.repo] ? nodeById[p.repo].label : "";
      var branchL = nodeById[p.branch] ? nodeById[p.branch].label : "";
      return source + " &middot; " + escapeHtml(repoL) + " / " + escapeHtml(branchL) +
        ' &middot; <span style="font-family:ui-monospace,monospace">' + escapeHtml(p.ref.slice(0, 7)) +
        "</span> &middot; +" + p.insertions + " −" + p.deletions;
    }
    var bits = [source];
    if (p.repo && nodeById[p.repo]) bits.push(escapeHtml(nodeById[p.repo].label));
    if (p.detail) bits.push(escapeHtml(p.detail));
    return bits.join(" &middot; ");
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // --- legend (change kinds + activity categories) -----------------------
  // Full-range event counts drive which filter chips exist (so a chip never
  // disappears mid-session); the windowed `catCounts` drive the legend totals,
  // which reflect the currently selected time range.
  var fullEventCounts = {};
  pulses.forEach(function (p) {
    fullEventCounts[p.event] = (fullEventCounts[p.event] || 0) + 1;
  });
  var catCounts = {};
  var windowCount = 0;
  function computeCounts() {
    catCounts = {};
    windowCount = 0;
    pulses.forEach(function (p) {
      if (p.t < T0) return;
      catCounts[p.category] = (catCounts[p.category] || 0) + 1;
      windowCount++;
    });
  }

  function buildLegend() {
    var changeOrder = ["code", "tests", "docs", "build", "deps", "config", "data", "assets", "other"];
    var eventOrder = ["push", "pull", "loop-ok", "loop-fail", "msg-in", "msg-out", "session", "access"];
    function rows(keys) {
      var h = "";
      keys.forEach(function (k) {
        if (!catCounts[k]) return;
        var col = DATA.palette[k] || "#9fb0c0";
        h += '<div class="legend-row"><span class="sw" style="background:' + col +
          ";color:" + col + '"></span><span class="nm">' + k + '</span><span class="ct">' +
          catCounts[k] + "</span></div>";
      });
      return h;
    }
    var changeHtml = rows(changeOrder), eventHtml = rows(eventOrder);
    var html = "";
    if (changeHtml) html += "<h4>changes</h4>" + changeHtml;
    if (eventHtml) html += "<h4>activity</h4>" + eventHtml;
    legendEl.innerHTML = html;
    if (!hasPulses) legendEl.style.display = "none";
  }

  // --- activity / commit list (the side rail) ----------------------------
  var activeFilter = "all";
  var rowById = {};
  var activeRowId = null;

  function shortTime(t) {
    var iso = new Date(t * 1000).toISOString();
    return iso.slice(5, 10) + " " + iso.slice(11, 16);
  }

  function eventSub(p) {
    var parts = [p.source];
    if (p.repo && nodeById[p.repo]) parts.push(nodeById[p.repo].label);
    if (p.event === "commit") parts.push("+" + p.insertions + " −" + p.deletions);
    else if (p.detail) parts.push(p.detail);
    return parts.join(" · ");
  }

  function seekTo(t) {
    cursor = t;
    playing = false;
    playBtn.textContent = "▶";
  }

  function setActiveRow(id) {
    if (activeRowId === id) return;
    if (activeRowId && rowById[activeRowId]) rowById[activeRowId].classList.remove("active");
    activeRowId = id;
    var row = rowById[id];
    if (!row) return;
    row.classList.add("active");
    if (playing) {
      var top = row.offsetTop, hh = row.offsetHeight;
      if (top < eventListEl.scrollTop || top + hh > eventListEl.scrollTop + eventListEl.clientHeight) {
        eventListEl.scrollTop = top - eventListEl.clientHeight / 2 + hh / 2;
      }
    }
  }

  function buildEventList() {
    var kinds = null;
    FILTERS.forEach(function (f) { if (f.id === activeFilter) kinds = f.kinds; });
    rowById = {};
    var frag = document.createDocumentFragment();
    var shown = 0;
    for (var i = pulses.length - 1; i >= 0; i--) {
      var p = pulses[i];
      if (p.t < T0) continue; // narrowed range: only events inside the window
      if (kinds && kinds.indexOf(p.event) === -1) continue;
      shown++;
      var row = document.createElement("div");
      row.className = "ev-row";
      var col = DATA.palette[p.category] || "#9fb0c0";
      row.innerHTML =
        '<span class="ev-dot" style="background:' + col + ";color:" + col + '"></span>' +
        '<div class="ev-body"><div class="ev-title">' + escapeHtml(p.title) + "</div>" +
        '<div class="ev-sub">' + escapeHtml(eventSub(p)) + "</div></div>" +
        '<span class="ev-time">' + shortTime(p.t) + "</span>";
      (function (pp, rr) {
        rr.addEventListener("click", function () { seekTo(pp.t); setActiveRow(pp.id); });
      })(p, row);
      rowById[p.id] = row;
      frag.appendChild(row);
    }
    eventListEl.innerHTML = "";
    if (!shown) eventListEl.innerHTML = '<div class="ev-empty">no events</div>';
    else eventListEl.appendChild(frag);
    if (activeRowId && rowById[activeRowId]) rowById[activeRowId].classList.add("active");
  }

  (function buildFilters() {
    FILTERS.forEach(function (f) {
      if (f.kinds && !f.kinds.some(function (k) { return fullEventCounts[k]; })) return; // skip empty
      var b = document.createElement("button");
      b.textContent = f.label;
      if (f.id === activeFilter) b.className = "active";
      b.addEventListener("click", function () {
        activeFilter = f.id;
        Array.prototype.forEach.call(filtersEl.children, function (c) { c.classList.remove("active"); });
        b.classList.add("active");
        buildEventList();
      });
      filtersEl.appendChild(b);
    });
  })();

  // --- speed + range controls --------------------------------------------
  var spanLabelEl = null;
  var rangeButtons = [];
  (function buildControls() {
    [0.5, 1, 2, 4].forEach(function (m) {
      var b = document.createElement("button");
      b.textContent = m + "×";
      if (m === multiplier) b.className = "active";
      b.addEventListener("click", function () {
        multiplier = m;
        Array.prototype.forEach.call(speedsEl.children, function (c) { c.classList.remove("active"); });
        b.classList.add("active");
      });
      speedsEl.appendChild(b);
    });
    // trailing-window presets — "last week" is the default view, "last month" the opt-in
    [{ d: 7, l: "7d" }, { d: 30, l: "30d" }].forEach(function (r) {
      var b = document.createElement("button");
      b.textContent = r.l;
      b.addEventListener("click", function () { applyRange(r.d); });
      rangeButtons.push({ btn: b, days: r.d });
      rangesEl.appendChild(b);
    });
    spanLabelEl = document.createElement("span");
    spanLabelEl.className = "span";
    speedsEl.parentNode.appendChild(spanLabelEl);
  })();

  function updateSpanLabel() {
    if (!spanLabelEl) return;
    if (!hasPulses) { spanLabelEl.textContent = ""; return; }
    var days = Math.max(1, Math.round(span / DAY));
    var label = rangeDays != null ? ("last " + rangeDays + "d") : (days + " days");
    spanLabelEl.textContent = windowCount + " events · " + label;
  }

  // Narrow (or reset) the visible window to a trailing range and recompute all
  // range-dependent state: animation constants, cursor, legend, list and ECG.
  function applyRange(days) {
    rangeDays = days;
    T1 = FULL_T1;
    T0 = days != null ? Math.max(FULL_T0, FULL_T1 - days * DAY) : FULL_T0;
    span = Math.max(1, T1 - T0);
    TAU = Math.max(span * 0.035, 1);               // glow decay (data-seconds)
    RISE = TAU * 0.18;                              // onset time
    WINDOW = TAU * 6;                               // how far back a pulse matters
    TRAVEL = Math.max(TAU * 1.1, span * 0.02);      // edge travel duration
    TAIL = TAU * 5;                                 // post-end fade before looping
    DOMAIN_END = T1 + TAIL;
    baseSpeed = span / 26;                          // whole window in ~26s at 1x
    cursor = T0;
    computeCounts();
    buildLegend();
    buildEventList();
    updateSpanLabel();
    rangeButtons.forEach(function (rb) { rb.btn.classList.toggle("active", rb.days === rangeDays); });
  }
  applyRange(7); // default view: last week (30d is one tap away)

  playBtn.addEventListener("click", function () {
    playing = !playing;
    playBtn.textContent = playing ? "❚❚" : "▶";
    if (playing && cursor >= DOMAIN_END) cursor = T0;
  });
  playBtn.textContent = playing ? "❚❚" : "▶";

  // --- mobile chrome toggles ---------------------------------------------
  // On phones the legend is a tap-to-show overlay and the activity rail is a
  // bottom drawer; these flip body classes the CSS media query keys off.
  function toggleBody(cls, btn) {
    var on = document.body.classList.toggle(cls);
    if (btn) btn.classList.toggle("active", on);
  }
  if (legendToggle) {
    legendToggle.addEventListener("click", function () { toggleBody("legend-open", legendToggle); });
  }
  function openList() {
    var on = document.body.classList.toggle("list-open");
    if (listToggle) listToggle.classList.toggle("active", on);
  }
  if (listToggle) listToggle.addEventListener("click", openList);
  if (drawerHandle) drawerHandle.addEventListener("click", openList);

  scrub.addEventListener("input", function () {
    var frac = Number(scrub.value) / 1000;
    cursor = T0 + frac * (DOMAIN_END - T0);
    playing = false;
    playBtn.textContent = "▶";
  });

  // ECG click/drag to scrub
  function ecgSeek(clientX) {
    var r = ecg.getBoundingClientRect();
    var frac = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
    cursor = T0 + frac * (DOMAIN_END - T0);
    playing = false;
    playBtn.textContent = "▶";
  }
  var ecgDown = false;
  ecg.addEventListener("mousedown", function (e) { ecgDown = true; ecgSeek(e.clientX); });
  window.addEventListener("mousemove", function (e) { if (ecgDown) ecgSeek(e.clientX); });
  window.addEventListener("mouseup", function () { ecgDown = false; });
  ecg.addEventListener("touchstart", function (e) { ecgSeek(e.touches[0].clientX); }, { passive: true });
  ecg.addEventListener("touchmove", function (e) { e.preventDefault(); ecgSeek(e.touches[0].clientX); }, { passive: false });

  // --- pan / zoom + hover ------------------------------------------------
  var hovered = null;
  var dragging = false, dragStart = null;
  stage.addEventListener("mousedown", function (e) { dragging = true; dragStart = { x: e.clientX - userOX, y: e.clientY - userOY }; });
  window.addEventListener("mouseup", function () { dragging = false; });
  stage.addEventListener("mousemove", function (e) {
    if (dragging) {
      userOX = e.clientX - dragStart.x;
      userOY = e.clientY - dragStart.y;
      tooltip.hidden = true;
      return;
    }
    hitTest(e.clientX, e.clientY);
  });
  stage.addEventListener("mouseleave", function () { tooltip.hidden = true; hovered = null; });
  stage.addEventListener("wheel", function (e) {
    e.preventDefault();
    var w = toWorld(e.clientX, e.clientY);
    var factor = Math.exp(-e.deltaY * 0.0015);
    userScale = Math.max(0.3, Math.min(6, userScale * factor));
    var w2 = toWorld(e.clientX, e.clientY);
    var s = view.fit * userScale;
    userOX += (w2[0] - w[0]) * s;
    userOY += (w2[1] - w[1]) * s;
  }, { passive: false });
  stage.addEventListener("dblclick", function () { userScale = 1; userOX = 0; userOY = 0; });

  // touch: one finger pans the graph, two fingers pinch-zoom around their
  // midpoint — so the canvas is fully navigable on a phone.
  var touchDrag = null, pinch = null;
  function touchMid(t0, t1) { return { x: (t0.clientX + t1.clientX) / 2, y: (t0.clientY + t1.clientY) / 2 }; }
  function touchDist(t0, t1) {
    var dx = t0.clientX - t1.clientX, dy = t0.clientY - t1.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }
  stage.addEventListener("touchstart", function (e) {
    tooltip.hidden = true;
    if (e.touches.length === 1) {
      touchDrag = { x: e.touches[0].clientX - userOX, y: e.touches[0].clientY - userOY };
      pinch = null;
    } else if (e.touches.length === 2) {
      touchDrag = null;
      pinch = { dist: touchDist(e.touches[0], e.touches[1]), scale: userScale };
    }
  }, { passive: true });
  stage.addEventListener("touchmove", function (e) {
    if (e.touches.length === 1 && touchDrag) {
      e.preventDefault();
      userOX = e.touches[0].clientX - touchDrag.x;
      userOY = e.touches[0].clientY - touchDrag.y;
    } else if (e.touches.length === 2 && pinch) {
      e.preventDefault();
      var mid = touchMid(e.touches[0], e.touches[1]);
      var w = toWorld(mid.x, mid.y);
      var ratio = touchDist(e.touches[0], e.touches[1]) / Math.max(1, pinch.dist);
      userScale = Math.max(0.3, Math.min(6, pinch.scale * ratio));
      var w2 = toWorld(mid.x, mid.y);
      var s = view.fit * userScale;
      userOX += (w2[0] - w[0]) * s;
      userOY += (w2[1] - w[1]) * s;
    }
  }, { passive: false });
  stage.addEventListener("touchend", function (e) {
    if (e.touches.length === 0) { touchDrag = null; pinch = null; }
    else if (e.touches.length === 1) {
      pinch = null;
      touchDrag = { x: e.touches[0].clientX - userOX, y: e.touches[0].clientY - userOY };
    }
  });

  function hitTest(mx, my) {
    var best = null, bestD = 24 * 24;
    for (var i = 0; i < DATA.nodes.length; i++) {
      var n = DATA.nodes[i];
      var p = toScreen(n.x, n.y);
      var dx = p[0] - mx, dy = p[1] - my;
      var d = dx * dx + dy * dy;
      if (d < bestD) { bestD = d; best = n; }
    }
    hovered = best ? best.id : null;
    if (best) {
      var cnt = pulses.filter(function (p) {
        return p.node === best.id || p.source_id === best.id || (p.path && p.path.indexOf(best.id) !== -1);
      }).length;
      tooltip.innerHTML = '<div class="tt-label">' + escapeHtml(best.label) + '</div>' +
        '<div class="tt-kind">' + best.kind + (cnt ? " · " + cnt + " events" : "") + "</div>";
      tooltip.style.left = mx + "px";
      tooltip.style.top = my + "px";
      tooltip.hidden = false;
    } else {
      tooltip.hidden = true;
    }
  }

  // --- loop --------------------------------------------------------------
  function frame(now) {
    if (!lastFrame) lastFrame = now;
    var dt = Math.min(0.1, (now - lastFrame) / 1000);
    lastFrame = now;
    if (playing && hasPulses) {
      cursor += dt * baseSpeed * multiplier;
      if (cursor > DOMAIN_END) cursor = T0; // loop for a living, ambient feel
    }
    render(now);
    requestAnimationFrame(frame);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(frame);
})();
