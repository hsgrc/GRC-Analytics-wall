import requests

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
r.raise_for_status()
models = {m.get("name") for m in r.json().get("models", [])}
print("Ollama:", OLLAMA_BASE_URL)
print("Configured model:", OLLAMA_MODEL)
print("Model installed:", OLLAMA_MODEL in models)
