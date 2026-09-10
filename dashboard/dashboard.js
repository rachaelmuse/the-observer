const state = { current: null, tab: "investigations", payload: null, investigations: [] };

const $ = (id) => document.getElementById(id);

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

$("run").addEventListener("click", async () => {
  const question = $("question").value.trim();
  const urls = $("urls").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const search = $("search").checked;
  if (!question) {
    $("status").textContent = "A question is required.";
    return;
  }
  $("status").textContent = "Running… this follows evidence, not speed.";
  try {
    const result = await api("/investigations/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, urls, search }),
    });
    state.current = result.report.investigation_id;
    state.payload = result;
    $("status").textContent = `Investigation ${state.current} reached ${result.report.status}.`;
    await refresh();
    renderReport(result.report);
  } catch (err) {
    $("status").textContent = String(err.message || err);
  }
});

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    state.tab = btn.dataset.tab;
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b === btn));
    renderList();
  });
});

async function refresh() {
  const list = await api("/investigations");
  state.investigations = list.investigations || [];
  if (state.current) {
    state.detail = await api(`/investigations/${state.current}`);
    state.report = await api(`/investigations/${state.current}/report`);
  }
  renderList();
  if (state.report) renderReport(state.report);
}

function cards(items, textFn, clickFn) {
  if (!items || !items.length) return `<p class="empty">none recorded</p>`;
  return items.map((item, i) => {
    const label = textFn(item);
    return `<div class="card" data-i="${i}">${escapeHtml(label)}</div>`;
  }).join("");
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderList() {
  const el = $("list");
  const d = state.detail || {};
  const report = state.report || {};
  const tab = state.tab;
  let html = `<h2>${tab}</h2>`;
  if (tab === "investigations") {
    html += cards(state.investigations, (x) => `${x.id} — ${x.status} — ${x.question}`, null);
  } else if (tab === "evidence") {
    html += cards(d.evidence, (x) => `${x.id} [${x.status}] ${x.description || ""}`);
  } else if (tab === "sources") {
    html += cards(d.sources, (x) => `${x.source_type || "source"} · ${x.publisher || x.url} (${x.hierarchy})`);
  } else if (tab === "claims") {
    html += cards(d.claims, (x) => `${x.epistemic_kind}/${x.status}: ${x.text}`);
  } else if (tab === "entities") {
    html += cards(d.entities, (x) => `${x.name} (${x.entity_type})`);
  } else if (tab === "relationships") {
    html += d.relationships && d.relationships.length
      ? cards(d.relationships, (x) => `${x.rel_type} inferred=${x.inferred}`)
      : `<p class="empty">no relationships recorded</p>`;
  } else if (tab === "timeline") {
    const t = report.timeline;
    html += Array.isArray(t) ? cards(t, (x) => `${x.when} ${x.what}`) : `<p class="empty">${t || "no dated events recorded"}</p>`;
  } else if (tab === "hypotheses") {
    html += cards(d.hypotheses, (x) => `${x.id}${x.is_counter ? " COUNTER" : ""}: ${x.text}`);
  } else if (tab === "contradictions") {
    const items = Array.isArray(report.contradictions)
      ? report.contradictions
      : Array.isArray(d.contradictions)
        ? d.contradictions
        : [];
    html += items.length
      ? cards(items, (x) => `${x.id} independent=${x.independent} ${x.reason || ""}`)
      : `<p class="empty">no contradictions recorded</p>`;
  } else if (tab === "confidence") {
    const items = (d.claims || []).map((c) => `${c.id}: ${c.confidence}`);
    html += items.length ? items.map((x) => `<div class="card">${escapeHtml(x)}</div>`).join("") : `<p class="empty">no confidence scores</p>`;
  } else if (tab === "queue") {
    html += `<p>Current status: ${escapeHtml((d.status || "none"))}</p>`;
  } else if (tab === "audit") {
    html += `<p class="empty">Loading audit…</p>`;
    api("/audit").then((data) => {
      el.innerHTML = `<h2>audit</h2>` + cards(data.events, (x) => `${x.created_at} ${x.action} ${x.target}`);
    });
    $("list").innerHTML = html;
    bindEntityClicks();
    return;
  } else if (tab === "registry") {
    api("/registry").then((data) => {
      const caps = (data.capabilities || []).map((c) => `${c.id}: ${c.status} — ${c.reason}`);
      el.innerHTML = `<h2>registry</h2>` + caps.map((x) => `<div class="card">${escapeHtml(x)}</div>`).join("");
    });
    $("list").innerHTML = html;
    return;
  }
  el.innerHTML = html;
  bindEntityClicks();
}

function bindEntityClicks() {
  if (state.tab !== "entities" || !state.detail) return;
  $("list").querySelectorAll(".card").forEach((card, i) => {
    card.addEventListener("click", async () => {
      const ent = state.detail.entities[i];
      const panel = await api(`/investigations/${state.current}/entities/${ent.id}`);
      $("panel-body").textContent = JSON.stringify(panel, null, 2);
    });
  });
  $("list").querySelectorAll(".card").forEach((card, i) => {
    if (state.tab === "investigations") {
      card.addEventListener("click", async () => {
        state.current = state.investigations[i].id;
        await refresh();
      });
    }
  });
}

function renderReport(report) {
  const sections = [
    ["Executive Summary", report.executive_summary],
    ["Inquiry (who / what / when / where / possible how / possible why)", report.inquiry],
    ["What We Know", report.what_we_know],
    ["What We Do Not Know", report.what_we_do_not_know],
    ["Conclusion", report.conclusion],
    ["Source Ledger", report.source_ledger],
  ];
  $("report").innerHTML = `<h2>Report</h2>` + sections.map(([k, v]) =>
    `<h3>${k}</h3><pre>${escapeHtml(typeof v === "string" ? v : JSON.stringify(v, null, 2))}</pre>`
  ).join("");
}

document.querySelector('.tabs button[data-tab="investigations"]').classList.add("active");
refresh().catch((err) => { $("status").textContent = String(err.message || err); });
