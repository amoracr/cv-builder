import os

from base import BaseLLMProvider
from schemas import AtsOptimizedCv, JobMatchAnalysis


class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY es obligatoria cuando LLM_ENGINE=openai")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = self.evaluate_job_prompt.format(
            cv_text=cv_text, job_description=job_description
        )

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
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
        cv_text = self.load_local_cv()
        prompt = self.write_cv_prompt.format(
            cv_text=cv_text, job_description=job_description
        )

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
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