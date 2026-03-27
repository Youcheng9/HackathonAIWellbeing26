"""Integration pipeline for schedule optimization.

This module ties together the scheduler pieces so the UI can hand over a
single payload and receive a single result object back. It normalizes student
preferences, runs the scheduler, and returns burnout-aware metadata for the
optimized plan.
"""

from __future__ import annotations

import sys
from typing import Any, cast

if sys.version_info < (3, 12):
    from typing_extensions import NotRequired, TypedDict
else:  # pragma: no cover - stdlib path on Python 3.12+
    from typing import NotRequired, TypedDict

from src.burnout.scorer import compute_burnout_score
from src.scheduler.constraints import DAY_ORDER, Commitment, ScheduledTask, SleepWindow, Task
from src.scheduler.optimizer import OptimizationResult, optimize_schedule


DEFAULT_SLEEP_WINDOW: SleepWindow = {"start": 23.0, "end": 7.0}


class SchedulerPreferences(TypedDict, total=False):
    """Optional user settings that tune scheduling behavior.

    These are soft configuration values, not changes to the core scheduler
    concept. Users can customize how the optimizer searches for valid slots
    without changing the hard constraints around deadlines, commitments, and
    sleep windows.
    """

    max_daily_hours: float
    preferred_study_start: float
    preferred_study_end: float
    slot_step: float
    buffer_hours: float
    weekly_hours_threshold: float
    late_night_cutoff: float
    max_consecutive_blocks: int
    min_breaks_per_day: int
    deadline_cluster_days: int


class PipelineInput(TypedDict, total=False):
    """Expected request shape for the integration layer."""

    commitments: list[Commitment]
    tasks: list[Task]
    sleep_window: SleepWindow
    preferences: NotRequired[SchedulerPreferences]
    max_daily_hours: float
    workday_start: float
    workday_end: float
    slot_step: float
    buffer_hours: float


class PipelineResult(TypedDict):
    """Single response object for the UI or API layer."""

    original_tasks: list[Task]
    optimized_schedule: list[ScheduledTask]
    unscheduled_tasks: list[Task]
    metadata: dict[str, Any]


def run_pipeline(payload: PipelineInput) -> PipelineResult:
    """Validate the incoming payload and run the scheduler.

    The function stays intentionally small so it is easy to expand later with:
    - baseline burnout scoring before optimization
    - richer explanation generation
    - before/after comparison metrics
    """

    normalized_input = _normalize_pipeline_input(payload)
    optimization = optimize_schedule(
        tasks=normalized_input["tasks"],
        commitments=normalized_input["commitments"],
        sleep_window=normalized_input["sleep_window"],
        max_daily_hours=normalized_input["max_daily_hours"],
        workday_start=normalized_input["workday_start"],
        workday_end=normalized_input["workday_end"],
        slot_step=normalized_input["slot_step"],
        buffer_hours=normalized_input["buffer_hours"],
    )

    return _build_pipeline_result(
        normalized_input=normalized_input,
        optimization=optimization,
    )


def _normalize_pipeline_input(payload: PipelineInput) -> dict[str, Any]:
    """Fill in defaults and fail early on malformed input."""

    tasks = cast(list[Task], payload.get("tasks", []))
    commitments = cast(list[Commitment], payload.get("commitments", []))
    sleep_window = cast(SleepWindow, payload.get("sleep_window", DEFAULT_SLEEP_WINDOW))
    preferences = cast(SchedulerPreferences, payload.get("preferences", {}))

    _validate_tasks(tasks)
    _validate_commitments(commitments)
    _validate_sleep_window(sleep_window)
    _validate_preferences(preferences)

    max_daily_hours = float(
        preferences.get("max_daily_hours", payload.get("max_daily_hours", 8.0))
    )
    workday_start = float(
        preferences.get("preferred_study_start", payload.get("workday_start", 7.0))
    )
    workday_end = float(
        preferences.get("preferred_study_end", payload.get("workday_end", 22.0))
    )
    slot_step = float(preferences.get("slot_step", payload.get("slot_step", 0.5)))
    buffer_hours = float(
        preferences.get("buffer_hours", payload.get("buffer_hours", 1.0))
    )

    return {
        "tasks": tasks,
        "commitments": commitments,
        "sleep_window": sleep_window,
        "preferences": dict(preferences),
        "max_daily_hours": max_daily_hours,
        "workday_start": workday_start,
        "workday_end": workday_end,
        "slot_step": slot_step,
        "buffer_hours": buffer_hours,
    }


