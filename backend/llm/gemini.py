import os

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY es obligatoria cuando LLM_ENGINE=gemini")

        self.client = genai.Client(api_key=api_key)
        self.types = types
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = self.evaluate_job_prompt.format(
            cv_text=cv_text, job_description=job_description
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobMatchAnalysis,
                temperature=self.evaluate_job_temperature,
                max_output_tokens=self.evaluate_job_tokens,
            ),
        )
        return JobMatchAnalysis.model_validate_json(response.text)

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        cv_text = self.load_local_cv()
        prompt = self.write_cv_prompt.format(
            cv_text=cv_text, job_description=job_description
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AtsOptimizedCv,
                temperature=self.write_cv_temperature,
                max_output_tokens=self.write_cv_tokens,
            ),
        )
        return AtsOptimizedCv.model_validate_json(response.text)
