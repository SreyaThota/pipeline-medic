from fastapi import FastAPI
import requests

app = FastAPI()

@app.post("/diagnose")
def diagnose(log_text: str):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2",
            "prompt": f"Summarize this build log in 2 sentences:\n{log_text}",
            "stream": False
        }
    )
    return {"summary": response.json()["response"]}