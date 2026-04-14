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

let currentSessionId = null;
let currentIndexName = null;
let repoPathOnServer = null;

function showPage(id) {
  document.querySelectorAll('.container').forEach(el => el.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

let selectedPrompt = null;

function buildPromptList(containerId, runBtnId) {
  const container = document.getElementById(containerId);
  const runBtn    = document.getElementById(runBtnId);
  container.innerHTML = '';

  PROMPTS.forEach(item => {
    const btn = document.createElement('button');
    btn.className = 'prompt-option';
    btn.innerHTML = `<span class="prompt-id"></span> ${item.desc}`;
    btn.addEventListener('click', () => {
      container.querySelectorAll('.prompt-option').forEach(o => o.classList.remove('selected'));
      btn.classList.add('selected');
      selectedPrompt = item;
      runBtn.disabled = false;
    });
    container.appendChild(btn);
  });
}

document.getElementById("backButton").addEventListener("click", () => showPage('homepage'));
document.getElementById("uploadButton").addEventListener("click", () => {

  const fileInput = document.getElementById("fileInput");
  const status = document.getElementById("status");

  //Case 1: File uploaded
  if (fileInput.files.length > 0) {

    // Populate file list on page 2
    const filesList = document.getElementById("files-list");
    filesList.innerHTML = Array.from(fileInput.files)
      .map(f => `<p>${f.webkitRelativePath || f.name}</p>`)
      .join('');

    buildPromptList('prompt-select-files', 'run-btn-files');

    showPage('page-files');
    return;

  }

  //Case 2: Nothing selected
  status.textContent = "Please upload a file or folder first.";

});


//Checks if repo exists
async function checkRepoExists(repoUrl) {
  try {
      const response = await fetch('http://127.0.0.1:5000/api/repo_exists', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify({ url: repoUrl })
      });

      const data = await response.json();

      if (response.ok) {
          console.log("Exists:", data.exists);
      } else {
          console.error("Error:", data.error);
      }
      console.log("Data received:", data);
      return data.exists;
  } catch (err) {
      console.error("Request failed:", err);
  }
}

//Pulls down all the files from the github
async function downloadGithubRepo(repoOwner, repoName, tempDir) {
  try {
      const response = await fetch('http://127.0.0.1:5000/api/download_github_repo', {
          method: 'POST',
          headers: {
              'Content-Type': 'application/json'
          },
          body: JSON.stringify({
              repo_owner: repoOwner,
              repo_name: repoName,
              temp_dir: tempDir
          })
      });

      const data = await response.json();

      if (response.ok) {
          console.log("Download success:", data);
      } else {
          console.error("Error:", data.error);
      }

      return data;
  } catch (err) {
      console.error("Request failed:", err);
  }
}

//Gets the tempt directory
function getSessionPath(choice = "", userInputSessionId = "") {
  // Generate random session ID (8 hex chars)
  const randomId = crypto.randomUUID().replace(/-/g, "").slice(0, 8);

  // const sessionId = (choice !== "3")
  //     ? randomId
  //     : userInputSessionId.trim();

  sessionId = randomId

  // In browser, no true cwd → simulate with base path
  const basePath = ""; // or something like "/tmp" if your backend expects it

  const fullPath = `${basePath}/repo_${sessionId}`;

  return { sessionId, fullPath };
}
//
document.getElementById("backButton2").addEventListener("click", () => showPage('homepage'));
document.getElementById("loadRepoButton").addEventListener("click", async (event) => {
    event.preventDefault();
    const repoURL = document.getElementById("repoURL").value.trim();
    const status = document.getElementById("status");

    const cleanURL = repoURL.replace(/\.git$/, '').replace(/\/$/, '');
    const match = cleanURL.match(/github\.com\/([^\/]+)\/([^\/]+)/);
    if (!match) return;

    const [_, owner, repo] = match;

    try {
        if (await checkRepoExists(repoURL)) {
            status.textContent = "Downloading repository...";
            const sessionInfo = getSessionPath(); // your existing helper
            currentSessionId = sessionInfo.sessionId;

            // Step A: Download
            const downloadData = await downloadGithubRepo(owner, repo, sessionInfo);
            repoPathOnServer = downloadData.path;

            // Step B: Initialize Index (Backend Pipeline)
            status.textContent = "Indexing files (this may take a minute)...";
            const initRes = await fetch('http://127.0.0.1:5000/api/initialize_index', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ repo_path: repoPathOnServer, session_id: currentSessionId })
            });
            const initData = await initRes.json();
            currentIndexName = initData.index_name;

            document.getElementById("repo-name-display").textContent = `${owner} / ${repo}`;
            buildPromptList('prompt-select-repo', 'run-btn-repo');
            showPage('page-repo');
            status.textContent = "";
        }
    } catch (error) {
        status.textContent = "Error: " + error.message;
    }
});

