import os

from .base import BaseLLMProvider
from .claude import ClaudeProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider


def get_llm_provider(task: str = "evaluate") -> BaseLLMProvider:
    """
    Retorna el proveedor LLM según la tarea configurada en el .env:
    - task="evaluate": Lee EVALUATE_ENGINE (por defecto 'ollama')
    - task="write": Lee WRITE_CV_ENGINE (por defecto 'gemini')
    Mantiene compatibilidad con el antiguo LLM_ENGINE si fuera necesario.
    """
    task = task.strip().lower()

    # Seleccionar la variable de entorno según la fase del pipeline
    if task == "evaluate":
        engine = os.getenv("EVALUATE_ENGINE", os.getenv("LLM_ENGINE", "ollama"))
    elif task == "write":
        engine = os.getenv("WRITE_CV_ENGINE", os.getenv("LLM_ENGINE", "gemini"))
    else:
        # Por si pasa directamente el nombre del engine
        engine = task

    engine = engine.strip().lower()

    # Mapeo de proveedores disponibles
    providers = {
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
    }

    provider_cls = providers.get(engine)
    if not provider_cls:
        raise ValueError(
            f"Motor de LLM no válido: '{engine}'. Las opciones permitidas son: {list(providers.keys())}"
        )

    return provider_cls()
