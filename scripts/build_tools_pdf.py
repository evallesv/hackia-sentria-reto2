"""Genera el entregable de herramientas a partir de un registro honesto y editable."""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parent.parent


def main():
    source = ROOT / "docs/delivery/tools-used.json"
    data = json.loads(source.read_text())
    output = ROOT / "docs/delivery/herramientas-ia-preparacion.pdf"
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SentriaTitle",
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor("#14382e"),
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SentriaBody", fontName="Helvetica", fontSize=10, leading=15, spaceAfter=8
        )
    )
    story = []

    def p(text, style="SentriaBody"):
        story.append(Paragraph(escape(text), styles[style]))

    p("EQUIPO SENTRIA / RETO 02", "Heading2")
    p("Herramientas de IA", "SentriaTitle")
    p(data["stage"])
    p("Fecha de corte: " + data["date"] + ". Documento de registro técnico de la entrega.")
    p("Integrantes del Equipo Sentria", "Heading2")
    for member in data["team"]:
        p(member["name"] + " | " + member["linkedin"])
    story.append(Spacer(1, 5 * mm))
    tool = data["tools"][0]
    p(tool["name"] + " - " + tool["status"], "Heading2")
    for key, label in [
        ("model", "Modelo"),
        ("purpose", "Propósito"),
        ("application", "Aplicación"),
        ("results", "Resultados"),
        ("evidence", "Evidencia"),
        ("limits", "Límites"),
    ]:
        p(label + ": " + tool[key])
    p("Fuentes analizadas", "Heading2")
    p(
        "Especificaciones del reto 2; bases oficiales de hackIAthon Panamá; "
        "aviso de tratamiento de datos del organizador. "
        "Ubicaciones y hashes registrados en docs/sources/manifest.json."
    )
    p(
        "Fecha de referencia de las bases: 23/09/2026. Este documento registra la base técnica "
        "desarrollada al 27/09/2026."
    )
    story.append(PageBreak())
    p("Integraciones y adaptadores", "SentriaTitle")
    p(
        "Las siguientes herramientas disponen de adaptadores y configuración integrados "
        "en el código, con activación progresiva según los requerimientos de cada tarea."
    )
    for tool in data["tools"][1:]:
        p(tool["name"] + " - " + tool["status"], "Heading2")
        for key, label in [
            ("model", "Modelo"),
            ("purpose", "Propósito"),
            ("application", "Aplicación"),
            ("results", "Resultados"),
            ("evidence", "Evidencia"),
            ("limits", "Límites"),
        ]:
            p(label + ": " + tool[key])
    p("Control de calidad y seguridad", "Heading2")
    p(
        "Cálculos con precisión Decimal; evidencia trazable y referenciada; revisión y "
        "decisión bajo criterio humano; datos de prueba sintéticos; credenciales fuera de Git. "
        "La aplicación está empaquetada en contenedor Linux ARM64 y desplegada en producción "
        "en Fly.io con HTTPS y CI/CD automatizado."
    )
    p(
        "Entrega completada: commits en GitHub, modelo gemini-2.5-flash-lite validado en vivo, "
        "y enlace público operativo: https://sentria.fly.dev"
    )

    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#b9c9c1"))
        canvas.line(20 * mm, 17 * mm, 190 * mm, 17 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(20 * mm, 12 * mm, "Equipo Sentria | Herramientas IA | 27/09/2026")
        canvas.drawRightString(190 * mm, 12 * mm, str(doc.page))

    SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=24 * mm,
        title="Equipo Sentria - Herramientas de IA",
        author="Equipo Sentria",
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
