import requests
from ..config.settings import settings


class OllamaClient:
    """Very small Ollama HTTP wrapper. Keeps calls isolated so tests can mock it.

    Expects an Ollama server at settings.BASE_URL serving the model named in settings.CHAT_MODEL.
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.BASE_URL
        self.model = model or settings.CHAT_MODEL

    def generate(self, prompt: str, temperature: float | None = None) -> str:
        url = f"{self.base_url}/api/generate"
        body = {"model": self.model, "prompt": prompt}
        if temperature is not None:
            body["temperature"] = temperature
        try:
            resp = requests.post(url, json=body, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Ollama response shapes vary; be defensive
            if isinstance(data, dict):
                return data.get("text") or data.get("output") or str(data)
            return str(data)
        except Exception:
            return ""
