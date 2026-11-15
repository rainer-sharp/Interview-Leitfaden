"""Exporte eines Interviews: Markdown zum Lesen, CSV zum Auswerten, PDF zum Ablegen."""
import csv
import html
import io
import re
import unicodedata
from itertools import groupby

from app.models import Answer, Interview

STATUS_LABEL = {
    "offen": "offen",
    "beantwortet": "beantwortet",
    "uebersprungen": "übersprungen",
    "spaeter": "später nochmal",
}
CSV_COLUMNS = [
    "interview_id", "person", "organisation", "datum", "projekt", "gruppe", "katalog", "version",
    "position", "abschnitt", "frage", "pflicht", "status", "notiz",
]


def _date(interview: Interview) -> str:
    return interview.datum.strftime("%d.%m.%Y")


def meta(interview: Interview) -> list[tuple[str, str]]:
    catalog = interview.questionnaire
    rows = [("Person", interview.person)]
    if interview.organisation:
        rows.append(("Organisation", interview.organisation))
    rows += [
        ("Datum", _date(interview)),
        ("Projekt", catalog.group.project.name),
        ("Gruppe", catalog.group.name),
        ("Fragenkatalog", f"{catalog.name} (Version {catalog.version})"),
        ("Status", interview.status),
    ]
    return rows


def _sections(interview: Interview) -> list[tuple[str, list[Answer]]]:
    return [(name, list(items)) for name, items in groupby(interview.answers, key=lambda a: a.question_snapshot["abschnitt"])]


def transcripts(interview: Interview) -> list[tuple[str, str]]:
    """(Dateiname, Text) je Aufnahme mit Transkript. Die eigene Überschrift und Kopfzeilen des Skripts entfallen,
    im Export stehen sie unter „Transkript“."""
    result = []
    for recording in interview.recordings:
        text = recording.transkript.strip()
        if not text:
            continue
        lines = text.splitlines()
        if "---" in lines[:15] and lines[0].startswith("# "):
            lines = lines[lines.index("---") + 1:]
        result.append((recording.dateiname, "\n".join(lines).strip()))
    return result


def evaluation_text(interview: Interview) -> str:
    """Letzte fertige Bewertung; sie bleibt stehen, solange eine neue läuft oder fehlschlägt."""
    evaluation = interview.evaluation
    return evaluation.text.strip() if evaluation is not None else ""


def evaluation_note(interview: Interview) -> str:
    """Herkunftsvermerk, z. B. „Erstellt am 10.11.2026 14:03 mit modell-a, mit Transkript, von Hand überarbeitet“."""
    evaluation = interview.evaluation
    parts = []
    if evaluation.fertig_am:
        parts.append(f"Erstellt am {evaluation.fertig_am.strftime('%d.%m.%Y %H:%M')} UTC")
    if evaluation.modell:
        parts.append(f"mit {evaluation.modell}")
    parts.append("mit Transkript" if evaluation.mit_transkript else "nur aus den Notizen")
    if evaluation.bearbeitet:
        parts.append("von Hand überarbeitet")
    return "KI-generiert – bitte prüfen. " + ", ".join(parts) + "."


def demote(markdown: str, levels: int) -> str:
    """Überschriften der LLM-Antwort unter die Export-Überschrift einordnen (## → ###)."""
    return re.sub(r"^(#{1,6}) ", lambda m: "#" * min(6, len(m.group(1)) + levels) + " ", markdown, flags=re.M)


def slug(text: str, fallback: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_text).strip("-").lower()[:40] or fallback


def filename(interview: Interview, extension: str) -> str:
    return f"interview-{interview.id}-{interview.datum.isoformat()}-{slug(interview.person, 'person')}.{extension}"


