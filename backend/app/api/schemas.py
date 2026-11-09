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
    group_name: str
    questionnaire_name: str
    version: int
    fragen: int
    bearbeitet: int


class InterviewOut(InterviewSummary):
    gesamtnotiz: str
    answers: list[AnswerOut]
