'''
GitHub REST API 
'''
import requests
import os

folder_location = "temp_files/"

def set_up_github_connection(repo_url, token_location="GITHUBACCESSTOKEN"):
    """
    Sets up github connection
    """
    with open(token_location, "r") as f:
        token = f.read().strip()

    repo_names = "/".join(repo_url.rstrip(".git").split("/")[-2:])

    url = f"https://api.github.com/repos/{repo_names}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return headers, url

def set_up_github_connection(owner, repo, token_location="GITHUBACCESSTOKEN"):
    """
    Sets up github connection
    """
    with open(token_location, "r") as f:
        token = f.read().strip()

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return headers, url

def check_repo_exists(url):
    """
        Makes a test call to the API to validate the repo exists
        Parameters:
            url: The link to the starting point of the repo
        Returns:
            True if repo is found, false otherwise
    """

    repo_names = "/".join(url.rstrip(".git").split("/")[-2:])

    url = f"https://api.github.com/repos/{repo_names}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers)

    response.raise_for_status()
    if response.status_code != 200:
        print(f"Failed to send request")
        print(f"Message: {response.json()['message']}")
        return false;
    return true;

def get_repo_contents(headers, url, save_path):
    """
    Downloads the repo contents to files under the dynamic save_path.
    """
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Create the base save_path if it doesn't exist
    os.makedirs(save_path, exist_ok=True)

    # Save the raw repo metadata
    # with open(os.path.join(save_path, 'code.txt'), 'w', encoding='utf-8') as f:
    #     f.write(str(data) + '\n')
        
    contents_url = data['contents_url'].replace('{+path}', '')
    
    # Initial fetch
    contents_response = requests.get(contents_url, headers=headers)
    contents_response.raise_for_status()
    contents_data = contents_response.json()

    # Queue to handle directories iteratively
    content_queue = contents_data
    
    while len(content_queue) > 0:
        item = content_queue.pop(0)
        
        if item['type'] == 'file':
            file_response = requests.get(item['download_url'], headers=headers)
            file_response.raise_for_status()

            # Use the dynamic save_path
            local_path = os.path.join(save_path, item['path'])
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, 'w', encoding='utf-8') as file:
                file.write(file_response.text)
                
        elif item['type'] == 'dir':
            # Fetch directory contents and add them to the queue
            dir_resp = requests.get(item['url'], headers=headers)
            dir_resp.raise_for_status()
            content_queue.extend(dir_resp.json())


def get_commit_history(headers, url, save_path):
    """
    Prints the commit history to a file under save_path/commits.txt
    """
    commits_url = url + "/commits"
    response = requests.get(commits_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    file_path = os.path.join(save_path, 'commits.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('--------------------------------------------\n')
        for item in data:
            if item['commit']['verification']['payload']:
                f.write(item['commit']['verification']['payload'])
                f.write('\n--------------------------------------------\n')
                
def get_issue_history(headers, url, save_path):
    """
    Prints the github issue history to a file under save_path/issues.txt
    """
    issues_url = url + "/issues"
    params = {"state" : "all"}
    
    response = requests.get(issues_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    
    file_path = os.path.join(save_path, 'issues.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            if item.get('title'):
                f.write('--------------------------------------------\n')
                f.write("TITLE: " + item['title'] + "\n")
            if item.get('state'):
                f.write("ISSUE STATE: " + item['state'] + "\n")
            if item.get('labels'):
                f.write("LABELS:\n")
                for label in item['labels']:
                    if label.get('name'):
                        f.write(" - " + label['name'] + "\n")
            if item.get('assignees'):
                f.write("ASSIGNEES:\n")
                for assignee in item['assignees']:
                    f.write(" - " + assignee['login'] + "\n")
            if item.get("body"):
                f.write(item['body'] + "\n")
            if item.get('url'):
                f.write("COMMENTS:\n")
                comments_url = item['url'] + "/comments"
                comments_resp = requests.get(comments_url, headers=headers)
                if comments_resp.status_code == 200:
                    comment_data = comments_resp.json()
                    for comment in comment_data:
                        if comment.get('body'):
                            f.write("\t" + comment['body'] + "\n")

def list_pull_requests(headers, url, save_path, state="open", per_page=30, page=1):
    """
    Lists pull requests for the repo.
    """
    pulls_url = url + "/pulls"
    params = {
        "state": state,
        "per_page": per_page,
        "page": page,
        "sort": "created",
        "direction": "desc",
    }

    response = requests.get(pulls_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    # Create a PRS folder inside the unique save_path
    prs_dir = os.path.join(save_path, "PRS")
    os.makedirs(prs_dir, exist_ok=True)
    
    file_path = os.path.join(prs_dir, 'pulls_list.txt')
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(f"PRs (state={state}, per_page={per_page}, page={page})\n")
        f.write("--------------------------------------------\n")
        for pr in data:
            f.write(f"#{pr.get('number')}  {pr.get('title')}\n")
            f.write(f"State: {pr.get('state')} | Draft: {pr.get('draft')} | Merged: {pr.get('merged_at') is not None}\n")
            f.write(f"Author: {pr.get('user', {}).get('login')} | Created: {pr.get('created_at')} | Updated: {pr.get('updated_at')}\n")
            f.write(f"URL: {pr.get('html_url')}\n")
            f.write("--------------------------------------------\n")

    return data

def get_pull_request_details(headers, url, pull_number, save_path):
    """
    Gets full details for a specific pull request.
    """
    pr_url = url + f"/pulls/{pull_number}"

    response = requests.get(pr_url, headers=headers)
    response.raise_for_status()
    pr = response.json()

    prs_dir = os.path.join(save_path, "PRS")
    os.makedirs(prs_dir, exist_ok=True)
    
    file_path = os.path.join(prs_dir, 'pr_details.txt')
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(f"PR Details: #{pr.get('number')} - {pr.get('title')}\n")
        f.write("--------------------------------------------\n")
        # ... (rest of PR write logic remains the same)
        f.write(f"State: {pr.get('state')} | Draft: {pr.get('draft')} | Merged: {pr.get('merged_at') is not None}\n")
        f.write(f"URL: {pr.get('html_url')}\n")

    return pr

def get_pr_review_comments(headers, url, pull_number, save_path):
    """
    Prints the github PR history to a file.
    """
    comments_url = url + f"/pulls/{pull_number}/comments"
    response = requests.get(comments_url, headers=headers)
    data = response.json()

    prs_dir = os.path.join(save_path, "PRS")
    os.makedirs(prs_dir, exist_ok=True)

    file_path = os.path.join(prs_dir, 'pr_review_comments.txt')
    with open(file_path, 'w', encoding='utf-8') as f:
        for comment in data:
            user = comment['user']['login']
            body = comment['body']
            path = comment['path']

            f.write(f"User: {user}\n")
            f.write(f"File: {path}\n")
            f.write(f"Comment: {body}\n")
            f.write('--------------------------------------------\n')