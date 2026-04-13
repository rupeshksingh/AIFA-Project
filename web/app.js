/* global vis */

const DEFAULT_CUSTOM_JSON = `{
  "locations": ["A", "B", "C", "D"],
  "roads": [
    { "from": "A", "to": "B", "status": "clear" },
    { "from": "B", "to": "C", "status": "blocked" },
    { "from": "C", "to": "D", "status": "clear" }
  ],
  "resources": {
    "Bulldozer1": "A",
    "MedTeam1": "A"
  },
  "victims_untreated": ["D"],
  "goal_treated": ["D"]
}`;

function apiBase() {
  if (location.protocol === "file:") {
    return "http://127.0.0.1:8765";
  }
  return "";
}

function canonicalEdgeId(from, to) {
  return from < to ? `${from}|${to}` : `${to}|${from}`;
}

function edgeStyleForStatus(status) {
  const blocked = status === "blocked";
  return {
    color: { color: blocked ? "#b71c1c" : "#1b5e20" },
    dashes: blocked ? [10, 6] : false,
    title: status,
  };
}

/** @type {{ network: import('vis-network').Network | null, nodes: import('vis-data').DataSet | null, edges: import('vis-data').DataSet | null, bulldozerN: number, medN: number, inited: boolean }} */
const mapBuilder = {
  network: null,
  nodes: null,
  edges: null,
  bulldozerN: 1,
  medN: 1,
  inited: false,
};

function getActiveCustomTab() {
  const active = document.querySelector(".segmented-btn.is-active");
  return active ? active.getAttribute("data-custom-tab") : "visual";
}

function getLocationsFromBuilder() {
  if (!mapBuilder.nodes) return [];
  return mapBuilder.nodes.getIds().slice().sort();
}

function getRoadsFromBuilder() {
  if (!mapBuilder.edges) return [];
  /** @type {Map<string, { from: string, to: string, status: string }>} */
  const seen = new Map();
  mapBuilder.edges.forEach((e) => {
    const from = e.from;
    const to = e.to;
    const key = canonicalEdgeId(from, to);
    const status = e.roadStatus === "blocked" ? "blocked" : "clear";
    const a = from < to ? from : to;
    const b = from < to ? to : from;
    if (!seen.has(key)) seen.set(key, { from: a, to: b, status });
  });
  return Array.from(seen.values());
}

function serializeMapBuilderToDoc() {
  return {
    locations: getLocationsFromBuilder(),
    roads: getRoadsFromBuilder(),
    resources: collectResourcesFromDom(),
    victims_untreated: collectVictimFlags("untreated"),
    goal_treated: collectVictimFlags("goal"),
  };
}

function collectResourcesFromDom() {
  /** @type {Record<string, string>} */
  const resources = {};
  document.querySelectorAll("#resourceRows .resource-row").forEach((row) => {
    const nameInp = row.querySelector(".res-name");
    const locSel = row.querySelector(".res-loc");
    if (!nameInp || !locSel) return;
    const name = nameInp.value.trim();
    const loc = locSel.value;
    if (name && loc) resources[name] = loc;
  });
  return resources;
}

function collectVictimFlags(kind) {
  const cls = kind === "goal" ? ".vg-goal" : ".vg-untreated";
  /** @type {string[]} */
  const out = [];
  document.querySelectorAll("#victimGoalRows .victim-goal-row").forEach((row) => {
    const loc = row.getAttribute("data-location");
    const cb = row.querySelector(cls);
    if (loc && cb && cb.checked) out.push(loc);
  });
  return out.slice().sort();
}

function rebuildResourceLocationOptions() {
  const ids = getLocationsFromBuilder();
  document.querySelectorAll("#resourceRows .res-loc").forEach((sel) => {
    const cur = sel.value;
    sel.innerHTML = ids.map((id) => `<option value="${id}">${id}</option>`).join("");
    if (ids.includes(cur)) sel.value = cur;
    else if (ids.length) sel.value = ids[0];
  });
}

