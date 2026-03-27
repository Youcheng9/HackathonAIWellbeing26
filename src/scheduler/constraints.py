"""Basic rule checks for the scheduler."""

from __future__ import annotations
import sys
from typing import Literal

if sys.version_info < (3, 12):
    from typing_extensions import TypedDict
else:  # pragma: no cover - stdlib path on Python 3.12+
    from typing import TypedDict


DayName = Literal["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_ORDER: dict[DayName, int] = {
    "Mon": 0,
    "Tue": 1,
    "Wed": 2,
    "Thu": 3,
    "Fri": 4,
    "Sat": 5,
    "Sun": 6,
}

# -- Custom Data Structures --
class TimeBlock(TypedDict):
    day: DayName
    start: float
    end: float

class Commitment(TimeBlock):
    title: str


class Task(TypedDict):
    title: str
    duration: float
    deadline_day: DayName


class ScheduledTask(TimeBlock):
    title: str


class SleepWindow(TypedDict):
    start: float
    end: float

# -- Helper Functions --
def is_valid_time_range(start: float, end: float) -> bool:
    """Make sure a block stays within one day and has real length."""
    return 0 <= start < end <= 24


def overlaps(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    """Check whether two time ranges collide."""
    return start_a < end_b and start_b < end_a


def is_within_sleep_window(start: float, end: float, sleep_window: SleepWindow) -> bool:
    """Check whether a slot runs into the user's sleep hours."""
    sleep_start = sleep_window["start"]
    sleep_end = sleep_window["end"]

    if not is_valid_time_range(start, end):
        return True

    if sleep_start <= sleep_end:
        return overlaps(start, end, sleep_start, sleep_end)

    # Handles sleep windows that cross midnight, like 23:00 to 07:00.
    return overlaps(start, end, sleep_start, 24) or overlaps(start, end, 0, sleep_end)


def is_slot_available(
    day: DayName,
    start: float,
    end: float,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask] | None = None,
) -> bool:
    """Check whether a slot is free on that day."""
    if not is_valid_time_range(start, end):
        return False

    if is_within_sleep_window(start, end, sleep_window):
        return False

    for commitment in commitments:
        if commitment["day"] == day and overlaps(start, end, commitment["start"], commitment["end"]):
            return False

    for scheduled_task in scheduled_tasks or []:
        if scheduled_task["day"] == day and overlaps(
            start,
            end,
            scheduled_task["start"],
            scheduled_task["end"],
        ):
            return False

    return True


def meets_deadline(task: Task, day: DayName) -> bool:
    """A task is valid only if it lands on or before its deadline day."""
    return DAY_ORDER[day] <= DAY_ORDER[task["deadline_day"]]


def get_day_load(day: DayName, scheduled_tasks: list[ScheduledTask]) -> float:
    """Add up how many hours of task work are already on a day."""
    return sum(task["end"] - task["start"] for task in scheduled_tasks if task["day"] == day)


def respects_daily_workload_limit(
    day: DayName,
    start: float,
    end: float,
    scheduled_tasks: list[ScheduledTask],
    max_daily_hours: float = 8.0,
) -> bool:
    """Make sure a day does not go past the workload limit."""
    proposed_hours = end - start
    return get_day_load(day, scheduled_tasks) + proposed_hours <= max_daily_hours


def can_schedule_task(
    task: Task,
    day: DayName,
    start: float,
    commitments: list[Commitment],
    sleep_window: SleepWindow,
    scheduled_tasks: list[ScheduledTask] | None = None,
    max_daily_hours: float = 8.0,
) -> bool:
    """Bundle the main checks the optimizer cares about."""
    end = start + task["duration"]
    placed_tasks = scheduled_tasks or []

    return (
        meets_deadline(task, day)
        and is_slot_available(day, start, end, commitments, sleep_window, placed_tasks)
        and respects_daily_workload_limit(day, start, end, placed_tasks, max_daily_hours)
    )
