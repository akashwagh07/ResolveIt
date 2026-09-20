def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "time" in data


def test_list_departments(client):
    response = client.get("/api/departments")
    assert response.status_code == 200
    departments = response.json()
    assert len(departments) == 10
    dept_codes = {d["code"] for d in departments}
    expected_codes = {
        "ROADS",
        "STREET_LIGHTING",
        "WASTE",
        "WATER",
        "DRAINAGE",
        "PARKS_ENVIRONMENT",
        "ENCROACHMENT",
        "ANIMALS",
        "TRAFFIC",
        "SANITATION",
    }
    assert dept_codes == expected_codes


def test_complaint_detail_includes_events(client):
    # Test seeded complaint 1
    c1_id = "c0000001-0000-0000-0000-000000000001"
    response = client.get(f"/api/complaints/{c1_id}")
    assert response.status_code == 200
    complaint = response.json()
    assert complaint["id"] == c1_id
    assert complaint["category"] == "ROADS"
    assert len(complaint["events"]) > 0
    assert len(complaint["evidence"]) > 0

    # Also test events sub-resource endpoint
    events_response = client.get(f"/api/complaints/{c1_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == len(complaint["events"])
    assert events[0]["action"] == "SUBMIT_COMPLAINT"


def test_complaint_not_found_404(client):
    response = client.get("/api/complaints/unknown-uuid-0000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    events_response = client.get("/api/complaints/unknown-uuid-0000/events")
    assert events_response.status_code == 404
    assert "not found" in events_response.json()["detail"].lower()


def test_list_complaints_with_filters(client):
    response = client.get("/api/complaints?status=CITIZEN_CONFIRMATION")
    assert response.status_code == 200
    complaints = response.json()
    assert len(complaints) >= 1
    for c in complaints:
        assert c["status"] == "CITIZEN_CONFIRMATION"

    response = client.get("/api/complaints?category=ROADS")
    assert response.status_code == 200
    for c in response.json():
        assert c["category"] == "ROADS"

    response = client.get("/api/complaints?citizen_contact=%2B91+9822012345")
    assert response.status_code == 200
    res_data = response.json()
    assert len(res_data) >= 1
    for c in res_data:
        assert c["citizen_contact"] == "+91 9822012345"


def test_list_complaints_empty_and_whitespace_filter_treated_as_absent(client):
    # Baseline all complaints
    all_resp = client.get("/api/complaints")
    assert all_resp.status_code == 200
    all_complaints = all_resp.json()
    assert len(all_complaints) >= 6

    # Empty string query parameters: citizen_contact=&status=
    empty_resp = client.get("/api/complaints?citizen_contact=&status=")
    assert empty_resp.status_code == 200
    assert len(empty_resp.json()) == len(all_complaints)

    # Whitespace-only query parameters: citizen_contact=%20&status=%20&category=%20&department_id=
    ws_resp = client.get("/api/complaints?citizen_contact=%20&status=%20&category=%20&department_id=")
    assert ws_resp.status_code == 200
    assert len(ws_resp.json()) == len(all_complaints)


def test_list_complaints_pinned_response_shape(client):
    response = client.get("/api/complaints")
    assert response.status_code == 200
    complaints = response.json()
    assert isinstance(complaints, list)
    assert len(complaints) > 0

    pinned_fields = [
        ("id", str),
        ("status", str),
        ("category", str),
        ("issue", str),
        ("severity_level", str),
        ("priority", str),
        ("latitude", (float, int)),
        ("longitude", (float, int)),
        ("created_at", str),
        ("citizen_contact", str),
    ]

    for item in complaints:
        assert isinstance(item, dict)
        for field_name, expected_type in pinned_fields:
            assert field_name in item, f"Missing field '{field_name}' in complaint summary"
            assert isinstance(item[field_name], expected_type), (
                f"Field '{field_name}' had type {type(item[field_name])}, expected {expected_type}"
            )

