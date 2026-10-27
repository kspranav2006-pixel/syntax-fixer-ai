// SyntaxFixer AI Dashboard Frontend Logic

let scanData = null;
let selectedFile = null;
let repairedCount = 0;

// Elements
const targetInput = document.getElementById("target-input");
const providerSelect = document.getElementById("provider-select");
const btnScan = document.getElementById("btn-scan");
const btnFixAll = document.getElementById("btn-fix-all");
const btnFixSelected = document.getElementById("btn-fix-selected");
const btnQuickFixtures = document.getElementById("btn-quick-fixtures");
const btnAgenticRun = document.getElementById("btn-agentic-run");

const statsRow = document.getElementById("stats-row");
const statTotalErrors = document.getElementById("stat-total-errors");
const statBrokenFiles = document.getElementById("stat-broken-files");
const statRepaired = document.getElementById("stat-repaired");
const statBranch = document.getElementById("stat-branch");

const filesList = document.getElementById("files-list");
const fileCounter = document.getElementById("file-counter");
const currentFileTitle = document.getElementById("current-file-title");
const currentFileMeta = document.getElementById("current-file-meta");
const errorDetailsView = document.getElementById("error-details-view");
const terminalLogsView = document.getElementById("terminal-logs-view");
const diffCodeView = document.getElementById("diff-code-view");

// Agentic elements
const tabBtnAgentic = document.getElementById("tab-btn-agentic");
const tabContentAgentic = document.getElementById("tab-content-agentic");
const agenticPlanContainer = document.getElementById("agentic-plan-container");
const agenticPlanSteps = document.getElementById("agentic-plan-steps");
const agenticDialogueFeed = document.getElementById("agentic-dialogue-feed");
const agenticStatusBadge = document.getElementById("agentic-status-badge");

// Settings Modal
const btnOpenSettings = document.getElementById("btn-open-settings");
const btnCloseSettings = document.getElementById("btn-close-settings");
const settingsModal = document.getElementById("settings-modal");
const btnSaveSettings = document.getElementById("btn-save-settings");
const inputGeminiKey = document.getElementById("input-gemini-key");
const inputOpenaiKey = document.getElementById("input-openai-key");
const inputGhToken = document.getElementById("input-gh-token");
const currentProviderLabel = document.getElementById("current-provider-label");

// Tabs
const tabBtnError = document.getElementById("tab-btn-error");
const tabBtnLogs = document.getElementById("tab-btn-logs");
const tabBtnDiff = document.getElementById("tab-btn-diff");
const tabContentError = document.getElementById("tab-content-error");
const tabContentLogs = document.getElementById("tab-content-logs");
const tabContentDiff = document.getElementById("tab-content-diff");

// Initialize
window.addEventListener("DOMContentLoaded", async () => {
  // Load stored settings
  inputGeminiKey.value = localStorage.getItem("GEMINI_API_KEY") || "";
  inputOpenaiKey.value = localStorage.getItem("OPENAI_API_KEY") || "";
  inputGhToken.value = localStorage.getItem("GITHUB_TOKEN") || "";

  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    if (cfg.default_provider) {
      providerSelect.value = cfg.default_provider;
      currentProviderLabel.innerText = cfg.default_provider.toUpperCase();
    }
  } catch (e) {
    console.error("Config fetch error:", e);
  }

  setupEventListeners();
});

function setupEventListeners() {
  providerSelect.addEventListener("change", () => {
    currentProviderLabel.innerText = providerSelect.value.toUpperCase();
  });

  btnQuickFixtures.addEventListener("click", () => {
    targetInput.value = "tests/fixtures";
    runScan();
  });

  btnScan.addEventListener("click", runScan);
  btnFixAll.addEventListener("click", runFixAll);
  btnFixSelected.addEventListener("click", runFixSelected);
  btnAgenticRun.addEventListener("click", runAgenticWorkflow);

  // Tabs
  tabBtnError.addEventListener("click", () => switchTab("error"));
  tabBtnLogs.addEventListener("click", () => switchTab("logs"));
  tabBtnDiff.addEventListener("click", () => switchTab("diff"));
  tabBtnAgentic.addEventListener("click", () => switchTab("agentic"));

  // Settings
  btnOpenSettings.addEventListener("click", () => settingsModal.classList.remove("hidden"));
  btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
  btnSaveSettings.addEventListener("click", () => {
    localStorage.setItem("GEMINI_API_KEY", inputGeminiKey.value.trim());
    localStorage.setItem("OPENAI_API_KEY", inputOpenaiKey.value.trim());
    localStorage.setItem("GITHUB_TOKEN", inputGhToken.value.trim());
    settingsModal.classList.add("hidden");
    alert("Settings saved successfully!");
  });
}

