"""Basic regression tests for the scheduler layer.

These tests focus on the responsibilities owned by the scheduler/optimizer:
- enforcing scheduling constraints
- placing tasks before their deadlines
- avoiding collisions with commitments and sleep windows
- surfacing tasks that cannot be scheduled
"""

from __future__ import annotations

import pytest

from src.integration.pipeline import run_pipeline
from src.scheduler.constraints import can_schedule_task, is_slot_available
from src.scheduler.optimizer import optimize_schedule


@pytest.fixture
def default_sleep_window() -> dict[str, float]:
    return {"start": 23.0, "end": 7.0}


@pytest.fixture
def constraint_commitments() -> list[dict[str, float | str]]:
    return [
        {"title": "Algorithms", "day": "Mon", "start": 9.0, "end": 10.5},
        {"title": "Work Shift", "day": "Tue", "start": 13.0, "end": 17.0},
    ]


@pytest.fixture
def optimizer_commitments() -> list[dict[str, float | str]]:
    return [
        {"title": "Biology", "day": "Mon", "start": 9.0, "end": 10.0},
        {"title": "Calculus", "day": "Tue", "start": 10.0, "end": 11.5},
        {"title": "Work", "day": "Wed", "start": 14.0, "end": 18.0},
    ]


def test_slot_available_when_it_avoids_commitments_and_sleep(
    constraint_commitments: list[dict[str, float | str]],
    default_sleep_window: dict[str, float],
) -> None:
    assert is_slot_available(
        day="Mon",
        start=11.0,
        end=12.0,
        commitments=constraint_commitments,
        sleep_window=default_sleep_window,
    )


def test_slot_unavailable_when_it_overlaps_a_commitment(
    constraint_commitments: list[dict[str, float | str]],
    default_sleep_window: dict[str, float],
) -> None:
    assert not is_slot_available(
        day="Mon",
        start=9.5,
        end=10.0,
        commitments=constraint_commitments,
        sleep_window=default_sleep_window,
    )


def test_task_cannot_be_scheduled_after_deadline(
    constraint_commitments: list[dict[str, float | str]],
    default_sleep_window: dict[str, float],
) -> None:
    task = {"title": "Essay Draft", "duration": 1.5, "deadline_day": "Tue"}

    assert not can_schedule_task(
        task=task,
        day="Wed",
        start=10.0,
        commitments=constraint_commitments,
        sleep_window=default_sleep_window,
    )


def test_slot_can_exactly_fit_between_two_commitments(
    default_sleep_window: dict[str, float],
) -> None:
    commitments = [
        {"title": "Morning Class", "day": "Mon", "start": 9.0, "end": 10.0},
        {"title": "Lunch Shift", "day": "Mon", "start": 12.0, "end": 13.0},
    ]

    assert is_slot_available(
        day="Mon",
        start=10.0,
        end=12.0,
        commitments=commitments,
        sleep_window=default_sleep_window,
    )


def test_slot_unavailable_when_it_crosses_sleep_boundary(
    default_sleep_window: dict[str, float],
) -> None:
    assert not is_slot_available(
        day="Mon",
        start=22.5,
        end=23.5,
        commitments=[],
        sleep_window=default_sleep_window,
    )


def test_optimizer_places_tasks_before_deadlines(
    optimizer_commitments: list[dict[str, float | str]],
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Math Homework", "duration": 2.0, "deadline_day": "Tue"},
        {"title": "Lab Report", "duration": 1.5, "deadline_day": "Wed"},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=optimizer_commitments,
        sleep_window=default_sleep_window,
    )

    assert result["unscheduled_tasks"] == []
    assert len(result["scheduled_tasks"]) == 2

    scheduled_days = {task["title"]: task["day"] for task in result["scheduled_tasks"]}
    assert scheduled_days["Math Homework"] in {"Mon", "Tue"}
    assert scheduled_days["Lab Report"] in {"Mon", "Tue", "Wed"}


def test_optimizer_returns_unscheduled_tasks_when_week_is_full(
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Capstone Project", "duration": 8.0, "deadline_day": "Mon"},
    ]
    heavy_commitments = [
        {"title": "Class Block", "day": "Mon", "start": 7.0, "end": 22.0},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=heavy_commitments,
        sleep_window=default_sleep_window,
    )

    assert result["scheduled_tasks"] == []
    assert result["unscheduled_tasks"] == tasks


def test_optimizer_partially_schedules_when_only_some_tasks_fit(
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Short Quiz Prep", "duration": 1.0, "deadline_day": "Mon"},
        {"title": "Long Paper", "duration": 4.0, "deadline_day": "Mon"},
    ]
    commitments = [
        {"title": "Class Block", "day": "Mon", "start": 8.0, "end": 11.0},
        {"title": "Work Shift", "day": "Mon", "start": 12.0, "end": 16.0},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=commitments,
        sleep_window=default_sleep_window,
        workday_start=7.0,
        workday_end=17.0,
        max_daily_hours=5.0,
    )

    scheduled_titles = {task["title"] for task in result["scheduled_tasks"]}
    unscheduled_titles = {task["title"] for task in result["unscheduled_tasks"]}

    assert scheduled_titles == {"Short Quiz Prep"}
    assert unscheduled_titles == {"Long Paper"}


