# CodeMap 🗺️

## Project Setup

`python3 -m venv venv`

`source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)

`pip install -r requirements.txt`

## Dependencies Setup

### 1. Python Environment

Follow the project setup above to create a virtual environment and install dependencies.

### 2. Start Elasticsearch (Docker)

Make sure Docker Desktop is installed and running. Then run this (same command you used):

```
docker run -d --name es-local \
  -p 9201:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.15.0
```

- Wait 30–60 seconds for it to start.
- Test it works:
  ```
  curl http://127.0.0.1:9201
  ```
  Should return JSON with `"tagline": "You Know, for Search"`.

### 3. Start Ollama (local LLM)

- Download/install Ollama: https://ollama.com/download (Mac/Windows app)
- Open a terminal tab and start the server:
  ```
  ollama serve
  ```
  (leave this running)
- In another terminal tab, download/run a model:
  ```
  ollama run llama3.1
  ```
  (or `ollama run mistral` for smaller/faster — first time downloads ~4–5 GB, takes a few minutes)

## GitHub REST API Setup

### Access Tokens

Some access commands require a GitHub authentication code, which is outlined in [this guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
**This token is private and should not be shared publically**, a convenient way to store it is to create a file `GITHUBACCESSTOKEN` in the top-level folder of this repo `CodeMap/` and paste the code into there. This file is automatically ignored by the `.gitignore` file, so it will not be tracked by git. I have my testing script automatically pull the token from this file.

### Running test script

`python3 testing/githubRest/test.py`