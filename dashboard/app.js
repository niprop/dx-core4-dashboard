async function loadReport() {
  const candidates = ["report.json", "../data/report.json", "../data/sample_report.json"];
  for (const url of candidates) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (res.ok) return await res.json();
    } catch (e) { /* try next */ }
  }
  return null;
}

function fmt(n, digits = 1) {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  return Number(n).toFixed(digits);
}

function badge(rating) {
  return `<span class="badge ${rating}">${rating}</span>`;
}

function renderDora(dora) {
  return `
    <div class="grid-4">
      <div class="card">
        <h3>Lead Time for Changes</h3>
        <div class="value">${fmt(dora.lead_time_for_changes_hours)}h</div>
        ${badge(dora.lead_time_rating)}
      </div>
      <div class="card">
        <h3>Deployment Frequency</h3>
        <div class="value">${fmt(dora.deployment_frequency_per_week)}/wk</div>
        ${badge(dora.deployment_frequency_rating)}
      </div>
      <div class="card">
        <h3>Change Failure Rate</h3>
        <div class="value">${dora.change_failure_rate_pct ?? "–"}%</div>
        ${badge(dora.change_failure_rate_rating)}
      </div>
      <div class="card">
        <h3>MTTR</h3>
        <div class="value">${fmt(dora.mttr_hours)}h</div>
        ${badge(dora.mttr_rating)}
      </div>
    </div>
  `;
}

function renderPrTable(prs) {
  if (!prs || !prs.length) return `<p class="note">No merged PRs in this window.</p>`;
  const rows = prs.map(p => `
    <tr>
      <td>#${p.number}</td>
      <td>${p.title}</td>
      <td>${p.merged_at ? new Date(p.merged_at).toLocaleDateString() : "–"}</td>
      <td><a href="${p.html_url}" target="_blank" rel="noopener">view</a></td>
    </tr>
  `).join("");
  return `
    <table>
      <thead><tr><th>PR</th><th>Title</th><th>Merged</th><th></th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderCore4Chart(core4) {
  const ctx = document.getElementById("core4Chart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Speed (throughput/wk)", "Effectiveness (deploys/wk)", "Quality (100 - CFR%)", "Impact (% linked)"],
      datasets: [{
        label: "Core 4",
        data: [
          core4.speed.pr_throughput_per_week ?? 0,
          core4.effectiveness.deployment_frequency_per_week ?? 0,
          core4.quality.change_failure_rate_pct != null ? 100 - core4.quality.change_failure_rate_pct : 0,
          core4.impact.pct_prs_linked_to_issue ?? 0,
        ],
        backgroundColor: ["#7cc4ff", "#3ecf8e", "#f5c451", "#f5716c"],
        borderRadius: 6,
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9aa0b4" }, grid: { color: "#262b3a" } },
        y: { ticks: { color: "#9aa0b4" }, grid: { color: "#262b3a" } },
      }
    }
  });
}

function renderAiChart(ai) {
  const ctx = document.getElementById("aiChart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["AI-assisted PRs", "Non-AI PRs"],
      datasets: [{
        label: "Median cycle time (hours)",
        data: [ai.median_cycle_time_hours_ai_assisted ?? 0, ai.median_cycle_time_hours_non_ai ?? 0],
        backgroundColor: ["#7cc4ff", "#4a4f61"],
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#9aa0b4" }, grid: { color: "#262b3a" } },
        y: { ticks: { color: "#9aa0b4" }, grid: { color: "#262b3a" } },
      }
    }
  });
}

(async function init() {
  const report = await loadReport();
  const app = document.getElementById("app");
  const meta = document.getElementById("meta");

  if (!report) {
    app.innerHTML = `<div class="empty">No report.json found. Run <code>python -m dx_dashboard.cli --owner OWNER --repo REPO</code> to generate one.</div>`;
    return;
  }

  meta.textContent = `${report.repo} · generated ${new Date(report.generated_at).toLocaleString()} · ${report.methodology}`;

  app.innerHTML = `
    ${renderDora(report.dora)}
    <div class="two-col">
      <section class="card">
        <h2>Core 4</h2>
        <canvas id="core4Chart" height="180"></canvas>
      </section>
      <section class="card">
        <h2>AI-Assisted vs. Non-AI Cycle Time</h2>
        <canvas id="aiChart" height="180"></canvas>
        <p class="note">${report.ai_impact.pct_prs_ai_assisted ?? 0}% of merged PRs flagged as AI-assisted (${report.ai_impact.ai_assisted_pr_count} of ${report.ai_impact.ai_assisted_pr_count + report.ai_impact.non_ai_pr_count}). ${report.ai_impact.note}</p>
      </section>
    </div>
    <section class="card">
      <h2>Recent Merged PRs</h2>
      ${renderPrTable(report.recent_prs)}
    </section>
  `;

  renderCore4Chart(report.core4);
  renderAiChart(report.ai_impact);
})();