async function runAnalysis() {
    const resultsContainer = document.getElementById("results-content");
    const fileSelect = document.getElementById("file-select");
    
    // 1. Clear previous result and setup visual feedback
    resultsContainer.innerHTML = `
        <div id="loading-container">
            <p id="loading-text"><strong>Llama 3 is thinking...</strong></p>
            <p id="timer-text">Time elapsed: 0s</p>
            <p style="font-size: 0.8rem; color: #666;">(Check browser console and terminal for details)</p>
        </div>
    `;

    // 2. Start a timer to show activity
    let seconds = 0;
    const timerInterval = setInterval(() => {
        seconds++;
        const timerEl = document.getElementById("timer-text");
        if (timerEl) timerEl.textContent = `Time elapsed: ${seconds}s`;
    }, 1000);

    console.log("%c[FETCH] Sending request to Flask API...", "color: blue; font-weight: bold;");

    try {
        const payload = {
            index_name: currentIndexName,
            template_key: selectedPrompt.key,
            file_index: fileSelect.value !== "" ? parseInt(fileSelect.value) : null
        };

        const response = await fetch('http://127.0.0.1:5000/api/query_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

        const data = await response.json();
        
        // 3. Stop timer and show result
        clearInterval(timerInterval);
        console.log("%c[SUCCESS] Response received from Llama 3.", "color: green; font-weight: bold;");
        
        resultsContainer.innerHTML = data.answer 
            ? `<div class="answer-box"><pre style="white-space: pre-wrap;">${data.answer}</pre></div>` 
            : `<p class="error">Error: ${data.error}</p>`;

    } catch (error) {
        clearInterval(timerInterval);
        console.error("[ERROR] Query failed:", error);
        resultsContainer.innerHTML = `<p class="error"><strong>Analysis Failed:</strong> ${error.message}</p>`;
    }
}


/* 
    try {

      const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`);

      if (response.ok) {
        document.getElementById("repo-name-display").textContent = `${owner} / ${repo}`;
        buildPromptList('prompt-select-repo', 'run-btn-repo');
        showPage('page-repo');
      } else {
        status.textContent = "Repository not found.";
      }

    } catch (error) {
      status.textContent = "Error checking repository.";
    }

    return;
  }

  //Case 2: Nothing entered
  status.textContent = "Please upload a file OR paste a GitHub repo URL.";
*/


//Adding things from here and below for page three where the results are posted 
//and the dropdown for file and function

// =============================================================================
// TODO: REPLACE BELOW WITH ELASTICSEARCH DATA
// =============================================================================
 
// List of all file names in the repo
const esFiles = ["index.js", "app.py", "style.css"];
 
// Map of file name → array of function names inside that file
const esFunctionsByFile = {
  "index.js":   ["handleClick", "renderApp", "fetchData"],
  "app.py":     ["main", "process_input", "connect_db"],
  "style.css":  []
};
 
// Flat list of every function across all files (auto-derived — do not edit)
const esAllFunctions = [...new Set(Object.values(esFunctionsByFile).flat())];
 
// =============================================================================
 
function populateSelect(selectEl, items, placeholder) {
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    selectEl.appendChild(opt);
  });
}
 
async function setupPage3Dropdowns(prompt) {
    const fileSection = document.getElementById("file-dropdown-section");
    const fileSelect = document.getElementById("file-select");

    // Fetch the actual file list from the backend index
    const res = await fetch('http://127.0.0.1:5000/api/get_files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index_name: currentIndexName })
    });
    const data = await res.json();
    
    // Show dropdown if prompt needs it (C1, C2, C3, D2)
    if (["C1", "C2", "C3", "D2"].includes(prompt.id)) {
        fileSection.classList.remove("hidden");
        fileSelect.innerHTML = '<option value="">-- Select a File --</option>';
        data.files.forEach((file, index) => {
            const opt = document.createElement("option");
            opt.value = index;
            opt.textContent = file.value;
            fileSelect.appendChild(opt);
        });
    } else {
        fileSection.classList.add("hidden");
    }
}
 
function goToPage3(prevPage) {
  document.getElementById("selected-prompt-title").textContent = selectedPrompt.desc;
  document.getElementById("backButton3").dataset.prev = prevPage;
  setupPage3Dropdowns(selectedPrompt);
  showPage("page-results");
}
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("run-query-btn").addEventListener("click", runAnalysis);

  document.getElementById("run-btn-files").addEventListener("click", () => {
    goToPage3("page-files");
  });
 
  document.getElementById("run-btn-repo").addEventListener("click", () => {
    goToPage3("page-repo");
  });
 
  document.getElementById("backButton3").addEventListener("click", () => {
    showPage(document.getElementById("backButton3").dataset.prev || "homepage");
  });
});

