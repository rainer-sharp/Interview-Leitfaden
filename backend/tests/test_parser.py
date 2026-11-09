import pytest

from app.importers.parser import decode, parse_csv, parse_file, parse_json

EXPECTED = [
    ("Einstieg", 1, "Wie sieht Ihr typischer Arbeitstag aus?", "Locker beginnen", True, "text"),
    ("Einkauf", 2, "Wie bestellen Sie heute Bauteile für das Größenlager?", "Nach Tools fragen", True, "text"),
    ("Einkauf", 3, "Wie zufrieden sind Sie mit den Lieferzeiten?", "", False, "skala"),
]


def rows(result):
    return [(r.abschnitt, r.position, r.frage, r.hinweis, r.pflicht, r.typ) for r in result.rows]


@pytest.mark.parametrize(
    "filename, encoding",
    [("fragen_utf8.csv", "utf-8"), ("fragen_cp1252.csv", "windows-1252"), ("fragen.xlsx", None), ("fragen.json", "utf-8")],
)
def test_valid_files_map_to_same_schema(testdata, filename, encoding):
    result = parse_file(filename, (testdata / filename).read_bytes())
    assert result.errors == []
    assert result.ok
    assert result.encoding == encoding
    assert rows(result) == EXPECTED


def test_comma_file_with_only_required_column_uses_defaults(testdata):
    result = parse_file("x.csv", (testdata / "fragen_kommas.csv").read_bytes())
    assert result.ok and result.trennzeichen == ","
    assert rows(result) == [
        ("Einkauf", None, "Wie, wann und wo bestellen Sie?", "", False, "text"),
        ("Allgemein", None, "Nur die Pflichtspalte ist nötig", "", False, "text"),
    ]


def test_faulty_file_reports_expected_errors_with_lines(testdata):
    result = parse_file("x.csv", (testdata / "fragen_fehlerhaft.csv").read_bytes())
    assert not result.ok
    found = [(e.zeile, e.meldung) for e in result.errors]
    assert found == [
        (3, "Position 1 ist doppelt (auch in Zeile 2)."),
        (4, "Die Frage ist leer."),
        (5, "Unbekannter Typ „freitext“ (erlaubt: text, skala, ja_nein, auswahl)."),
        (6, "Position „abc“ ist keine positive ganze Zahl."),
        (6, "Pflicht „vielleicht“ ist nicht erkennbar (erwartet: ja/nein)."),
    ]


def test_bom_is_removed_from_first_column():
    result = parse_csv("﻿frage;typ\nA;text\n".encode())
    assert result.ok and result.rows[0].frage == "A"


def test_utf16_excel_unicode_text():
    assert decode("frage\nÄ\n".encode("utf-16")) == ("frage\nÄ\n", "utf-16")


def test_header_is_case_insensitive_and_unknown_columns_warn():
    result = parse_csv("Frage;Bemerkung\nA;x\n".encode())
    assert result.ok and [w.meldung for w in result.warnings] == ["Unbekannte Spalten werden ignoriert: bemerkung."]


def test_missing_required_column():
    result = parse_csv(b"abschnitt;text\nA;B\n")
    assert [e.meldung for e in result.errors] == ["Die Pflichtspalte „frage“ fehlt in der Kopfzeile."]


def test_multiline_cells_keep_real_line_numbers():
    result = parse_csv('frage;hinweis\n"A";"mehr\nzeilig"\n;x\n'.encode())
    assert result.errors[0].zeile == 4


def test_blank_rows_are_skipped_and_rows_sorted_by_position():
    result = parse_csv(b"frage;position\nZwei;2\n;;\nOhne;\nEins;1\n")
    assert [r.frage for r in result.rows] == ["Eins", "Zwei", "Ohne"]


@pytest.mark.parametrize("data", [b"", b"\n\n"])
def test_empty_csv(data):
    assert parse_csv(data).errors[0].meldung == "Die Datei ist leer."


def test_header_only_has_no_questions():
    assert parse_csv(b"frage\n").errors[0].meldung == "Die Datei enthält keine Fragen."


def test_broken_xlsx_is_reported_not_raised():
    assert parse_file("x.xlsx", b"keine zip-datei").errors[0].meldung == "Die Excel-Datei konnte nicht gelesen werden."


@pytest.mark.parametrize("data", [b"{kaputt", b'{"a": 1}', b"[1, 2]"])
def test_invalid_json_is_reported(data):
    assert parse_json(data).errors


def test_unknown_extension():
    assert "nicht unterstützt" in parse_file("x.pdf", b"x").errors[0].meldung
