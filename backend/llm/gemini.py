import os

from google import genai
from google.genai import types

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class GeminiProvider(BaseLLMProvider):
    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY es obligatoria para usar Gemini")

        self.client = genai.Client(api_key=api_key)
        self.types = types

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL", os.getenv("GEMINI_LIGHT_MODEL", "gemini-2.5-flash")
        )

        self.write_model = os.getenv(
            "WRITE_CV_MODEL", os.getenv("GEMINI_PRO_MODEL", self.evaluate_model)
        )

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        prompt = self.get_evaluation_prompt(job_description)

        response = self.client.models.generate_content(
            model=self.evaluate_model,
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
        prompt = self.get_write_cv_prompt(job_description)

        response = self.client.models.generate_content(
            model=self.write_model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AtsOptimizedCv,
                temperature=self.write_cv_temperature,
                max_output_tokens=self.write_cv_tokens,
            ),
        )
        return AtsOptimizedCv.model_validate_json(response.text)
