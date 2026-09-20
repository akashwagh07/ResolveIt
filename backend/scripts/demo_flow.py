"""End-to-end demo flow script demonstrating full complaint lifecycle."""

import argparse
import os
import struct
import sys
import time
import zlib
import httpx


def generate_tiny_png() -> bytes:
    """Generate a valid 1x1 pixel PNG image using only standard library."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc

    raw_scanline = b"\x00\x00\xff\x00"  # 1 green pixel
    idat_data = zlib.compress(raw_scanline)
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + idat_data))
    idat = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + idat_crc

    iend_crc = struct.pack(">I", zlib.crc32(b"IEND"))
    iend = struct.pack(">I", 0) + b"IEND" + iend_crc
    return sig + ihdr + idat + iend


def run_demo(
    base_url: str,
    text: str,
    lat: float,
    lng: float,
    name: str,
    contact: str,
) -> None:
    passcode = os.getenv("OFFICER_PASSCODE", "officer123")

    # 120 second timeout for resilience against cold starts and heavy queues
    client = httpx.Client(base_url=base_url, timeout=120.0)

    print("=" * 65)
    print("ResolveIt Demo Flow: Citizen -> Admin -> Officer -> Citizen")
    print(f"Target Server: {base_url}")
    print("=" * 65)

    # 1. Citizen submits report
    print(f"\n1. Citizen '{name}' submitting civic report...")
    t0 = time.perf_counter()
    res = client.post(
        "/api/complaints",
        data={
            "citizen_name": name,
            "citizen_contact": contact,
            "text": text,
            "latitude": lat,
            "longitude": lng,
            "address_text": f"Coordinates: {lat:.4f}, {lng:.4f}",
        },
    )
    dt1 = time.perf_counter() - t0
    if res.status_code not in (200, 201):
        print(f"FAILED to submit complaint: {res.status_code} {res.text}")
        sys.exit(1)

    c_data = res.json()
    complaint_id = c_data["complaint_id"]
    current_status = c_data["status"]
    dept_code = c_data.get("department", {}).get("code", "UNKNOWN")
    print(f"   Complaint ID: {complaint_id}")
    print(f"   Status:       {current_status}")
    print(f"   Department:   {dept_code}")
    print(f"   Elapsed:      {dt1:.2f}s")

    # Discover admin account
    users_res = client.get("/api/users")
    users = users_res.json() if users_res.status_code == 200 else []
    admin = next((u for u in users if u["role"] == "ADMIN"), None)
    admin_id = str(admin["id"]) if admin else "1"
    admin_headers = {
        "X-Demo-Role": "ADMIN",
        "X-Demo-User-Id": admin_id,
        "X-Demo-Passcode": passcode,
    }

    # 1b. If complaint is in HUMAN_REVIEW, have admin confirm classification so flow continues
    if current_status == "HUMAN_REVIEW":
        print("\n[NOTE] Complaint routed to HUMAN_REVIEW (AI unavailable, quota cooldown, or low confidence).")
        print(f"Admin (ID {admin_id}) confirming classification to continue...")
        t_rev = time.perf_counter()
        confirm_class_res = client.post(
            f"/api/complaints/{complaint_id}/actions/confirm_classification",
            headers=admin_headers,
            json={},
        )
        dt_rev = time.perf_counter() - t_rev
        if confirm_class_res.status_code != 200:
            print(f"FAILED to confirm classification: {confirm_class_res.status_code} {confirm_class_res.text}")
            sys.exit(1)
        current_status = confirm_class_res.json()["status"]
        print(f"   Result: Classification confirmed -> {current_status}")
        print(f"   Elapsed: {dt_rev:.2f}s")

    # Read complaint detail to dynamically pick officer from complaint's own department
    detail_res = client.get(f"/api/complaints/{complaint_id}")
    detail_data = detail_res.json() if detail_res.status_code == 200 else {}
    dept_id = detail_data.get("department", {}).get("id") if detail_data.get("department") else None

    officers = [u for u in users if u["role"] == "OFFICER"]
    matching_officer = None
    if dept_id is not None:
        matching_officer = next((u for u in officers if u.get("department_id") == dept_id), None)
    if not matching_officer and officers:
        matching_officer = officers[0]

    if not matching_officer:
        print("ERROR: No demo officer account found to assign complaint.")
        sys.exit(1)

    officer_id = matching_officer["id"]
    officer_name = matching_officer["name"]
    officer_headers = {
        "X-Demo-Role": "OFFICER",
        "X-Demo-User-Id": str(officer_id),
        "X-Demo-Passcode": passcode,
    }

    # 2. Admin assigns complaint to Officer of the complaint's department
    print(f"\n2. Admin (ID {admin_id}) assigning complaint to '{officer_name}' (ID {officer_id})...")
    t0 = time.perf_counter()
    assign_res = client.post(
        f"/api/complaints/{complaint_id}/actions/assign",
        headers=admin_headers,
        json={"officer_id": officer_id, "note": "Assigned via automated demo flow"},
    )
    dt2 = time.perf_counter() - t0
    if assign_res.status_code != 200:
        print(f"FAILED to assign: {assign_res.status_code} {assign_res.text}")
        sys.exit(1)
    assign_data = assign_res.json()
    print(f"   Result: {assign_data['message']}")
    print(f"   Status: {assign_data['status']}")
    print(f"   Elapsed: {dt2:.2f}s")

    # 3. Officer starts work
    print(f"\n3. Officer (ID {officer_id}) starting work...")
    t0 = time.perf_counter()
    start_res = client.post(
        f"/api/complaints/{complaint_id}/actions/start_work",
        headers=officer_headers,
        json={},
    )
    dt3 = time.perf_counter() - t0
    if start_res.status_code != 200:
        print(f"FAILED to start work: {start_res.status_code} {start_res.text}")
        sys.exit(1)
    start_data = start_res.json()
    print(f"   Result: {start_data['message']}")
    print(f"   Status: {start_data['status']}")
    print(f"   Elapsed: {dt3:.2f}s")

    # 4. Officer uploads resolution evidence
    print(f"\n4. Officer (ID {officer_id}) uploading resolution evidence...")
    png_bytes = generate_tiny_png()
    files = [
        ("after_images", ("resolution_fix.png", png_bytes, "image/png")),
    ]
    t0 = time.perf_counter()
    res_upload = client.post(
        f"/api/complaints/{complaint_id}/resolution",
        headers=officer_headers,
        data={"description": "Issue repaired and verified on-site by field team."},
        files=files,
    )
    dt4 = time.perf_counter() - t0
    if res_upload.status_code != 200:
        print(f"FAILED to submit resolution: {res_upload.status_code} {res_upload.text}")
        sys.exit(1)
    res_data = res_upload.json()
    print(f"   Resolution ID: {res_data['resolution_id']}")
    print(f"   Status (post-verification): {res_data['status']}")
    print(f"   Elapsed: {dt4:.2f}s")

    # 5. Admin approves resolution
    print(f"\n5. Admin (ID {admin_id}) approving resolution...")
    t0 = time.perf_counter()
    approve_res = client.post(
        f"/api/complaints/{complaint_id}/actions/approve_resolution",
        headers=admin_headers,
        json={},
    )
    dt5 = time.perf_counter() - t0
    if approve_res.status_code != 200:
        print(f"FAILED to approve: {approve_res.status_code} {approve_res.text}")
        sys.exit(1)
    approve_data = approve_res.json()
    print(f"   Result: {approve_data['message']}")
    print(f"   Status: {approve_data['status']}")
    print(f"   Elapsed: {dt5:.2f}s")

    # 6. Citizen confirms resolution
    print(f"\n6. Citizen ({contact}) confirming resolution...")
    citizen_headers = {
        "X-Demo-Role": "CITIZEN",
        "X-Citizen-Contact": contact,
    }
    t0 = time.perf_counter()
    confirm_res = client.post(
        f"/api/complaints/{complaint_id}/actions/confirm_resolution",
        headers=citizen_headers,
        json={},
    )
    dt6 = time.perf_counter() - t0
    if confirm_res.status_code != 200:
        print(f"FAILED to confirm resolution: {confirm_res.status_code} {confirm_res.text}")
        sys.exit(1)
    confirm_data = confirm_res.json()
    print(f"   Result: {confirm_data['message']}")
    print(f"   Status: {confirm_data['status']}")
    print(f"   Elapsed: {dt6:.2f}s")

    total_time = dt1 + dt2 + dt3 + dt4 + dt5 + dt6
    print("\n" + "=" * 65)
    print(f"Demo flow completed successfully in {total_time:.2f}s! Complaint is fully RESOLVED.")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ResolveIt end-to-end lifecycle demo flow.")
    parser.add_argument(
        "--base",
        default="http://127.0.0.1:8000",
        help="Base URL of running ResolveIt backend (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--text",
        default="Huge pothole near the school gate for a week, bikes cannot pass",
        help="Complaint description text",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=16.7112,
        help="Latitude coordinate (default: 16.7112)",
    )
    parser.add_argument(
        "--lng",
        type=float,
        default=74.2405,
        help="Longitude coordinate (default: 74.2405)",
    )
    parser.add_argument(
        "--name",
        default="Test User",
        help="Citizen name (default: 'Test User')",
    )
    parser.add_argument(
        "--contact",
        default="+91 9000000000",
        help="Citizen contact number (default: '+91 9000000000')",
    )
    args = parser.parse_args()
    run_demo(
        base_url=args.base,
        text=args.text,
        lat=args.lat,
        lng=args.lng,
        name=args.name,
        contact=args.contact,
    )


if __name__ == "__main__":
    main()
