"""Alle Interviews eines Projekts in einer Datei: Markdown zum Lesen oder Weitergeben, JSON zum Weiterverarbeiten.

Je Interview: Metadaten, Fragen mit Notizen, Gesamtnotiz, KI-Bewertung und Transkripte. Mit nur_transkripte
enthält die Datei je Interview nur Kopfdaten und Transkripte.
"""
import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Group, Interview, Project, Questionnaire
from app.services import export


def interviews_of(db: Session, project: Project) -> list[Interview]:
    return (
        db.query(Interview)
        .join(Questionnaire, Interview.questionnaire_id == Questionnaire.id)
        .join(Group, Questionnaire.group_id == Group.id)
        .filter(Group.project_id == project.id)
        .order_by(Interview.datum, Interview.id)
        .all()
    )


def filename(project: Project, extension: str, suffix: str = "") -> str:
    slug = export.slug(project.name, "projekt")
    return f"projekt-{project.id}-{slug}{suffix}.{extension}"


def _title(interview: Interview) -> str:
    who = interview.person + (f" ({interview.organisation})" if interview.organisation else "")
    return f"{who}, {interview.datum.strftime('%d.%m.%Y')}"


def to_markdown(db: Session, project: Project, nur_transkripte: bool = False) -> str:
    interviews = interviews_of(db, project)
    with_transcript = sum(bool(export.transcripts(i)) for i in interviews)
    lines = [f"# Projekt: {project.name}", ""]
    if project.beschreibung:
        lines += [project.beschreibung, ""]
    lines += [
        f"- **Interviews:** {len(interviews)} (davon {with_transcript} mit Transkript)",
        f"- **Gruppen:** {', '.join(g.name for g in project.groups) or '–'}",
        f"- **Inhalt:** {'nur Transkripte' if nur_transkripte else 'Notizen, Gesamtnotiz, KI-Bewertung und Transkripte'}",
        f"- **Exportiert:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        "## Inhalt",
        "",
    ]
    lines += [f"{n}. {_title(i)} – {i.questionnaire.group.name}" for n, i in enumerate(interviews, start=1)]
    if not interviews:
        lines.append("_(keine Interviews)_")
    for number, interview in enumerate(interviews, start=1):
        lines += ["", "---", ""]
        if nur_transkripte:
            lines += [f"## {number}. Interview: {_title(interview)}", ""]
            lines += [f"- **{label}:** {value}" for label, value in export.meta(interview)]
            texts = export.transcripts(interview)
            for name, text in texts:
                lines += ["", f"### Transkript: {name}", "", export.demote(text, 2)]
            if not texts:
                lines += ["", "_(kein Transkript)_"]
        else:
            body = export.demote(export.to_markdown(interview), 1).rstrip()
            lines.append(body.replace("## Interview: ", f"## {number}. Interview: ", 1))
    return "\n".join(lines) + "\n"


def interview_data(interview: Interview, nur_transkripte: bool = False) -> dict:
    catalog = interview.questionnaire
    data = {
        "id": interview.id,
        "person": interview.person,
        "organisation": interview.organisation,
        "datum": interview.datum.isoformat(),
        "status": interview.status,
        "interviewer": interview.interviewer.name if interview.interviewer else None,
        "gruppe": catalog.group.name,
        "katalog": catalog.name,
        "katalog_version": catalog.version,
        "transkripte": [
            {"datei": r.dateiname, "text": r.transkript, "status": r.transkript_status}
            for r in interview.recordings
            if r.transkript.strip()
        ],
    }
    if nur_transkripte:
        return data
    evaluation = interview.evaluation
    data |= {
        "gesamtnotiz": interview.gesamtnotiz,
        "antworten": [
            {
                "position": a.position,
                "abschnitt": a.question_snapshot["abschnitt"],
                "frage": a.question_snapshot["text"],
                "hinweis": a.question_snapshot.get("hinweis", ""),
                "pflicht": a.question_snapshot["pflicht"],
                "status": a.status,
                "notiz": a.notiz,
            }
            for a in interview.answers
        ],
        "ki_bewertung": None
        if evaluation is None or not evaluation.text.strip()
        else {
            "text": evaluation.text,
            "modell": evaluation.modell,
            "mit_transkript": evaluation.mit_transkript,
            "bearbeitet": evaluation.bearbeitet,
            "erstellt_am": evaluation.fertig_am.isoformat() if evaluation.fertig_am else None,
        },
    }
    return data


def to_json(db: Session, project: Project, nur_transkripte: bool = False) -> str:
    document = {
        "format": "interview-leitfaden-projekt/1",
        "exportiert_am": datetime.now().isoformat(timespec="seconds"),
        "inhalt": "transkripte" if nur_transkripte else "vollstaendig",
        "projekt": {
            "id": project.id,
            "name": project.name,
            "beschreibung": project.beschreibung,
            "gruppen": [g.name for g in project.groups],
        },
        "interviews": [interview_data(i, nur_transkripte) for i in interviews_of(db, project)],
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"
