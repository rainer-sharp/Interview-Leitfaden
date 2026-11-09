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
    "interview_id", "person", "organisation", "datum", "gruppe", "katalog", "version",
    "position", "abschnitt", "frage", "pflicht", "status", "notiz",
]


def _date(interview: Interview) -> str:
    return interview.datum.strftime("%d.%m.%Y")


def _meta(interview: Interview) -> list[tuple[str, str]]:
    catalog = interview.questionnaire
    rows = [("Person", interview.person)]
    if interview.organisation:
        rows.append(("Organisation", interview.organisation))
    rows += [
        ("Datum", _date(interview)),
        ("Gruppe", catalog.group.name),
        ("Fragenkatalog", f"{catalog.name} (Version {catalog.version})"),
        ("Status", interview.status),
    ]
    return rows


def _sections(interview: Interview) -> list[tuple[str, list[Answer]]]:
    return [(name, list(items)) for name, items in groupby(interview.answers, key=lambda a: a.question_snapshot["abschnitt"])]


def filename(interview: Interview, extension: str) -> str:
    slug = unicodedata.normalize("NFKD", interview.person).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", slug).strip("-").lower()[:40] or "person"
    return f"interview-{interview.id}-{interview.datum.isoformat()}-{slug}.{extension}"


def to_markdown(interview: Interview) -> str:
    lines = [f"# Interview: {interview.person}", ""]
    lines += [f"- **{label}:** {value}" for label, value in _meta(interview)]
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
        catalog.group.name, catalog.name, str(catalog.version),
    ]
    rows = []
    for answer in interview.answers:
        question = answer.question_snapshot
        rows.append(base + [
            str(answer.position), question["abschnitt"], question["text"],
            "ja" if question["pflicht"] else "nein", answer.status, answer.notiz,
        ])
    rows.append(base + ["", "", "Gesamtnotiz", "", interview.status, interview.gesamtnotiz])
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


def to_html(interview: Interview) -> str:
    e = html.escape
    parts = [
        "<!doctype html><html lang='de'><head><meta charset='utf-8'><style>",
        "@page { size: A4; margin: 2cm 2cm 2.2cm; "
        "@bottom-right { content: 'Seite ' counter(page) ' von ' counter(pages); font-size: 8pt; color: #777; } }",
        "body { font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; line-height: 1.45; color: #1c1f1e; }",
        "h1 { font-size: 17pt; margin: 0 0 8pt; } h2 { font-size: 12.5pt; color: #175a54; margin: 18pt 0 4pt;"
        " border-bottom: 0.5pt solid #ccc; padding-bottom: 2pt; }",
        "h3 { font-size: 10.5pt; margin: 10pt 0 3pt; page-break-after: avoid; }",
        "table.meta td { padding: 1pt 10pt 1pt 0; vertical-align: top; } table.meta td:first-child { color: #666; }",
        ".note { white-space: pre-wrap; margin: 0; } .empty, .status { color: #777; font-style: italic; margin: 0 0 2pt; }",
        ".tag { font-size: 8pt; color: #175a54; font-weight: normal; }",
        "</style></head><body>",
        f"<h1>Interview: {e(interview.person)}</h1><table class='meta'>",
    ]
    parts += [f"<tr><td>{e(label)}</td><td>{e(value)}</td></tr>" for label, value in _meta(interview)]
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
    parts.append("</body></html>")
    return "".join(parts)


def to_pdf(interview: Interview) -> bytes:
    from weasyprint import HTML  # spät importieren: lädt Pango, nur wenn wirklich ein PDF gebraucht wird

    # Kein Zugriff auf Dateien oder Netz aus dem Dokument heraus
    def deny(url: str, *args, **kwargs):
        raise ValueError(f"Externe Ressource blockiert: {url}")

    return HTML(string=to_html(interview), url_fetcher=deny).write_pdf()
