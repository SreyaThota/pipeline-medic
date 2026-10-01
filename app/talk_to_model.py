import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "llama3.2",
        "prompt": "Explain what a build pipeline is, in one sentence.",
        "stream": False
    }
)

print(response.json()["response"])