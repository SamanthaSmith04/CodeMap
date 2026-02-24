# CodeMap 🗺️

## Project Setup

`python3 -m venv venv`

`source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)

`pip install -r requirements.txt`


## Access Tokens
Some access commands require a GitHub authentication code, which is outlined in [this guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)
**This token is private and should not be shared publically**, a convenient way to store it is to create a file `GITHUBACCESSTOKEN` in the top-level folder of this repo `CodeMap/` and paste the code into there. This file is automatically ignored by the `.gitignore` file, so it will not be tracked by git. I have my testing script automatically pull the token from this file.

## Running code
```
docker run -d --name es-local \
     -p 9201:9200 \
     -e "discovery.type=single-node" \
     -e "xpack.security.enabled=false" \
     docker.elastic.co/elasticsearch/elasticsearch:8.15.0
```

```
curl http://127.0.0.1:9201
```

```
ollama serve
```

```
ollama run llama3.1
```