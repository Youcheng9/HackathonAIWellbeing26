"""Shared baseline scheduling and burnout helpers.

These utilities are safe to import from API code because they do not depend on
frontend-only libraries such as Streamlit or pandas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.burnout.rules import RULES
from src.burnout.scorer import compute_burnout_score
from src.scheduler.constraints import DAY_ORDER, can_schedule_task


DAY_NAMES = sorted(DAY_ORDER, key=DAY_ORDER.get)


@dataclass
class BurnoutAssessment:
    """Frontend-friendly burnout summary."""

    score: int
    level: str
    reasons: list[str]
    metrics: dict[str, Any]


def build_baseline_schedule(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Build a naive baseline schedule that clusters work close to deadlines."""

    tasks = [dict(task) for task in payload.get("tasks", [])]
    commitments = payload.get("commitments", [])
    sleep_window = payload.get("sleep_window", {"start": 23.0, "end": 7.0})
    settings = resolve_settings(payload)

    scheduled_tasks: list[dict[str, Any]] = []
    unscheduled_tasks: list[dict[str, Any]] = []

    for task in sorted(
        tasks,
        key=lambda item: (
            DAY_ORDER.get(item.get("deadline_day", "Mon"), 0),
            item.get("duration", 0.0),
            item.get("title", ""),
        ),
    ):
        placement = _find_latest_single_slot(
            task=task,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=scheduled_tasks,
            max_daily_hours=settings["max_daily_hours"],
            workday_start=settings["workday_start"],
            workday_end=settings["workday_end"],
            slot_step=settings["slot_step"],
        )
        if placement is not None:
            scheduled_tasks.append(placement)
            continue

        split_placements = _find_latest_split_slots(
            task=task,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=scheduled_tasks,
            max_daily_hours=settings["max_daily_hours"],
            workday_start=settings["workday_start"],
            workday_end=settings["workday_end"],
            slot_step=settings["slot_step"],
        )

        if split_placements is None:
            unscheduled_tasks.append(task)
            continue
        scheduled_tasks.extend(split_placements)

    scheduled_tasks.sort(
        key=lambda item: (
            DAY_ORDER.get(item["day"], 0),
            item["start"],
            item["title"],
        )
    )

    return {
        "scheduled_tasks": scheduled_tasks,
        "unscheduled_tasks": unscheduled_tasks,
    }


def assess_burnout(
    *,
    commitments: list[dict[str, Any]],
    scheduled_tasks: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    unscheduled_tasks: list[dict[str, Any]],
    max_daily_hours: float,
    weekly_hours_threshold: float,
    late_night_cutoff: float,
    max_consecutive_blocks: int,
    min_breaks_per_day: int,
    deadline_cluster_days: int,
) -> BurnoutAssessment:
    """Score burnout risk using the shared scorer and return a UI-friendly model."""

    assessment = compute_burnout_score(
        scheduled_tasks,
        tasks,
        commitments=commitments,
        unscheduled_tasks=unscheduled_tasks,
        max_daily_hours=max_daily_hours,
        weekly_hours_threshold=weekly_hours_threshold,
        late_night_cutoff=late_night_cutoff,
        max_consecutive_blocks=max_consecutive_blocks,
        min_breaks_per_day=min_breaks_per_day,
        deadline_cluster_days=deadline_cluster_days,
    )

    return BurnoutAssessment(
        score=int(assessment["score"]),
        level=str(assessment["level"]),
        reasons=list(assessment["reasons"]),
        metrics=dict(assessment["metrics"]),
    )


def resolve_settings(payload: dict[str, Any]) -> dict[str, float]:
    """Resolve scheduler settings from payload defaults/preferences."""

    preferences = payload.get("preferences", {})
    return {
        "max_daily_hours": float(preferences.get("max_daily_hours", payload.get("max_daily_hours", 8.0))),
        "workday_start": float(
            preferences.get("preferred_study_start", payload.get("workday_start", 7.0))
        ),
        "workday_end": float(
            preferences.get("preferred_study_end", payload.get("workday_end", 22.0))
        ),
        "slot_step": float(preferences.get("slot_step", payload.get("slot_step", 0.5))),
        "weekly_hours_threshold": float(
            preferences.get("weekly_hours_threshold", RULES["WEEKLY_HOURS_THRESHOLD"])
        ),
        "late_night_cutoff": float(
            preferences.get("late_night_cutoff", RULES["LATE_NIGHT_CUTOFF"])
        ),
        "max_consecutive_blocks": float(
            preferences.get("max_consecutive_blocks", RULES["MAX_CONSECUTIVE_BLOCKS"])
        ),
        "min_breaks_per_day": float(
            preferences.get("min_breaks_per_day", RULES["MIN_BREAKS_PER_DAY"])
        ),
        "deadline_cluster_days": float(
            preferences.get("deadline_cluster_days", RULES["DEADLINE_CLUSTER_DAYS"])
        ),
    }


