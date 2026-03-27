from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.scheduler.constraints import DAY_ORDER


DAY_NAMES = sorted(DAY_ORDER, key=DAY_ORDER.get)
DEADLINE_OPTIONS = ["", *DAY_NAMES]
DEFAULT_SAMPLE_PATH = Path(__file__).resolve().parents[2] / "data" / "sample_input.json"
DAY_ALIASES = {
    "mon": "Mon",
    "monday": "Mon",
    "tue": "Tue",
    "tues": "Tue",
    "tuesday": "Tue",
    "wed": "Wed",
    "wednesday": "Wed",
    "thu": "Thu",
    "thur": "Thu",
    "thurs": "Thu",
    "thursday": "Thu",
    "fri": "Fri",
    "friday": "Fri",
    "sat": "Sat",
    "saturday": "Sat",
    "sun": "Sun",
    "sunday": "Sun",
}


def load_sample_payload(path: Path | None = None) -> dict[str, Any]:
    """Read demo input data used to seed the UI."""

    sample_path = path or DEFAULT_SAMPLE_PATH
    with sample_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def render_input_panel(sample_payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Render editable input controls and return the payload on each rerun."""

    _initialize_state(sample_payload)

    title_col, action_col = st.columns([5, 1])
    with title_col:
        st.subheader("1) Input Data")
        st.caption(
            "Add fixed commitments and flexible tasks, then run burnout analysis and "
            "AI schedule rearrangement."
        )
    with action_col:
        if st.button("Reset", use_container_width=True):
            _initialize_state(sample_payload, force=True)
            if hasattr(st, "rerun"):
                st.rerun()
            else:  # pragma: no cover - legacy Streamlit compatibility
                st.experimental_rerun()

    commitments_tab, tasks_tab, settings_tab = st.tabs(
        ["Classes + Work Shifts", "Tasks + Deadlines", "Scheduler Settings"]
    )

    with commitments_tab:
        st.caption("Time format: 24-hour decimal values (e.g., 9.5 = 9:30 AM, 13.5 = 1:30 PM).")
        commitments_df = _initial_editor_frame(
            st.session_state["ui_commitments"],
            ["title", "day", "start", "end"],
            {"title": "", "day": "Mon", "start": 9.0, "end": 10.0},
        )
        edited_commitments = st.data_editor(
            commitments_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="ui_commitments_editor",
            column_config={
                "title": st.column_config.TextColumn("Title", required=True),
                "day": st.column_config.SelectboxColumn("Day", options=DAY_NAMES, required=True),
                "start": st.column_config.NumberColumn(
                    "Start (24h)",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.5,
                    format="%.1f",
                    required=True,
                ),
                "end": st.column_config.NumberColumn(
                    "End (24h)",
                    min_value=0.0,
                    max_value=24.0,
                    step=0.5,
                    format="%.1f",
                    required=True,
                ),
            },
        )
        st.session_state["ui_commitments"] = _coerce_commitments(edited_commitments)

    with tasks_tab:
        st.caption("Leave deadline blank if a task has no strict day (it will be treated as week-end).")
        tasks_df = _initial_editor_frame(
            st.session_state["ui_tasks"],
            ["title", "duration", "deadline_day"],
            {"title": "", "duration": 1.0, "deadline_day": ""},
        )
        edited_tasks = st.data_editor(
            tasks_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="ui_tasks_editor",
            column_config={
                "title": st.column_config.TextColumn("Task", required=True),
                "duration": st.column_config.NumberColumn(
                    "Hours",
                    min_value=0.5,
                    max_value=24.0,
                    step=0.5,
                    format="%.1f",
                    required=True,
                ),
                "deadline_day": st.column_config.SelectboxColumn(
                    "Deadline Day (optional)",
                    options=DEADLINE_OPTIONS,
                    required=False,
                ),
            },
        )
        st.session_state["ui_tasks"] = _coerce_tasks(edited_tasks)

    with settings_tab:
        st.caption("All time values below are in 24-hour decimal format.")
        left, right = st.columns(2)

        with left:
            st.markdown("**Workload Preferences**")
            st.number_input(
                "Max study hours per day (hours)",
                min_value=1.0,
                max_value=16.0,
                step=0.5,
                key="ui_max_daily_hours",
                help="Example: 8.0 means up to 8 hours of task work in one day.",
            )
            st.number_input(
                "Preferred study start (24h)",
                min_value=0.0,
                max_value=23.5,
                step=0.5,
                key="ui_workday_start",
                help="Example: 7.0 = 7:00 AM, 13.5 = 1:30 PM.",
            )
            st.number_input(
                "Preferred study end (24h)",
                min_value=0.5,
                max_value=24.0,
                step=0.5,
                key="ui_workday_end",
                help="Example: 22.0 = 10:00 PM.",
            )
            st.number_input(
                "Weekly workload comfort limit (hours)",
                min_value=1.0,
                max_value=100.0,
                step=1.0,
                key="ui_weekly_hours_threshold",
                help="Burnout alerts will treat totals above this weekly load as risky.",
            )

        with right:
            st.markdown("**Sleep + Search Settings**")
            st.number_input(
                "Sleep start (24h)",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                key="ui_sleep_start",
            )
            st.number_input(
                "Sleep end (24h)",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                key="ui_sleep_end",
            )
            st.number_input(
                "Scheduler slot step (hours)",
                min_value=0.25,
                max_value=2.0,
                step=0.25,
                key="ui_slot_step",
            )
            st.number_input(
                "Preferred buffer near other blocks",
                min_value=0.0,
                max_value=3.0,
                step=0.25,
                key="ui_buffer_hours",
            )

        burnout_left, burnout_right = st.columns(2)
        with burnout_left:
            st.markdown("**Burnout Alert Preferences**")
            st.number_input(
                "Late-night cutoff (24h)",
                min_value=0.0,
                max_value=24.0,
                step=0.5,
                key="ui_late_night_cutoff",
                help="Work ending at or after this time increases burnout risk.",
            )
            st.number_input(
                "Max consecutive heavy blocks",
                min_value=1,
                max_value=10,
                step=1,
                key="ui_max_consecutive_blocks",
                help="Alerts trigger when long blocks are chained beyond this count.",
            )
        with burnout_right:
            st.markdown("**Recovery Preferences**")
            st.number_input(
                "Minimum meaningful breaks per long day",
                min_value=0,
                max_value=6,
                step=1,
                key="ui_min_breaks_per_day",
                help="Long days should include at least this many 30+ minute breaks.",
            )
            st.number_input(
                "Deadline cluster window (days)",
                min_value=1,
                max_value=7,
                step=1,
                key="ui_deadline_cluster_days",
                help="Deadlines inside this many days are treated as a stress cluster.",
            )

    st.caption(
        f"{len(st.session_state['ui_commitments'])} commitments, "
        f"{len(st.session_state['ui_tasks'])} tasks."
    )
    run_clicked = st.button(
        "Analyze Burnout Risk and Rearrange Schedule",
        type="primary",
        use_container_width=True,
    )

    return _build_payload_from_state(), run_clicked


def _initialize_state(sample_payload: dict[str, Any], *, force: bool = False) -> None:
    """Seed Streamlit session state with sample values."""

    if st.session_state.get("ui_initialized") and not force:
        return

    if force:
        for widget_key in ("ui_commitments_editor", "ui_tasks_editor"):
            if widget_key in st.session_state:
                del st.session_state[widget_key]

    preferences = sample_payload.get("preferences", {})
    sleep_window = sample_payload.get("sleep_window", {})

    st.session_state["ui_commitments"] = deepcopy(sample_payload.get("commitments", []))
    st.session_state["ui_tasks"] = deepcopy(sample_payload.get("tasks", []))
    st.session_state["ui_max_daily_hours"] = float(
        preferences.get("max_daily_hours", sample_payload.get("max_daily_hours", 8.0))
    )
    st.session_state["ui_workday_start"] = float(
        preferences.get("preferred_study_start", sample_payload.get("workday_start", 7.0))
    )
    st.session_state["ui_workday_end"] = float(
        preferences.get("preferred_study_end", sample_payload.get("workday_end", 22.0))
    )
    st.session_state["ui_slot_step"] = float(
        preferences.get("slot_step", sample_payload.get("slot_step", 0.5))
    )
    st.session_state["ui_buffer_hours"] = float(
        preferences.get("buffer_hours", sample_payload.get("buffer_hours", 1.0))
    )
    st.session_state["ui_weekly_hours_threshold"] = float(
        preferences.get("weekly_hours_threshold", 50.0)
    )
    st.session_state["ui_late_night_cutoff"] = float(
        preferences.get("late_night_cutoff", 23.0)
    )
    st.session_state["ui_max_consecutive_blocks"] = int(
        preferences.get("max_consecutive_blocks", 3)
    )
    st.session_state["ui_min_breaks_per_day"] = int(
        preferences.get("min_breaks_per_day", 1)
    )
    st.session_state["ui_deadline_cluster_days"] = int(
        preferences.get("deadline_cluster_days", 2)
    )
    st.session_state["ui_sleep_start"] = float(sleep_window.get("start", 23.0))
    st.session_state["ui_sleep_end"] = float(sleep_window.get("end", 7.0))
    st.session_state["ui_initialized"] = True


def _initial_editor_frame(
    rows: list[dict[str, Any]],
    columns: list[str],
    empty_row: dict[str, Any],
) -> pd.DataFrame:
    """Return a data frame that keeps editor columns stable."""

    if rows:
        return pd.DataFrame(rows, columns=columns)
    return pd.DataFrame([empty_row], columns=columns)


def _coerce_commitments(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Normalize commitment rows from Streamlit's editor output."""

    commitments: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        day = _normalize_day(row.get("day"))
        commitments.append(
            {
                "title": title,
                "day": day,
                "start": _to_float(row.get("start"), fallback=0.0),
                "end": _to_float(row.get("end"), fallback=0.0),
            }
        )

    return commitments


def _coerce_tasks(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Normalize task rows from Streamlit's editor output."""

    tasks: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        tasks.append(
            {
                "title": title,
                "duration": _to_float(row.get("duration"), fallback=0.0),
                "deadline_day": _normalize_day(row.get("deadline_day"), allow_empty=True),
            }
        )

    return tasks


def _normalize_day(raw_day: Any, *, allow_empty: bool = False) -> str:
    """Normalize day strings to scheduler day abbreviations."""

    candidate = str(raw_day or "").strip().lower()
    if allow_empty and not candidate:
        return ""
    if candidate in DAY_ALIASES:
        return DAY_ALIASES[candidate]
    return "" if allow_empty else "Mon"


def _to_float(value: Any, *, fallback: float) -> float:
    """Parse floats from data-editor values safely."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _build_payload_from_state() -> dict[str, Any]:
    """Build scheduler payload from current Streamlit session state."""

    max_daily_hours = float(st.session_state["ui_max_daily_hours"])
    workday_start = float(st.session_state["ui_workday_start"])
    workday_end = float(st.session_state["ui_workday_end"])
    slot_step = float(st.session_state["ui_slot_step"])
    buffer_hours = float(st.session_state["ui_buffer_hours"])
    weekly_hours_threshold = float(st.session_state["ui_weekly_hours_threshold"])
    late_night_cutoff = float(st.session_state["ui_late_night_cutoff"])
    max_consecutive_blocks = int(st.session_state["ui_max_consecutive_blocks"])
    min_breaks_per_day = int(st.session_state["ui_min_breaks_per_day"])
    deadline_cluster_days = int(st.session_state["ui_deadline_cluster_days"])

    scheduler_tasks: list[dict[str, Any]] = []
    for task in st.session_state["ui_tasks"]:
        normalized_deadline = _normalize_day(task.get("deadline_day"), allow_empty=True) or "Sun"
        scheduler_tasks.append(
            {
                "title": str(task.get("title", "")).strip(),
                "duration": _to_float(task.get("duration"), fallback=0.0),
                "deadline_day": normalized_deadline,
            }
        )

    payload = {
        "commitments": st.session_state["ui_commitments"],
        "tasks": scheduler_tasks,
        "sleep_window": {
            "start": float(st.session_state["ui_sleep_start"]),
            "end": float(st.session_state["ui_sleep_end"]),
        },
        "preferences": {
            "max_daily_hours": max_daily_hours,
            "preferred_study_start": workday_start,
            "preferred_study_end": workday_end,
            "slot_step": slot_step,
            "buffer_hours": buffer_hours,
            "weekly_hours_threshold": weekly_hours_threshold,
            "late_night_cutoff": late_night_cutoff,
            "max_consecutive_blocks": max_consecutive_blocks,
            "min_breaks_per_day": min_breaks_per_day,
            "deadline_cluster_days": deadline_cluster_days,
        },
        "max_daily_hours": max_daily_hours,
        "workday_start": workday_start,
        "workday_end": workday_end,
        "slot_step": slot_step,
        "buffer_hours": buffer_hours,
    }

    return payload

