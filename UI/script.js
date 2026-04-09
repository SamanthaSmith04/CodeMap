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
      const response = await fetch('/api/repo_exists', {
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

      return data;
  } catch (err) {
      console.error("Request failed:", err);
  }
}

//Pulls down all the files from the github
async function downloadGithubRepo(repoOwner, repoName, tempDir) {
  try {
      const response = await fetch('/api/download_github_repo', {
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

  const sessionId = (choice !== "3")
      ? randomId
      : userInputSessionId.trim();

  // In browser, no true cwd → simulate with base path
  const basePath = ""; // or something like "/tmp" if your backend expects it

  const fullPath = `${basePath}/repo_${sessionId}`;

  return { sessionId, fullPath };
}
//
document.getElementById("backButton2").addEventListener("click", () => showPage('homepage'));
document.getElementById("loadRepoButton").addEventListener("click", async () => {

  const repoURL = document.getElementById("repoURL").value.trim();
  const status = document.getElementById("status");

  //Case 1: Repo URL entered
  //if (repoURL) {

    const cleanURL = repoURL.replace(/\.git$/, '').replace(/\/$/, '');
    const match = cleanURL.match(/github\.com\/([^\/]+)\/([^\/]+)/);

    const owner = match[1];
    const repo = match[2];
  try{
    if (checkRepoExists(repoURL)) {
      document.getElementById("repo-name-display").textContent = `${owner} / ${repo}`;
      buildPromptList('prompt-select-repo', 'run-btn-repo');
      showPage('page-repo'); 
      //Pulls the files from the github repo to a temp file for us to use to run
      tempDir = getSessionPath()
      downloadGithubRepo(owner, repo, tempDir);
    } else {
      status.textContent = "Invalid GitHub URL.";
    }
  }catch (error) {
    console.error(error);
    status.textContent = "Error checking repository.";
  }

  });


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
 
function setupPage3Dropdowns(prompt) {
  const fileSection     = document.getElementById("file-dropdown-section");
  const functionSection = document.getElementById("function-dropdown-section");
  const fileSelect      = document.getElementById("file-select");
  const functionSelect  = document.getElementById("function-select");
 
  if (!fileSection || !functionSection) return;

  // Hide both to start
  fileSection.classList.add("hidden");
  functionSection.classList.add("hidden");
  functionSelect.disabled = true;

  
  switch(prompt.id) {

    case "A1":
        query_session(null, "A1");

      break;
      
    case "A2":
        //Call func
      break;

    case "A3":
        //Call func
      break;
    
    case "B1":
        //Call func
      break; 

    case "B2":
        //Call func
      break;

    case "B3":
        //Call func
      break;

    case "B4":
        //Call func
      break;

    case "C1":
     // File dropdown only
      populateSelect(fileSelect, esFiles, "-- Choose a file --");
      fileSection.classList.remove("hidden");
      break;

    case "C2":
      // Function dropdown only (not dependent on a file)
      populateSelect(functionSelect, esAllFunctions, "-- Choose a function --");
      functionSelect.disabled = false;
      functionSection.classList.remove("hidden");
      break;
      
    case "C3":
        // File first, then function dropdown populates based on selection
      populateSelect(fileSelect, esFiles, "-- Choose a file --");
      populateSelect(functionSelect, [], "-- Select a file first --");
      fileSection.classList.remove("hidden");
      functionSection.classList.remove("hidden");
 
      fileSelect.addEventListener("change", () => {
        const selectedFile = fileSelect.value;
        if (selectedFile && esFunctionsByFile[selectedFile]) {
          populateSelect(functionSelect, esFunctionsByFile[selectedFile], "-- Choose a function --");
          functionSelect.disabled = false;
        } else {
          populateSelect(functionSelect, [], "-- Select a file first --");
          functionSelect.disabled = true;
        }
      });
      break;

    case "D1":
        //Call func
      break; 
    
    case "D2":
        // File first, then function dropdown populates based on selection
      populateSelect(fileSelect, esFiles, "-- Choose a file --");
      populateSelect(functionSelect, [], "-- Select a file first --");
      fileSection.classList.remove("hidden");
      functionSection.classList.remove("hidden");
 
      fileSelect.addEventListener("change", () => {
        const selectedFile = fileSelect.value;
        if (selectedFile && esFunctionsByFile[selectedFile]) {
          populateSelect(functionSelect, esFunctionsByFile[selectedFile], "-- Choose a function --");
          functionSelect.disabled = false;
        } else {
          populateSelect(functionSelect, [], "-- Select a file first --");
          functionSelect.disabled = true;
        }
      });
      break;

    case "E1":
        //Call func
      break; 

    case "E2":
        //Call func
      break; 

  }
}
 
function goToPage3(prevPage) {
  document.getElementById("selected-prompt-title").textContent = selectedPrompt.desc;
  document.getElementById("backButton3").dataset.prev = prevPage;
  setupPage3Dropdowns(selectedPrompt);
  showPage("page-results");
}
document.addEventListener("DOMContentLoaded", () => {
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

