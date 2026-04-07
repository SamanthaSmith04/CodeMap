const PROMPTS = [
  { id: "A1", key: "project_summary",         desc: "High-level repository overview" },
  { id: "A2", key: "real_world",              desc: "How users interact with the system" },
  { id: "A3", key: "main_components",         desc: "Major components & modules" },
  { id: "B1", key: "repo_file_structure",     desc: "Directory & file structure" },
  { id: "B2", key: "entry_points_and_files",  desc: "Entry points & key files" },
  { id: "B3", key: "high_level_architecture", desc: "Architecture & subsystems" },
  { id: "B4", key: "program_flow",            desc: "Execution flow start to finish" },
  { id: "C1", key: "file_explanation",        desc: "What a specific file does" },
  { id: "C2", key: "feature_overview",        desc: "How a feature works end-to-end" },
  { id: "C3", key: "method_explanation",      desc: "Key methods & how they interact" },
  { id: "D1", key: "write_readme",            desc: "Write a comprehensive README" },
  { id: "D2", key: "debug_suggestions",       desc: "Common debugging points" },
  { id: "E1", key: "list-files",              desc: "List all files in the repo (JSON)" },
  { id: "E2", key: "list-functions",          desc: "List all functions per file (JSON)" },
];

let selectedPrompt = null;
let currentSessionId = null;
let indexedFiles = [];   // [{ value, path }]
let indexedFileNames = [];
let functionsByFile = {};  // optional/dummy frontend map

function showPage(id) {
  document.querySelectorAll(".container").forEach(el => el.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
}

function buildPromptList(containerId, runBtnId) {
  const container = document.getElementById(containerId);
  const runBtn = document.getElementById(runBtnId);
  container.innerHTML = "";

  PROMPTS.forEach(item => {
    const btn = document.createElement("button");
    btn.className = "prompt-option";
    btn.textContent = item.desc;

    btn.addEventListener("click", () => {
      container.querySelectorAll(".prompt-option").forEach(o => o.classList.remove("selected"));
      btn.classList.add("selected");
      selectedPrompt = item;
      runBtn.disabled = false;
    });

    container.appendChild(btn);
  });
}

function populateSelect(selectEl, items, placeholder) {
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    selectEl.appendChild(opt);
  });
}

function promptNeedsFile(promptId) {
  return ["C1", "C2", "C3", "D2"].includes(promptId);
}

function buildDummyFunctionMap() {
  // Optional frontend-only helper logic.
  // Since backend only supports file_index right now, this is mainly for UI.
  functionsByFile = {};
  indexedFileNames.forEach(name => {
    functionsByFile[name] = [];
  });
}

function setupPage3Dropdowns(prompt) {
  const fileSection = document.getElementById("file-dropdown-section");
  const functionSection = document.getElementById("function-dropdown-section");
  const fileSelect = document.getElementById("file-select");
  const functionSelect = document.getElementById("function-select");

  if (!fileSection || !functionSection || !fileSelect || !functionSelect) return;

  fileSection.classList.add("hidden");
  functionSection.classList.add("hidden");
  fileSelect.innerHTML = "";
  functionSelect.innerHTML = "";
  functionSelect.disabled = true;

  if (!promptNeedsFile(prompt.id)) {
    return;
  }

  populateSelect(fileSelect, indexedFileNames, "-- Choose a file --");
  fileSection.classList.remove("hidden");

  // Keep this lightweight. Python does not actually accept function_index yet.
  if (prompt.id === "C3") {
    populateSelect(functionSelect, [], "-- Choose a file first --");
    functionSection.classList.remove("hidden");

    fileSelect.onchange = () => {
      const selectedFile = fileSelect.value;
      const functions = functionsByFile[selectedFile] || [];
      populateSelect(functionSelect, functions, functions.length ? "-- Choose a function --" : "-- No functions available --");
      functionSelect.disabled = functions.length === 0;
    };
  } else {
    fileSelect.onchange = null;
    functionSelect.onchange = null;
  }
}

function renderResult(data) {
  const results = document.getElementById("results-content");

  const selectedFileHtml = data.selected_file
    ? `<p><strong>Selected file:</strong> ${data.selected_file}</p>`
    : "";

  results.innerHTML = `
    ${selectedFileHtml}
    <div class="result-block">
      <h3>${data.description || "Result"}</h3>
      <pre style="white-space: pre-wrap;">${data.answer || ""}</pre>
    </div>
  `;
}

