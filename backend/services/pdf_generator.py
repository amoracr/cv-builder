from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def generate_pdf_from_markdown(markdown_content: str, output_path: str) -> str:
    """
    Convierte un string en Markdown a HTML y genera un PDF profesional usando WeasyPrint.
    """
    html_body = markdown.markdown(
        markdown_content, 
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    
    template = env.get_template("cv_markdown.html")
    final_html = template.render(markdown_html=html_body)
    
    HTML(string=final_html).write_pdf(output_path)
    return output_path

def generate_cover_letter_pdf(content: str, output_path: str) -> str:
    html_body = markdown.markdown(content, extensions=['nl2br'])

    # Usar plantilla específica para cartas
    template = env.get_template('cover_letter.html')
    final_html = template.render(markdown_html=html_body)

    HTML(string=final_html).write_pdf(output_path)
    return output_path