function rebuildVictimGoalRows() {
  const container = document.getElementById("victimGoalRows");
  if (!container || !mapBuilder.nodes) return;
  /** @type {Record<string, { u: boolean, g: boolean }>} */
  const prev = {};
  container.querySelectorAll(".victim-goal-row").forEach((row) => {
    const loc = row.getAttribute("data-location");
    if (!loc) return;
    const u = row.querySelector(".vg-untreated");
    const g = row.querySelector(".vg-goal");
    prev[loc] = { u: !!(u && u.checked), g: !!(g && g.checked) };
  });
  container.innerHTML = "";
  const ids = getLocationsFromBuilder();
  for (const loc of ids) {
    const p = prev[loc] || { u: false, g: false };
    const row = document.createElement("div");
    row.className = "victim-goal-row";
    row.setAttribute("data-location", loc);
    row.innerHTML = `
      <span class="vg-loc">${loc}</span>
      <label class="vg-label"><input type="checkbox" class="vg-untreated" ${p.u ? "checked" : ""} /> Untreated</label>
      <label class="vg-label"><input type="checkbox" class="vg-goal" ${p.g ? "checked" : ""} /> Goal</label>
    `;
    container.appendChild(row);
  }
}

function addResourceRow(defaultName) {
  const wrap = document.getElementById("resourceRows");
  if (!wrap) return;
  const row = document.createElement("div");
  row.className = "resource-row";
  row.innerHTML = `
    <input type="text" class="res-name" value="${defaultName}" spellcheck="false" />
    <select class="res-loc"></select>
    <button type="button" class="btn ghost btn-sm res-remove" aria-label="Remove resource">×</button>
  `;
  wrap.appendChild(row);
  row.querySelector(".res-remove")?.addEventListener("click", () => {
    row.remove();
  });
  rebuildResourceLocationOptions();
}

/**
 * @param {Record<string, unknown>} doc
 */
function loadDocIntoMapBuilder(doc) {
  if (!mapBuilder.nodes || !mapBuilder.edges) return;
  const locations = doc.locations;
  const roads = doc.roads;
  const resources = doc.resources;
  const victimsUntreated = doc.victims_untreated;
  const goalTreated = doc.goal_treated;
  if (!Array.isArray(locations) || !Array.isArray(roads)) {
    throw new Error("Document must include locations and roads arrays.");
  }

  mapBuilder.nodes.clear();
  mapBuilder.edges.clear();

  const locs = locations.map((x) => String(x));
  const n = locs.length;
  const cx = 280;
  const cy = 200;
  const r = n ? Math.min(150, 360 / (2 * Math.sin(Math.PI / Math.max(n, 1)))) : 0;
  locs.forEach((loc, i) => {
    const ang = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
    mapBuilder.nodes.add({
      id: loc,
      label: loc,
      x: cx + r * Math.cos(ang),
      y: cy + r * Math.sin(ang),
    });
  });

  roads.forEach((raw) => {
    if (!raw || typeof raw !== "object") return;
    const fr = String(/** @type {{ from?: string }} */ (raw).from ?? "");
    const to = String(/** @type {{ to?: string }} */ (raw).to ?? "");
    const status = /** @type {{ status?: string }} */ (raw).status === "blocked" ? "blocked" : "clear";
    if (!fr || !to || fr === to) return;
    const id = canonicalEdgeId(fr, to);
    const st = edgeStyleForStatus(status);
    mapBuilder.edges.add({
      id,
      from: fr,
      to: to,
      roadStatus: status,
      ...st,
      width: 3,
      smooth: { type: "cubicBezier", roundness: 0.2 },
    });
  });

  const resWrap = document.getElementById("resourceRows");
  if (resWrap) {
    resWrap.innerHTML = "";
    if (resources && typeof resources === "object" && !Array.isArray(resources)) {
      for (const [name, loc] of Object.entries(resources)) {
        addResourceRow(String(name));
        const last = resWrap.lastElementChild;
        const sel = last?.querySelector(".res-loc");
        const inp = last?.querySelector(".res-name");
        if (inp) inp.value = String(name);
        if (sel && locs.includes(String(loc))) sel.value = String(loc);
      }
    }
  }
  rebuildResourceLocationOptions();
  rebuildVictimGoalRows();
  if (Array.isArray(victimsUntreated)) {
    victimsUntreated.forEach((loc) => {
      const row = document.querySelector(`#victimGoalRows .victim-goal-row[data-location="${String(loc)}"]`);
      const cb = row?.querySelector(".vg-untreated");
      if (cb) cb.checked = true;
    });
  }
  if (Array.isArray(goalTreated)) {
    goalTreated.forEach((loc) => {
      const row = document.querySelector(`#victimGoalRows .victim-goal-row[data-location="${String(loc)}"]`);
      const cb = row?.querySelector(".vg-goal");
      if (cb) cb.checked = true;
    });
  }
}

