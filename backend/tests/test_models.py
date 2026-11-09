from datetime import date

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import Answer, Base, Group, Interview, Question, Questionnaire


@pytest.fixture
def session(database):
    with Session(get_engine()) as db:
        yield db


def _catalog(db: Session) -> Questionnaire:
    catalog = Questionnaire(group=Group(name="Kunden Einkauf", beschreibung=""), name="Leitfaden")
    catalog.questions.append(Question(position=1, text="Wie geht's?"))
    db.add(catalog)
    db.commit()
    return catalog


def test_migration_creates_all_tables(database):
    assert set(inspect(get_engine()).get_table_names()) >= {
        "group", "questionnaire", "question", "interview", "answer", "audit_log",
    }


def test_migration_matches_models(database):
    with get_engine().connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_defaults(session):
    question = _catalog(session).questions[0]
    assert (question.abschnitt, question.hinweis, question.pflicht, question.typ) == ("Allgemein", "", False, "text")


def test_group_delete_cascades(session):
    catalog = _catalog(session)
    session.delete(catalog.group)
    session.commit()
    assert session.query(Question).count() == 0


def test_catalog_with_interview_cannot_be_removed_by_db(session):
    catalog = _catalog(session)
    session.add(Interview(questionnaire=catalog, person="A", datum=date(2026, 11, 9)))
    session.commit()
    with pytest.raises(IntegrityError):
        session.connection().exec_driver_sql(f"DELETE FROM questionnaire WHERE id={catalog.id}")


def test_interview_delete_removes_answers(session):
    interview = Interview(questionnaire=_catalog(session), person="A", datum=date(2026, 11, 9))
    interview.answers.append(Answer(position=1, question_snapshot={"text": "x"}))
    session.add(interview)
    session.commit()
    session.delete(interview)
    session.commit()
    assert session.query(Answer).count() == 0
