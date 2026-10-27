"""Tests for FastAPI Web Dashboard backend endpoints."""

from fastapi.testclient import TestClient
from syntax_agent.web.app import app

client = TestClient(app)


def test_get_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "default_provider" in data
    assert "supported_extensions" in data


def test_scan_endpoint_fixtures():
    response = client.post("/api/scan", json={"target": "tests/fixtures"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_errors"] >= 2
    assert "broken_calculator.py" in str(data["errors"])


def test_fix_endpoint_with_heuristic():
    response = client.post(
        "/api/fix",
        json={
            "target": "tests/fixtures",
            "file_path": "broken_calculator.py",
            "provider": "heuristic",
            "write_back": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["iterations_used"] >= 1
    assert "def calculate_average(numbers):" in data["repaired_code"]
    assert data["diff"] != ""


def test_agentic_run_endpoint():
    response = client.post(
        "/api/agentic-run",
        json={
            "target": "tests/fixtures",
            "provider": "heuristic",
            "dry_run": True,
            "create_branch": False,
            "commit": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "plan" in data
    assert len(data["plan"]) >= 2
    assert "messages" in data
    assert len(data["messages"]) > 5
    assert "file_tasks" in data
