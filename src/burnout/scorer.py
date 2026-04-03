"""Reusable burnout scoring utilities for the current app schema."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.scheduler.constraints import DAY_ORDER

from src.burnout.rules import RULES, WEIGHTS


DAY_NAMES = sorted(DAY_ORDER, key=DAY_ORDER.get)


def compute_burnout_score(
    schedule: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    *,
    commitments: list[dict[str, Any]] | None = None,
    unscheduled_tasks: list[dict[str, Any]] | None = None,
    max_daily_hours: float | None = None,
    weekly_hours_threshold: float | None = None,
    late_night_cutoff: float | None = None,
    max_consecutive_blocks: int | None = None,
    min_breaks_per_day: int | None = None,
    deadline_cluster_days: int | None = None,
) -> dict[str, Any]:
    """Compute burnout score against the app's current schedule/task schema."""

    commitments = commitments or []
    unscheduled_tasks = unscheduled_tasks or []
    effective_daily_limit = float(
        RULES["DAILY_HOURS_THRESHOLD"] if max_daily_hours is None else max_daily_hours
    )
    effective_weekly_limit = float(
        RULES["WEEKLY_HOURS_THRESHOLD"]
        if weekly_hours_threshold is None
        else weekly_hours_threshold
    )
    effective_late_night_cutoff = float(
        RULES["LATE_NIGHT_CUTOFF"] if late_night_cutoff is None else late_night_cutoff
    )
    effective_max_consecutive_blocks = int(
        RULES["MAX_CONSECUTIVE_BLOCKS"]
        if max_consecutive_blocks is None
        else max_consecutive_blocks
    )
    effective_min_breaks_per_day = int(
        RULES["MIN_BREAKS_PER_DAY"] if min_breaks_per_day is None else min_breaks_per_day
    )
    effective_deadline_cluster_days = int(
        RULES["DEADLINE_CLUSTER_DAYS"]
        if deadline_cluster_days is None
        else deadline_cluster_days
    )

    block_map = _group_blocks_by_day(commitments, schedule)
    score = 0
    reasons: list[tuple[int, str]] = []

    daily_hours = calculate_daily_hours(block_map)
    weekly = weekly_hours(block_map)

    def add_reason(points: int, text: str) -> None:
        nonlocal score
        score += points
        reasons.append((points, text))

    # Daily overload
    overloaded_days = [day for day, hours in daily_hours.items() if hours > effective_daily_limit]
    if overloaded_days:
        highest_day = max(overloaded_days, key=lambda day: daily_hours[day])
        add_reason(
            WEIGHTS["daily_overload"],
            (
                f"{', '.join(overloaded_days)} exceed the daily safe workload. "
                f"{highest_day} reaches {daily_hours[highest_day]:.1f} hours."
            ),
        )

    # Weekly overload
    if weekly > effective_weekly_limit:
        add_reason(
            WEIGHTS["weekly_overload"],
            f"Total weekly load is {weekly:.1f} hours, above a healthy limit.",
        )

    # Late night
    late_night_blocks = detect_late_night(block_map, cutoff=effective_late_night_cutoff)
    if late_night_blocks:
        add_reason(WEIGHTS["late_night"], f"{late_night_blocks} blocks run late at night.")

    # Consecutive work blocks
    max_consecutive_heavy = max(
        (_count_consecutive_heavy_blocks(block_map[day]) for day in DAY_NAMES),
        default=0,
    )
    if max_consecutive_heavy > effective_max_consecutive_blocks:
        add_reason(
            WEIGHTS["consecutive_blocks"],
            f"{max_consecutive_heavy} heavy blocks are chained with little recovery.",
        )

    # Lack of breaks
    breakless_days = [
        day
        for day in DAY_NAMES
        if daily_hours[day] >= 7.0 and count_breaks(block_map[day]) < effective_min_breaks_per_day
    ]
    if breakless_days:
        add_reason(
            WEIGHTS["no_breaks"],
            f"{', '.join(breakless_days)} are long days without a meaningful break.",
        )

    # No light day
    light_days = [day for day, hours in daily_hours.items() if hours <= 2.0]
    if not light_days:
        add_reason(WEIGHTS["no_light_day"], "There is no light recovery day in this week.")

    # Deadline clustering
    clustered_deadlines = detect_deadline_clusters(
        tasks,
        deadline_cluster_days=effective_deadline_cluster_days,
    )
    if clustered_deadlines >= 3:
        add_reason(
            WEIGHTS["deadline_cluster"],
            f"{clustered_deadlines} deadlines are clustered inside a 48-hour window.",
        )

    # Context switching
    context_switch_days = [day for day in DAY_NAMES if len(block_map[day]) >= 6]
    if context_switch_days:
        add_reason(
            WEIGHTS["context_switching"],
            f"{', '.join(context_switch_days)} have high context switching with many short blocks.",
        )

    # Unscheduled tasks are app-specific pressure, separate from the original rules set.
    if unscheduled_tasks:
        add_reason(
            10,
            f"{len(unscheduled_tasks)} task(s) could not be scheduled before deadlines.",
        )

    score = min(score, 100)
    top_reasons = [text for _, text in sorted(reasons, key=lambda item: item[0], reverse=True)[:3]]

    return {
        "score": score,
        "level": classify_score(score),
        "reasons": top_reasons or ["Workload looks balanced with manageable pressure."],
        "metrics": {
            "daily_hours": daily_hours,
            "total_hours": weekly,
            "heavy_day_threshold": round(effective_daily_limit * 0.75, 2),
            "heavy_days": [
                day for day, hours in daily_hours.items() if hours >= round(effective_daily_limit * 0.75, 2)
            ],
            "overloaded_days": overloaded_days,
            "late_night_blocks": late_night_blocks,
            "context_switch_days": context_switch_days,
            "max_consecutive_heavy": max_consecutive_heavy,
            "unscheduled_count": len(unscheduled_tasks),
            "weekly_hours_threshold": effective_weekly_limit,
            "late_night_cutoff": effective_late_night_cutoff,
            "max_consecutive_blocks": effective_max_consecutive_blocks,
            "min_breaks_per_day": effective_min_breaks_per_day,
            "deadline_cluster_days": effective_deadline_cluster_days,
        },
    }


