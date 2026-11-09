import pytest


@pytest.fixture
def group_id(client):
    return client.post("/api/groups", json={"name": "Lager"}).json()["id"]


def upload(testdata, filename="fragen_utf8.csv"):
    return {"file": (filename, (testdata / filename).read_bytes())}


def save(client, testdata, filename="fragen_utf8.csv", **form):
    return client.post("/api/import", files=upload(testdata, filename), data=form)


def test_preview_returns_rows_without_saving(client, testdata, group_id):
    body = client.post("/api/import/vorschau", files=upload(testdata, "fragen_cp1252.csv")).json()
    assert body["ok"] is True and body["encoding"] == "windows-1252" and len(body["rows"]) == 3
    assert client.get(f"/api/groups/{group_id}").json()["questionnaires"] == []


def test_preview_lists_errors(client, testdata):
    body = client.post("/api/import/vorschau", files=upload(testdata, "fragen_fehlerhaft.csv")).json()
    assert body["ok"] is False and len(body["errors"]) == 5


def test_faulty_file_is_never_saved(client, testdata, group_id):
    response = save(client, testdata, "fragen_fehlerhaft.csv", modus="neu", group_id=group_id, name="K")
    assert response.status_code == 422
    assert client.get(f"/api/groups/{group_id}").json()["questionnaires"] == []


def test_new_catalog(client, testdata, group_id):
    response = save(client, testdata, "fragen.xlsx", modus="neu", group_id=group_id, name="Leitfaden")
    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["version"], body["fragen"]) == ("Leitfaden", 1, 3)
    assert [q["position"] for q in body["questions"]] == [1, 2, 3]
    assert body["questions"][2]["typ"] == "skala"


def test_new_catalog_with_taken_name_points_to_version(client, testdata, group_id):
    save(client, testdata, modus="neu", group_id=group_id, name="Leitfaden")
    response = save(client, testdata, modus="neu", group_id=group_id, name="Leitfaden")
    assert response.status_code == 409 and "neue Version" in response.json()["detail"]


def test_new_version_leaves_old_one_untouched(client, testdata, group_id):
    first = save(client, testdata, modus="neu", group_id=group_id, name="Leitfaden").json()
    second = save(client, testdata, "fragen_kommas.csv", modus="version", questionnaire_id=first["id"]).json()
    assert (second["name"], second["version"], second["fragen"]) == ("Leitfaden", 2, 2)
    assert second["id"] != first["id"]
    assert client.get(f"/api/questionnaires/{first['id']}").json()["fragen"] == 3


def test_append_continues_numbering(client, testdata, group_id):
    first = save(client, testdata, modus="neu", group_id=group_id, name="Leitfaden").json()
    body = save(client, testdata, "fragen_kommas.csv", modus="anhaengen", questionnaire_id=first["id"]).json()
    assert body["id"] == first["id"] and body["version"] == 1
    assert [q["position"] for q in body["questions"]] == [1, 2, 3, 4, 5]
    assert body["questions"][3]["text"] == "Wie, wann und wo bestellen Sie?"


@pytest.mark.parametrize(
    "form, status",
    [
        ({"modus": "neu", "name": "K"}, 422),
        ({"modus": "neu", "group_id": 1}, 422),
        ({"modus": "neu", "group_id": 99, "name": "K"}, 404),
        ({"modus": "version"}, 422),
        ({"modus": "anhaengen", "questionnaire_id": 99}, 404),
        ({"modus": "falsch"}, 422),
    ],
)
def test_save_form_validation(client, testdata, group_id, form, status):
    assert save(client, testdata, **form).status_code == status


def test_too_large_file(client):
    response = client.post("/api/import/vorschau", files={"file": ("x.csv", b"x" * (5 * 1024 * 1024 + 1))})
    assert response.status_code == 413


def test_sample_download_passes_own_import(client):
    response = client.get("/api/import/beispiel.csv")
    assert response.status_code == 200 and "attachment" in response.headers["content-disposition"]
    assert client.post("/api/import/vorschau", files={"file": ("b.csv", response.content)}).json()["ok"] is True
