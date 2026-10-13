import os

from .base import BaseLLMProvider
from .schemas import AtsCoverLetter, AtsOptimizedCv, JobMatchAnalysis


class OpenAIProvider(BaseLLMProvider):

    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY es obligatoria para usar OpenAI")

        self.client = OpenAI(api_key=api_key)

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL", os.getenv("OPENAI_LIGHT_MODEL", "gpt-4o-mini")
        )

        self.write_model = os.getenv(
            "WRITE_CV_MODEL",
            os.getenv("OPENAI_PRO_MODEL", "gpt-4o"),
        )

        self.write_cl_model = os.getenv(
            "WRITE_CL_MODEL",
            os.getenv("OPENAI_PRO_MODEL", "gpt-4o"),
        )

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        prompt = self.get_evaluation_prompt(job_description)

        completion = self.client.beta.chat.completions.parse(
            model=self.evaluate_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a critical, unbiased technical recruiter.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=JobMatchAnalysis,
            temperature=self.evaluate_job_temperature,
            max_tokens=self.evaluate_job_tokens,
        )
        return completion.choices[0].message.parsed

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        prompt = self.get_write_cv_prompt(job_description)

        completion = self.client.beta.chat.completions.parse(
            model=self.write_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ATS CV writer.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=AtsOptimizedCv,
            temperature=self.write_cv_temperature,
            max_tokens=self.write_cv_tokens,
        )
        return completion.choices[0].message.parsed

    def generate_cover_letter(self, job_description: str) -> AtsCoverLetter:
        prompt = self.get_write_cl_prompt(job_description)

        completion = self.client.beta.chat.completions.parse(
            model=self.write_cl_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert technical career consultant and"
                        " corporate copywriter. You write highly persuasive,"
                        " concise, and tailored cover letters strictly based on"
                        " candidate facts."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=AtsCoverLetter,
            temperature=self.write_cl_temperature,
            max_tokens=self.write_cl_tokens,
        )
        return completion.choices[0].message.parsed