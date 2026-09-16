/**
 * app.js — GeM PDF Extractor Frontend Controller
 * ================================================
 * Connects to the FastAPI backend and drives all UI interactions.
 */

// ── Configuration ──────────────────────────────────────────────────
const getApiBase = () => {
  if (window.location.protocol.startsWith("http")) {
    // If running under dev server on standard dev ports, point to FastAPI on port 8000
    if (window.location.port === "3000" || window.location.port === "5500" || window.location.port === "5173") {
      return "http://127.0.0.1:8000";
    }
    return window.location.origin;
  }
  // If running via file:/// protocol
  return "http://127.0.0.1:8000";
};

const API_BASE = getApiBase();

// ── State ──────────────────────────────────────────────────────────
let state = {
  currentView: "dashboard",
  isOnline: false,
  records: {
    data: [],
    filter: "all",
    search: "",
    page: 0,
    limit: 50,
    totalMatched: 0,
    totalMaster: 0,
    totalValue: 0,
    passCount: 0,
    reviewCount: 0,
  },
  config: {
    default_input_dir: "./pdfs",
    default_output_dir: "./output",
  },
  extraction: {
    polling: null,
  },
};


// ═══════════════════════════════════════════════════════════════════
//  INITIALIZATION
// ═══════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupSearch();
  setupFilters();
  setupSidebar();
  checkBackendConnection();
  loadConfig();
  loadDashboardData();

  // Heartbeat check every 4 seconds to auto-reconnect if server starts/restarts
  setInterval(async () => {
    const wasOnline = state.isOnline;
    const nowOnline = await checkBackendConnection();
    if (!wasOnline && nowOnline) {
      loadConfig();
      loadDashboardData();
      if (state.currentView === "records") loadRecords();
    }
  }, 4000);
});


// ═══════════════════════════════════════════════════════════════════
//  NAVIGATION
// ═══════════════════════════════════════════════════════════════════

function setupNavigation() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      switchView(btn.dataset.view);
    });
  });

  document.getElementById("btn-refresh").addEventListener("click", async () => {
    await checkBackendConnection();
    await loadDashboardData();
    if (state.currentView === "records") await loadRecords();
    showToast("Data refreshed", "info");
  });
}

function switchView(viewName) {
  state.currentView = viewName;

  // Update nav active state
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });

  // Update views
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.remove("active");
  });
  const targetView = document.getElementById(`view-${viewName}`);
  if (targetView) targetView.classList.add("active");

  // Update title
  const titles = { dashboard: "Dashboard", extract: "Extract PDFs", records: "Records" };
  document.getElementById("topbar-title").textContent = titles[viewName] || viewName;

  // Load data for the view
  if (viewName === "records") loadRecords();
  if (viewName === "dashboard") loadDashboardData();

  // Close sidebar on mobile
  document.getElementById("sidebar").classList.remove("open");
}

// Make switchView globally accessible for onclick handlers
window.switchView = switchView;


// ═══════════════════════════════════════════════════════════════════
//  SIDEBAR (MOBILE TOGGLE)
// ═══════════════════════════════════════════════════════════════════

function setupSidebar() {
  const toggleBtn = document.getElementById("sidebar-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      document.getElementById("sidebar").classList.toggle("open");
    });
  }
}


// ═══════════════════════════════════════════════════════════════════
//  BACKEND CONNECTION
// ═══════════════════════════════════════════════════════════════════

async function checkBackendConnection() {
  const statusEl = document.getElementById("connection-status");
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    if (res.ok) {
      statusEl.innerHTML = `<span class="status-dot online"></span><span class="status-text">Backend Online</span>`;
      state.isOnline = true;
      return true;
    } else {
      throw new Error("Bad response");
    }
  } catch {
    statusEl.innerHTML = `<span class="status-dot offline"></span><span class="status-text">Backend Offline</span>`;
    state.isOnline = false;
    return false;
  }
}

async function loadConfig() {
  try {
    const res = await fetch(`${API_BASE}/api/config`);
    if (res.ok) {
      const data = await res.json();
      state.config = data;
      const inEl = document.getElementById("input-dir");
      const outEl = document.getElementById("output-dir");
      if (inEl && (!inEl.value || inEl.value === "./pdfs")) {
        inEl.value = data.default_input_dir || "./pdfs";
      }
      if (outEl && (!outEl.value || outEl.value === "./output")) {
        outEl.value = data.default_output_dir || "./output";
      }
    }
  } catch {
    // Silently use defaults
  }
}


// ═══════════════════════════════════════════════════════════════════
//  DASHBOARD
// ═══════════════════════════════════════════════════════════════════

