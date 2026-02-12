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