def group(client, name="Lager"):
    response = client.post("/api/groups", json={"name": name, "beschreibung": "Team"})
    assert response.status_code == 201
    return response.json()


def catalog(client, group_id, name="Leitfaden"):
    response = client.post(f"/api/groups/{group_id}/questionnaires", json={"name": name})
    assert response.status_code == 201
    return response.json()


def question(client, catalog_id, text, **fields):
    response = client.post(f"/api/questionnaires/{catalog_id}/questions", json={"text": text, **fields})
    assert response.status_code == 201
    return response.json()


def test_group_crud(client):
    created = group(client)
    assert created["name"] == "Lager"
    assert client.get("/api/groups").json()[0]["id"] == created["id"]
    assert client.get(f"/api/groups/{created['id']}").json()["beschreibung"] == "Team"
    updated = client.put(f"/api/groups/{created['id']}", json={"name": "Lagerteam", "beschreibung": ""})
    assert updated.json()["name"] == "Lagerteam"
    assert client.delete(f"/api/groups/{created['id']}").status_code == 204
    assert client.get(f"/api/groups/{created['id']}").status_code == 404


def test_group_name_rules(client):
    group(client)
    assert client.post("/api/groups", json={"name": "Lager"}).status_code == 409
    assert client.post("/api/groups", json={"name": "   "}).status_code == 422
    other = group(client, "Einkauf")
    assert client.put(f"/api/groups/{other['id']}", json={"name": "Lager"}).status_code == 409


def test_missing_entities_are_404(client):
    assert client.get("/api/groups/99").status_code == 404
    assert client.put("/api/groups/99", json={"name": "x"}).status_code == 404
    assert client.delete("/api/groups/99").status_code == 404
    assert client.post("/api/groups/99/questionnaires", json={"name": "x"}).status_code == 404
    assert client.get("/api/questionnaires/99").status_code == 404
    assert client.delete("/api/questions/99").status_code == 404


def test_catalog_crud_and_versions(client):
    group_id = group(client)["id"]
    first = catalog(client, group_id)
    assert first["version"] == 1
    assert catalog(client, group_id)["version"] == 2
    assert catalog(client, group_id, "Anderer")["version"] == 1
    renamed = client.put(f"/api/questionnaires/{first['id']}", json={"name": "Neu"})
    assert renamed.json()["name"] == "Neu"
    assert client.get(f"/api/groups/{group_id}").json()["questionnaires"][0]["name"] == "Anderer"
    assert client.delete(f"/api/questionnaires/{first['id']}").status_code == 204
    assert client.get(f"/api/questionnaires/{first['id']}").status_code == 404


def test_rename_to_taken_name_and_version_conflicts(client):
    group_id = group(client)["id"]
    catalog(client, group_id, "A")
    other = catalog(client, group_id, "B")
    assert client.put(f"/api/questionnaires/{other['id']}", json={"name": "A"}).status_code == 409


def test_question_crud_keeps_positions_gapless(client):
    catalog_id = catalog(client, group(client)["id"])["id"]
    a = question(client, catalog_id, "A", abschnitt="Einstieg", pflicht=True, hinweis="locker")
    b = question(client, catalog_id, "B")
    c = question(client, catalog_id, "C")
    assert [a["position"], b["position"], c["position"]] == [1, 2, 3]
    assert a["pflicht"] is True and b["abschnitt"] == "Allgemein"

    updated = client.put(f"/api/questions/{b['id']}", json={"text": "B2", "typ": "skala"}).json()
    assert (updated["text"], updated["typ"], updated["position"]) == ("B2", "skala", 2)

    assert client.delete(f"/api/questions/{b['id']}").status_code == 204
    questions = client.get(f"/api/questionnaires/{catalog_id}").json()["questions"]
    assert [(q["text"], q["position"]) for q in questions] == [("A", 1), ("C", 2)]


def test_question_validation(client):
    catalog_id = catalog(client, group(client)["id"])["id"]
    url = f"/api/questionnaires/{catalog_id}/questions"
    assert client.post(url, json={"text": "  "}).status_code == 422
    assert client.post(url, json={"text": "A", "typ": "unbekannt"}).status_code == 422


def test_order_moves_questions_between_sections(client):
    catalog_id = catalog(client, group(client)["id"])["id"]
    a = question(client, catalog_id, "A", abschnitt="X")
    b = question(client, catalog_id, "B", abschnitt="X")
    response = client.put(
        f"/api/questionnaires/{catalog_id}/order",
        json=[{"id": b["id"], "abschnitt": "Y"}, {"id": a["id"], "abschnitt": "X"}],
    )
    assert response.status_code == 200
    questions = client.get(f"/api/questionnaires/{catalog_id}").json()["questions"]
    assert [(q["text"], q["position"], q["abschnitt"]) for q in questions] == [("B", 1, "Y"), ("A", 2, "X")]


def test_order_rejects_incomplete_or_foreign_lists(client):
    group_id = group(client)["id"]
    catalog_id = catalog(client, group_id)["id"]
    a = question(client, catalog_id, "A")
    b = question(client, catalog_id, "B")
    foreign = question(client, catalog(client, group_id, "Fremd")["id"], "F")
    url = f"/api/questionnaires/{catalog_id}/order"
    item = lambda q: {"id": q["id"], "abschnitt": "X"}  # noqa: E731
    assert client.put(url, json=[item(a)]).status_code == 422
    assert client.put(url, json=[item(a), item(a)]).status_code == 422
    assert client.put(url, json=[item(a), item(foreign)]).status_code == 422
    assert client.put(url, json=[item(a), item(b)]).status_code == 200