def test_optimizer_handles_multiple_tasks_competing_for_limited_time(
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Task A", "duration": 2.0, "deadline_day": "Mon"},
        {"title": "Task B", "duration": 2.0, "deadline_day": "Mon"},
        {"title": "Task C", "duration": 2.0, "deadline_day": "Mon"},
    ]
    commitments = [
        {"title": "Morning Block", "day": "Mon", "start": 9.0, "end": 13.0},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=commitments,
        sleep_window=default_sleep_window,
        workday_start=7.0,
        workday_end=17.0,
        max_daily_hours=4.0,
    )

    assert len(result["scheduled_tasks"]) == 2
    assert len(result["unscheduled_tasks"]) == 1


def test_optimizer_splits_long_task_across_multiple_days(
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Research Project", "duration": 5.0, "deadline_day": "Tue"},
    ]
    commitments = [
        {"title": "Monday Class", "day": "Mon", "start": 9.0, "end": 12.0},
        {"title": "Tuesday Class", "day": "Tue", "start": 10.0, "end": 13.0},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=commitments,
        sleep_window=default_sleep_window,
        workday_start=7.0,
        workday_end=14.0,
    )

    assert result["unscheduled_tasks"] == []
    assert len(result["scheduled_tasks"]) > 1
    assert all(task["title"] == "Research Project" for task in result["scheduled_tasks"])
    assert sum(task["end"] - task["start"] for task in result["scheduled_tasks"]) == pytest.approx(
        5.0
    )


def test_optimizer_does_not_commit_partial_split_when_full_task_cannot_fit(
    default_sleep_window: dict[str, float],
) -> None:
    tasks = [
        {"title": "Final Project", "duration": 6.0, "deadline_day": "Tue"},
    ]
    commitments = [
        {"title": "Monday Block", "day": "Mon", "start": 8.0, "end": 12.0},
        {"title": "Tuesday Block", "day": "Tue", "start": 8.0, "end": 12.0},
    ]

    result = optimize_schedule(
        tasks=tasks,
        commitments=commitments,
        sleep_window=default_sleep_window,
        workday_start=7.0,
        workday_end=13.0,
        max_daily_hours=2.0,
    )

    assert result["scheduled_tasks"] == []
    assert result["unscheduled_tasks"] == tasks


def test_pipeline_uses_nested_preferences_to_override_defaults() -> None:
    payload = {
        "tasks": [
            {"title": "Reading", "duration": 1.0, "deadline_day": "Mon"},
        ],
        "commitments": [],
        "sleep_window": {"start": 23.0, "end": 7.0},
        "preferences": {
            "max_daily_hours": 4.0,
            "preferred_study_start": 8.0,
            "preferred_study_end": 20.0,
            "slot_step": 1.0,
            "buffer_hours": 0.5,
        },
    }

    result = run_pipeline(payload)

    assert result["metadata"]["scheduler_settings"]["max_daily_hours"] == 4.0
    assert result["metadata"]["scheduler_settings"]["workday_start"] == 8.0
    assert result["metadata"]["scheduler_settings"]["workday_end"] == 20.0
    assert result["metadata"]["scheduler_settings"]["slot_step"] == 1.0
    assert result["metadata"]["scheduler_settings"]["buffer_hours"] == 0.5
    assert result["metadata"]["preferences"] == payload["preferences"]


def test_pipeline_rejects_invalid_preference_values() -> None:
    payload = {
        "tasks": [
            {"title": "Reading", "duration": 1.0, "deadline_day": "Mon"},
        ],
        "commitments": [],
        "sleep_window": {"start": 23.0, "end": 7.0},
        "preferences": {
            "preferred_study_start": 20.0,
            "preferred_study_end": 8.0,
        },
    }

    with pytest.raises(ValueError):
        run_pipeline(payload)


def test_pipeline_returns_schedule_quality_metrics() -> None:
    payload = {
        "tasks": [
            {"title": "Essay", "duration": 2.0, "deadline_day": "Mon"},
            {"title": "Project", "duration": 2.0, "deadline_day": "Tue"},
        ],
        "commitments": [
            {"title": "Class", "day": "Mon", "start": 9.0, "end": 10.0},
        ],
        "sleep_window": {"start": 23.0, "end": 7.0},
        "preferences": {
            "max_daily_hours": 4.0,
            "preferred_study_start": 7.0,
            "preferred_study_end": 12.0,
            "slot_step": 1.0,
            "buffer_hours": 0.0,
        },
    }

    result = run_pipeline(payload)
    metrics = result["metadata"]["schedule_quality"]

    assert metrics["total_scheduled_hours"] == 4.0
    assert metrics["unscheduled_hours"] == 0.0
    assert metrics["heavy_day_threshold"] == 3.0
    assert metrics["scheduled_day_count"] == 2
    assert "Mon" in metrics["daily_load_hours"]
    assert "Tue" in metrics["daily_load_hours"]
    assert metrics["sleep_window"] == payload["sleep_window"]


def test_pipeline_counts_split_tasks_in_schedule_quality() -> None:
    payload = {
        "tasks": [
            {"title": "Research Project", "duration": 5.0, "deadline_day": "Tue"},
        ],
        "commitments": [
            {"title": "Monday Class", "day": "Mon", "start": 9.0, "end": 12.0},
            {"title": "Tuesday Class", "day": "Tue", "start": 10.0, "end": 13.0},
        ],
        "sleep_window": {"start": 23.0, "end": 7.0},
        "preferences": {
            "preferred_study_start": 7.0,
            "preferred_study_end": 14.0,
            "slot_step": 0.5,
            "buffer_hours": 0.0,
        },
    }

    result = run_pipeline(payload)
    metrics = result["metadata"]["schedule_quality"]

    assert metrics["split_task_count"] == 1
    assert metrics["scheduled_day_count"] > 1
