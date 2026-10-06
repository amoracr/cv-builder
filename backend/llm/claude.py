import os

from .base import BaseLLMProvider
from .schemas import AtsOptimizedCv, JobMatchAnalysis


class ClaudeProvider(BaseLLMProvider):
    def __init__(self):
        super().__init__()
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY es obligatoria cuando LLM_ENGINE=claude")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = self.evaluate_job_prompt.format(
            cv_text=cv_text, job_description=job_description
        )
        
        # Usando la interfaz estructurada de Anthropic con Pydantic
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=self.evaluate_job_tokens,
            temperature=self.evaluate_job_temperature,
            betas=["structured-outputs-2025-11-13"],
            response_format=JobMatchAnalysis,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.parsed

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        cv_text = self.load_local_cv()
        prompt = self.write_cv_prompt.format(
            cv_text=cv_text, job_description=job_description
        )
        
        response = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=self.write_cv_tokens,
            temperature=self.write_cv_temperature,
            betas=["structured-outputs-2025-11-13"],
            response_format=AtsOptimizedCv,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.parsed