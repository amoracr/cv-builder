import os
import re
from abc import ABC, abstractmethod

from .schemas import AtsOptimizedCv, JobMatchAnalysis


class BaseLLMProvider(ABC):
    def __init__(self):
        super().__init__()
        self.evaluate_job_temperature = float(
            os.getenv("EVALUATE_JOB_TEMPERATURE", "1.0")
        )
        self.evaluate_job_tokens = int(os.getenv("EVALUATE_JOB_TOKENS", "256"))
        self.evaluate_job_prompt = """[INSTRUCTIONS]
        You are a strict, critical technical recruiter. Do NOT be overly generous. 
        Evaluate the CANDIDATE CV against the JOB DESCRIPTION using a strict matching criteria:
        1. Start from 0%. Add points ONLY for direct, exact matches in core stack, experience years, and required domain.
        2. SUBSTANTIALLY PENALIZE missing mandatory requirements, seniorities, or core frameworks.
        3. PENALIZE if location is not remote or candidate should relocate to job location.
        4. Compute a realistic match_percentage (0-100). Be diverse: if it's a poor fit, it should score 30% to 50%. Do not default to 85%.
        5. Set 'should_apply' to true ONLY if match_percentage >= 80, otherwise false.
        6. 'matching_techs': List ONLY core overlapping tech (max 6).
        7. 'missing_techs': List missing critical requirements (max 5).
        8. 'reasoning': Write a single direct sentence in Spanish explaining the score. STRICTLY under 80 words. 
        9. DO NOT INCLUDE ANY PERSONAL INFORMATION.

        ### CANDIDATE CV
        {cv_text}

        ### JOB DESCRIPTION
        {job_description}
        """

        self.write_cv_temperature = float(os.getenv("WRITE_CV_TEMPERATURE", "1.0"))
        self.write_cv_tokens = int(os.getenv("WRITE_CV_TOKENS", "256"))
        self.write_cv_prompt = """[INSTRUCTIONS]
        Tailor the BASE CV for the target JOB DESCRIPTION in professional English.
        - Zero hallucinations: only use real experience from the Base CV.
        - Clean Markdown output. Max 2 pages equivalent.

        ### BASE CV
        {cv_text}

        ### JOB DESCRIPTION
        {job_description}
        """

    @abstractmethod
    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        pass

    @abstractmethod
    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        pass

    def clean_markdown_to_plain_text(self, markdown_content: str) -> str:
        text = re.sub(r"!\[.*?\]\(.*?\)", "", markdown_content)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text.strip()

    def load_local_cv(self, file_path: str = "/app/data/cv.md") -> str:
        path = file_path if os.path.exists(file_path) else "data/cv.md"
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No se encontró el archivo de CV en la ruta: {path}."
            )
        with open(path, "r", encoding="utf-8") as f:
            return self.clean_markdown_to_plain_text(f.read())