def to_markdown(interview: Interview) -> str:
    lines = [f"# Interview: {interview.person}", ""]
    lines += [f"- **{label}:** {value}" for label, value in meta(interview)]
    for section, answers in _sections(interview):
        lines += ["", f"## {section}"]
        for answer in answers:
            question = answer.question_snapshot
            title = f"### {answer.position}. {question['text']}"
            if question["pflicht"]:
                title += " *(Pflicht)*"
            lines += ["", title, ""]
            if answer.status != "beantwortet":
                lines += [f"_Status: {STATUS_LABEL[answer.status]}_", ""]
            lines.append(answer.notiz.strip() or "_(keine Notiz)_")
    lines += ["", "## Gesamtnotiz", "", interview.gesamtnotiz.strip() or "_(keine Gesamtnotiz)_", ""]
    if evaluation := evaluation_text(interview):
        lines += ["## KI-Bewertung", "", f"_{evaluation_note(interview)}_", "", demote(evaluation, 1), ""]
    for name, text in transcripts(interview):
        lines += [f"## Transkript: {name}", "", text, ""]
    return "\n".join(lines)


def _csv_safe(value: str) -> str:
    """Verhindert, dass Excel Notizen wie „=SUMME(…)“ als Formel ausführt."""
    if value[:1] in ("=", "+", "@", "\t", "\r") or (value[:1] == "-" and value[1:2] not in (" ", "")):
        return "'" + value
    return value


def csv_rows(interview: Interview) -> list[list[str]]:
    catalog = interview.questionnaire
    base = [
        str(interview.id), interview.person, interview.organisation, interview.datum.isoformat(),
        catalog.group.project.name, catalog.group.name, catalog.name, str(catalog.version),
    ]
    rows = []
    for answer in interview.answers:
        question = answer.question_snapshot
        rows.append(base + [
            str(answer.position), question["abschnitt"], question["text"],
            "ja" if question["pflicht"] else "nein", answer.status, answer.notiz,
        ])
    rows.append(base + ["", "", "Gesamtnotiz", "", interview.status, interview.gesamtnotiz])
    if evaluation := evaluation_text(interview):
        rows.append(base + ["", "KI-Bewertung", interview.evaluation.modell, "", "ki-bewertung", evaluation])
    for name, text in transcripts(interview):
        rows.append(base + ["", "Transkript", name, "", "transkript", text])
    return [[_csv_safe(cell) for cell in row] for row in rows]