function renderError(message) {
  document.getElementById("results-content").innerHTML = `
    <p style="color: red;"><strong>Error:</strong> ${message}</p>
  `;
}

async function startRepoSession(owner, repo) {
  const response = await fetch("/api/start_repo_session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ owner, repo })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Failed to start repo session");
  }

  currentSessionId = data.session_id;
  indexedFiles = data.files || [];
  indexedFileNames = indexedFiles.map(f => f.value);
  buildDummyFunctionMap();

  return data;
}

async function runSelectedPrompt() {
  if (!selectedPrompt) {
    renderError("No prompt selected.");
    return;
  }

  if (!currentSessionId) {
    renderError("No active session. Load a repository first.");
    return;
  }

  const fileSelect = document.getElementById("file-select");
  const needsFile = promptNeedsFile(selectedPrompt.id);

  let fileIndex = null;

  if (needsFile) {
    const selectedFileName = fileSelect.value;
    if (!selectedFileName) {
      renderError("Please choose a file first.");
      return;
    }

    fileIndex = indexedFiles.findIndex(f => f.value === selectedFileName);
    if (fileIndex < 0) {
      renderError("Invalid file selection.");
      return;
    }
  }

  document.getElementById("results-content").innerHTML = `<p>Running query...</p>`;

  try {
    const response = await fetch("/api/query_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        template_key: selectedPrompt.key,
        file_index: fileIndex
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Query failed");
    }

    renderResult(data);
  } catch (err) {
    renderError(err.message);
  }
}

function goToPage3(prevPage) {
  document.getElementById("selected-prompt-title").textContent = selectedPrompt.desc;
  document.getElementById("backButton3").dataset.prev = prevPage;
  document.getElementById("results-content").innerHTML = "";
  setupPage3Dropdowns(selectedPrompt);
  showPage("page-results");
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("backButton").addEventListener("click", () => showPage("homepage"));
  document.getElementById("backButton2").addEventListener("click", () => showPage("homepage"));

  document.getElementById("uploadButton").addEventListener("click", () => {
    const fileInput = document.getElementById("fileInput");
    const status = document.getElementById("status");

    if (fileInput.files.length > 0) {
      const filesList = document.getElementById("files-list");
      filesList.innerHTML = Array.from(fileInput.files)
        .map(f => `<p>${f.webkitRelativePath || f.name}</p>`)
        .join("");

      // Dummy only for now unless you add a Flask upload endpoint
      indexedFiles = Array.from(fileInput.files).map(f => ({
        value: f.webkitRelativePath || f.name,
        path: f.webkitRelativePath || f.name
      }));
      indexedFileNames = indexedFiles.map(f => f.value);
      buildDummyFunctionMap();

      buildPromptList("prompt-select-files", "run-btn-files");
      showPage("page-files");
      return;
    }

    status.textContent = "Please upload a file or folder first.";
  });

  document.getElementById("loadRepoButton").addEventListener("click", async () => {
    const repoURL = document.getElementById("repoURL").value.trim();
    const status = document.getElementById("status");

    if (!repoURL) {
      status.textContent = "Please upload a file OR paste a GitHub repo URL.";
      return;
    }

    const cleanURL = repoURL.replace(/\.git$/, "").replace(/\/$/, "");
    const match = cleanURL.match(/github\.com\/([^\/]+)\/([^\/]+)/);

    if (!match) {
      status.textContent = "Invalid GitHub URL.";
      return;
    }

    const owner = match[1];
    const repo = match[2];

    try {
      status.textContent = "Loading repository...";
      await startRepoSession(owner, repo);

      document.getElementById("repo-name-display").textContent = `${owner} / ${repo}`;
      buildPromptList("prompt-select-repo", "run-btn-repo");
      status.textContent = "";
      showPage("page-repo");
    } catch (error) {
      status.textContent = error.message || "Error loading repository.";
    }
  });

  document.getElementById("run-btn-files").addEventListener("click", () => {
    goToPage3("page-files");
  });

  document.getElementById("run-btn-repo").addEventListener("click", () => {
    goToPage3("page-repo");
  });

  document.getElementById("run-query-btn").addEventListener("click", async () => {
    await runSelectedPrompt();
  });

  document.getElementById("backButton3").addEventListener("click", () => {
    showPage(document.getElementById("backButton3").dataset.prev || "homepage");
  });
});