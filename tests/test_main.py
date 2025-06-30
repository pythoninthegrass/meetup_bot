import pytest
from app.main import User, UserInDB, app, get_current_user
from fastapi.testclient import TestClient
from jose import jwt
from unittest.mock import MagicMock, patch


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def mock_user():
    return UserInDB(username="testuser", email="test@example.com", hashed_password="hashed_password")


@pytest.fixture
def mock_access_token(mock_user):
    return create_test_token({"sub": mock_user.username})


def create_test_token(data: dict):
    return jwt.encode(data, "test_secret_key", algorithm="HS256")


@pytest.fixture
def auth_headers(mock_access_token):
    return {"Authorization": f"Bearer {mock_access_token}"}


async def override_get_current_user():
    return UserInDB(username="testuser", email="test@example.com", hashed_password="hashed_password")


# Override the dependency for testing
app.dependency_overrides[get_current_user] = override_get_current_user


def test_health_check(test_client):
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_login_success(test_client):
    with patch('app.main.load_user') as mock_load_user, patch('app.main.verify_password', return_value=True):
        mock_load_user.return_value = UserInDB(username="testuser", email="test@example.com", hashed_password="hashed_password")

        response = test_client.post("/auth/login", data={"username": "testuser", "password": "password"})
        assert response.status_code == 303  # Redirect
        assert response.headers["location"] == "/docs"


def test_login_failure(test_client):
    with patch('app.main.load_user') as mock_load_user, patch('app.main.verify_password', return_value=False):
        mock_load_user.return_value = None

        response = test_client.post("/auth/login", data={"username": "testuser", "password": "wrong_password"})
        assert response.status_code == 404


def test_get_token(test_client, auth_headers):
    mock_tokens = {"access_token": "test_access_token", "refresh_token": "test_refresh_token"}

    with patch('main.gen_token', return_value=mock_tokens):
        response = test_client.get("/api/token", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert "test_access_token" in response.json()


def test_get_events(test_client, auth_headers):
    mock_events = [
        {
            "name": "Test Group",
            "date": "Thu 5/26 11:30 am",
            "title": "Test Event",
            "description": "Test Description",
            "eventUrl": "https://test.url",
            "city": "Oklahoma City",
        }
    ]

    with patch('main.get_all_events', return_value=mock_events):
        response = test_client.get(
            "/api/events", headers=auth_headers, params={"location": "Oklahoma City", "exclusions": "Tulsa"}
        )
        assert response.status_code == 200
        assert response.json() == mock_events


def test_check_schedule(test_client, auth_headers):
    mock_schedule = {
        "should_post": True,
        "current_time": "Thursday 10:00 CDT",
        "schedule_time": "Thursday 10:00 CDT",
        "time_diff_minutes": 0,
    }

    with patch('main.should_post_to_slack', return_value=mock_schedule):
        response = test_client.get("/api/check-schedule", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == mock_schedule


def test_post_slack(test_client, auth_headers):
    mock_message = ["Test message"]

    with patch('main.get_events'), patch('main.fmt_json', return_value=mock_message), patch('main.send_message'):
        response = test_client.post(
            "/api/slack",
            headers=auth_headers,
            params={"location": "Oklahoma City", "exclusions": "Tulsa", "channel_name": "test-channel"},
        )
        assert response.status_code == 200
        assert response.json() == mock_message


def test_snooze_slack_post(test_client, auth_headers):
    with patch('main.snooze_schedule'):
        response = test_client.post("/api/snooze", headers=auth_headers, params={"duration": "5_minutes"})
        assert response.status_code == 200
        assert response.json() == {"message": "Slack post snoozed for 5_minutes"}


def test_get_current_schedule(test_client, auth_headers):
    mock_schedules = {
        "schedules": [
            {"day": "Monday", "schedule_time": "10:00", "enabled": True, "snooze_until": None, "original_schedule_time": "10:00"}
        ]
    }

    with patch(
        'main.get_schedule',
        return_value=MagicMock(
            day="Monday", schedule_time="10:00", enabled=True, snooze_until=None, original_schedule_time="10:00"
        ),
    ):
        response = test_client.get("/api/schedule", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == mock_schedules


def test_unauthorized_access(test_client):
    response = test_client.get("/api/events")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_invalid_token(test_client):
    headers = {"Authorization": "Bearer invalid_token"}
    response = test_client.get("/api/events", headers=headers)
    assert response.status_code == 401
    assert "detail" in response.json()
