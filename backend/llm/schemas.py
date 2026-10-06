from typing import Literal

from pydantic import BaseModel, Field


class JobMatchAnalysis(BaseModel):
    match_percentage: int = Field(
        description="Porcentaje de coincidencia del 0 al 100 basado estrictamente en el CV y los requisitos.",
        ge=0,
        le=100
    )
    matching_techs: list[str] = Field(
        description="Tecnologías o habilidades del puesto que SÍ están presentes en el CV.",
        max_length=6,
    )
    missing_techs: list[str] = Field(
        description="Tecnologías o habilidades requeridas que el CV NO menciona.",
        max_length=5,
    )
    reasoning: str = Field(
        description="Breve justificación de por qué se le asigna este porcentaje de match.",
        max_length=1024,
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
