"""API regression tests for the FastAPI layer."""

from __future__ import annotations

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from src.api.server import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_payload() -> dict[str, object]:
    return {
        "commitments": [
            {"title": "CS 101", "day": "Mon", "start": 9.0, "end": 10.5},
            {"title": "Work Shift", "day": "Tue", "start": 14.0, "end": 18.0},
        ],
        "tasks": [
            {"title": "Essay Draft", "duration": 2.0, "deadline_day": "Tue"},
            {"title": "Quiz Prep", "duration": 1.5, "deadline_day": "Wed"},
        ],
        "sleep_window": {"start": 23.0, "end": 7.0},
        "preferences": {
            "max_daily_hours": 8.0,
            "preferred_study_start": 7.0,
            "preferred_study_end": 22.0,
            "slot_step": 0.5,
            "buffer_hours": 1.0,
            "weekly_hours_threshold": 50.0,
            "late_night_cutoff": 23.0,
            "max_consecutive_blocks": 3,
            "min_breaks_per_day": 1,
            "deadline_cluster_days": 2,
        },
    }


def test_health_endpoint_returns_ok_status(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_returns_before_after_plans_and_assessments(
    client: TestClient,
    sample_payload: dict[str, object],
) -> None:
    response = client.post("/api/analyze", json=sample_payload)

    assert response.status_code == 200

    body = response.json()
    assert set(body) == {
        "before_plan",
        "after_plan",
        "before_assessment",
        "after_assessment",
        "metadata",
    }

    assert set(body["before_plan"]) == {"scheduled_tasks", "unscheduled_tasks"}
    assert set(body["after_plan"]) == {"scheduled_tasks", "unscheduled_tasks"}
    assert {"score", "level", "reasons", "metrics"} <= set(body["before_assessment"])
    assert {"score", "level", "reasons", "metrics"} <= set(body["after_assessment"])

    metadata = body["metadata"]
    assert isinstance(metadata["scheduled_task_count"], int)
    assert isinstance(metadata["unscheduled_task_count"], int)
    assert isinstance(metadata["burnout_score"], int)
    assert metadata["burnout_level"] in {"Low", "Moderate", "High"}
    assert isinstance(metadata["burnout_reasons"], list)
    assert isinstance(metadata["burnout_metrics"], dict)


def test_analyze_endpoint_returns_422_for_invalid_task_payload(
    client: TestClient,
    sample_payload: dict[str, object],
) -> None:
    invalid_payload = dict(sample_payload)
    invalid_payload["tasks"] = [
        {"title": "Broken Task", "duration": 1.0},
    ]

    response = client.post("/api/analyze", json=invalid_payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert any(error.get("loc") == ["body", "tasks", 0, "deadline_day"] for error in detail)
