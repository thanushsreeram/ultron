from __future__ import annotations

import re
from pathlib import Path


def _safe_path(name: str, brain) -> Path:
    name = name.strip('"')
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    path = (brain.settings.workspace / name).resolve()
    path.relative_to(brain.settings.workspace.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _build_pdf(path: Path, title: str, content: str) -> None:
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Flowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )
    from xml.sax.saxutils import escape

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "UltronTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=22,
        leading=27,
        spaceAfter=24,
    )
    body_style = ParagraphStyle(
        "UltronBody",
        parent=styles["BodyText"],
        fontSize=11,
        leading=16,
        spaceAfter=9,
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.75 * inch, 0.45 * inch, "Created by ULTRON")
        canvas.drawRightString(
            A4[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}"
        )
        canvas.restoreState()

    story: list[Flowable] = [Paragraph(escape(title), title_style)]
    for block in re.split(r"\n\s*\n", content.strip()):
        if block.strip() == "---PAGE---":
            story.append(PageBreak())
            continue
        lines = [escape(line) for line in block.splitlines()]
        story.append(Paragraph("<br/>".join(lines), body_style))
        story.append(Spacer(1, 4))
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.7 * inch,
        title=title,
        author="ULTRON AI Assistant",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def _pdf(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /pdf "file.pdf" "content", Boss.'
    path = _safe_path(args[0], brain)
    content = " ".join(args[1:]).strip('"')
    title = path.stem.replace("-", " ").replace("_", " ").title()
    if path.exists() and not brain.confirm(f"Overwrite {path.name}?"):
        return "PDF creation cancelled, Boss."
    _build_pdf(path, title, content)
    return f"PDF created at {path}, Boss."


def _pdf_topic(args, brain) -> str:
    if len(args) < 2:
        return 'Usage: /pdf-topic "file.pdf" "topic or instructions", Boss.'
    path = _safe_path(args[0], brain)
    request = " ".join(args[1:]).strip('"')
    content = brain.chat(
        f"Create a well-structured document about: {request}",
        extra_system=(
            "Write a polished document with a clear title, short introduction, useful "
            "headings, examples, and conclusion. Use plain text headings and paragraphs."
        ),
    )
    if path.exists() and not brain.confirm(f"Overwrite {path.name}?"):
        return "PDF creation cancelled, Boss."
    _build_pdf(path, path.stem.replace("-", " ").title(), content)
    return f"I researched and created the PDF at {path}, Boss."


def _read_pdf(args, brain) -> str:
    if not args:
        return 'Usage: /readpdf "file.pdf", Boss.'
    from pypdf import PdfReader

    path = (brain.settings.workspace / args[0].strip('"')).resolve()
    path.relative_to(brain.settings.workspace.resolve())
    if not path.is_file():
        return f"I cannot find {path}, Boss."
    reader = PdfReader(str(path))
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    return text[:12000] or "I found no extractable text in that PDF, Boss."


def register(registry) -> None:
    registry.register("pdf", _pdf, "<file.pdf> <content> create a PDF")
    registry.register("pdf-topic", _pdf_topic, "<file.pdf> <topic> write and create a PDF")
    registry.register("readpdf", _read_pdf, "<file.pdf> extract PDF text")
