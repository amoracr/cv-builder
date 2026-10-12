import os
import ollama

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class OllamaProvider(BaseLLMProvider):
    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)

        self.host = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        if not self.host:
            raise ValueError("OLLAMA_BASE_URL es obligatoria cuando se usa Ollama")

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL", os.getenv("OLLAMA_LIGHT_MODEL", "qwen2.5-coder:7b")
        )

        self.write_model = os.getenv(
            "WRITE_CV_MODEL", os.getenv("OLLAMA_PRO_MODEL", self.evaluate_model)
        )

        self.client = ollama.Client(host=self.host)

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        prompt = self.get_evaluation_prompt(job_description)

        response = self.client.chat(
            model=self.evaluate_model,
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
        prompt = self.get_write_cv_prompt(job_description)

        system_instruction = (
            "You are a strict data-transformation compiler. "
            "You never invent data, use placeholders, or write career plans. "
            "You output valid JSON matching the schema containing the factual candidate data with optimized bullet points."
        )

        response = self.client.chat(
            model=self.write_model,
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {"role": "user", "content": prompt},
            ],
            format=AtsOptimizedCv.model_json_schema(),
            options={
                "temperature": self.write_cv_temperature,
                "num_predict": self.write_cv_tokens,
                "top_p": 0.1,
                "repeat_penalty": 1.15,
            },
        )

        return AtsOptimizedCv.model_validate_json(response.message.content)
