import os
import requests


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def chat(model: str, system_prompt: str, messages: list[dict], user_message: str) -> str:
    """Send a chat request to Ollama and return the response text."""
    payload = {
        "model": model,
        "messages": _build_messages(system_prompt, messages, user_message),
        "stream": False,
    }
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "Sorry, I took too long to respond. Please try again."
    except Exception as e:
        return f"Error contacting AI service: {str(e)}"


def list_models() -> list[str]:
    """Return list of model names available in Ollama."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        return [os.getenv("DEFAULT_MODEL", "tinyllama")]


def is_available() -> bool:
    try:
        requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return True
    except Exception:
        return False


def _build_messages(system_prompt: str, history: list[dict], user_message: str) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "user" if msg["sender_type"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages
