"""Smoke tests for auth + core endpoints (no external AI calls)."""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_register_and_login(api_client):
    resp = api_client.post(
        reverse("v1:register"),
        {
            "email": "new@neuraforge.ai",
            "full_name": "New User",
            "password": "Str0ngPass!2024",
            "password_confirm": "Str0ngPass!2024",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data

    resp = api_client.post(
        reverse("v1:login"),
        {"email": "new@neuraforge.ai", "password": "Str0ngPass!2024"},
        format="json",
    )
    assert resp.status_code == 200
    assert "access" in resp.data and "refresh" in resp.data
    assert resp.data["user"]["email"] == "new@neuraforge.ai"


@pytest.mark.django_db
def test_me_requires_auth(api_client):
    assert api_client.get(reverse("v1:me")).status_code == 401


@pytest.mark.django_db
def test_me_returns_profile(auth_client, user):
    resp = auth_client.get(reverse("v1:me"))
    assert resp.status_code == 200
    assert resp.data["email"] == user.email
    # Profile auto-created by signal.
    assert resp.data["profile"] is not None


@pytest.mark.django_db
def test_create_team(auth_client):
    resp = auth_client.post(reverse("v1:team-list"), {"name": "Research Lab"}, format="json")
    assert resp.status_code == 201
    assert resp.data["my_role"] == "admin"


def test_health_check(api_client):
    # Health endpoint is unauthenticated; DB check runs against the test DB.
    resp = api_client.get("/health/")
    assert resp.status_code in (200, 503)
    assert "checks" in resp.data