def write_csv(rows: list[list[str]]) -> str:
    """Semikolon und BOM: so öffnet ein deutsches Excel die Datei ohne Import-Assistent richtig."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    writer.writerows(rows)
    return "﻿" + buffer.getvalue()


def to_csv(interview: Interview) -> str:
    return write_csv(csv_rows(interview))


_STYLE = [
    "@page { size: A4; margin: 2cm 2cm 2.2cm; "
    "@bottom-right { content: 'Seite ' counter(page) ' von ' counter(pages); font-size: 8pt; color: #777; } }",
    "body { font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; line-height: 1.45; color: #1c1f1e; }",
    "h1 { font-size: 17pt; margin: 0 0 8pt; } h2 { font-size: 12.5pt; color: #175a54; margin: 18pt 0 4pt;"
    " border-bottom: 0.5pt solid #ccc; padding-bottom: 2pt; }",
    "h3 { font-size: 10.5pt; margin: 10pt 0 3pt; page-break-after: avoid; }",
    "h4 { font-size: 10pt; margin: 8pt 0 2pt; page-break-after: avoid; }",
    "table.meta td { padding: 1pt 10pt 1pt 0; vertical-align: top; } table.meta td:first-child { color: #666; }",
    ".note { white-space: pre-wrap; margin: 0; } .empty, .status { color: #777; font-style: italic; margin: 0 0 2pt; }",
    ".tag { font-size: 8pt; color: #175a54; font-weight: normal; }",
    "h2.transcript { page-break-before: always; } .turn { margin: 0 0 5pt; white-space: pre-wrap; }",
    ".ki p, .ki li { margin: 0 0 4pt; } .ki ul, .ki ol { margin: 0 0 6pt; padding-left: 14pt; }",
    ".ki-note { color: #777; font-size: 8.5pt; font-style: italic; }",
]


def _head() -> str:
    return "<!doctype html><html lang='de'><head><meta charset='utf-8'><style>" + "".join(_STYLE) + "</style></head><body>"


def to_html(interview: Interview) -> str:
    e = html.escape
    parts = [
        _head(),
        f"<h1>Interview: {e(interview.person)}</h1><table class='meta'>",
    ]
    parts += [f"<tr><td>{e(label)}</td><td>{e(value)}</td></tr>" for label, value in meta(interview)]
    parts.append("</table>")
    for section, answers in _sections(interview):
        parts.append(f"<h2>{e(section)}</h2>")
        for answer in answers:
            question = answer.question_snapshot
            tag = " <span class='tag'>Pflicht</span>" if question["pflicht"] else ""
            parts.append(f"<h3>{answer.position}. {e(question['text'])}{tag}</h3>")
            if answer.status != "beantwortet":
                parts.append(f"<p class='status'>Status: {e(STATUS_LABEL[answer.status])}</p>")
            note = answer.notiz.strip()
            parts.append(f"<p class='note'>{e(note)}</p>" if note else "<p class='empty'>(keine Notiz)</p>")
    gesamt = interview.gesamtnotiz.strip()
    parts.append("<h2>Gesamtnotiz</h2>")
    parts.append(f"<p class='note'>{e(gesamt)}</p>" if gesamt else "<p class='empty'>(keine Gesamtnotiz)</p>")
    if evaluation := evaluation_text(interview):
        parts.append("<h2>KI-Bewertung</h2>")
        parts.append(f"<p class='ki-note'>{e(evaluation_note(interview))}</p>")
        parts.append(f"<div class='ki'>{markdown_html(demote(evaluation, 2))}</div>")
    for name, text in transcripts(interview):
        parts.append(f"<h2 class='transcript'>Transkript: {e(name)}</h2>")
        for paragraph in (p.strip() for p in text.split("\n\n")):
            if paragraph:
                parts.append(f"<p class='turn'>{_turn_html(paragraph)}</p>")
    parts.append("</body></html>")
    return "".join(parts)


def _turn_html(paragraph: str) -> str:
    """Absatz aus dem Skript: „**[00:01:02] Name:** Text“ – nur dieses Fett wird übernommen, sonst alles escaped."""
    match = re.match(r"\*\*(.+?)\*\*\s*(.*)", paragraph, re.S)
    if match:
        return f"<b>{html.escape(match.group(1))}</b> {html.escape(match.group(2))}"
    return html.escape(paragraph)


def _inline(text: str) -> str:
    """Escaped Text mit **fett**, *kursiv*/_kursiv_ und `code`."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<i>\1</i>", text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def markdown_html(markdown: str) -> str:
    """Kleiner Markdown-Umsetzer für die LLM-Antwort: Überschriften, Listen, Absätze, Hervorhebungen.
    Bewusst ohne Bibliothek; rohes HTML aus der Antwort wird immer escaped."""
    out: list[str] = []
    paragraph: list[str] = []
    list_tag = ""

    def flush() -> None:
        nonlocal list_tag
        if paragraph:
            out.append(f"<p>{'<br>'.join(_inline(line) for line in paragraph)}</p>")
            paragraph.clear()
        if list_tag:
            out.append(f"</{list_tag}>")
            list_tag = ""

    for raw in markdown.splitlines():
        line = raw.strip()
        heading = re.match(r"(#{1,6})\s+(.*)", line)
        bullet = re.match(r"[-*+]\s+(.*)", line)
        numbered = re.match(r"\d+[.)]\s+(.*)", line)
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            flush()
        elif heading:
            flush()
            level = min(6, len(heading.group(1)))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif bullet or numbered:
            tag = "ul" if bullet else "ol"
            if paragraph or list_tag != tag:
                flush()
                out.append(f"<{tag}>")
                list_tag = tag
            out.append(f"<li>{_inline((bullet or numbered).group(1))}</li>")
        elif list_tag and raw[:1] in (" ", "\t"):  # eingerückte Fortsetzung eines Listenpunkts
            out[-1] = out[-1].removesuffix("</li>") + " " + _inline(line) + "</li>"
        else:
            if list_tag:
                flush()
            paragraph.append(line)
    flush()
    return "".join(out)