function initMapBuilderNetwork() {
  if (mapBuilder.inited) return;
  const container = document.getElementById("mapBuilder");
  if (!container) return;

  mapBuilder.nodes = new vis.DataSet([]);
  mapBuilder.edges = new vis.DataSet([]);
  const data = { nodes: mapBuilder.nodes, edges: mapBuilder.edges };

  mapBuilder.network = new vis.Network(container, data, {
    physics: false,
    interaction: { hover: true, multiselect: false },
    manipulation: {
      enabled: true,
      initiallyActive: true,
      addNode(nodeData, callback) {
        const suggested = `L${mapBuilder.bulldozerN + mapBuilder.medN}`;
        const id = window.prompt("Location id (unique name)", suggested);
        if (id == null) {
          callback(null);
          return;
        }
        const trimmed = id.trim();
        if (!trimmed || mapBuilder.nodes.get(trimmed)) {
          window.alert("Enter a unique non-empty location id.");
          callback(null);
          return;
        }
        nodeData.id = trimmed;
        nodeData.label = trimmed;
        nodeData.color = { background: "#e3f2fd", border: "#1565c0" };
        nodeData.borderWidth = 2;
        callback(nodeData);
        queueMicrotask(() => {
          rebuildResourceLocationOptions();
          rebuildVictimGoalRows();
        });
      },
      addEdge(edgeData, callback) {
        const from = edgeData.from;
        const to = edgeData.to;
        if (from === to) {
          callback(null);
          return;
        }
        const id = canonicalEdgeId(from, to);
        if (mapBuilder.edges.get(id)) {
          callback(null);
          return;
        }
        const st = edgeStyleForStatus("clear");
        edgeData.id = id;
        edgeData.from = from;
        edgeData.to = to;
        edgeData.roadStatus = "clear";
        edgeData.width = 3;
        edgeData.smooth = { type: "cubicBezier", roundness: 0.2 };
        Object.assign(edgeData, st);
        callback(edgeData);
      },
      deleteNode(nodeData, callback) {
        callback(nodeData);
        queueMicrotask(() => {
          rebuildResourceLocationOptions();
          rebuildVictimGoalRows();
        });
      },
      deleteEdge: true,
    },
    nodes: {
      shape: "box",
      margin: 12,
      font: { size: 13, face: "Source Sans 3, Segoe UI, sans-serif" },
      color: { background: "#e3f2fd", border: "#1565c0", highlight: { background: "#bbdefb", border: "#0d47a1" } },
      borderWidth: 2,
    },
    edges: {
      smooth: { type: "cubicBezier", roundness: 0.2 },
      width: 3,
    },
  });

  mapBuilder.network.on("dragEnd", () => {
    rebuildResourceLocationOptions();
  });

  mapBuilder.inited = true;
}

/**
 * @param {string[][]} facts
 * @param {Record<string, { x: number; y: number }> | null} layoutPositions
 */
