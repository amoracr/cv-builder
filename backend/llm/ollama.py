import os

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        import ollama

        self.host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.model = os.getenv("OLLAMA_MODEL")
        if not self.model:
            raise ValueError("OLLAMA_MODEL es obligatoria cuando LLM_ENGINE=ollama")
        self.client = ollama.Client(host=self.host)

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = self.evaluate_job_prompt.format(
            cv_text=cv_text, job_description=job_description
        )

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a critical, unbiased technical recruiter. Output strictly valid JSON matching the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            format=JobMatchAnalysis.model_json_schema(),
            options={
                "temperature": self.evaluate_job_temperature,
                "num_predict": self.evaluate_job_tokens,
            },
        )
        return JobMatchAnalysis.model_validate_json(response.message.content)

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        cv_text = self.load_local_cv()
        prompt = self.write_cv_prompt.format(
            cv_text=cv_text, job_description=job_description
        )

        response = self.client.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ATS CV writer. Output strictly valid JSON matching the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            format=AtsOptimizedCv.model_json_schema(),
            options={
                "temperature": self.write_cv_temperature,
                "num_predict": self.write_cv_tokens,
            },
        )
        return AtsOptimizedCv.model_validate_json(response.message.content)