def calculate_daily_hours(
    block_map: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    """Sum total hours per day across commitments and scheduled tasks."""

    return {
        day: round(sum(block["end"] - block["start"] for block in block_map[day]), 2)
        for day in DAY_NAMES
    }


def _count_consecutive_heavy_blocks(blocks: list[dict[str, Any]]) -> int:
    """Find longest sequence of hour-long blocks with minimal recovery gaps."""

    longest = 0
    current = 0
    previous_end = None

    for block in blocks:
        duration = block["end"] - block["start"]
        if duration < 1.0:
            current = 0
            previous_end = block["end"]
            continue

        if previous_end is None:
            current = 1
        else:
            gap = block["start"] - previous_end
            current = current + 1 if gap <= 0.25 else 1

        previous_end = block["end"]
        longest = max(longest, current)

    return longest


def detect_late_night(
    block_map: dict[str, list[dict[str, Any]]],
    *,
    cutoff: float,
) -> int:
    """Count blocks that cross the late-night cutoff."""

    return sum(
        1
        for day in DAY_NAMES
        for block in block_map[day]
        if block["end"] >= cutoff
    )


def detect_deadline_clusters(
    tasks: list[dict[str, Any]],
    *,
    deadline_cluster_days: int,
) -> int:
    """Return highest number of deadlines found in the configured day window."""

    counts: dict[int, int] = defaultdict(int)
    for task in tasks:
        deadline_day = task.get("deadline_day")
        if deadline_day in DAY_ORDER:
            counts[DAY_ORDER[deadline_day]] += 1

    best = 0
    window_size = deadline_cluster_days + 1
    for start in range(len(DAY_NAMES)):
        window_total = 0
        for offset in range(window_size):
            window_total += counts.get(start + offset, 0)
        best = max(best, window_total)

    return best


def count_breaks(day_schedule: list[dict[str, Any]]) -> int:
    """Count 30-minute recovery gaps between consecutive blocks."""

    if len(day_schedule) < 2:
        return 1

    breaks = 0
    for index in range(len(day_schedule) - 1):
        gap = day_schedule[index + 1]["start"] - day_schedule[index]["end"]
        if gap >= 0.5:
            breaks += 1

    return breaks


def weekly_hours(block_map: dict[str, list[dict[str, Any]]]) -> float:
    """Sum weekly hours across all days."""

    return round(
        sum(block["end"] - block["start"] for day in DAY_NAMES for block in block_map[day]),
        2,
    )


def classify_score(score):
    if score < 30:
        return "Low"
    if score < 60:
        return "Moderate"
    return "High"


def _group_blocks_by_day(
    commitments: list[dict[str, Any]],
    scheduled_tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Combine commitments and scheduled tasks into ordered day buckets."""

    day_map: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for commitment in commitments:
        day = commitment.get("day", "Mon")
        if day not in DAY_ORDER:
            continue
        day_map[day].append(
            {
                "title": str(commitment["title"]),
                "start": float(commitment["start"]),
                "end": float(commitment["end"]),
            }
        )

    for task in scheduled_tasks:
        day = task.get("day", "Mon")
        if day not in DAY_ORDER:
            continue
        day_map[day].append(
            {
                "title": str(task["title"]),
                "start": float(task["start"]),
                "end": float(task["end"]),
            }
        )

    for day in DAY_NAMES:
        day_map[day].sort(key=lambda block: (block["start"], block["end"], block["title"]))

    return day_map
