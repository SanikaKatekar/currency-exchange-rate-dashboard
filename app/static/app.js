const form = document.getElementById("query-form");
const startInput = document.getElementById("start-date");
const endInput = document.getElementById("end-date");
const breakdownInput = document.getElementById("breakdown");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const tableSection = document.getElementById("table-section");
const ratesBody = document.getElementById("rates-body");
const sourceLabel = document.getElementById("source-label");

let chart;

function formatRate(value) {
  return Number(value).toFixed(4);
}

function formatPct(value) {
  if (value === null || value === undefined) {
    return "—";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

function pctClass(value) {
  if (value === null || value === undefined || value === 0) {
    return "";
  }
  return value > 0 ? "positive" : "negative";
}

function setDefaultDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);

  endInput.value = end.toISOString().slice(0, 10);
  startInput.value = start.toISOString().slice(0, 10);
}

function showStatus(message) {
  statusEl.hidden = false;
  statusEl.textContent = message;
}

function hideStatus() {
  statusEl.hidden = true;
  statusEl.textContent = "";
}

function renderSummary(totals) {
  document.getElementById("start-rate").textContent = formatRate(totals.start_rate);
  document.getElementById("end-rate").textContent = formatRate(totals.end_rate);
  document.getElementById("mean-rate").textContent = formatRate(totals.mean_rate);

  const totalChange = document.getElementById("total-change");
  totalChange.textContent = formatPct(totals.total_pct_change);
  totalChange.className = `metric-value ${pctClass(totals.total_pct_change)}`;
}

function renderTable(days) {
  ratesBody.innerHTML = "";

  if (!days || days.length === 0) {
    tableSection.hidden = true;
    return;
  }

  tableSection.hidden = false;

  for (const row of days) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.date}</td>
      <td>${formatRate(row.rate)}</td>
      <td class="${pctClass(row.pct_change)}">${formatPct(row.pct_change)}</td>
    `;
    ratesBody.appendChild(tr);
  }
}

function renderChart(days) {
  const canvas = document.getElementById("rate-chart");
  const labels = days.map((row) => row.date);
  const values = days.map((row) => row.rate);

  if (chart) {
    chart.destroy();
  }

  chart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "EUR → USD",
          data: values,
          borderColor: "#1f6feb",
          backgroundColor: "rgba(31, 111, 235, 0.12)",
          fill: true,
          tension: 0.25,
          pointRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(context) {
              return `Rate: ${formatRate(context.parsed.y)}`;
            },
          },
        },
      },
      scales: {
        y: {
          ticks: {
            callback(value) {
              return Number(value).toFixed(4);
            },
          },
        },
      },
    },
  });
}

async function loadSummary() {
  hideStatus();
  resultsEl.hidden = true;

  const params = new URLSearchParams({
    start: startInput.value,
    end: endInput.value,
    breakdown: breakdownInput.value,
  });

  try {
    const response = await fetch(`/summary?${params.toString()}`);
    const payload = await response.json();

    if (!response.ok) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : Array.isArray(payload.detail)
            ? payload.detail.map((item) => item.msg || item).join("; ")
            : "Unable to load exchange rates.";
      throw new Error(detail);
    }

    renderSummary(payload.totals);
    renderTable(payload.days);
    renderChart(payload.days || []);
    sourceLabel.textContent = `Data source: ${payload.source}`;
    resultsEl.hidden = false;
  } catch (error) {
    showStatus(error.message);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadSummary();
});

setDefaultDates();
loadSummary();
