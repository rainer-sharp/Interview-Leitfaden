from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Optional200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
QuestionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
QuestionType = Literal["text", "skala", "ja_nein", "auswahl"]
AnswerStatus = Literal["offen", "beantwortet", "uebersprungen", "spaeter"]


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GroupIn(BaseModel):
    name: Name
    beschreibung: str = ""
    projekt_id: int | None = None  # beim Anlegen; ohne Angabe das Standardprojekt


class ProjectIn(BaseModel):
    name: Name
    beschreibung: str = ""
    ki_anweisung: Annotated[str, StringConstraints(max_length=20_000)] = ""
    # None = unverändert, leer = allgemeine Analyse-Anweisung aus den Einstellungen
    ki_analyse_anweisung: Annotated[str, StringConstraints(max_length=20_000)] | None = None


class ProjectCopyIn(BaseModel):
    name: Name | None = None  # ohne Angabe „<Name> (Kopie)“
    beschreibung: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    beschreibung: str
    ki_anweisung: str
    ki_analyse_anweisung: str
    angelegt_am: datetime
    gruppen: int
    kataloge: int
    interviews: int
    mitglieder: list[dict]


class QuestionnaireSummary(Orm):
    id: int
    group_id: int
    name: str
    version: int
    importiert_am: datetime
    fragen: int
    interviews: int


class GroupOut(Orm):
    id: int
    projekt_id: int
    projekt_name: str
    name: str
    beschreibung: str
    questionnaires: list[QuestionnaireSummary]


class QuestionnaireIn(BaseModel):
    name: Name


class QuestionIn(BaseModel):
    text: QuestionText
    abschnitt: Name = "Allgemein"
    hinweis: str = ""
    pflicht: bool = False
    typ: QuestionType = "text"


class QuestionOut(Orm):
    id: int
    questionnaire_id: int
    abschnitt: str
    position: int
    text: str
    hinweis: str
    pflicht: bool
    typ: str


class QuestionnaireOut(QuestionnaireSummary):
    group_name: str
    questions: list[QuestionOut]


class OrderItem(BaseModel):
    id: int
    abschnitt: Name


class InterviewIn(BaseModel):
    questionnaire_id: int
    person: Name
    organisation: Optional200 = ""
    datum: date


class InterviewUpdate(BaseModel):
    person: Name | None = None
    organisation: Optional200 | None = None
    datum: date | None = None
    gesamtnotiz: str | None = None


class AnswerUpdate(BaseModel):
    notiz: str | None = None
    status: AnswerStatus | None = None


class AnswerOut(Orm):
    id: int
    position: int
    question_snapshot: dict
    notiz: str
    status: str
    geaendert_am: datetime


class InterviewSummary(Orm):
    id: int
    questionnaire_id: int
    person: str
    organisation: str
    datum: date
    status: str
    projekt_id: int
    projekt_name: str
    group_name: str
    questionnaire_name: str
    version: int
    fragen: int
    bearbeitet: int
    interviewer_id: int | None
    interviewer_name: str
    darf_bearbeiten: bool


class InterviewOut(InterviewSummary):
    gesamtnotiz: str
    answers: list[AnswerOut]
    aufnahmen: list["RecordingOut"]


TranscriptionMode = Literal["mix", "tracks"]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class RecordingOut(Orm):
    id: int
    interview_id: int
    dateiname: str
    groesse: int
    hochgeladen_am: datetime
    transkript_status: str
    transkript_optionen: dict
    transkript: str
    transkript_fehler: str
    transkript_log: str
    transkript_start: datetime | None
    transkript_ende: datetime | None


class TranscriptionStart(BaseModel):
    modus: TranscriptionMode = "mix"
    name_ich: Short = ""
    name_partner: Short = ""
    begriffe: str = ""


class TranscriptUpdate(BaseModel):
    transkript: str


class TranscriptionSettingsOut(BaseModel):
    url: str
    model: str
    api_key_gesetzt: bool
    modus: TranscriptionMode
    name_ich: str
    begriffe: str
    ffmpeg_verfuegbar: bool


class TranscriptionSettingsIn(BaseModel):
    """None = unverändert, leerer Text = zurück auf die Vorgabe."""

    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^(|https?://\S+)$")] | None = None
    model: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    api_key: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    modus: Literal["", "mix", "tracks"] | None = None
    name_ich: Short | None = None
    begriffe: str | None = None


class ServerCheckOut(BaseModel):
    ok: bool
    meldung: str
    modelle: list[str]


class EvaluationOut(BaseModel):
    """status „keine“, solange das Interview nicht bewertet wurde."""

    status: Literal["keine", "wartend", "laeuft", "fertig", "fehler"]
    text: str = ""
    fehler: str = ""
    modell: str = ""
    mit_transkript: bool = False
    bearbeitet: bool = False
    gestartet_am: datetime | None = None
    fertig_am: datetime | None = None
    hat_transkript: bool  # liegt jetzt ein Transkript vor (für den Hinweis vor dem Start)
    anweisung_quelle: Literal["projekt", "allgemein"]  # welche Anweisung beim nächsten Start gilt
    projekt_name: str
    transkription_laeuft: bool


class ProjectAnalysisOut(BaseModel):
    """status „keine“, solange das Projekt nicht analysiert wurde."""

    status: Literal["keine", "wartend", "laeuft", "fertig", "fehler"]
    analyse: str = ""
    kurzfassung: str = ""
    fehler: str = ""
    fortschritt: str = ""
    modell: str = ""
    interviews: int = 0
    umfang: str = ""
    bearbeitet: bool = False
    gestartet_am: datetime | None = None
    fertig_am: datetime | None = None
    # Stand jetzt, für den Hinweis vor dem Start
    interviews_jetzt: int
    mit_transkript: int
    mit_bewertung: int
    anweisung_quelle: Literal["projekt", "allgemein"]


class ProjectAnalysisUpdate(BaseModel):
    analyse: str | None = None
    kurzfassung: str | None = None


class EvaluationUpdate(BaseModel):
    text: str


class LlmSettingsOut(BaseModel):
    url: str
    model: str
    api_key_gesetzt: bool
    anweisung: str
    anweisung_angepasst: bool
    analyse_anweisung: str
    analyse_anweisung_angepasst: bool


class LlmSettingsIn(BaseModel):
    """None = unverändert, leerer Text = zurück auf die Vorgabe."""

    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500, pattern=r"^(|https?://\S+)$")] | None = None
    model: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    api_key: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    anweisung: Annotated[str, StringConstraints(max_length=20_000)] | None = None
    analyse_anweisung: Annotated[str, StringConstraints(max_length=20_000)] | None = None


class LlmCheckOut(ServerCheckOut):
    modell: str


InterviewOut.model_rebuild()
