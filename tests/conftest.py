import pytest

from app import create_app
from app.extensions import db
from app.models import User
from config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(username="admin", role="Administrator")
        admin.set_password("StrongPassword123!")
        staff = User(username="staff", role="Park Staff")
        staff.set_password("StrongPassword123!")
        db.session.add_all([admin, staff])
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username="admin"):
    return client.post(
        "/login",
        data={"username": username, "password": "StrongPassword123!"},
        follow_redirects=False,
    )


@pytest.fixture()
def admin_client(client):
    login(client, "admin")
    return client


@pytest.fixture()
def staff_client(client):
    login(client, "staff")
    return client
