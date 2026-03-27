"""Shared burnout scoring thresholds and rule weights."""

RULES = {
    "DAILY_HOURS_THRESHOLD": 8,
    "MAX_CONSECUTIVE_BLOCKS": 3,
    "LATE_NIGHT_CUTOFF": 23,  # 11 PM
    "MIN_BREAKS_PER_DAY": 1,
    "DEADLINE_CLUSTER_DAYS": 2,
    "WEEKLY_HOURS_THRESHOLD": 50,
}

WEIGHTS = {
    "daily_overload": 15,
    "consecutive_blocks": 10,
    "no_breaks": 10,
    "deadline_cluster": 15,
    "late_night": 10,
    "no_light_day": 15,
    "weekly_overload": 15,
    "context_switching": 10,
}