def _build_pipeline_result(
    *,
    normalized_input: dict[str, Any],
    optimization: OptimizationResult,
) -> PipelineResult:
    """Create a predictable response object for downstream layers."""

    burnout_assessment = compute_burnout_score(
        optimization["scheduled_tasks"],
        normalized_input["tasks"],
        commitments=normalized_input["commitments"],
        unscheduled_tasks=optimization["unscheduled_tasks"],
        max_daily_hours=normalized_input["max_daily_hours"],
        weekly_hours_threshold=float(
            normalized_input["preferences"].get("weekly_hours_threshold", 50.0)
        ),
        late_night_cutoff=float(
            normalized_input["preferences"].get("late_night_cutoff", 23.0)
        ),
        max_consecutive_blocks=int(
            normalized_input["preferences"].get("max_consecutive_blocks", 3)
        ),
        min_breaks_per_day=int(
            normalized_input["preferences"].get("min_breaks_per_day", 1)
        ),
        deadline_cluster_days=int(
            normalized_input["preferences"].get("deadline_cluster_days", 2)
        ),
    )

    return {
        "original_tasks": list(normalized_input["tasks"]),
        "optimized_schedule": optimization["scheduled_tasks"],
        "unscheduled_tasks": optimization["unscheduled_tasks"],
        "metadata": {
            "scheduled_task_count": len(optimization["scheduled_tasks"]),
            "unscheduled_task_count": len(optimization["unscheduled_tasks"]),
            "sleep_window": normalized_input["sleep_window"],
            "scheduler_settings": {
                "max_daily_hours": normalized_input["max_daily_hours"],
                "workday_start": normalized_input["workday_start"],
                "workday_end": normalized_input["workday_end"],
                "slot_step": normalized_input["slot_step"],
                "buffer_hours": normalized_input["buffer_hours"],
            },
            "preferences": normalized_input["preferences"],
            "schedule_quality": _build_schedule_quality_metrics(
                scheduled_tasks=optimization["scheduled_tasks"],
                unscheduled_tasks=optimization["unscheduled_tasks"],
                sleep_window=normalized_input["sleep_window"],
                max_daily_hours=normalized_input["max_daily_hours"],
            ),
            "burnout_score": burnout_assessment["score"],
            "burnout_level": burnout_assessment["level"],
            "burnout_reasons": burnout_assessment["reasons"],
            "burnout_metrics": burnout_assessment["metrics"],
            "insights": list(burnout_assessment["reasons"]),
        },
    }


def _validate_tasks(tasks: list[Task]) -> None:
    """Check the minimum fields the optimizer depends on."""

    for index, task in enumerate(tasks, start=1):
        if not task.get("title"):
            raise ValueError(f"Task #{index} is missing a title.")
        if float(task["duration"]) <= 0:
            raise ValueError(f"Task '{task['title']}' must have a positive duration.")
        if "deadline_day" not in task:
            raise ValueError(f"Task '{task['title']}' is missing a deadline_day.")


def _validate_commitments(commitments: list[Commitment]) -> None:
    """Check fixed blocks before the scheduler works around them."""

    for index, commitment in enumerate(commitments, start=1):
        if not commitment.get("title"):
            raise ValueError(f"Commitment #{index} is missing a title.")
        if float(commitment["start"]) >= float(commitment["end"]):
            raise ValueError(
                f"Commitment '{commitment['title']}' must end after it starts."
            )


def _validate_sleep_window(sleep_window: SleepWindow) -> None:
    """Make sure sleep hours stay within a single 24-hour clock."""

    start = float(sleep_window["start"])
    end = float(sleep_window["end"])

    if not 0 <= start <= 24:
        raise ValueError("sleep_window start must be between 0 and 24.")
    if not 0 <= end <= 24:
        raise ValueError("sleep_window end must be between 0 and 24.")


