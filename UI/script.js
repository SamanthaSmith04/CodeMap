document.getElementById("Continue").addEventListener("click", async () => {

    const fileInput = document.getElementById("fileInput");
    const repoURL = document.getElementById("repoURL").value.trim();
    const status = document.getElementById("status");
  
    //Case 1: File uploaded
    if (fileInput.files.length > 0) {
  
      const file = fileInput.files[0];
      status.textContent = `File uploaded: ${file.name}`;
  
      return;
    }
  
    //Case 2: Repo URL entered
    if (repoURL) {
  
      const match = repoURL.match(/github\.com\/([^\/]+)\/([^\/]+)/);
  
      if (!match) {
        status.textContent = "Invalid GitHub URL.";
        return;
      }
  
      const owner = match[1];
      const repo = match[2];
  
      try {
  
        const response = await fetch(`https://api.github.com/repos/${owner}/${repo}`);
  
        if (response.ok) {
          status.textContent = "Repository exists!";
        } else {
          status.textContent = "Repository not found.";
        }
  
      } catch (error) {
        status.textContent = "Error checking repository.";
      }
  
      return;
    }
  
    //Case 3: Nothing entered
    status.textContent = "Please upload a file OR paste a GitHub repo URL.";
  
  });

function goToNextPage() {
    const fileInput = document.getElementById('fileInput');
    const repoName = document.getElementById('repoName');
    const ownerName = document.getElementById('ownerName');


    if (!fileInput.files.length && (repoName.value != "Repository Name")&& (ownerName.value != "Owner Name")) {
      alert('Please upload a file or enter github information');
      return;
    }

    // Simulated file list (this would come from backend later)
    const files = fileInput.files.length
      ? Array.from(fileInput.files).map(f => f.name)
      : ['README.md', 'src/', 'package.json'];

    document.getElementById('page-upload').classList.add('hidden');
    document.getElementById('page-files').classList.remove('hidden');

    document.getElementById('projectName').innerText =
      fileInput.files.length
        ? `Uploaded: ${fileInput.files[0].name}`
        : `Link: ${linkInput.value}`;

    const dropdown = document.getElementById('fileDropdown');
    dropdown.innerHTML = '<option>Select a file...</option>';

    files.forEach(file => {
      const option = document.createElement('option');
      option.value = file;
      option.textContent = file;
      dropdown.appendChild(option);
    });
  }

function loadGithubRepo() {

  const repoLink = document.getElementById("repoLink").value;

  if (!repoLink) {
    alert("Please paste a GitHub repo link");
    return;
  }

  console.log("Loading repo:", repoLink);

  goToFilePage();
  }

function loadLocalFiles() {

const files = document.getElementById("fileUpload").files;

if (files.length === 0) {
  alert("Please upload files");
  return;
}

console.log("Uploaded files:", files);

goToFilePage();
}