function switchTab(tab) {
  [tabBtnError, tabBtnLogs, tabBtnDiff, tabBtnAgentic].forEach(b => {
    b.classList.remove("active", "border-indigo-500", "text-indigo-400");
    b.classList.add("text-slate-400");
  });
  [tabContentError, tabContentLogs, tabContentDiff, tabContentAgentic].forEach(c => c.classList.add("hidden"));

  if (tab === "error") {
    tabBtnError.classList.add("active", "border-indigo-500", "text-indigo-400");
    tabContentError.classList.remove("hidden");
  } else if (tab === "logs") {
    tabBtnLogs.classList.add("active", "border-indigo-500", "text-indigo-400");
    tabContentLogs.classList.remove("hidden");
  } else if (tab === "diff") {
    tabBtnDiff.classList.add("active", "border-indigo-500", "text-indigo-400");
    tabContentDiff.classList.remove("hidden");
  } else if (tab === "agentic") {
    tabBtnAgentic.classList.add("active", "border-indigo-500", "text-indigo-400");
    tabContentAgentic.classList.remove("hidden");
  }
}

async function runAgenticWorkflow() {
  btnAgenticRun.disabled = true;
  btnAgenticRun.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Agentic AI Running...</span>`;
  switchTab("agentic");

  agenticStatusBadge.innerText = "EXECUTING";
  agenticStatusBadge.className = "px-2 py-0.5 text-[10px] rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold animate-pulse";
  agenticDialogueFeed.innerHTML = `<div class="text-indigo-400 py-3"><i class="fa-solid fa-spinner fa-spin mr-2"></i> Initializing multi-agent cognitive architecture...</div>`;

  const target = targetInput.value.trim() || ".";
  const provider = providerSelect.value;
  let apiKey = null;
  if (provider === "gemini") apiKey = localStorage.getItem("GEMINI_API_KEY");
  else if (provider === "openai") apiKey = localStorage.getItem("OPENAI_API_KEY");

  try {
    const res = await fetch("/api/agentic-run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target,
        goal: "Autonomously detect, diagnose, repair, and verify all syntax errors in repository.",
        provider,
        api_key: apiKey || null,
        create_branch: true,
        commit: true,
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Agentic run failed");

    // Render Phased Plan
    if (data.plan && data.plan.length > 0) {
      agenticPlanContainer.classList.remove("hidden");
      agenticPlanSteps.innerHTML = "";
      data.plan.forEach(step => {
        const stepEl = document.createElement("div");
        const statusClass = step.status === "verified" ? "text-emerald-400" : "text-slate-400";
        stepEl.className = "flex items-center justify-between p-1.5 rounded bg-slate-900 border border-slate-800";
        stepEl.innerHTML = `
          <div class="flex items-center space-x-2 truncate">
            <span class="text-purple-400 font-bold">#${step.step_id}</span>
            <span class="text-slate-200 truncate">${step.title}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${step.assigned_role}</span>
            <span class="text-[10px] font-bold ${statusClass}">${step.status.toUpperCase()}</span>
          </div>
        `;
        agenticPlanSteps.appendChild(stepEl);
      });
    }

    // Render Inter-Agent Messages
    agenticDialogueFeed.innerHTML = "";
    const roleBadges = {
      "Orchestrator": "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
      "Planner": "bg-purple-500/10 text-purple-400 border-purple-500/20",
      "Diagnostician": "bg-blue-500/10 text-blue-400 border-blue-500/20",
      "Repairer": "bg-amber-500/10 text-amber-400 border-amber-500/20",
      "Critic": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      "GitOps": "bg-slate-500/10 text-slate-300 border-slate-500/20",
    };

    data.messages.forEach(msg => {
      const msgEl = document.createElement("div");
      const senderBadge = roleBadges[msg.sender] || "bg-slate-800 text-slate-300";
      const recipBadge = roleBadges[msg.recipient] || "bg-slate-800 text-slate-300";

      msgEl.className = "p-2.5 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1";
      msgEl.innerHTML = `
        <div class="flex items-center justify-between text-[10px]">
          <div class="flex items-center space-x-1.5">
            <span class="px-1.5 py-0.5 rounded border font-bold ${senderBadge}">${msg.sender}</span>
            <span class="text-slate-500">→</span>
            <span class="px-1.5 py-0.5 rounded border font-bold ${recipBadge}">${msg.recipient}</span>
            <span class="text-slate-400 font-mono">(${msg.message_type})</span>
          </div>
          <span class="text-slate-600 font-mono">${msg.timestamp}</span>
        </div>
        <div class="text-slate-300 pl-1 text-[11px]">${escapeHtml(msg.content)}</div>
      `;
      agenticDialogueFeed.appendChild(msgEl);
    });

    agenticStatusBadge.innerText = data.success ? "COMPLETED ✅" : "FINISHED";
    agenticStatusBadge.className = data.success
      ? "px-2 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold"
      : "px-2 py-0.5 text-[10px] rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold";

    // Update stats and file cards
    if (data.file_tasks) {
      let verifiedCount = 0;
      Object.entries(data.file_tasks).forEach(([fPath, task]) => {
        if (task.status === "verified") {
          verifiedCount++;
          markFileRepaired(fPath);
        }
      });
      statRepaired.innerText = verifiedCount;
      if (data.git_branch) statBranch.innerText = data.git_branch;
    }

  } catch (err) {
    agenticDialogueFeed.innerHTML = `<div class="p-3 bg-rose-500/10 text-rose-400 rounded-lg">Agentic execution error: ${err.message}</div>`;
    agenticStatusBadge.innerText = "FAILED ❌";
    agenticStatusBadge.className = "px-2 py-0.5 text-[10px] rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold";
  } finally {
    btnAgenticRun.disabled = false;
    btnAgenticRun.innerHTML = `<i class="fa-solid fa-brain"></i> <span>Agentic AI</span>`;
  }
}

async function runScan() {
  const target = targetInput.value.trim() || ".";
  btnScan.disabled = true;
  btnScan.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Scanning...</span>`;
  filesList.innerHTML = `<div class="text-center py-10 text-slate-400 text-sm"><i class="fa-solid fa-spinner fa-spin text-2xl mb-2"></i><div>Analyzing codebase syntax...</div></div>`;

  try {
    const res = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target,
        github_token: localStorage.getItem("GITHUB_TOKEN") || null
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Scan request failed");

    scanData = data;
    renderScanResults(data);
  } catch (err) {
    alert("Scan failed: " + err.message);
    filesList.innerHTML = `<div class="p-4 text-xs text-rose-400 bg-rose-500/10 rounded-xl">Error: ${err.message}</div>`;
  } finally {
    btnScan.disabled = false;
    btnScan.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>Scan Repo</span>`;
  }
}

function renderScanResults(data) {
  statsRow.classList.remove("hidden");
  statTotalErrors.innerText = data.total_errors;
  statBrokenFiles.innerText = data.files_with_errors;
  statRepaired.innerText = "0";
  statBranch.innerText = data.is_remote ? "Cloned" : "Local Workspace";

  btnFixAll.disabled = data.files_with_errors === 0;
  fileCounter.innerText = `${data.files_with_errors} broken files found`;

  if (data.files_with_errors === 0) {
    filesList.innerHTML = `
      <div class="p-6 text-center text-emerald-400 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
        <i class="fa-solid fa-circle-check text-3xl mb-2 block"></i>
        <strong>Repository Clean!</strong>
        <p class="text-xs text-slate-400 mt-1">Zero syntax errors found across all checked files.</p>
      </div>`;
    return;
  }

  filesList.innerHTML = "";
  const fileEntries = Object.entries(data.errors);

  fileEntries.forEach(([filePath, errors], index) => {
    const firstErr = errors[0];
    const card = document.createElement("div");
    card.className = "file-card p-3 rounded-xl border border-slate-800 bg-slate-950/60 hover:bg-slate-800/80 cursor-pointer transition flex items-start justify-between";
    card.dataset.filePath = filePath;

    card.innerHTML = `
      <div class="flex-1 pr-2">
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
            ${firstErr.language.toUpperCase()}
          </span>
          <span class="text-xs font-mono text-slate-200 font-semibold truncate max-w-[200px]" title="${filePath}">
            ${filePath}
          </span>
        </div>
        <div class="text-[11px] text-slate-400 mt-1 truncate">
          ${firstErr.error_message}
        </div>
        <div class="text-[10px] text-slate-500 mt-0.5">
          Line ${firstErr.line_number || '?'}${firstErr.column_number ? ':' + firstErr.column_number : ''}
        </div>
      </div>
      <div class="text-xs text-rose-400 font-semibold pt-1">
        ${errors.length} err
      </div>
    `;

    card.addEventListener("click", () => selectFile(filePath, errors, card));
    filesList.appendChild(card);

    if (index === 0) {
      selectFile(filePath, errors, card);
    }
  });
}

function selectFile(filePath, errors, cardEl) {
  selectedFile = filePath;
  document.querySelectorAll(".file-card").forEach(c => c.classList.remove("border-indigo-500", "bg-slate-800"));
  if (cardEl) cardEl.classList.add("border-indigo-500", "bg-slate-800");

  currentFileTitle.innerText = filePath;
  const firstErr = errors[0];
  currentFileMeta.innerText = `${errors.length} syntax error(s) | Line ${firstErr.line_number || '?'}`;
  btnFixSelected.disabled = false;

  // Render error details
  let errorText = `File: ${filePath}\nLanguage: ${firstErr.language.toUpperCase()}\n\n`;
  errors.forEach((err, idx) => {
    errorText += `[Error ${idx + 1}] Line ${err.line_number || '?'}, Col ${err.column_number || '?'}\n`;
    errorText += `Message: ${err.error_message}\n\n`;
    if (err.context_snippet) {
      errorText += `${err.context_snippet}\n\n`;
    }
  });
  errorDetailsView.innerText = errorText;
  switchTab("error");
}

async function runFixSelected() {
  if (!selectedFile) return;

  btnFixSelected.disabled = true;
  btnFixSelected.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Repairing...</span>`;

  switchTab("logs");
  terminalLogsView.innerText = `[AGENT] Initializing syntax repair loop for: ${selectedFile}...\n`;

  const provider = providerSelect.value;
  let apiKey = null;
  if (provider === "gemini") apiKey = localStorage.getItem("GEMINI_API_KEY");
  else if (provider === "openai") apiKey = localStorage.getItem("OPENAI_API_KEY");

  try {
    const res = await fetch("/api/fix", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: targetInput.value.trim() || ".",
        file_path: selectedFile,
        provider: provider,
        api_key: apiKey || null,
        write_back: true,
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Fix failed");

    // Display reflection logs
    let logLines = `[AGENT REPORT] File: ${selectedFile}\nStatus: ${data.success ? 'VERIFIED PASSED ✅' : 'FAILED ❌'}\nIterations used: ${data.iterations_used}\n\n`;
    data.reflection_logs.forEach(l => {
      logLines += `> ${l}\n`;
    });
    terminalLogsView.innerText = logLines;

    // Display diff
    if (data.diff) {
      diffCodeView.innerHTML = `<code class="language-diff">${escapeHtml(data.diff)}</code>`;
      if (window.Prism) Prism.highlightAll();
      switchTab("diff");
    }

    if (data.success) {
      repairedCount++;
      statRepaired.innerText = repairedCount;
      markFileRepaired(selectedFile);
    }
  } catch (e) {
    terminalLogsView.innerText += `\n[ERROR] ${e.message}\n`;
  } finally {
    btnFixSelected.disabled = false;
    btnFixSelected.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Fix This File</span>`;
  }
}

async function runFixAll() {
  btnFixAll.disabled = true;
  btnFixAll.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Fixing All...</span>`;

  switchTab("logs");
  terminalLogsView.innerText = `[AGENT] Initiating batch repository repair...\n`;

  const provider = providerSelect.value;
  let apiKey = null;
  if (provider === "gemini") apiKey = localStorage.getItem("GEMINI_API_KEY");
  else if (provider === "openai") apiKey = localStorage.getItem("OPENAI_API_KEY");

  try {
    const res = await fetch("/api/fix-all", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target: targetInput.value.trim() || ".",
        provider: provider,
        api_key: apiKey || null,
        create_branch: true,
        commit: true,
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Batch fix failed");

    let logText = `[BATCH COMPLETE] ${data.fixed_files_count}/${data.total_files} files repaired successfully.\n`;
    if (data.branch_name) {
      logText += `Git Branch Created: ${data.branch_name}\n\n`;
      statBranch.innerText = data.branch_name;
    }

    data.results.forEach(r => {
      logText += `--------------------------------------\n`;
      logText += `File: ${r.file_path} -> ${r.success ? 'PASSED ✅' : 'FAILED ❌'}\n`;
      r.reflection_logs.forEach(l => logText += `  ${l}\n`);
      if (r.success) markFileRepaired(r.file_path);
    });

    terminalLogsView.innerText = logText;
    statRepaired.innerText = data.fixed_files_count;
  } catch (e) {
    terminalLogsView.innerText += `\n[ERROR] ${e.message}\n`;
  } finally {
    btnFixAll.disabled = false;
    btnFixAll.innerHTML = `<i class="fa-solid fa-bolt"></i> <span>Fix All</span>`;
  }
}

function markFileRepaired(filePath) {
  const card = document.querySelector(`.file-card[data-file-path="${filePath}"]`);
  if (card) {
    card.classList.remove("border-slate-800", "border-indigo-500");
    card.classList.add("border-emerald-500/40", "bg-emerald-950/20");
    const badge = card.querySelector(".text-rose-400");
    if (badge) {
      badge.className = "text-xs text-emerald-400 font-bold pt-1";
      badge.innerHTML = `<i class="fa-solid fa-check"></i> Fixed`;
    }
  }
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