function factsToGraph(facts, layoutPositions) {
  const nodeMap = new Map();
  const edgeKeys = new Set();
  /** @type {{ from: string; to: string; color: { color: string }; width: number; dashes: boolean | number[]; smooth: { type: string; roundness: number } }[]} */
  const edges = [];

  function ensureNode(id) {
    if (!nodeMap.has(id)) {
      nodeMap.set(id, { id, label: String(id) });
    }
  }

  function edgeBlocked(u, v) {
    return facts.some(
      (f) =>
        f[0] === "blocked" &&
        f.length >= 3 &&
        ((f[1] === u && f[2] === v) || (f[1] === v && f[2] === u)),
    );
  }

  function edgeClear(u, v) {
    return facts.some(
      (f) =>
        f[0] === "clear" &&
        f.length >= 3 &&
        ((f[1] === u && f[2] === v) || (f[1] === v && f[2] === u)),
    );
  }

  for (const f of facts) {
    if (f[0] === "connected" && f.length >= 3) {
      const u = f[1];
      const v = f[2];
      ensureNode(u);
      ensureNode(v);
      const key = u < v ? `${u}|${v}` : `${v}|${u}`;
      if (edgeKeys.has(key)) continue;
      edgeKeys.add(key);
      let color = "#757575";
      if (edgeBlocked(u, v)) color = "#c62828";
      else if (edgeClear(u, v)) color = "#2e7d32";
      const blocked = edgeBlocked(u, v);
      edges.push({
        from: u,
        to: v,
        color: { color },
        width: 3,
        dashes: blocked ? [10, 6] : false,
        smooth: { type: "cubicBezier", roundness: 0.15 },
      });
    }
  }

  for (const n of nodeMap.values()) {
    n.label = String(n.id);
  }

  for (const f of facts) {
    if (f[0] === "at" && f.length >= 3) {
      const resource = f[1];
      const loc = f[2];
      ensureNode(loc);
      const node = nodeMap.get(loc);
      node.label += `\n[${resource}]`;
    } else if (f[0] === "victims_untreated" && f.length >= 2) {
      ensureNode(f[1]);
      nodeMap.get(f[1]).label += "\n· Untreated victims";
    } else if (f[0] === "victims_treated" && f.length >= 2) {
      ensureNode(f[1]);
      nodeMap.get(f[1]).label += "\n· Treated";
    }
  }

  /** @type {Map<string, 'untreated' | 'treated' | null>} */
  const victimAt = new Map();
  for (const f of facts) {
    if (f[0] === "victims_untreated" && f.length >= 2) victimAt.set(f[1], "untreated");
  }
  for (const f of facts) {
    if (f[0] === "victims_treated" && f.length >= 2) victimAt.set(f[1], "treated");
  }

  const nodes = Array.from(nodeMap.values()).map((n) => {
    const p = layoutPositions && layoutPositions[n.id];
    const vs = victimAt.get(n.id);
    let bg = "#e3f2fd";
    let border = "#1565c0";
    if (vs === "treated") {
      bg = "#c8e6c9";
      border = "#2e7d32";
    } else if (vs === "untreated") {
      bg = "#ffe0b2";
      border = "#ef6c00";
    }
    const atHere = facts.filter((f) => f[0] === "at" && f.length >= 3 && f[2] === n.id).length;
    const nodeOut = {
      ...n,
      color: {
        background: bg,
        border,
        highlight: { background: bg, border: "#0d47a1" },
      },
      borderWidth: atHere > 0 ? 3 : 2,
      shape: "box",
      margin: 12,
      font: { size: 13, multi: true, face: "Source Sans 3, Segoe UI, sans-serif" },
    };
    if (p) {
      return {
        ...nodeOut,
        x: p.x,
        y: p.y,
        fixed: { x: true, y: true },
      };
    }
    return nodeOut;
  });

  return { nodes, edges };
}

const playback = {
  network: null,
  layoutPositions: null,
  steps: [],
  index: 0,
};

function destroyNetwork() {
  if (playback.network) {
    playback.network.destroy();
    playback.network = null;
  }
  playback.layoutPositions = null;
}

const playbackOptions = {
  physics: {
    enabled: true,
    stabilization: { iterations: 200 },
  },
  layout: { randomSeed: 42 },
  nodes: {
    shape: "box",
    margin: 12,
    font: { size: 13, multi: true, face: "Source Sans 3, Segoe UI, sans-serif" },
  },
  edges: {
    smooth: { type: "cubicBezier", roundness: 0.15 },
    width: 3,
  },
};

/**
 * @param {HTMLElement} container
 */
