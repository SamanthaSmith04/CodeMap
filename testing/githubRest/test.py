'''
Testing script for demonstrating GitHub REST API usage.

'''
import requests
import os

owner = "SamanthaSmith04"
repo = "GeodesicSurfaceInformedPlanner"
token_location = "GITHUBACCESSTOKEN"
token = open(token_location, "r").read().strip()

url = f"https://api.github.com/repos/{owner}/{repo}"

headers = {
  "Accept": "application/vnd.github+json",
  "Authorization": f"Bearer {token}",
  "X-GitHub-Api-Version": "2022-11-28",
}

def get_repo_contents():
    response = requests.get(url, headers=headers)

    response.raise_for_status()
    if response.status_code != 200:
        print(f"Failed to send request")
        print(f"Message: {response.json()['message']}")
        return
    data = response.json()

    # Open out.txt for writing
    folder_location = "testing/githubRest/files/"

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(folder_location), exist_ok=True)
    with open('testing/githubRest/code.txt', 'w') as f:
        f.write(str(data) + '\n')  # Write the repository data

        contents_url = data['contents_url'].replace('{+path}', '')
        trees_url = data['trees_url'].replace('{/sha}', '')
        f.write("Contents URL: " + contents_url + '\n')
        f.write("Trees URL: " + trees_url + '\n')

        # Example: Fetch repository contents
        contents_response = requests.get(contents_url, headers=headers) 
        contents_response.raise_for_status()
        contents_data = contents_response.json()
        f.write("Repository Contents: " + str(contents_data) + '\n')

        # Read files from contents_data
        content_queue = []
        for item in contents_data:
            if item['type'] == 'file':
                file_response = requests.get(item['download_url'], headers=headers)
                file_response.raise_for_status()
                f.write(f"Contents of {item['name']}:\n{file_response.text}\n")
                file = open(folder_location + "/" + item['name'], 'w')
                file.write(file_response.text)
                file.close()
            elif item['type'] == 'dir':
                content_queue.append(item['path'])

        while len(content_queue) > 0:
            current_path = content_queue.pop(0)
            dir_contents_url = contents_url + current_path
            dir_response = requests.get(dir_contents_url, headers=headers)
            dir_response.raise_for_status()
            dir_contents_data = dir_response.json()
            for item in dir_contents_data:
                if item['type'] == 'file':
                    file_response = requests.get(item['download_url'], headers=headers)
                    file_response.raise_for_status()
                    f.write(f"Contents of {item['name']}:\n{file_response.text}\n")
                    file = open(folder_location + "/" + item['name'], 'w')
                    file.write(file_response.text)
                    file.close()
                elif item['type'] == 'dir':
                    content_queue.append(item['path'])

def get_commit_history():
    commits_url = url + "/commits"
    response = requests.get(commits_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    with open('testing/githubRest/commits.txt', 'w') as f:
        f.write('--------------------------------------------\n')
        for item in data:
            if item['commit']['verification']['payload']:
                f.write(item['commit']['verification']['payload'])
                f.write('\n--------------------------------------------\n')

def list_pull_requests(state="open", per_page=30, page=1, output_path="testing/githubRest/pulls_list.txt"):
    """
    Lists pull requests for the repo.
    state: "open", "closed", or "all"
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

    with open(output_path, "w") as f:
        f.write(f"PRs (state={state}, per_page={per_page}, page={page})\n")
        f.write("--------------------------------------------\n")
        for pr in data:
            f.write(f"#{pr.get('number')}  {pr.get('title')}\n")
            f.write(f"State: {pr.get('state')} | Draft: {pr.get('draft')} | Merged: {pr.get('merged_at') is not None}\n")
            f.write(f"Author: {pr.get('user', {}).get('login')} | Created: {pr.get('created_at')} | Updated: {pr.get('updated_at')}\n")
            f.write(f"URL: {pr.get('html_url')}\n")
            f.write("--------------------------------------------\n")

    return data

def get_pull_request_details(pull_number, output_path="testing/githubRest/pr_details.txt"):
    """
    Gets full details for a specific pull request.
    """
    pr_url = url + f"/pulls/{pull_number}"

    response = requests.get(pr_url, headers=headers)
    response.raise_for_status()
    pr = response.json()

    with open(output_path, "w") as f:
        f.write(f"PR Details: #{pr.get('number')} - {pr.get('title')}\n")
        f.write("--------------------------------------------\n")
        f.write(f"State: {pr.get('state')} | Draft: {pr.get('draft')} | Merged: {pr.get('merged_at') is not None}\n")
        f.write(f"Author: {pr.get('user', {}).get('login')}\n")
        f.write(f"Created: {pr.get('created_at')}\n")
        f.write(f"Updated: {pr.get('updated_at')}\n")
        f.write(f"Base: {pr.get('base', {}).get('ref')}  <-  Head: {pr.get('head', {}).get('ref')}\n")
        f.write(f"Additions: {pr.get('additions')} | Deletions: {pr.get('deletions')} | Changed files: {pr.get('changed_files')}\n")
        f.write(f"Commits: {pr.get('commits')} | Comments: {pr.get('comments')} | Review comments: {pr.get('review_comments')}\n")
        f.write(f"URL: {pr.get('html_url')}\n")
        f.write("--------------------------------------------\n\n")

        body = pr.get("body") or ""
        if body.strip():
            f.write("Body:\n")
            f.write(body)
            f.write("\n")

    return pr

def get_pr_review_comments(pull_number):
    comments_url = url + f"/pulls/{pull_number}/comments"
    response = requests.get(comments_url, headers=headers)
    data = response.json()

    with open('testing/githubRest/pr_review_comments.txt', 'w') as f:
        for comment in data:
            user = comment['user']['login']
            body = comment['body']
            path = comment['path']

            f.write(f"User: {user}\n")
            f.write(f"File: {path}\n")
            f.write(f"Comment: {body}\n")
            f.write('--------------------------------------------\n')
    
def get_issue_history():
    issues_url = url + "/issues"
    params = {
        "state" : "all"
    }
    response = requests.get(issues_url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    with open('testing/githubRest/issues.txt', 'w') as f:
        for item in data:
            if item['title']:
                f.write('--------------------------------------------\n')
                f.write("TITLE: " + item['title'] + "\n")
            if item['state']:
                f.write("ISSUE STATE: " + item['state'] + "\n")
            if item['labels']:
                f.write("LABELS:\n")
                for label in item['labels']:
                    if label['name']:
                        f.write(" - " + label['name'] + "\n")
            if item['assignees']:
                f.write("ASSIGNEES:\n")
                for assignee in item['assignees']:
                    f.write(" - " + assignee['login'] + "\n")
            if item["body"]:
                f.write(item['body'] + "\n")
            if item['url']:
                f.write("COMMENTS:\n")
                comments_url = item['url'] + "/comments"
                comments_resp = requests.get(comments_url, headers=headers)
                comments_resp.raise_for_status()
                comment_data = comments_resp.json()
                for comment in comment_data:
                    if comment['body']:
                        f.write("\t" + comment['body'] + "\n")


if __name__ == "__main__":
    get_repo_contents()
    get_commit_history()
    list_pull_requests()
    get_pull_request_details(44)
    get_pr_review_comments(44)