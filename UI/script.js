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

document.getElementById("backButton2").addEventListener("click", () => showPage('homepage'));
document.getElementById("loadRepoButton").addEventListener("click", async () => {

  const repoURL = document.getElementById("repoURL").value.trim();
  const status = document.getElementById("status");

  //Case 1: Repo URL entered
  if (repoURL) {

    const cleanURL = repoURL.replace(/\.git$/, '').replace(/\/$/, '');
    const match = cleanURL.match(/github\.com\/([^\/]+)\/([^\/]+)/);

    if (!match) {
      status.textContent = "Invalid GitHub URL.";
      return;
    }

    const owner = match[1];
    const repo = match[2];

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

});