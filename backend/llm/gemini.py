import os

import google.genai.errors
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import BaseLLMProvider
from .schemas import AtsCoverLetter, AtsOptimizedCv, JobMatchAnalysis


class GeminiProvider(BaseLLMProvider):

    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY es obligatoria para usar Gemini")

        self.client = genai.Client(api_key=api_key)
        self.types = types

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL", os.getenv("GEMINI_LIGHT_MODEL", "gemini-2.5-flash")
        )

        self.write_cv_model = os.getenv(
            "WRITE_CV_MODEL", os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-flash")
        )

        self.write_cl_model = os.getenv(
            "WRITE_CL_MODEL", os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-flash")
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(google.genai.errors.ServerError),
        reraise=True,
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

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(google.genai.errors.ServerError),
        reraise=True,
    )
    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        prompt = self.get_write_cv_prompt(job_description)

        response = self.client.models.generate_content(
            model=self.write_cv_model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AtsOptimizedCv,
                temperature=self.write_cv_temperature,
                max_output_tokens=self.write_cv_tokens,
            ),
        )
        return AtsOptimizedCv.model_validate_json(response.text)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(google.genai.errors.ServerError),
        reraise=True,
    )
    def generate_cover_letter(self, job_description: str) -> AtsCoverLetter:
        prompt = self.get_write_cl_prompt(job_description)

        response = self.client.models.generate_content(
            model=self.write_cl_model,
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AtsCoverLetter,
                temperature=self.write_cl_temperature,
                max_output_tokens=self.write_cl_tokens,
            ),
        )

        content = response.text.strip()

        # Limpieza defensiva en caso de cercas de código ```json
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return AtsCoverLetter.model_validate_json(content)