async function loadDashboardData() {
  try {
    const res = await fetch(`${API_BASE}/api/records?limit=5&offset=0`);
    if (!res.ok) throw new Error("Failed to load records");

    const data = await res.json();
    state.records.totalMaster = data.total_master || 0;
    state.records.totalValue = data.total_value_inr || 0;
    state.records.passCount = data.pass_count || 0;
    state.records.reviewCount = data.review_count || 0;

    updateStatsCards();
    renderDashboardTable(data.records || []);
  } catch {
    // Graceful: show dashes
    updateStatsCards();
  }
}

function updateStatsCards() {
  const { totalMaster, passCount, reviewCount, totalValue } = state.records;
  document.getElementById("stat-total-val").textContent = formatNumber(totalMaster);
  document.getElementById("stat-pass-val").textContent = formatNumber(passCount);
  document.getElementById("stat-review-val").textContent = formatNumber(reviewCount);
  document.getElementById("stat-value-val").textContent = formatCurrency(totalValue);
}

function renderDashboardTable(records) {
  const tbody = document.getElementById("dashboard-table-body");

  if (!records.length) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5"><div class="empty-state-inline">No records yet. Extract some PDFs to get started.</div></td></tr>`;
    return;
  }

  tbody.innerHTML = records
    .map((r, i) => {
      const status = r.validation_status || "REVIEW";
      const badgeClass = status === "PASS" ? "pass" : "review";
      return `
      <tr onclick='showRecordDetail(${JSON.stringify(r).replace(/'/g, "&#39;")})'>
        <td style="color:var(--text-primary);font-weight:600;">${truncate(r.contract_no, 22)}</td>
        <td>${truncate(r.seller_company_name, 25)}</td>
        <td><span class="badge ${badgeClass}">${status}</span></td>
        <td style="text-align:right;font-family:'JetBrains Mono',monospace;font-size:0.8rem;">${formatCurrency(r.total_order_value)}</td>
        <td style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text-muted);">${truncate(r.file_name, 28)}</td>
      </tr>`;
    })
    .join("");
}


// ═══════════════════════════════════════════════════════════════════
//  EXTRACTION — SCAN & RUN
// ═══════════════════════════════════════════════════════════════════

async function scanFolder() {
  const inputDir = document.getElementById("input-dir").value.trim();
  const outputDir = document.getElementById("output-dir").value.trim();

  if (!inputDir) {
    showToast("Please enter an input directory", "error");
    return;
  }

  const btn = document.getElementById("btn-scan");
  btn.disabled = true;
  btn.innerHTML = `<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Scanning...`;

  try {
    const res = await fetch(`${API_BASE}/api/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_dir: inputDir, output_dir: outputDir }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Scan failed");
    }

    const data = await res.json();
    document.getElementById("scan-total").textContent = data.total_pdfs;
    document.getElementById("scan-processed").textContent = data.already_processed;
    document.getElementById("scan-new").textContent = data.new_to_process;
    document.getElementById("scan-results").style.display = "block";
    document.getElementById("btn-start-extract").disabled = data.new_to_process === 0 && !document.getElementById("reprocess-all").checked;

    showToast(`Found ${data.total_pdfs} PDFs (${data.new_to_process} new)`, "success");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Scan Folder`;
  }
}

window.scanFolder = scanFolder;

async function startExtraction() {
  const inputDir = document.getElementById("input-dir").value.trim();
  const outputDir = document.getElementById("output-dir").value.trim();
  const reprocessAll = document.getElementById("reprocess-all").checked;

  const btn = document.getElementById("btn-start-extract");
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input_dir: inputDir, output_dir: outputDir, reprocess_all: reprocessAll }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Extraction failed to start");
    }

    document.getElementById("progress-panel").style.display = "flex";
    showToast("Extraction started!", "success");
    startProgressPolling();
  } catch (err) {
    showToast(err.message, "error");
    btn.disabled = false;
  }
}

window.startExtraction = startExtraction;


// ── Progress Polling ───────────────────────────────────────────────

