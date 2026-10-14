import os
import re
import textwrap
from abc import ABC, abstractmethod

from .schemas import AtsOptimizedCv, JobMatchAnalysis, AtsCoverLetter


class BaseLLMProvider(ABC):
    def __init__(self, cv_file_path: str = "/app/data/cv.md"):
        super().__init__()
        self.cv_file_path = cv_file_path

        self.evaluate_job_temperature = float(
            os.getenv("EVALUATE_JOB_TEMPERATURE", "0.1")
        )
        self.evaluate_job_tokens = int(os.getenv("EVALUATE_JOB_TOKENS", "3000"))

        self.evaluate_job_prompt_template = textwrap.dedent("""[INSTRUCTIONS]
            You are a strict, critical technical recruiter and ATS evaluation engine. 
            Evaluate the CANDIDATE CV against the JOB DESCRIPTION based on exact technical requirements, years of experience, and location constraints.

            SCORING RULES:
            1. BASE & TRANSFERABLE SKILLS: Start from 0%. Add points for direct matches or valid transferable ecosystem skills.
            2. LOCATION & REMOTE CONSTRAINT: If the job description explicitly requires on-site presence where the candidate cannot work, match_percentage MUST BE CAPPED AT MAXIMUM 56%.
            3. MANDATORY PENALTIES: Substantially penalize missing critical mandatory requirements.
            4. SCORING DISTRIBUTION: 80-100 (Exceptional), 65-79 (Moderate), 0-64 (Poor).
            5. 'matching_techs': List ONLY core overlapping technologies (max 6).
            6. 'missing_techs': List missing critical requirements (max 5).
            7. 'reasoning': Write a single direct sentence in explaining the score. STRICTLY under 80 words.
            8. DO NOT INCLUDE ANY PERSONAL INFORMATION IN THE REASONING.
            9. DO A FRESH START FOR EVERY EVALUATION.

            ### CANDIDATE CV
            {cv_text}

            ### JOB DESCRIPTION
            {job_description}
            """)

        self.write_cv_temperature = float(os.getenv("WRITE_CV_TEMPERATURE", "0.05"))
        self.write_cv_tokens = int(os.getenv("WRITE_CV_TOKENS", "8000"))

        self.write_cv_prompt_template = textwrap.dedent("""\
            <task>
            Rewrite and tailor the candidate's complete BASE CV to optimize it for the TARGET JOB DESCRIPTION.
            </task>

            <constraints>
            - DO NOT invent or alter names, companies, dates, or degrees.
            - DO NOT generate essays, intros, or career plans.
            - Output ONLY the final customized CV in clean Markdown.
            </constraints>

            <base_cv>
            {cv_text}
            </base_cv>

            <job_description>
            {job_description}
            </job_description>
            """)

        self.write_cl_temperature = float(os.getenv("WRITE_CL_TEMPERATURE", "0.05"))
        self.write_cl_tokens = int(os.getenv("WRITE_CL_TOKENS", "8000"))

        self.write_cl_prompt_template = textwrap.dedent("""\
            <task>
            Write a highly tailored, persuasive, and ATS-optimized COVER LETTER for the candidate matching the TARGET JOB DESCRIPTION based EXCLUSIVELY on their BASE CV.
            </task>

            <constraints>
            - TRUTH & ACCURACY: DO NOT invent, exaggerate, or assume experience, skills, degrees, or metrics not present in the CANDIDATE CV.
            - LANGUAGE MATCH: Detect and write in the EXACT same language as the JOB DESCRIPTION (English or Spanish).
            - LENGTH & STRUCTURE: Keep the total document strictly to 3 concise, high-impact paragraphs (under 200 words total).
            - NO HOLLOW FORMALITIES: Avoid generic openings (e.g., "I am writing to apply for...", "Dear Sir/Madam"). Start directly with a compelling technical value proposition hook.
            - REQUIREMENT & GOAL MATCHING: Select 2 to 4 key technical requirements AND 2 to 4 stated company goals/objectives from the job description that directly match the candidate's actual CV experience.
            - FORMAT: Output MUST be valid JSON adhering strictly to the requested schema. The `cover_letter` field must contain the complete, beautifully formatted Markdown document ready for rendering.
            </constraints>

            <instructions>
            1. Analyze <job_description> to extract 2 to 4 core technical requirements AND 2 to 4 key organizational/technical goals.
            2. Cross-reference with <candidate_cv> to map those exact requirements and goals to real candidate engineering achievements, projects, and stack.
            3. Construct Paragraph 1 (Hook & Alignment): State the specific position, express direct alignment with 1-2 core goals of the job description, and present a strong technical value proposition.
            4. Construct Paragraph 2 (Requirement & Goal Bridge): Explicitly bridge 2 to 4 technical requirements and company objectives directly to concrete achievements, technologies, and projects from the candidate's CV.
            5. Construct Paragraph 3 (Call to Action & Impact): Reiterate how the candidate will help achieve the remaining goals, state confidence in delivering immediate value, and invite a brief technical discussion.
            6. Assemble the final text into the `cover_letter` field as a single, clean Markdown document with appropriate salutation, line breaks, and professional sign-off.
            </instructions>

            <candidate_cv>
            {cv_text}
            </candidate_cv>

            <job_description>
            {job_description}
            </job_description>
            """)

    def load_local_cv(self) -> str:
        path = self.cv_file_path if os.path.exists(self.cv_file_path) else "data/cv.md"
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No se encontró el archivo de CV en la ruta: {path}."
            )
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def clean_markdown_to_plain_text(self, markdown_content: str) -> str:
        if not markdown_content:
            return ""
        text = re.sub(r"!\[.*?\]\(.*?\)", "", markdown_content)
        text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
        text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def get_evaluation_prompt(self, job_description: str) -> str:
        cv_text = self.load_local_cv()
        return self.evaluate_job_prompt_template.format(
            cv_text=cv_text, job_description=job_description
        )

    def get_write_cv_prompt(self, job_description: str) -> str:
        cv_text = self.load_local_cv()
        return self.write_cv_prompt_template.format(
            cv_text=cv_text, job_description=job_description
        )

    def get_write_cl_prompt(self, job_description: str) -> str:
        cv_text = self.load_local_cv()
        return self.write_cl_prompt_template.format(
            cv_text=cv_text, job_description=job_description
        )

    @abstractmethod
    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        pass

    @abstractmethod
    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        pass

    @abstractmethod
    def generate_cover_letter(self, job_description: str) -> AtsCoverLetter:
        pass
