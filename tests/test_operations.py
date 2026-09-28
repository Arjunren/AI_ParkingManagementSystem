from datetime import date, timedelta

from app.extensions import db
from app.models import Facility, ParkZone


def make_zone(client):
    return client.post(
        "/api/zones",
        json={
            "name": "Picnic Area",
            "description": "Reservable spaces",
            "max_capacity": 100,
            "current_visitors": 10,
            "status": "Open",
        },
    ).get_json()["item"]


def make_facility(client, zone_id):
    return client.post(
        "/api/facilities",
        json={
            "name": "Gazebo A",
            "facility_type": "Gazebo",
            "zone_id": zone_id,
            "description": "Covered picnic space",
            "capacity": 25,
            "status": "Available",
            "last_inspection_date": "",
            "next_inspection_date": "",
        },
    ).get_json()["item"]


def test_visitor_crud_and_exit(admin_client):
    response = admin_client.post(
        "/api/visitors",
        json={
            "display_name": "Walk-in",
            "category": "Adult",
            "contact_info": "",
            "guest_count": 2,
            "entry_time": "",
        },
    )
    assert response.status_code == 201
    visitor = response.get_json()["item"]
    assert visitor["status"] == "Inside"
    assert admin_client.put(
        f"/api/visitors/{visitor['id']}",
        json={"display_name": "Updated Walk-in", "category": "Adult", "contact_info": "", "guest_count": 2},
    ).status_code == 200
    assert admin_client.post(f"/api/visitors/{visitor['id']}/exit", json={}).get_json()["item"]["status"] == "Exited"
    assert admin_client.delete(f"/api/visitors/{visitor['id']}").status_code == 204


def test_facility_crud_and_double_booking(admin_client):
    zone = make_zone(admin_client)
    facility = make_facility(admin_client, zone["id"])
    assert facility["status"] == "Available"
    update = {**facility, "name": "Gazebo Alpha", "zone_id": zone["id"], "last_inspection_date": "", "next_inspection_date": ""}
    assert admin_client.put(f"/api/facilities/{facility['id']}", json=update).status_code == 200
    booking = {
        "customer_name": "Test Customer",
        "contact_info": "",
        "facility_id": facility["id"],
        "reservation_date": (date.today() + timedelta(days=1)).isoformat(),
        "start_time": "10:00",
        "end_time": "12:00",
        "guest_count": 10,
        "payment_status": "Pending",
        "status": "Confirmed",
    }
    assert admin_client.post("/api/reservations", json=booking).status_code == 201
    overlap = {**booking, "start_time": "11:00", "end_time": "13:00"}
    response = admin_client.post("/api/reservations", json=overlap)
    assert response.status_code == 400
    assert "already booked" in response.get_json()["error"]


def test_maintenance_incident_and_feedback(admin_client):
    zone = make_zone(admin_client)
    facility = make_facility(admin_client, zone["id"])
    maintenance = admin_client.post(
        "/api/maintenance",
        json={
            "issue_title": "Broken fixture",
            "description": "Needs inspection",
            "zone_id": zone["id"],
            "facility_id": facility["id"],
            "priority": "High",
            "assigned_staff_id": "",
            "status": "Open",
        },
    )
    assert maintenance.status_code == 201
    incident = admin_client.post(
        "/api/incidents",
        json={
            "incident_type": "Safety Concern",
            "zone_id": zone["id"],
            "incident_date": date.today().isoformat(),
            "incident_time": "14:00",
            "description": "Slippery surface",
            "severity": "Medium",
            "status": "Open",
            "action_taken": "Marked area",
        },
    )
    assert incident.status_code == 201
    feedback = admin_client.post(
        "/api/feedback",
        json={
            "rating": 3,
            "category": "Cleanliness",
            "comment": "More bins requested",
            "zone_id": zone["id"],
            "facility_id": "",
            "status": "New",
            "is_anonymous": True,
        },
    )
    assert feedback.status_code == 201


def test_invalid_input_is_rejected(admin_client):
    response = admin_client.post(
        "/api/visitors",
        json={"display_name": "", "category": "Unknown", "guest_count": -2},
    )
    assert response.status_code == 400

