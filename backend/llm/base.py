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
        You are a strict, critical technical recruiter and ATS evaluation engine. 
        Evaluate the CANDIDATE CV against the JOB DESCRIPTION based on exact technical requirements, years of experience, and location constraints.

        SCORING RULES:
        1. BASE & TRANSFERABLE SKILLS: Start from 0%. Add points for direct matches or valid transferable ecosystem skills (e.g., Laravel/Yii/Django/FastAPI equivalences, Vue/React component paradigms). Do not penalize minor framework variations if core architectural competency is proven.
        2. LOCATION & REMOTE CONSTRAINT: If the job description explicitly requires on-site presence, hybrid attendance, or relocation to a non-remote location where the candidate cannot work, the total match_percentage MUST BE CAPPED AT MAXIMUM 64%.
        3. MANDATORY PENALTIES: Substantially penalize missing critical mandatory requirements or unmatched seniorities. 
        4. SCORING DISTRIBUTION (Strict Calibration):
        - 80 to 100: Exceptional match. Direct core stack, appropriate seniority, fully remote or matches location.
        - 65 to 79: Moderate/Good match. Minor skill gaps or close alignment that requires human verification.
        - 0 to 64: Poor fit, major skill gaps, or on-site/relocation constraint violation.
        5. 'matching_techs': List ONLY core overlapping technologies found in both texts (max 6).
        6. 'missing_techs': List missing critical requirements or deal-breakers (max 5).
        7. 'reasoning': Write a single direct sentence in Spanish explaining the score and key factors. STRICTLY under 80 words.
        8. DO NOT INCLUDE ANY PERSONAL INFORMATION IN THE REASONING.

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
        if not markdown_content:
            return ""

        # 1. Eliminar imágenes en markdown: ![alt](url)
        text = re.sub(r"!\[.*?\]\(.*?\)", "", markdown_content)

        # 2. Convertir enlaces en markdown [texto](url) a solo texto
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)

        # 3. Eliminar bloques de código completos
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        # 4. Eliminar encabezados (ej: # H1, ## H2, ### H3) dejando solo el texto
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # 5. Eliminar líneas divisorias o horizontales (--- o ***)
        text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        # 6. Remover negritas y cursivas (**, *, __, _) conservando el texto interior
        text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
        text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)

        # 7. Normalizar listas (quitar guiones o asteriscos al inicio de línea de las viñetas si lo deseas, o dejarlos)
        # text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)

        # 8. Limpiar saltos de línea múltiples excesivos y dejar un formato limpio
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        return text.strip()

    def load_local_cv(self, file_path: str = "/app/data/cv.md") -> str:
        path = file_path if os.path.exists(file_path) else "data/cv.md"
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No se encontró el archivo de CV en la ruta: {path}."
            )
        with open(path, "r", encoding="utf-8") as f:
            return self.clean_markdown_to_plain_text(f.read())
