import os

from base import BaseLLMProvider
from claude import ClaudeProvider
from gemini import GeminiProvider
from ollama import OllamaProvider
from openai import OpenAIProvider


def get_llm_provider() -> BaseLLMProvider:
    engine = os.getenv("LLM_ENGINE", "").strip().lower()

    if not engine:
        raise ValueError(
            "La variable de entorno LLM_ENGINE no está definida en el archivo .env"
        )
    if engine == "claude":
        return ClaudeProvider()
    elif engine == "gemini":
        return GeminiProvider()
    elif engine == "ollama":
        return OllamaProvider()
    elif engine == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(
            f"Motor de LLM no válido: '{engine}'. Las opciones permitidas en LLM_ENGINE son 'gemini' u 'ollama'."
        )
