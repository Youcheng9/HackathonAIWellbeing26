# Scheduler Contract

This document describes the scheduler and optimizer input/output contract for
frontend and backend integration. It is separate from the main project README
so scheduler-specific details can evolve without changing the project overview.

## Purpose

The scheduler is responsible for:
- respecting fixed commitments
- keeping work outside the sleep window
- placing tasks on or before their deadlines
- staying within daily workload limits
- splitting long tasks across multiple valid chunks when needed
- returning unscheduled tasks when no valid slot exists

## Input Payload

```json
{
  "commitments": [
    {
      "title": "CS 101 Lecture",
      "day": "Mon",
      "start": 9.0,
      "end": 10.5
    }
  ],
  "tasks": [
    {
      "title": "History Essay",
      "duration": 2.0,
      "deadline_day": "Tue"
    }
  ],
  "sleep_window": {
    "start": 23.0,
    "end": 7.0
  },
  "preferences": {
    "max_daily_hours": 8.0,
    "preferred_study_start": 7.0,
    "preferred_study_end": 22.0,
    "slot_step": 0.5,
    "buffer_hours": 1.0
  }
}
```

## Input Fields

### `commitments`

Fixed time blocks such as:
- classes
- work shifts
- labs
- meetings

Each commitment contains:
- `title`: string
- `day`: `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, or `Sun`
- `start`: float in 24-hour decimal format
- `end`: float in 24-hour decimal format

Example:
- `13.5` means `1:30 PM`

### `tasks`

Assignments or study work to be scheduled.

Each task contains:
- `title`: string
- `duration`: float hours required
- `deadline_day`: latest valid day for scheduling

### `sleep_window`

Time range when tasks must not be scheduled.

Fields:
- `start`: float between `0` and `24`
- `end`: float between `0` and `24`

This supports sleep windows that cross midnight, such as:
- `23.0` to `7.0`

### `preferences`

Optional user-controlled settings.

Fields:
- `max_daily_hours`: maximum task hours per day
- `preferred_study_start`: earliest preferred study start
- `preferred_study_end`: latest preferred study end
- `slot_step`: time-grid step used when searching for valid starts
- `buffer_hours`: preferred spacing around nearby blocks

If `preferences` is omitted, the scheduler uses default values.

## Output Payload

```json
{
  "original_tasks": [
    {
      "title": "History Essay",
      "duration": 2.0,
      "deadline_day": "Tue"
    }
  ],
  "optimized_schedule": [
    {
      "title": "History Essay",
      "day": "Tue",
      "start": 7.0,
      "end": 9.0
    }
  ],
  "unscheduled_tasks": [],
  "metadata": {
    "scheduled_task_count": 1,
    "unscheduled_task_count": 0,
    "sleep_window": {
      "start": 23.0,
      "end": 7.0
    },
    "scheduler_settings": {
      "max_daily_hours": 8.0,
      "workday_start": 7.0,
      "workday_end": 22.0,
      "slot_step": 0.5,
      "buffer_hours": 1.0
    },
    "preferences": {
      "max_daily_hours": 8.0,
      "preferred_study_start": 7.0,
      "preferred_study_end": 22.0,
      "slot_step": 0.5,
      "buffer_hours": 1.0
    },
    "schedule_quality": {
      "daily_load_hours": {
        "Mon": 0.0,
        "Tue": 2.0,
        "Wed": 0.0,
        "Thu": 0.0,
        "Fri": 0.0,
        "Sat": 0.0,
        "Sun": 0.0
      },
      "total_scheduled_hours": 2.0,
      "unscheduled_hours": 0.0,
      "heavy_day_threshold": 6.0,
      "heavy_days": [],
      "split_task_count": 0,
      "scheduled_day_count": 1,
      "earliest_scheduled_start": 7.0,
      "latest_scheduled_end": 9.0,
      "sleep_window": {
        "start": 23.0,
        "end": 7.0
      }
    },
    "burnout_score": 25,
    "burnout_level": "Low",
    "burnout_reasons": [
      "Workload looks balanced with manageable pressure."
    ],
    "burnout_metrics": {
      "daily_hours": {
        "Mon": 2.0,
        "Tue": 0.0,
        "Wed": 0.0,
        "Thu": 0.0,
        "Fri": 0.0,
        "Sat": 0.0,
        "Sun": 0.0
      },
      "total_hours": 2.0,
      "heavy_day_threshold": 6.0,
      "heavy_days": [],
      "overloaded_days": [],
      "late_night_blocks": 0,
      "context_switch_days": [],
      "max_consecutive_heavy": 1,
      "unscheduled_count": 0,
      "weekly_hours_threshold": 50.0,
      "late_night_cutoff": 23.0,
      "max_consecutive_blocks": 3,
      "min_breaks_per_day": 1,
      "deadline_cluster_days": 2
    },
    "insights": [
      "Workload looks balanced with manageable pressure."
    ]
  }
}
```

## Output Fields

### `original_tasks`

The raw input task list for comparison and UI display.

### `optimized_schedule`

Tasks that were successfully placed.

Each scheduled item contains:
- `title`
- `day`
- `start`
- `end`

Important:
- A long task may appear more than once in `optimized_schedule`
- Multiple entries with the same `title` represent split chunks of one task

### `unscheduled_tasks`

Tasks the optimizer could not place without breaking constraints.

### `metadata`

Extra information for integration and future expansion.

Current fields:
- `scheduled_task_count`
- `unscheduled_task_count`
- `sleep_window`
- `scheduler_settings`
- `preferences`
- `schedule_quality`
- `burnout_score`
- `burnout_level`
- `burnout_reasons`
- `burnout_metrics`
- `insights`

### `metadata.schedule_quality`

Scheduler-focused summary metrics for the generated plan.

Current fields:
- `daily_load_hours`
- `total_scheduled_hours`
- `unscheduled_hours`
- `heavy_day_threshold`
- `heavy_days`
- `split_task_count`
- `scheduled_day_count`
- `earliest_scheduled_start`
- `latest_scheduled_end`
- `sleep_window`

## Notes For Frontend Integration

- Send JSON in the same shape as the input payload above.
- Treat `unscheduled_tasks` as a valid outcome, not an error.
- Use `metadata.scheduler_settings` to show which scheduler settings were
  applied after defaults and preferences were resolved.
- Use `metadata.preferences` to show user-selected scheduling preferences.
- Use `metadata.schedule_quality` to render daily load summaries or schedule
  health indicators in the UI.
- If a task appears multiple times in `optimized_schedule`, group those entries
  in the UI as split chunks of the same assignment.

## Current Limitations

- Burnout metadata is heuristic and currently reports the optimized plan only.
- The optimizer uses heuristics rather than a full solver.
- Split chunks currently reuse the same task title rather than adding a chunk
  label such as "Part 1" or "Part 2".