def _validate_preferences(preferences: SchedulerPreferences) -> None:
    """Validate optional scheduler tuning values.

    Preferences are optional, but when they are supplied we validate them here
    so the optimizer receives a predictable configuration.
    """

    max_daily_hours = preferences.get("max_daily_hours")
    if max_daily_hours is not None and float(max_daily_hours) <= 0:
        raise ValueError("preferences.max_daily_hours must be greater than 0.")

    preferred_study_start = preferences.get("preferred_study_start")
    preferred_study_end = preferences.get("preferred_study_end")

    if preferred_study_start is not None and not 0 <= float(preferred_study_start) <= 24:
        raise ValueError("preferences.preferred_study_start must be between 0 and 24.")
    if preferred_study_end is not None and not 0 <= float(preferred_study_end) <= 24:
        raise ValueError("preferences.preferred_study_end must be between 0 and 24.")
    if (
        preferred_study_start is not None
        and preferred_study_end is not None
        and float(preferred_study_start) >= float(preferred_study_end)
    ):
        raise ValueError(
            "preferences.preferred_study_start must be earlier than "
            "preferences.preferred_study_end."
        )

    slot_step = preferences.get("slot_step")
    if slot_step is not None and float(slot_step) <= 0:
        raise ValueError("preferences.slot_step must be greater than 0.")

    buffer_hours = preferences.get("buffer_hours")
    if buffer_hours is not None and float(buffer_hours) < 0:
        raise ValueError("preferences.buffer_hours cannot be negative.")

    weekly_hours_threshold = preferences.get("weekly_hours_threshold")
    if weekly_hours_threshold is not None and float(weekly_hours_threshold) <= 0:
        raise ValueError("preferences.weekly_hours_threshold must be greater than 0.")

    late_night_cutoff = preferences.get("late_night_cutoff")
    if late_night_cutoff is not None and not 0 <= float(late_night_cutoff) <= 24:
        raise ValueError("preferences.late_night_cutoff must be between 0 and 24.")

    max_consecutive_blocks = preferences.get("max_consecutive_blocks")
    if max_consecutive_blocks is not None and int(max_consecutive_blocks) < 1:
        raise ValueError("preferences.max_consecutive_blocks must be at least 1.")

    min_breaks_per_day = preferences.get("min_breaks_per_day")
    if min_breaks_per_day is not None and int(min_breaks_per_day) < 0:
        raise ValueError("preferences.min_breaks_per_day cannot be negative.")

    deadline_cluster_days = preferences.get("deadline_cluster_days")
    if deadline_cluster_days is not None and int(deadline_cluster_days) < 1:
        raise ValueError("preferences.deadline_cluster_days must be at least 1.")


def _build_schedule_quality_metrics(
    *,
    scheduled_tasks: list[ScheduledTask],
    unscheduled_tasks: list[Task],
    sleep_window: SleepWindow,
    max_daily_hours: float,
) -> dict[str, Any]:
    """Summarize the schedule in a frontend-friendly shape.

    These metrics stay scheduler-focused. They do not replace burnout scoring,
    but they give the rest of the project a compact summary of how the planned
    workload is distributed.
    """

    ordered_days = sorted(DAY_ORDER, key=DAY_ORDER.get)
    daily_load_hours = {
        day: round(
            sum(task["end"] - task["start"] for task in scheduled_tasks if task["day"] == day),
            2,
        )
        for day in ordered_days
    }
    total_scheduled_hours = round(sum(daily_load_hours.values()), 2)
    unscheduled_hours = round(sum(task["duration"] for task in unscheduled_tasks), 2)
    heavy_day_threshold = round(max_daily_hours * 0.75, 2)
    heavy_days = [day for day, hours in daily_load_hours.items() if hours >= heavy_day_threshold]
    split_task_count = _count_split_tasks(scheduled_tasks)
    earliest_start = (
        min(task["start"] for task in scheduled_tasks) if scheduled_tasks else None
    )
    latest_end = max(task["end"] for task in scheduled_tasks) if scheduled_tasks else None

    return {
        "daily_load_hours": daily_load_hours,
        "total_scheduled_hours": total_scheduled_hours,
        "unscheduled_hours": unscheduled_hours,
        "heavy_day_threshold": heavy_day_threshold,
        "heavy_days": heavy_days,
        "split_task_count": split_task_count,
        "scheduled_day_count": sum(1 for hours in daily_load_hours.values() if hours > 0),
        "earliest_scheduled_start": earliest_start,
        "latest_scheduled_end": latest_end,
        "sleep_window": sleep_window,
    }


def _count_split_tasks(scheduled_tasks: list[ScheduledTask]) -> int:
    """Count how many original tasks were split into multiple scheduled chunks."""

    task_occurrences: dict[str, int] = {}
    for task in scheduled_tasks:
        task_occurrences[task["title"]] = task_occurrences.get(task["title"], 0) + 1

    return sum(1 for count in task_occurrences.values() if count > 1)
