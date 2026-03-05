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