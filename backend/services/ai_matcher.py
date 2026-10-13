from llm.LLMProvider import get_llm_provider
from llm.schemas import AtsCoverLetter, AtsOptimizedCv, JobMatchAnalysis


def evaluate_job_offer(job_description: str) -> JobMatchAnalysis:
    # Instancia el motor configurado para evaluar
    evaluator = get_llm_provider(task="evaluate")
    return evaluator.evaluate_job(job_description)


def generate_ats_cv(job_description: str) -> AtsOptimizedCv:
    # Instancia el motor configurado para escribir
    writer = get_llm_provider(task="write_cv")
    return writer.generate_cv(job_description)


def generate_ats_cl(job_description: str) -> AtsCoverLetter:
    # Instancia el motor configurado para la carta
    writer = get_llm_provider(task="write_letter")
    return writer.generate_cover_letter(job_description)