function renderCurrentStep(container) {
  const step = playback.steps[playback.index];
  if (!step) return;

  const { nodes, edges } = factsToGraph(step.facts, playback.layoutPositions);

  if (!playback.network) {
    const data = {
      nodes: new vis.DataSet(nodes),
      edges: new vis.DataSet(edges),
    };
    playback.network = new vis.Network(container, data, { ...playbackOptions });

    playback.network.once("stabilizationIterationsDone", () => {
      playback.layoutPositions = playback.network.getPositions();
      playback.network.setOptions({ physics: false });
      const updates = Object.keys(playback.layoutPositions).map((id) => ({
        id,
        x: playback.layoutPositions[id].x,
        y: playback.layoutPositions[id].y,
        fixed: { x: true, y: true },
      }));
      data.nodes.update(updates);
    });
  } else {
    playback.network.setData({
      nodes: new vis.DataSet(nodes),
      edges: new vis.DataSet(edges),
    });
    playback.network.setOptions({ physics: false });
  }
}

function setStepControls() {
  const prev = document.getElementById("stepPrev");
  const next = document.getElementById("stepNext");
  const label = document.getElementById("stepLabel");
  const max = playback.steps.length - 1;
  if (prev) prev.disabled = playback.index <= 0;
  if (next) next.disabled = playback.index >= max;
  const step = playback.steps[playback.index];
  if (label) {
    label.textContent = step ? `${playback.index + 1} / ${playback.steps.length} — ${step.title}` : "";
  }
}

function syncPlaybackUi() {
  const container = document.getElementById("graph");
  if (!container || playback.steps.length === 0) return;
  renderCurrentStep(container);
  setStepControls();
}

function bindCustomTabs() {
  document.querySelectorAll("[data-custom-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-custom-tab");
      document.querySelectorAll("[data-custom-tab]").forEach((b) => {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      const visPanel = document.getElementById("customVisualPanel");
      const jsonPanel = document.getElementById("customJsonPanel");
      if (visPanel) visPanel.classList.toggle("hidden", tab !== "visual");
      if (jsonPanel) jsonPanel.classList.toggle("hidden", tab !== "json");
    });
  });
}

function bindMapBuilderControls() {
  initMapBuilderNetwork();

  document.getElementById("toggleRoadBtn")?.addEventListener("click", () => {
    if (!mapBuilder.network || !mapBuilder.edges) return;
    const sel = mapBuilder.network.getSelection();
    const eid = sel.edges[0];
    if (!eid) {
      window.alert("Select a road edge on the map first (click the edge).");
      return;
    }
    const e = mapBuilder.edges.get(eid);
    if (!e) return;
    const next = e.roadStatus === "blocked" ? "clear" : "blocked";
    const st = edgeStyleForStatus(next);
    mapBuilder.edges.update({
      id: eid,
      roadStatus: next,
      ...st,
      width: 3,
      smooth: { type: "cubicBezier", roundness: 0.2 },
    });
  });

  document.getElementById("loadExampleMapBtn")?.addEventListener("click", () => {
    try {
      loadDocIntoMapBuilder(JSON.parse(DEFAULT_CUSTOM_JSON));
    } catch (e) {
      window.alert(String(e));
    }
  });

  document.getElementById("addBulldozerBtn")?.addEventListener("click", () => {
    addResourceRow(`Bulldozer${mapBuilder.bulldozerN++}`);
  });
  document.getElementById("addMedTeamBtn")?.addEventListener("click", () => {
    addResourceRow(`MedTeam${mapBuilder.medN++}`);
  });

  document.getElementById("exportMapJson")?.addEventListener("click", () => {
    const ta = document.getElementById("customJson");
    const doc = serializeMapBuilderToDoc();
    if (ta) ta.value = JSON.stringify(doc, null, 2);
    document.querySelector('[data-custom-tab="json"]')?.click();
  });

  document.getElementById("loadMapJson")?.addEventListener("click", () => {
    const ta = document.getElementById("customJson");
    if (!ta) return;
    try {
      const doc = JSON.parse(ta.value);
      if (!doc || typeof doc !== "object") throw new Error("JSON must be an object.");
      loadDocIntoMapBuilder(doc);
      document.querySelector('[data-custom-tab="visual"]')?.click();
    } catch (e) {
      window.alert(String(e));
    }
  });
}