def evaluation_markdown(interview: Interview) -> str:
    lines = [f"# KI-Bewertung: Interview mit {interview.person}", ""]
    lines += [f"- **{label}:** {value}" for label, value in meta(interview)]
    lines += ["", f"_{evaluation_note(interview)}_", "", interview.evaluation.text.strip(), ""]
    return "\n".join(lines)


def evaluation_html(interview: Interview) -> str:
    e = html.escape
    parts = [_head(), f"<h1>KI-Bewertung: Interview mit {e(interview.person)}</h1><table class='meta'>"]
    parts += [f"<tr><td>{e(label)}</td><td>{e(value)}</td></tr>" for label, value in meta(interview)]
    parts.append(f"</table><p class='ki-note'>{e(evaluation_note(interview))}</p>")
    parts.append(f"<div class='ki'>{markdown_html(interview.evaluation.text.strip())}</div>")
    parts.append("</body></html>")
    return "".join(parts)


def _analysis_note(analysis) -> str:
    parts = [f"{analysis.interviews} Interviews"]
    if analysis.umfang:
        parts.append(analysis.umfang)
    if analysis.fertig_am:
        parts.append(f"erstellt am {analysis.fertig_am.strftime('%d.%m.%Y %H:%M')} UTC")
    if analysis.modell:
        parts.append(f"mit {analysis.modell}")
    if analysis.bearbeitet:
        parts.append("von Hand überarbeitet")
    return "KI-generiert – bitte prüfen. " + ", ".join(parts) + "."


def analysis_markdown(project) -> str:
    analysis = project.analysis
    lines = [f"# KI-Analyse: Projekt {project.name}", ""]
    if project.beschreibung:
        lines += [project.beschreibung, ""]
    lines += [f"_{_analysis_note(analysis)}_", ""]
    if analysis.kurzfassung.strip():
        lines += ["## Kurzzusammenfassung", "", analysis.kurzfassung.strip(), ""]
    if analysis.analyse.strip():
        lines += ["## Analyse", "", demote(analysis.analyse.strip(), 1), ""]
    return "\n".join(lines)


def analysis_html(project) -> str:
    e = html.escape
    analysis = project.analysis
    parts = [_head(), f"<h1>KI-Analyse: Projekt {e(project.name)}</h1>"]
    if project.beschreibung:
        parts.append(f"<p>{e(project.beschreibung)}</p>")
    parts.append(f"<p class='ki-note'>{e(_analysis_note(analysis))}</p>")
    if analysis.kurzfassung.strip():
        parts.append(f"<h2>Kurzzusammenfassung</h2><div class='ki'>{markdown_html(analysis.kurzfassung.strip())}</div>")
    if analysis.analyse.strip():
        parts.append("<h2 class='transcript'>Analyse</h2>")
        parts.append(f"<div class='ki'>{markdown_html(demote(analysis.analyse.strip(), 1))}</div>")
    parts.append("</body></html>")
    return "".join(parts)


def analysis_pdf(project) -> bytes:
    return _pdf(analysis_html(project))


def _pdf(document: str) -> bytes:
    from weasyprint import HTML  # spät importieren: lädt Pango, nur wenn wirklich ein PDF gebraucht wird

    # Kein Zugriff auf Dateien oder Netz aus dem Dokument heraus
    def deny(url: str, *args, **kwargs):
        raise ValueError(f"Externe Ressource blockiert: {url}")

    return HTML(string=document, url_fetcher=deny).write_pdf()


def to_pdf(interview: Interview) -> bytes:
    return _pdf(to_html(interview))


def evaluation_pdf(interview: Interview) -> bytes:
    return _pdf(evaluation_html(interview))
