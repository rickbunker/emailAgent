"""Basic smoke tests for the Flask web UI.

These tests spin up the Flask application with `testing=True` and use the
built-in test client to verify that core routes respond successfully.
They don't require a running server or external services.
"""

# # Standard library imports

# # Third-party imports
import pytest
from flask import Flask

# # Local application imports
# Import create_app factory from the web UI package
from src.web_ui.app import create_app


@pytest.fixture(scope="module")
def app() -> Flask:  # type: ignore[return-type]
    """Return a Flask application configured for testing."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    return app


@pytest.fixture(scope="module")
def client(app: Flask):  # type: ignore[type-arg]
    """Return a Flask test client."""
    return app.test_client()


def test_health_endpoint(client):
    """/api/health should return status ok."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_assets_listing_and_detail(client):
    """List assets via API then request each asset detail page."""
    api_resp = client.get("/api/assets")
    assert api_resp.status_code == 200
    assets_data = api_resp.get_json().get("assets", [])  # type: ignore[index]

    # The application can run with zero assets; still succeed.
    for asset in assets_data:  # type: ignore[assignment-target]
        deal_id = asset["deal_id"]
        detail_resp = client.get(f"/assets/{deal_id}")
        assert detail_resp.status_code == 200, f"Asset {deal_id} detail failed"


def test_dashboard_page(client):
    """Dashboard root page should load successfully."""
    resp = client.get("/")
    assert resp.status_code == 200