function bindDemoUi() {
  const mode = document.getElementById("scenarioMode");
  const customRow = document.getElementById("customRow");
  const customJson = document.getElementById("customJson");
  const form = document.getElementById("planForm");
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const placeholder = document.getElementById("demoPlaceholder");
  const metrics = document.getElementById("metrics");
  const planList = document.getElementById("planList");
  const runBtn = document.getElementById("runBtn");

  if (customJson && !customJson.value.trim()) {
    customJson.value = DEFAULT_CUSTOM_JSON;
  }

  bindCustomTabs();
  bindMapBuilderControls();

  function updateMode() {
    const isCustom = mode.value === "custom";
    customRow.classList.toggle("hidden", !isCustom);
    if (isCustom) initMapBuilderNetwork();
  }

  mode.addEventListener("change", updateMode);
  updateMode();

  document.getElementById("stepPrev")?.addEventListener("click", () => {
    if (playback.index > 0) {
      playback.index -= 1;
      syncPlaybackUi();
    }
  });

  document.getElementById("stepNext")?.addEventListener("click", () => {
    if (playback.index < playback.steps.length - 1) {
      playback.index += 1;
      syncPlaybackUi();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    status.textContent = "";
    status.classList.remove("error");
    results.classList.add("hidden");
    if (placeholder) placeholder.classList.remove("hidden");
    destroyNetwork();
    playback.steps = [];
    playback.index = 0;
    planList.innerHTML = "";
    metrics.innerHTML = "";

    const algorithm = document.getElementById("algorithm").value;
    const heuristic = document.getElementById("heuristic").value;

    /** @type {Record<string, unknown>} */
    const payload = { algorithm, heuristic };

    if (mode.value === "custom") {
      if (getActiveCustomTab() === "visual") {
        try {
          payload.custom_scenario = serializeMapBuilderToDoc();
        } catch (err) {
          status.textContent = String(err);
          status.classList.add("error");
          return;
        }
      } else {
        let doc;
        try {
          doc = JSON.parse(customJson.value);
        } catch (err) {
          status.textContent = "Custom JSON is not valid JSON.";
          status.classList.add("error");
          return;
        }
        payload.custom_scenario = doc;
      }
    } else {
      payload.scenario = mode.value;
    }

    runBtn.disabled = true;
    status.textContent = "Running planner…";

    try {
      const res = await fetch(`${apiBase()}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 400) {
        status.textContent = data.error || "Bad request.";
        status.classList.add("error");
        return;
      }

      if (!data.success) {
        status.textContent =
          data.error ||
          "No plan found (goal unreachable with this configuration). " +
            `Nodes expanded: ${data.nodes_expanded ?? "—"}, time: ${
              data.time_taken != null ? `${data.time_taken.toFixed(4)}s` : "—"
            }.`;
        status.classList.add("error");
        metrics.innerHTML = `
          <span><strong>Algorithm</strong> ${data.algorithm}</span>
          <span><strong>Heuristic</strong> ${data.heuristic}</span>
          <span><strong>Nodes expanded</strong> ${data.nodes_expanded}</span>
          <span><strong>Time</strong> ${data.time_taken?.toFixed(4) ?? "—"}s</span>
        `;
        results.classList.remove("hidden");
        if (placeholder) placeholder.classList.add("hidden");
        return;
      }

      status.textContent = "Plan found.";
      metrics.innerHTML = `
        <span><strong>Algorithm</strong> ${data.algorithm}</span>
        <span><strong>Heuristic</strong> ${data.heuristic}</span>
        <span><strong>Plan length</strong> ${data.plan_length}</span>
        <span><strong>Nodes expanded</strong> ${data.nodes_expanded}</span>
        <span><strong>Time</strong> ${data.time_taken?.toFixed(4)}s</span>
      `;

      data.plan.forEach((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        planList.appendChild(li);
      });

      playback.steps = data.steps || [];
      playback.index = 0;
      destroyNetwork();
      results.classList.remove("hidden");
      if (placeholder) placeholder.classList.add("hidden");
      setStepControls();
      syncPlaybackUi();
    } catch (err) {
      status.textContent =
        "Could not reach the planner API. From the repo root run: python web/server.py";
      status.classList.add("error");
    } finally {
      runBtn.disabled = false;
    }
  });
}

bindDemoUi();