function startProgressPolling() {
  if (state.extraction.polling) clearInterval(state.extraction.polling);

  state.extraction.polling = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/progress`);
      if (!res.ok) return;

      const p = await res.json();
      updateProgressUI(p);

      if (p.completed || (!p.is_running && p.processed > 0)) {
        clearInterval(state.extraction.polling);
        state.extraction.polling = null;
        document.getElementById("btn-start-extract").disabled = false;
        showToast(p.message || "Extraction complete!", "success");
        loadDashboardData();
      }
    } catch {
      // Silently retry
    }
  }, 500);
}

function updateProgressUI(p) {
  document.getElementById("progress-bar").style.width = `${p.percentage || 0}%`;
  document.getElementById("progress-pct").textContent = `${p.percentage || 0}%`;
  document.getElementById("progress-detail").textContent = p.message || "";
  document.getElementById("progress-file").textContent = p.current_file || "—";
  document.getElementById("progress-count").textContent = `${p.processed} / ${p.total}`;
  document.getElementById("progress-speed").textContent = `${p.speed_fps || 0} pdf/s`;
  document.getElementById("progress-elapsed").textContent = `${p.elapsed_seconds || 0}s`;
  document.getElementById("progress-pass").textContent = p.pass_count || 0;
  document.getElementById("progress-review").textContent = p.review_count || 0;
  document.getElementById("progress-message").textContent = p.message || "";
}


// ═══════════════════════════════════════════════════════════════════
//  RECORDS VIEW
// ═══════════════════════════════════════════════════════════════════

function setupSearch() {
  let debounce;
  document.getElementById("records-search").addEventListener("input", (e) => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      state.records.search = e.target.value;
      state.records.page = 0;
      loadRecords();
    }, 350);
  });
}

function setupFilters() {
  document.querySelectorAll(".filter-pills .pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".filter-pills .pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.records.filter = pill.dataset.filter;
      state.records.page = 0;
      loadRecords();
    });
  });
}

async function loadRecords() {
  const { filter, search, page, limit } = state.records;
  const offset = page * limit;

  let url = `${API_BASE}/api/records?limit=${limit}&offset=${offset}`;
  if (filter !== "all") url += `&status=${filter}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load records");

    const data = await res.json();
    state.records.data = data.records || [];
    state.records.totalMatched = data.total || 0;
    state.records.totalMaster = data.total_master || 0;
    state.records.totalValue = data.total_value_inr || 0;
    state.records.passCount = data.pass_count || 0;
    state.records.reviewCount = data.review_count || 0;

    renderRecordsTable();
    updatePagination();
    updateStatsCards();
  } catch (err) {
    showToast("Could not load records. Is the backend running?", "error");
  }
}

