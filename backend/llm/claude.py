import os

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY es obligatoria para usar Claude")

        self.client = anthropic.Anthropic(api_key=api_key)

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL",
            os.getenv("CLAUDE_LIGHT_MODEL", "claude-3-5-haiku-20241022"),
        )

        self.write_model = os.getenv(
            "WRITE_CV_MODEL",
            os.getenv(
                "CLAUDE_PRO_MODEL",
                os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            ),
        )

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        prompt = self.get_evaluation_prompt(job_description)

        response = self.client.beta.messages.parse(
            model=self.evaluate_model,
            max_tokens=self.evaluate_job_tokens,
            temperature=self.evaluate_job_temperature,
            betas=["structured-outputs-2025-11-13"],
            response_format=JobMatchAnalysis,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.parsed

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        prompt = self.get_write_cv_prompt(job_description)

        response = self.client.beta.messages.parse(
            model=self.write_model,
            max_tokens=self.write_cv_tokens,
            temperature=self.write_cv_temperature,
            betas=["structured-outputs-2025-11-13"],
            response_format=AtsOptimizedCv,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.parsed