def _find_latest_single_slot(
    *,
    task: dict[str, Any],
    commitments: list[dict[str, Any]],
    sleep_window: dict[str, Any],
    scheduled_tasks: list[dict[str, Any]],
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
) -> dict[str, Any] | None:
    """Find latest valid contiguous slot for one task."""

    duration = float(task["duration"])
    for day in _days_to_deadline_reverse(task["deadline_day"]):
        for start in _descending_starts(
            duration=duration,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
        ):
            if can_schedule_task(
                task=task,
                day=day,
                start=start,
                commitments=commitments,
                sleep_window=sleep_window,
                scheduled_tasks=scheduled_tasks,
                max_daily_hours=max_daily_hours,
            ):
                return {
                    "title": task["title"],
                    "day": day,
                    "start": start,
                    "end": round(start + duration, 2),
                }
    return None


def _find_latest_split_slots(
    *,
    task: dict[str, Any],
    commitments: list[dict[str, Any]],
    sleep_window: dict[str, Any],
    scheduled_tasks: list[dict[str, Any]],
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
) -> list[dict[str, Any]] | None:
    """Split a task into latest possible chunks before deadline."""

    remaining = float(task["duration"])
    staged_schedule = list(scheduled_tasks)
    chunks: list[dict[str, Any]] = []

    while remaining > 1e-9:
        chunk = _find_latest_chunk(
            task=task,
            remaining_duration=remaining,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=staged_schedule,
            max_daily_hours=max_daily_hours,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
        )
        if chunk is None:
            return None

        chunks.append(chunk)
        staged_schedule.append(chunk)
        remaining = round(remaining - (chunk["end"] - chunk["start"]), 6)

    return chunks


def _find_latest_chunk(
    *,
    task: dict[str, Any],
    remaining_duration: float,
    commitments: list[dict[str, Any]],
    sleep_window: dict[str, Any],
    scheduled_tasks: list[dict[str, Any]],
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
) -> dict[str, Any] | None:
    """Find the latest valid chunk start/end for a split task."""

    for day in _days_to_deadline_reverse(task["deadline_day"]):
        for start in _descending_starts(
            duration=slot_step,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
        ):
            max_chunk = _largest_valid_chunk(
                task=task,
                day=day,
                start=start,
                remaining_duration=remaining_duration,
                commitments=commitments,
                sleep_window=sleep_window,
                scheduled_tasks=scheduled_tasks,
                max_daily_hours=max_daily_hours,
                workday_end=workday_end,
                slot_step=slot_step,
            )
            if max_chunk < slot_step:
                continue

            return {
                "title": task["title"],
                "day": day,
                "start": start,
                "end": round(start + max_chunk, 2),
            }

    return None


def _largest_valid_chunk(
    *,
    task: dict[str, Any],
    day: str,
    start: float,
    remaining_duration: float,
    commitments: list[dict[str, Any]],
    sleep_window: dict[str, Any],
    scheduled_tasks: list[dict[str, Any]],
    max_daily_hours: float,
    workday_end: float,
    slot_step: float,
) -> float:
    """Return the largest chunk duration valid at a proposed start time."""

    max_allowed = min(remaining_duration, workday_end - start)
    for duration in _descending_durations(max_allowed, slot_step):
        chunk_task = {
            "title": task["title"],
            "duration": duration,
            "deadline_day": task["deadline_day"],
        }
        if can_schedule_task(
            task=chunk_task,
            day=day,
            start=start,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=scheduled_tasks,
            max_daily_hours=max_daily_hours,
        ):
            return duration

    return 0.0


def _days_to_deadline_reverse(deadline_day: str) -> list[str]:
    """Return valid days up to deadline in reverse order."""

    deadline_index = DAY_ORDER.get(deadline_day, 0)
    valid_days = [day for day in DAY_NAMES if DAY_ORDER[day] <= deadline_index]
    return list(reversed(valid_days))


def _descending_starts(
    *,
    duration: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
) -> list[float]:
    """Create descending candidate starts for baseline scheduling."""

    last_start = workday_end - duration
    if last_start < workday_start:
        return []

    starts: list[float] = []
    current = last_start
    epsilon = 1e-9
    while current >= workday_start - epsilon:
        starts.append(round(current, 2))
        current -= slot_step
    return starts


def _descending_durations(max_duration: float, step: float) -> list[float]:
    """Return descending duration values aligned to slot step."""

    if step <= 0 or max_duration < step:
        return []

    units = int(max_duration / step + 1e-9)
    return [round(unit * step, 2) for unit in range(units, 0, -1)]
