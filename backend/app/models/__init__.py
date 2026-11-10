from datetime import date, datetime, timezone

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    beschreibung: Mapped[str] = mapped_column(Text, default="")

    questionnaires: Mapped[list["Questionnaire"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", order_by="Questionnaire.name, Questionnaire.version"
    )


class Questionnaire(Base):
    __tablename__ = "questionnaire"
    __table_args__ = (UniqueConstraint("group_id", "name", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    importiert_am: Mapped[datetime] = mapped_column(DateTime, default=now)

    group: Mapped[Group] = relationship(back_populates="questionnaires")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="questionnaire", cascade="all, delete-orphan", order_by="Question.position"
    )
    interviews: Mapped[list["Interview"]] = relationship(back_populates="questionnaire")


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(primary_key=True)
    questionnaire_id: Mapped[int] = mapped_column(ForeignKey("questionnaire.id", ondelete="CASCADE"), index=True)
    abschnitt: Mapped[str] = mapped_column(String(200), default="Allgemein")
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    hinweis: Mapped[str] = mapped_column(Text, default="")
    pflicht: Mapped[bool] = mapped_column(default=False)
    typ: Mapped[str] = mapped_column(String(20), default="text")

    questionnaire: Mapped[Questionnaire] = relationship(back_populates="questions")


class Interview(Base):
    __tablename__ = "interview"

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: Kataloge mit Interviews bleiben erhalten; Löschen läuft über das Interview.
    questionnaire_id: Mapped[int] = mapped_column(ForeignKey("questionnaire.id", ondelete="RESTRICT"), index=True)
    person: Mapped[str] = mapped_column(String(200))
    organisation: Mapped[str] = mapped_column(String(200), default="")
    datum: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="laufend")  # laufend | abgeschlossen
    gesamtnotiz: Mapped[str] = mapped_column(Text, default="")

    questionnaire: Mapped[Questionnaire] = relationship(back_populates="interviews")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="Answer.position"
    )
    recordings: Mapped[list["Recording"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="Recording.id"
    )


class Answer(Base):
    __tablename__ = "answer"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interview.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    question_snapshot: Mapped[dict] = mapped_column(JSON)
    notiz: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="offen")  # offen | beantwortet | uebersprungen | spaeter
    geaendert_am: Mapped[datetime] = mapped_column(DateTime, default=now)

    interview: Mapped[Interview] = relationship(back_populates="answers")


class Recording(Base):
    """Audio-Aufnahme eines Interviews; die Datei liegt unter AUDIO_DIR, hier nur der relative Pfad."""

    __tablename__ = "recording"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interview.id", ondelete="CASCADE"), index=True)
    dateiname: Mapped[str] = mapped_column(String(255))  # Originalname beim Hochladen
    pfad: Mapped[str] = mapped_column(String(255))  # relativ zu AUDIO_DIR
    groesse: Mapped[int] = mapped_column(BigInteger, default=0)
    hochgeladen_am: Mapped[datetime] = mapped_column(DateTime, default=now)
    # keine | wartend | laeuft | fertig | fehler
    transkript_status: Mapped[str] = mapped_column(String(20), default="keine")
    transkript_optionen: Mapped[dict] = mapped_column(JSON, default=dict)
    transkript: Mapped[str] = mapped_column(Text, default="")
    transkript_fehler: Mapped[str] = mapped_column(Text, default="")
    transkript_log: Mapped[str] = mapped_column(Text, default="")
    transkript_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transkript_ende: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    interview: Mapped[Interview] = relationship(back_populates="recordings")


class Setting(Base):
    """Einstellungen, die in der App geändert werden können (Schlüssel/Wert)."""

    __tablename__ = "setting"

    schluessel: Mapped[str] = mapped_column(String(100), primary_key=True)
    wert: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    """Bewusst ohne Inhalte: nur Entität und Aktion, keine personenbezogenen Daten."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    entitaet: Mapped[str] = mapped_column(String(100))
    aktion: Mapped[str] = mapped_column(String(50))
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime, default=now)
