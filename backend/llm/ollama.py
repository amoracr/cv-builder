import os

from .base import BaseLLMProvider
from .schemas import AtsCoverLetter, AtsOptimizedCv, JobMatchAnalysis


class OllamaProvider(BaseLLMProvider):
    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__(cv_file_path=cv_file_path)
        import ollama

        self.host = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        if not self.host:
            raise ValueError("OLLAMA_BASE_URL es obligatoria cuando se usa Ollama")

        self.evaluate_model = os.getenv(
            "EVALUATE_MODEL", os.getenv("OLLAMA_LIGHT_MODEL", "qwen2.5:3b")
        )

        self.write_cv_model = os.getenv(
            "WRITE_CV_MODEL", os.getenv("OLLAMA_PRO_MODEL", "qwen2.5:7b")
        )
        self.write_cl_model = os.getenv(
            "WRITE_CL_MODEL", os.getenv("OLLAMA_PRO_MODEL", "qwen2.5:7b")
        )

        self.client = ollama.Client(host=self.host)

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        prompt = self.get_evaluation_prompt(job_description)

        response = self.client.chat(
            model=self.evaluate_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a critical, unbiased technical recruiter."
                        " Output strictly valid JSON matching the schema."
                    ),
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
            "You are a strict data-transformation compiler. You never invent"
            " data, use placeholders, or write career plans. You output valid"
            " JSON matching the schema containing the factual candidate data"
            " with optimized bullet points."
        )

        response = self.client.chat(
            model=self.write_cv_model,
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

    def generate_cover_letter(self, job_description: str) -> AtsCoverLetter:
        prompt = self.get_write_cl_prompt(job_description)

        system_instruction = (
            "You are an expert technical career consultant and corporate"
            " copywriter. You write highly persuasive, concise, and tailored"
            " cover letters strictly based on candidate facts. You output ONLY"
            " strictly valid JSON matching the requested schema."
        )

        response = self.client.chat(
            model=self.write_cl_model,
            messages=[
                {
                    "role": "system",
                    "content": system_instruction,
                },
                {"role": "user", "content": prompt},
            ],
            format=AtsCoverLetter.model_json_schema(),
            options={
                "temperature": self.write_cl_temperature,
                "num_predict": self.write_cl_tokens,
                "top_p": 0.1,
                "repeat_penalty": 1.15,
            },
        )

        content = response.message.content.strip()

        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return AtsCoverLetter.model_validate_json(content)
