import os
import re
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class JobMatchAnalysis(BaseModel):
    match_percentage: int = Field(
        description="Porcentaje de coincidencia del 0 al 100 basado estrictamente en el CV y los requisitos."
    )
    matching_techs: list[str] = Field(
        description="Tecnologías o habilidades del puesto que SÍ están presentes en el CV."
    )
    missing_techs: list[str] = Field(
        description="Tecnologías o habilidades requeridas que el CV NO menciona."
    )
    reasoning: str = Field(
        description="Breve justificación de por qué se le asigna este porcentaje de match."
    )
    should_apply: bool = Field(
        description="True si el match_percentage es mayor o igual a 80, False en caso contrario."
    )


class AtsOptimizedCv(BaseModel):
    markdown_content: str = Field(
        description=(
            "CV completo adaptado orgánicamente a la oferta y optimizado para sistemas ATS "
            "en formato Markdown estricto. Longitud estricta: Diseñado para un máximo de 2 páginas "
            "(aproximadamente 600-700 palabras máximo), sin tablas complejas, con secciones claras "
            "(Resumen, Experiencia con viñetas de impacto, Habilidades, Educación)."
        )
    )
    summary_of_changes: str = Field(
        description="Breve explicación de los cambios clave realizados para destacar en esta oferta específica."
    )


class BaseLLMProvider(ABC):
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


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY es obligatoria cuando LLM_ENGINE=gemini")

        self.client = genai.Client(api_key=api_key)
        self.types = types
        # Usamos Flash para todo por velocidad y capacidad de estructura JSON
        self.fast_model = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")
        self.pro_model = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = f"""
        Eres un asistente experto en recursos humanos y automatización de empleo.
        Analiza la siguiente DESCRIPCIÓN DE PUESTO en comparación con el CV del candidato.
        Calcula un porcentaje de coincidencia real (match_percentage) del 0 al 100.
        Si el porcentaje es igual o mayor a 80, marca 'should_apply' como true. Si es menor, false.

        --- MI CV ---
        {cv_text}

        --- DESCRIPCIÓN DEL PUESTO ---
        {job_description}
        """
        response = self.client.models.generate_content(
            model=self.fast_model,  # Modelo rápido y ligero para análisis y JSON
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JobMatchAnalysis,
                temperature=0.1,
            ),
        )
        return JobMatchAnalysis.model_validate_json(response.text)

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        cv_text = self.load_local_cv()
        prompt = f"""
        Actúa como un reclutador técnico senior y un redactor profesional de CVs. 
        Your task is to tailor my base CV specifically for the job description below in professional English.

        CRITICAL RULES:
        1. ZERO HALLUCINATIONS: Do not invent or assume any experience, tools, or dates not present in my base CV.
        2. ATS-FRIENDLY: Clean Markdown only. No tables, no HTML.
        3. STRICT LENGTH: Max 2 pages (500-700 words max).

        --- MY BASE CV ---
        {cv_text}

        --- JOB DESCRIPTION ---
        {job_description}
        """
        response = self.client.models.generate_content(
            model=self.pro_model,  # Modelo Pro de mayor capacidad para prosa natural y detallada
            contents=prompt,
            config=self.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AtsOptimizedCv,
                temperature=0.15,
            ),
        )
        return AtsOptimizedCv.model_validate_json(response.text)


class OllamaProvider(BaseLLMProvider):
    def __init__(self):
        import ollama

        self.host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.fast_model = os.getenv("OLLAMA_FAST_MODEL", "qwen2.5:3b")
        self.pro_model = os.getenv("OLLAMA_PRO_MODEL", "qwen2.5:7b-instruct")
        self.client = ollama.Client(host=self.host)

    def evaluate_job(self, job_description: str) -> JobMatchAnalysis:
        cv_text = self.load_local_cv()
        prompt = f"""
        Eres un asistente experto en recursos humanos y automatización de empleo.
        Analiza la siguiente DESCRIPCIÓN DE PUESTO en comparación con el CV del candidato.
        Calcula un porcentaje de coincidencia real (match_percentage) del 0 al 100.
        Si el porcentaje es igual o mayor a 80, marca 'should_apply' como true. Si es menor, false.

        --- MI CV ---
        {cv_text}

        --- DESCRIPCIÓN DEL PUESTO ---
        {job_description}
        """
        response = self.client.chat(
            model=self.fast_model,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un evaluador técnico preciso que siempre responde estrictamente en el formato JSON solicitado.",
                },
                {"role": "user", "content": prompt},
            ],
            format=JobMatchAnalysis.model_json_schema(),
            options={"temperature": 0.1},
        )
        return JobMatchAnalysis.model_validate_json(response.message.content)

    def generate_cv(self, job_description: str) -> AtsOptimizedCv:
        cv_text = self.load_local_cv()
        prompt = f"""
        Actúa como un reclutador técnico senior y un redactor profesional de CVs. 
        Your task is to tailor my base CV specifically for the job description below in professional English.
        CRITICAL RULES: Zero hallucinations, clean markdown, max 2 pages.

        --- MY BASE CV ---
        {cv_text}

        --- DESCRIPCIÓN DEL PUESTO ---
        {job_description}
        """
        response = self.client.chat(
            model=self.pro_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert ATS CV writer. You respond strictly in valid JSON matching the requested schema.",
                },
                {"role": "user", "content": prompt},
            ],
            format=AtsOptimizedCv.model_json_schema(),
            options={"temperature": 0.15},
        )
        return AtsOptimizedCv.model_validate_json(response.message.content)


def get_llm_provider() -> BaseLLMProvider:
    engine = os.getenv("LLM_ENGINE", "").strip().lower()

    if not engine:
        raise ValueError(
            "La variable de entorno LLM_ENGINE no está definida en el archivo .env"
        )

    if engine == "gemini":
        return GeminiProvider()
    elif engine == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(
            f"Motor de LLM no válido: '{engine}'. Las opciones permitidas en LLM_ENGINE son 'gemini' u 'ollama'."
        )
