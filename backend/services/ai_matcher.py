

from services.LLMProvider import (
    AtsOptimizedCv,
    JobMatchAnalysis,
    get_llm_provider,
)


# Funciones auxiliares de lectura de CV



# Instancia global que utilizará el resto de la aplicación
_provider = get_llm_provider()


def evaluate_job_offer(job_description: str) -> JobMatchAnalysis:
    return _provider.evaluate_job(job_description)


def generate_ats_cv(job_description: str) -> AtsOptimizedCv:
    return _provider.generate_cv(job_description)
