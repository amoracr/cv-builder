from pydantic import BaseModel, Field


class JobMatchAnalysis(BaseModel):
    match_percentage: int = Field(
        description="Porcentaje de coincidencia del 0 al 100 basado estrictamente en el CV y los requisitos."
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
        max_length=16384,
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
