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