function renderRecordsTable() {
  const tbody = document.getElementById("records-table-body");
  const records = state.records.data;
  const offset = state.records.page * state.records.limit;

  if (!records.length) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="11"><div class="empty-state-inline">No records found.</div></td></tr>`;
    return;
  }

  tbody.innerHTML = records
    .map((r, i) => {
      const status = r.validation_status || "REVIEW";
      const badgeClass = status === "PASS" ? "pass" : "review";
      const rowJson = JSON.stringify(r).replace(/'/g, "&#39;").replace(/"/g, "&quot;");

      return `
      <tr onclick='showRecordDetail(JSON.parse(this.dataset.record))' data-record='${rowJson}'>
        <td class="col-narrow">${offset + i + 1}</td>
        <td style="color:var(--text-primary);font-weight:600;">${truncate(r.contract_no, 22)}</td>
        <td>${r.generated_date || "—"}</td>
        <td>${truncate(r.seller_company_name, 22)}</td>
        <td style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;">${r.seller_gstin || "—"}</td>
        <td>${truncate(r.brand, 15)}</td>
        <td class="col-right">${r.ordered_quantity || "—"}</td>
        <td class="col-right" style="font-family:'JetBrains Mono',monospace;">${formatNumber(r.unit_price)}</td>
        <td class="col-right" style="font-family:'JetBrains Mono',monospace;font-weight:600;">${formatCurrency(r.total_order_value)}</td>
        <td class="col-center"><span class="badge ${badgeClass}">${status}</span></td>
        <td style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:var(--text-muted);">${truncate(r.file_name, 25)}</td>
      </tr>`;
    })
    .join("");
}

function updatePagination() {
  const { page, limit, totalMatched } = state.records;
  const totalPages = Math.max(1, Math.ceil(totalMatched / limit));

  document.getElementById("page-info").textContent = `Page ${page + 1} of ${totalPages} (${totalMatched} records)`;
  document.getElementById("btn-prev").disabled = page === 0;
  document.getElementById("btn-next").disabled = page >= totalPages - 1;
}

function changePage(delta) {
  state.records.page += delta;
  loadRecords();
}

window.changePage = changePage;


// ═══════════════════════════════════════════════════════════════════
//  RECORD DETAIL MODAL
// ═══════════════════════════════════════════════════════════════════

function showRecordDetail(record) {
  if (!record) return;

  const modal = document.getElementById("record-modal");
  const title = document.getElementById("modal-title");
  const body = document.getElementById("modal-body");

  title.textContent = `Contract: ${record.contract_no || "—"}`;

  const fields = [
    { label: "Contract No", value: record.contract_no, mono: true },
    { label: "Generated Date", value: record.generated_date },
    { label: "Validation Status", value: record.validation_status, badge: true },
    { label: "Validation Score", value: record.validation_score ? `${record.validation_score}%` : "—" },
    { label: "Seller Company", value: record.seller_company_name, full: true },
    { label: "Seller Contact", value: record.seller_contact_no, mono: true },
    { label: "Seller Email", value: record.seller_email, mono: true },
    { label: "Seller GSTIN", value: record.seller_gstin, mono: true },
    { label: "Consignee Address", value: record.consignee_address, full: true },
    { label: "Consignee Email", value: record.consignee_email, mono: true },
    { label: "Buyer Email", value: record.buyer_email, mono: true },
    { label: "Paying Authority Email", value: record.paying_authority_email, mono: true },
    { label: "Brand", value: record.brand },
    { label: "Category & Quadrant", value: record.category_name_quadrant },
    { label: "Ordered Quantity", value: record.ordered_quantity },
    { label: "Unit Price (₹)", value: formatCurrency(record.unit_price), mono: true },
    { label: "Total Order Value (₹)", value: formatCurrency(record.total_order_value), mono: true },
    { label: "File Name", value: record.file_name, mono: true, full: true },
  ];

  if (record.validation_errors && record.validation_errors.length) {
    fields.push({
      label: "Validation Errors",
      value: record.validation_errors.join("; "),
      full: true,
    });
  }

  body.innerHTML = `<div class="detail-grid">${fields
    .map((f) => {
      const val = f.value || "—";
      let valueHtml;

      if (f.badge) {
        const cls = val === "PASS" ? "pass" : "review";
        valueHtml = `<span class="badge ${cls}">${val}</span>`;
      } else {
        valueHtml = `<span class="detail-value ${f.mono ? "mono" : ""}">${escapeHtml(String(val))}</span>`;
      }

      return `
        <div class="detail-item ${f.full ? "full-width" : ""}">
          <span class="detail-label">${f.label}</span>
          ${valueHtml}
        </div>`;
    })
    .join("")
  }</div>`;

  modal.style.display = "grid";

  // Close on overlay click
  modal.onclick = (e) => {
    if (e.target === modal) closeModal();
  };
}

window.showRecordDetail = showRecordDetail;

function closeModal() {
  document.getElementById("record-modal").style.display = "none";
}

window.closeModal = closeModal;

// Close modal on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});


// ═══════════════════════════════════════════════════════════════════
//  DOWNLOADS & FOLDER
// ═══════════════════════════════════════════════════════════════════

async function downloadFile(type) {
  const outputDir = document.getElementById("output-dir")?.value || state.config.default_output_dir || "./output";
  const url = `${API_BASE}/api/download/${type}?output_dir=${encodeURIComponent(outputDir)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || `Download failed`);
    }

    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = type === "excel" ? "gem_contracts.xlsx" : "gem_contracts.json";
    a.click();
    URL.revokeObjectURL(a.href);
    showToast(`${type === "excel" ? "Excel" : "JSON"} downloaded!`, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

window.downloadFile = downloadFile;

async function openOutputFolder() {
  const outputDir = document.getElementById("output-dir")?.value || state.config.default_output_dir || "./output";

  try {
    const res = await fetch(`${API_BASE}/api/open-folder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_path: outputDir }),
    });

    if (res.ok) {
      showToast("Folder opened in Explorer", "success");
    } else {
      const err = await res.json();
      throw new Error(err.error || "Failed to open folder");
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

window.openOutputFolder = openOutputFolder;


// ═══════════════════════════════════════════════════════════════════
//  TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════════

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast-exit");
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}


// ═══════════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════════

function formatNumber(val) {
  if (val === null || val === undefined || val === "NA" || val === "—") return "—";
  const num = Number(val);
  if (isNaN(num)) return String(val);
  return num.toLocaleString("en-IN");
}

function formatCurrency(val) {
  if (val === null || val === undefined || val === "NA" || val === "—") return "—";
  const num = Number(val);
  if (isNaN(num)) return String(val);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
  if (num >= 1000) return `₹${(num / 1000).toFixed(1)}K`;
  return `₹${num.toLocaleString("en-IN")}`;
}

function truncate(str, maxLen) {
  if (!str || str === "NA") return "—";
  return str.length > maxLen ? str.substring(0, maxLen) + "…" : str;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
