def _consult(client, headers):
    return client.post(
        "/api/consultations",
        headers=headers,
        json={"reason": "x", "priority": "routine", "consultation_type": "ward"},
    ).json()["id"]


def test_attachment_upload_download_delete(client, registrar):
    cid = _consult(client, registrar)
    content = b"lab report bytes \x00\x01"
    up = client.post(
        f"/api/consultations/{cid}/attachments",
        headers=registrar,
        files={"file": ("report.txt", content, "text/plain")},
    )
    assert up.status_code == 201
    aid = up.json()["id"]
    assert up.json()["size_bytes"] == len(content)

    dl = client.get(f"/api/attachments/{aid}/download", headers=registrar)
    assert dl.status_code == 200
    assert dl.content == content

    assert (
        client.delete(f"/api/attachments/{aid}", headers=registrar).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/consultations/{cid}/attachments", headers=registrar
        ).json()
        == []
    )


def test_attachment_empty_rejected(client, registrar):
    cid = _consult(client, registrar)
    r = client.post(
        f"/api/consultations/{cid}/attachments",
        headers=registrar,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert r.status_code == 400


def test_attachment_tenant_isolation(client, registrar, other_tenant):
    cid = _consult(client, registrar)
    up = client.post(
        f"/api/consultations/{cid}/attachments",
        headers=registrar,
        files={"file": ("r.txt", b"data", "text/plain")},
    )
    aid = up.json()["id"]
    assert (
        client.get(
            f"/api/attachments/{aid}/download", headers=other_tenant
        ).status_code
        == 404
    )


def test_fhir_patient_and_service_request(client, registrar):
    p = client.get("/api/fhir/Patient/1", headers=registrar)
    assert p.headers["content-type"].startswith("application/fhir+json")
    body = p.json()
    assert body["resourceType"] == "Patient"
    assert body["gender"] == "female"  # Grace
    assert body["identifier"][0]["value"] == "MRN-100234"

    cid = client.post(
        "/api/consultations",
        headers=registrar,
        json={
            "reason": "Debridement",
            "priority": "emergency",
            "consultation_type": "ward",
            "target_specialty": "Plastic Surgery",
        },
    ).json()["id"]
    sr = client.get(f"/api/fhir/ServiceRequest/{cid}", headers=registrar).json()
    assert sr["resourceType"] == "ServiceRequest"
    assert sr["status"] == "active"
    assert sr["priority"] == "stat"  # emergency -> stat
    assert sr["code"]["text"] == "Plastic Surgery"


def test_fhir_everything_bundle(client, registrar):
    e = client.get("/api/fhir/Patient/1/$everything", headers=registrar).json()
    assert e["resourceType"] == "Bundle"
    assert e["type"] == "searchset"
    types = {x["resource"]["resourceType"] for x in e["entry"]}
    assert "Patient" in types


def test_fhir_requires_auth(client):
    assert client.get("/api/fhir/metadata").status_code == 401
