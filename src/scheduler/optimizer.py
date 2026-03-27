"""Heuristic schedule optimizer for student tasks.

The project README describes a constraint-aware optimizer that:
- respects fixed commitments
- keeps work outside the user's sleep window
- tries to reduce workload clustering

This module provides a clean first implementation of that idea using
simple, understandable heuristics instead of a heavyweight solver.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):
    from typing_extensions import TypedDict
else:  # pragma: no cover - stdlib path on Python 3.12+
    from typing import TypedDict

from src.scheduler.constraints import (
    DAY_ORDER,
    Commitment,
    DayName,
    ScheduledTask,
    SleepWindow,
    Task,
    can_schedule_task,
    get_day_load,
)


DEFAULT_WORKDAY_START = 7.0
DEFAULT_WORKDAY_END = 22.0
DEFAULT_SLOT_STEP = 0.5
DEFAULT_BUFFER_HOURS = 1.0
DEFAULT_MAX_DAILY_HOURS = 8.0


class OptimizationResult(TypedDict):
    """Return both the placed tasks and anything the optimizer could not fit."""

    scheduled_tasks: list[ScheduledTask]
    unscheduled_tasks: list[Task]


def optimize_schedule(
    tasks: list[Task],
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    *,
    max_daily_hours: float = DEFAULT_MAX_DAILY_HOURS,
    workday_start: float = DEFAULT_WORKDAY_START,
    workday_end: float = DEFAULT_WORKDAY_END,
    slot_step: float = DEFAULT_SLOT_STEP,
    buffer_hours: float = DEFAULT_BUFFER_HOURS,
) -> OptimizationResult:
    """Build a healthier task plan around the user's fixed schedule.

    Strategy:
    1. Schedule urgent and longer tasks first so hard-to-place work gets priority.
    2. Search each day in deadline order.
    3. Prefer slots on lighter days to avoid stacking too much work together.
    4. Leave tasks unscheduled when no valid slot exists.

    The function intentionally returns unscheduled tasks rather than forcing an
    invalid plan. That keeps downstream burnout analysis honest.
    """

    if slot_step <= 0:
        raise ValueError("slot_step must be greater than 0")
    if workday_start >= workday_end:
        raise ValueError("workday_start must be earlier than workday_end")

    scheduled_tasks: list[ScheduledTask] = []
    unscheduled_tasks: list[Task] = []

    for task in _sort_tasks_for_scheduling(tasks):
        placements = _schedule_task(
            task=task,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=scheduled_tasks,
            max_daily_hours=max_daily_hours,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
            buffer_hours=buffer_hours,
        )

        if placements is None:
            unscheduled_tasks.append(task)
            continue

        scheduled_tasks.extend(placements)

    scheduled_tasks.sort(
        key=lambda item: (DAY_ORDER[item["day"]], item["start"], item["title"])
    )

    return {
        "scheduled_tasks": scheduled_tasks,
        "unscheduled_tasks": unscheduled_tasks,
    }


def _schedule_task(
    task: Task,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask],
    *,
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
    buffer_hours: float,
) -> list[ScheduledTask] | None:
    """Place a task in one block when possible, otherwise try split placement.

    Keeping single-block placement as the first choice preserves the original
    optimizer behavior. Splitting is used only as a fallback for long tasks
    that cannot fit into one continuous slot before the deadline.
    """

    placement = _find_best_slot(
        task=task,
        commitments=commitments,
        sleep_window=sleep_window,
        scheduled_tasks=scheduled_tasks,
        max_daily_hours=max_daily_hours,
        workday_start=workday_start,
        workday_end=workday_end,
        slot_step=slot_step,
        buffer_hours=buffer_hours,
    )
    if placement is not None:
        return [placement]

    return _find_split_slots(
        task=task,
        commitments=commitments,
        sleep_window=sleep_window,
        scheduled_tasks=scheduled_tasks,
        max_daily_hours=max_daily_hours,
        workday_start=workday_start,
        workday_end=workday_end,
        slot_step=slot_step,
        buffer_hours=buffer_hours,
    )


def _sort_tasks_for_scheduling(tasks: list[Task]) -> list[Task]:
    """Schedule the hardest tasks first.

    Earlier deadlines come first. For ties, longer tasks go earlier because
    they are usually more difficult to place later in the process.
    """

    return sorted(
        tasks,
        key=lambda task: (DAY_ORDER[task["deadline_day"]], -task["duration"], task["title"]),
    )


def _find_best_slot(
    task: Task,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask],
    *,
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
    buffer_hours: float,
) -> ScheduledTask | None:
    """Search for the best available slot for a single task.

    We score candidate slots instead of taking the first legal one.
    That helps spread work across the week and leaves some breathing room
    around existing commitments when possible.
    """

    best_candidate: ScheduledTask | None = None
    best_score: tuple[float, float, float, int] | None = None

    for day in _days_through_deadline(task["deadline_day"]):
        day_candidates = _generate_candidate_starts(
            task_duration=task["duration"],
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
        )

        for start in day_candidates:
            if not can_schedule_task(
                task=task,
                day=day,
                start=start,
                commitments=commitments,
                sleep_window=sleep_window,
                scheduled_tasks=scheduled_tasks,
                max_daily_hours=max_daily_hours,
            ):
                continue

            end = start + task["duration"]
            candidate = {
                "title": task["title"],
                "day": day,
                "start": start,
                "end": end,
            }
            score = _score_candidate_slot(
                candidate=candidate,
                commitments=commitments,
                scheduled_tasks=scheduled_tasks,
                buffer_hours=buffer_hours,
            )

            if best_score is None or score < best_score:
                best_candidate = candidate
                best_score = score

    return best_candidate


def _find_split_slots(
    task: Task,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask],
    *,
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
    buffer_hours: float,
) -> list[ScheduledTask] | None:
    """Try to place a task across multiple chunks before its deadline.

    This helper is transactional: if the full task duration cannot be placed,
    it returns ``None`` and commits nothing. That keeps the schedule honest and
    avoids half-scheduling a task without surfacing the failure.
    """

    remaining_duration = task["duration"]
    staged_tasks = list(scheduled_tasks)
    split_placements: list[ScheduledTask] = []

    while remaining_duration > 1e-9:
        chunk = _find_best_chunk(
            task=task,
            remaining_duration=remaining_duration,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=staged_tasks,
            max_daily_hours=max_daily_hours,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
            buffer_hours=buffer_hours,
        )
        if chunk is None:
            return None

        split_placements.append(chunk)
        staged_tasks.append(chunk)
        remaining_duration = round(remaining_duration - (chunk["end"] - chunk["start"]), 6)

    return split_placements


def _find_best_chunk(
    task: Task,
    remaining_duration: float,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask],
    *,
    max_daily_hours: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
    buffer_hours: float,
) -> ScheduledTask | None:
    """Find the best next chunk for a task that is being split.

    We prefer larger valid chunks so the schedule does not fragment more than
    necessary, while still keeping the existing preference for lighter days and
    cleaner spacing around nearby blocks.
    """

    best_candidate: ScheduledTask | None = None
    best_score: tuple[float, float, float, float, int] | None = None

    for day in _days_through_deadline(task["deadline_day"]):
        for start in _generate_candidate_starts(
            task_duration=slot_step,
            workday_start=workday_start,
            workday_end=workday_end,
            slot_step=slot_step,
        ):
            max_chunk_duration = _get_max_chunk_duration(
                day=day,
                start=start,
                remaining_duration=remaining_duration,
                task=task,
                commitments=commitments,
                sleep_window=sleep_window,
                scheduled_tasks=scheduled_tasks,
                max_daily_hours=max_daily_hours,
                workday_end=workday_end,
                slot_step=slot_step,
            )
            if max_chunk_duration < slot_step:
                continue

            candidate = {
                "title": task["title"],
                "day": day,
                "start": start,
                "end": round(start + max_chunk_duration, 2),
            }
            base_score = _score_candidate_slot(
                candidate=candidate,
                commitments=commitments,
                scheduled_tasks=scheduled_tasks,
                buffer_hours=buffer_hours,
            )
            score = (
                base_score[0],
                base_score[1],
                -max_chunk_duration,
                base_score[2],
                base_score[3],
            )

            if best_score is None or score < best_score:
                best_candidate = candidate
                best_score = score

    return best_candidate


def _get_max_chunk_duration(
    *,
    day: DayName,
    start: float,
    remaining_duration: float,
    task: Task,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask],
    max_daily_hours: float,
    workday_end: float,
    slot_step: float,
) -> float:
    """Measure how much of a task can fit continuously from a given start."""

    best_duration = 0.0
    candidate_duration = slot_step
    limit = min(remaining_duration, workday_end - start)

    while candidate_duration <= limit + 1e-9:
        candidate_task: Task = {
            "title": task["title"],
            "duration": round(candidate_duration, 2),
            "deadline_day": task["deadline_day"],
        }
        if not can_schedule_task(
            task=candidate_task,
            day=day,
            start=start,
            commitments=commitments,
            sleep_window=sleep_window,
            scheduled_tasks=scheduled_tasks,
            max_daily_hours=max_daily_hours,
        ):
            break

        best_duration = round(candidate_duration, 2)
        candidate_duration += slot_step

    return best_duration


def _days_through_deadline(deadline_day: DayName) -> list[DayName]:
    """Return all valid scheduling days up to and including the deadline."""

    ordered_days = sorted(DAY_ORDER, key=DAY_ORDER.get)
    deadline_index = DAY_ORDER[deadline_day]
    return [day for day in ordered_days if DAY_ORDER[day] <= deadline_index]


def _generate_candidate_starts(
    *,
    task_duration: float,
    workday_start: float,
    workday_end: float,
    slot_step: float,
) -> list[float]:
    """Create candidate start times on a fixed time grid."""

    last_start = workday_end - task_duration
    if last_start < workday_start:
        return []

    starts: list[float] = []
    current = workday_start
    epsilon = 1e-9

    while current <= last_start + epsilon:
        starts.append(round(current, 2))
        current += slot_step

    return starts


def _score_candidate_slot(
    candidate: ScheduledTask,
    commitments: list[Commitment],
    scheduled_tasks: list[ScheduledTask],
    *,
    buffer_hours: float,
) -> tuple[float, float, float, int]:
    """Lower scores are better.

    Score order:
    1. Current load on that day, so we prefer lighter days.
    2. Penalty for being too close to nearby commitments/tasks.
    3. Start time, so earlier valid slots win when all else is equal.
    4. Day index, which naturally prefers earlier days before deadlines.
    """

    day = candidate["day"]
    day_load = _get_total_day_load(
        day=day,
        commitments=commitments,
        scheduled_tasks=scheduled_tasks,
    )
    proximity_penalty = _calculate_proximity_penalty(
        candidate=candidate,
        commitments=commitments,
        scheduled_tasks=scheduled_tasks,
        buffer_hours=buffer_hours,
    )

    return (
        round(day_load, 2),
        round(proximity_penalty, 2),
        candidate["start"],
        DAY_ORDER[day],
    )


def _get_total_day_load(
    *,
    day: DayName,
    commitments: list[Commitment],
    scheduled_tasks: list[ScheduledTask],
) -> float:
    """Measure a day's full workload, including fixed commitments.

    Burnout and schedule quality depend on the student's total day pressure,
    not only the task hours placed by the optimizer. Using the combined load
    helps the optimizer avoid pushing tasks onto days that already contain
    long class or work blocks.
    """

    commitment_hours = sum(
        commitment["end"] - commitment["start"]
        for commitment in commitments
        if commitment["day"] == day
    )
    return round(commitment_hours + get_day_load(day, scheduled_tasks), 2)


def _calculate_proximity_penalty(
    candidate: ScheduledTask,
    commitments: list[Commitment],
    scheduled_tasks: list[ScheduledTask],
    *,
    buffer_hours: float,
) -> float:
    """Discourage placing tasks tightly against other blocks.

    This is a soft preference, not a hard rule. A packed day can still be used
    if there is no better option, but the optimizer will choose roomier slots
    first when it has the choice.
    """

    if buffer_hours <= 0:
        return 0.0

    same_day_blocks = [
        block
        for block in [*commitments, *scheduled_tasks]
        if block["day"] == candidate["day"]
    ]

    penalty = 0.0
    for block in same_day_blocks:
        gap_before = abs(candidate["start"] - block["end"])
        gap_after = abs(block["start"] - candidate["end"])
        closest_gap = min(gap_before, gap_after)

        if closest_gap < buffer_hours:
            penalty += buffer_hours - closest_gap

    return penalty
