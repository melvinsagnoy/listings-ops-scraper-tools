const form = document.getElementById("scrape-form");
const asinInput = document.getElementById("asin-input");
const asinCount = document.getElementById("asin-count");
const scrapeBtn = document.getElementById("scrape-btn");
const loadingEl = document.getElementById("loading");
const loadingText = document.getElementById("loading-text");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const resultsList = document.getElementById("results-list");
const againBtn = document.getElementById("again-btn");
const csvBtn = document.getElementById("csv-btn");

let collected = [];   // flat list of ProductData rows for CSV export
let lastResults = []; // last batch, for re-render

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function parseASINs(text) {
  // Split on newlines, commas, spaces, semicolons, tabs.
  return text
    .split(/[\s,;]+/)
    .map((s) => s.trim().toUpperCase())
    .filter((s) => s.length > 0);
}

function updateCount() {
  const asins = parseASINs(asinInput.value);
  asinCount.textContent = `${asins.length} ASIN${asins.length === 1 ? "" : "s"}`;
  scrapeBtn.disabled = asins.length === 0 || asins.length > 20;
}

asinInput.addEventListener("input", updateCount);
updateCount();

function setLoading(on, message) {
  if (on) {
    show(loadingEl);
    loadingText.textContent = message || "Scraping…";
    scrapeBtn.disabled = true;
    scrapeBtn.textContent = "Scraping…";
    hide(errorEl);
    hide(resultsEl);
  } else {
    hide(loadingEl);
    scrapeBtn.disabled = false;
    scrapeBtn.textContent = "Scrape Products";
    updateCount();
  }
}

function showError(message) {
  errorEl.textContent = message;
  show(errorEl);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderResults(results) {
  resultsList.innerHTML = "";
  for (const r of results) {
    const div = document.createElement("div");
    div.className = `result-item ${r.status}`;

    const ratingText = r.rating != null ? `${r.rating} out of 5 stars` : "—";
    const reviewText = r.review_count != null
      ? r.review_count.toLocaleString()
      : "—";
    const titleText = r.title || (r.error ? r.error : "Not available");

    div.innerHTML = `
      <div class="asin-line">
        ${escapeHtml(r.asin)}
        <span class="badge ${r.status}">${escapeHtml(r.status)}</span>
      </div>
      <dl>
        <dt>Title</dt><dd>${escapeHtml(titleText)}</dd>
        <dt>Rating</dt><dd>${escapeHtml(ratingText)}</dd>
        <dt>Review Count</dt><dd>${escapeHtml(reviewText)}</dd>
        <dt>URL</dt><dd>${escapeHtml(r.product_url || "—")}</dd>
        <dt>Scraped At</dt><dd>${escapeHtml(new Date(r.scraped_at).toLocaleString())}</dd>
      </dl>
    `;
    resultsList.appendChild(div);
  }
  show(resultsEl);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const asins = parseASINs(asinInput.value);
  if (asins.length === 0) return;
  if (asins.length > 20) {
    showError("Please enter 20 ASINs or fewer per request.");
    return;
  }

  setLoading(true, `Scraping ${asins.length} ASIN${asins.length === 1 ? "" : "s"}… this can take a while.`);

  try {
    const res = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asins }),
    });

    const payload = await res.json().catch(() => null);

    if (!res.ok) {
      const detail = payload && payload.detail
        ? (typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail))
        : `Request failed (${res.status})`;
      showError(detail);
      return;
    }

    if (!payload.results || payload.results.length === 0) {
      showError(payload.error || "No results returned.");
      return;
    }

    lastResults = payload.results;
    collected = collected.concat(payload.results.filter((r) => r.status === "success"));
    renderResults(payload.results);
  } catch (err) {
    showError("Network error. Please check your connection and try again.");
  } finally {
    setLoading(false);
  }
});

againBtn.addEventListener("click", () => {
  hide(resultsEl);
  hide(errorEl);
  asinInput.value = "";
  updateCount();
  asinInput.focus();
});

csvBtn.addEventListener("click", () => {
  const rows = collected.length > 0 ? collected : lastResults;
  if (rows.length === 0) return;
  const headers = ["asin", "status", "title", "rating", "review_count", "product_url", "scraped_at", "error"];
  const csv = [headers.join(",")];
  for (const row of rows) {
    csv.push(headers.map((h) => csvEscape(row[h])).join(","));
  }
  const blob = new Blob([csv.join("\n")], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "amazon-results.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const s = String(value);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}