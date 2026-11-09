"""Liest Fragenlisten aus CSV, XLSX und JSON und bildet sie auf ein gemeinsames Schema ab."""
import csv
import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import PurePath
from typing import Any
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

KNOWN_TYPES = ("text", "skala", "ja_nein", "auswahl")
COLUMNS = ("abschnitt", "position", "frage", "hinweis", "pflicht", "typ")
DEFAULT_SECTION = "Allgemein"
MAX_ROWS = 5000

TRUE_VALUES = {"ja", "j", "yes", "y", "true", "wahr", "1", "x"}
FALSE_VALUES = {"nein", "n", "no", "false", "falsch", "0", ""}


@dataclass
class Row:
    zeile: int
    abschnitt: str
    position: int | None
    frage: str
    hinweis: str
    pflicht: bool
    typ: str


@dataclass
class Issue:
    zeile: int | None
    meldung: str


@dataclass
class ParseResult:
    format: str
    encoding: str | None = None
    trennzeichen: str | None = None
    rows: list[Row] = field(default_factory=list)
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.rows)

    def to_dict(self) -> dict:
        return {**asdict(self), "ok": self.ok}


def decode(data: bytes) -> tuple[str, str]:
    """UTF-8 ist streng prüfbar; was daran scheitert, kommt von Excel unter Windows (1252)."""
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace"), "windows-1252"


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_key(key: Any) -> str:
    return _cell(key).lower()


def _parse_records(records: list[tuple[int, dict[str, Any]]], result: ParseResult) -> None:
    """Prüft die Datensätze; Reihenfolge = Position, sonst Dateireihenfolge."""
    seen_positions: dict[int, int] = {}
    for line, record in records:
        values = {key: _cell(record.get(key)) for key in COLUMNS}
        if not any(values.values()):
            continue

        frage = values["frage"]
        if not frage:
            result.errors.append(Issue(line, "Die Frage ist leer."))

        position: int | None = None
        if values["position"]:
            try:
                position = int(values["position"])
                if position < 1:
                    raise ValueError
            except ValueError:
                result.errors.append(Issue(line, f"Position „{values['position']}“ ist keine positive ganze Zahl."))
            else:
                if position in seen_positions:
                    result.errors.append(
                        Issue(line, f"Position {position} ist doppelt (auch in Zeile {seen_positions[position]}).")
                    )
                seen_positions.setdefault(position, line)

        pflicht_raw = values["pflicht"].lower()
        if pflicht_raw not in TRUE_VALUES | FALSE_VALUES:
            result.errors.append(Issue(line, f"Pflicht „{values['pflicht']}“ ist nicht erkennbar (erwartet: ja/nein)."))

        typ = values["typ"].lower() or "text"
        if typ not in KNOWN_TYPES:
            result.errors.append(
                Issue(line, f"Unbekannter Typ „{values['typ']}“ (erlaubt: {', '.join(KNOWN_TYPES)}).")
            )

        result.rows.append(
            Row(
                zeile=line,
                abschnitt=values["abschnitt"] or DEFAULT_SECTION,
                position=position,
                frage=frage,
                hinweis=values["hinweis"],
                pflicht=pflicht_raw in TRUE_VALUES,
                typ=typ,
            )
        )

    if not result.rows and not result.errors:
        result.errors.append(Issue(None, "Die Datei enthält keine Fragen."))

    # Stabil: ohne Position bleibt eine Zeile hinter allen nummerierten, in Dateireihenfolge.
    result.rows.sort(key=lambda row: (row.position is None, row.position or 0))


def _from_table(header: list[Any], body: list[tuple[int, list[Any]]], result: ParseResult) -> None:
    names = [_normalize_key(name) for name in header]
    if "frage" not in names:
        result.errors.append(Issue(1, "Die Pflichtspalte „frage“ fehlt in der Kopfzeile."))
        return
    unknown = [name for name in names if name and name not in COLUMNS]
    if unknown:
        result.warnings.append(Issue(1, f"Unbekannte Spalten werden ignoriert: {', '.join(unknown)}."))
    if len(body) > MAX_ROWS:
        result.errors.append(Issue(None, f"Die Datei hat mehr als {MAX_ROWS} Zeilen."))
        return
    records = [(line, dict(zip(names, row))) for line, row in body]
    _parse_records(records, result)


def parse_csv(data: bytes) -> ParseResult:
    text, encoding = decode(data)
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    result = ParseResult(format="csv", encoding=encoding, trennzeichen=delimiter)
    if not first_line:
        result.errors.append(Issue(None, "Die Datei ist leer."))
        return result
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        rows = [(reader.line_num, row) for row in reader]
    except csv.Error as error:
        result.errors.append(Issue(reader.line_num, f"Die CSV-Datei ist beschädigt: {error}."))
        return result
    rows = [(line, row) for line, row in rows if any(cell.strip() for cell in row)]
    _from_table(rows[0][1], rows[1:], result)
    return result


def parse_xlsx(data: bytes) -> ParseResult:
    result = ParseResult(format="xlsx")
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError):
        result.errors.append(Issue(None, "Die Excel-Datei konnte nicht gelesen werden."))
        return result
    try:
        rows = []
        for line, row in enumerate(workbook.worksheets[0].iter_rows(values_only=True), start=1):
            if line > MAX_ROWS + 1:
                result.errors.append(Issue(None, f"Die Datei hat mehr als {MAX_ROWS} Zeilen."))
                return result
            if any(cell not in (None, "") for cell in row):
                rows.append((line, list(row)))
    finally:
        workbook.close()
    if not rows:
        result.errors.append(Issue(None, "Die Datei ist leer."))
        return result
    _from_table(rows[0][1], rows[1:], result)
    return result


def parse_json(data: bytes) -> ParseResult:
    result = ParseResult(format="json")
    text, result.encoding = decode(data)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        result.errors.append(Issue(error.lineno, f"Die JSON-Datei ist ungültig: {error.msg}."))
        return result
    items = parsed.get("fragen") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        result.errors.append(Issue(None, "Erwartet wird eine Liste von Fragen oder ein Objekt mit „fragen“."))
        return result
    if len(items) > MAX_ROWS:
        result.errors.append(Issue(None, f"Die Datei hat mehr als {MAX_ROWS} Fragen."))
        return result
    records = []
    for number, item in enumerate(items, start=1):
        record = {_normalize_key(key): value for key, value in item.items()}
        if isinstance(record.get("pflicht"), bool):
            record["pflicht"] = "ja" if record["pflicht"] else "nein"
        records.append((number, record))
    _parse_records(records, result)
    return result


PARSERS = {".csv": parse_csv, ".txt": parse_csv, ".xlsx": parse_xlsx, ".json": parse_json}


def parse_file(filename: str, data: bytes) -> ParseResult:
    parser = PARSERS.get(PurePath(filename or "").suffix.lower())
    if parser is None:
        result = ParseResult(format="unbekannt")
        result.errors.append(Issue(None, "Dateityp nicht unterstützt. Erlaubt sind CSV, XLSX und JSON."))
        return result
    return parser(data)
