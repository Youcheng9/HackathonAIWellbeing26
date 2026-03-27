"""Streamlit presentation helpers for schedule comparison and burnout analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from src.scheduler.constraints import DAY_ORDER, can_schedule_task


DAY_NAMES = sorted(DAY_ORDER, key=DAY_ORDER.get)
RISK_COLORS = {
    "Low": "#2f855a",
    "Moderate": "#b7791f",
    "High": "#c53030",
}


@dataclass
class BurnoutAssessment:
    """Frontend-friendly burnout summary."""

    score: int
    level: str
    reasons: list[str]
    metrics: dict[str, Any]


def inject_theme() -> None:
    """Inject page-level styling for the hackathon demo UI."""

    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at 8% -10%, rgba(34, 139, 120, 0.18), transparent 35%),
                    radial-gradient(circle at 90% 0%, rgba(223, 123, 52, 0.15), transparent 33%),
                    linear-gradient(180deg, #f4f8f5 0%, #f9f5ec 100%);
            }
            html, body, [class*="st-"], [class*="css"] {
                font-family: "Trebuchet MS", "Gill Sans", "Verdana", sans-serif;
            }
            h1, h2, h3, h4 {
                font-family: "Georgia", "Palatino Linotype", serif;
                letter-spacing: 0.2px;
            }
            .hero-shell {
                border: 1px solid rgba(44, 104, 86, 0.25);
                background: linear-gradient(120deg, #d8efe6 0%, #f8e7d1 100%);
                border-radius: 18px;
                padding: 1.1rem 1.2rem;
                margin-bottom: 1rem;
                animation: riseIn .6s ease;
            }
            .hero-title {
                font-size: 1.55rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
                color: #183f34;
            }
            .hero-subtitle {
                font-size: 0.97rem;
                color: #21483d;
                line-height: 1.45;
            }
            .score-tile {
                border: 2px solid rgba(44, 104, 86, 0.22);
                border-radius: 14px;
                padding: 0.85rem 1rem;
                background: rgba(255, 255, 255, 0.8);
                animation: riseIn .55s ease;
                min-height: 140px;
            }
            .tile-title {
                font-size: 0.87rem;
                letter-spacing: 0.4px;
                text-transform: uppercase;
                opacity: 0.8;
                margin-bottom: 0.35rem;
            }
            .tile-score {
                font-size: 2rem;
                font-weight: 700;
                line-height: 1.1;
                margin-bottom: 0.25rem;
            }
            .risk-pill {
                display: inline-block;
                color: #fff;
                padding: 0.18rem 0.55rem;
                border-radius: 999px;
                font-size: 0.78rem;
                font-weight: 700;
            }
            .tile-note {
                margin-top: 0.45rem;
                font-size: 0.84rem;
                color: #3f3f3f;
            }
            .week-grid {
                display: grid;
                grid-template-columns: repeat(7, minmax(0, 1fr));
                gap: 0.5rem;
            }
            .day-card {
                border: 1px solid rgba(0, 0, 0, 0.12);
                border-radius: 12px;
                padding: 0.45rem;
                background: rgba(255, 255, 255, 0.84);
                min-height: 130px;
                animation: riseIn .5s ease both;
            }
            .day-card:nth-child(1) { animation-delay: .02s; }
            .day-card:nth-child(2) { animation-delay: .04s; }
            .day-card:nth-child(3) { animation-delay: .06s; }
            .day-card:nth-child(4) { animation-delay: .08s; }
            .day-card:nth-child(5) { animation-delay: .10s; }
            .day-card:nth-child(6) { animation-delay: .12s; }
            .day-card:nth-child(7) { animation-delay: .14s; }
            .day-label {
                font-size: 0.82rem;
                font-weight: 700;
                margin-bottom: 0.35rem;
                color: #264139;
                border-bottom: 1px dashed rgba(38, 65, 57, 0.28);
                padding-bottom: 0.25rem;
            }
            .block {
                border-radius: 8px;
                padding: 0.38rem 0.42rem;
                margin-bottom: 0.32rem;
                font-size: 0.75rem;
                line-height: 1.3;
            }
            .block.task {
                background: #e5f0ff;
                border-left: 4px solid #2b6cb0;
            }
            .block.fixed {
                background: #ffeed8;
                border-left: 4px solid #c05621;
            }
            .block-time {
                font-size: 0.71rem;
                opacity: 0.84;
            }
            .block-title {
                font-weight: 700;
            }
            .empty-day {
                font-size: 0.74rem;
                color: #5b5b5b;
                font-style: italic;
                padding-top: 0.2rem;
            }
            @media (max-width: 980px) {
                .week-grid {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }
            }
            @media (max-width: 640px) {
                .week-grid {
                    grid-template-columns: 1fr;
                }
            }
            @keyframes riseIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render hero section."""

    st.markdown(
        """
        <section class="hero-shell">
            <div class="hero-title">BalanceAI Demo</div>
            <div class="hero-subtitle">
                Enter class/work constraints and assignment deadlines, then compare a
                deadline-clustered baseline plan against the AI-optimized healthier schedule.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_results(payload: dict[str, Any], optimized_result: dict[str, Any]) -> None:
    """Render burnout and schedule comparison outputs."""

    before_plan = build_baseline_schedule(payload)
    before_schedule = before_plan["scheduled_tasks"]
    before_unscheduled = before_plan["unscheduled_tasks"]
    after_schedule = optimized_result["optimized_schedule"]
    after_unscheduled = optimized_result["unscheduled_tasks"]

    settings = _resolve_settings(payload)
    before_assessment = assess_burnout(
        commitments=payload.get("commitments", []),
        scheduled_tasks=before_schedule,
        tasks=payload.get("tasks", []),
        unscheduled_tasks=before_unscheduled,
        max_daily_hours=settings["max_daily_hours"],
    )
    after_assessment = assess_burnout(
        commitments=payload.get("commitments", []),
        scheduled_tasks=after_schedule,
        tasks=payload.get("tasks", []),
        unscheduled_tasks=after_unscheduled,
        max_daily_hours=settings["max_daily_hours"],
    )

    st.subheader("2) Burnout Risk")
    _render_score_cards(before_assessment, after_assessment)

    reasons_left, reasons_right = st.columns(2)
    with reasons_left:
        st.markdown("**Top Risk Reasons (Before)**")
        _render_reason_list(before_assessment.reasons)
    with reasons_right:
        st.markdown("**Top Risk Reasons (After)**")
        _render_reason_list(after_assessment.reasons)

    st.subheader("3) Before vs After Schedule Comparison")
    _render_change_summary(
        before=before_assessment,
        after=after_assessment,
        before_unscheduled=before_unscheduled,
        after_unscheduled=after_unscheduled,
    )
    _render_load_chart(before_assessment, after_assessment)
    _render_task_comparison_table(
        tasks=payload.get("tasks", []),
        before_schedule=before_schedule,
        after_schedule=after_schedule,
    )

    before_tab, after_tab = st.tabs(["Before Schedule", "After Schedule"])
    with before_tab:
        _render_schedule_grid(
            commitments=payload.get("commitments", []),
            scheduled_tasks=before_schedule,
        )
        _render_unscheduled_tasks(before_unscheduled, empty_message="All tasks were placed.")
    with after_tab:
        _render_schedule_grid(
            commitments=payload.get("commitments", []),
            scheduled_tasks=after_schedule,
        )
        _render_unscheduled_tasks(after_unscheduled, empty_message="All tasks were placed.")


def build_baseline_schedule(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Build a naive baseline schedule that clusters work close to deadlines."""

    tasks = [dict(task) for task in payload.get("tasks", [])]
    commitments = payload.get("commitments", [])
    sleep_window = payload.get("sleep_window", {"start": 23.0, "end": 7.0})
    settings = _resolve_settings(payload)

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
) -> BurnoutAssessment:
    """Score burnout risk using explainable frontend-side heuristics."""

    block_map = _group_blocks_by_day(commitments, scheduled_tasks)
    daily_hours = {
        day: round(sum(block["end"] - block["start"] for block in block_map[day]), 2)
        for day in DAY_NAMES
    }
    total_hours = round(sum(daily_hours.values()), 2)
    heavy_day_threshold = round(max_daily_hours * 0.75, 2)

    score = 0
    reasons: list[tuple[int, str]] = []

    def add_reason(points: int, text: str) -> None:
        nonlocal score
        score += points
        reasons.append((points, text))

    overloaded_days = [day for day, hours in daily_hours.items() if hours > max_daily_hours]
    if overloaded_days:
        highest_day = max(overloaded_days, key=lambda day: daily_hours[day])
        add_reason(
            15,
            (
                f"{', '.join(overloaded_days)} exceed the daily safe workload. "
                f"{highest_day} reaches {daily_hours[highest_day]:.1f} hours."
            ),
        )

    max_consecutive_heavy = max(
        (_count_consecutive_heavy_blocks(block_map[day]) for day in DAY_NAMES),
        default=0,
    )
    if max_consecutive_heavy >= 4:
        add_reason(10, f"{max_consecutive_heavy} heavy blocks are chained with little recovery.")

    breakless_days = [
        day
        for day in DAY_NAMES
        if daily_hours[day] >= 7.0 and not _has_meaningful_break(block_map[day])
    ]
    if breakless_days:
        add_reason(10, f"{', '.join(breakless_days)} are long days without a meaningful break.")

    clustered_deadlines = _max_deadline_cluster(tasks, window_size=3)
    if clustered_deadlines >= 3:
        add_reason(
            15,
            f"{clustered_deadlines} deadlines are clustered inside a 48-hour window.",
        )

    late_night_blocks = sum(
        1 for day in DAY_NAMES for block in block_map[day] if block["end"] > 22.5
    )
    if late_night_blocks > 0:
        add_reason(10, f"{late_night_blocks} blocks run late at night.")

    recovery_days = [day for day, hours in daily_hours.items() if hours <= 2.0]
    if not recovery_days:
        add_reason(15, "There is no light recovery day in this week.")

    if total_hours > 50:
        add_reason(15, f"Total weekly load is {total_hours:.1f} hours, above a healthy limit.")

    context_switch_days = [day for day in DAY_NAMES if len(block_map[day]) >= 6]
    if context_switch_days:
        add_reason(
            10,
            f"{', '.join(context_switch_days)} have high context switching with many short blocks.",
        )

    if unscheduled_tasks:
        add_reason(
            10,
            f"{len(unscheduled_tasks)} task(s) could not be scheduled before deadlines.",
        )

    score = min(score, 100)
    level = _risk_level(score)
    top_reasons = [text for _, text in sorted(reasons, key=lambda item: item[0], reverse=True)[:3]]

    return BurnoutAssessment(
        score=score,
        level=level,
        reasons=top_reasons or ["Workload looks balanced with manageable pressure."],
        metrics={
            "daily_hours": daily_hours,
            "total_hours": total_hours,
            "heavy_day_threshold": heavy_day_threshold,
            "heavy_days": [day for day, hours in daily_hours.items() if hours >= heavy_day_threshold],
            "overloaded_days": overloaded_days,
            "late_night_blocks": late_night_blocks,
            "context_switch_days": context_switch_days,
            "max_consecutive_heavy": max_consecutive_heavy,
            "unscheduled_count": len(unscheduled_tasks),
        },
    )


def _render_score_cards(before: BurnoutAssessment, after: BurnoutAssessment) -> None:
    """Render burnout score cards."""

    score_delta = after.score - before.score
    unscheduled_delta = after.metrics["unscheduled_count"] - before.metrics["unscheduled_count"]

    col_before, col_after, col_delta = st.columns(3)
    with col_before:
        _render_score_card("Before", before)
    with col_after:
        _render_score_card("After (AI Optimized)", after)
    with col_delta:
        delta_note = f"Score change: {score_delta:+d}"
        unscheduled_note = f"Unscheduled tasks change: {unscheduled_delta:+d}"
        _render_delta_card(delta_note, unscheduled_note)


def _render_score_card(label: str, assessment: BurnoutAssessment) -> None:
    """Render a single burnout score card."""

    color = RISK_COLORS[assessment.level]
    st.markdown(
        f"""
        <div class="score-tile" style="border-color: {color};">
            <div class="tile-title">{escape(label)}</div>
            <div class="tile-score" style="color:{color};">{assessment.score}</div>
            <span class="risk-pill" style="background:{color};">{assessment.level}</span>
            <div class="tile-note">Top signal: {escape(assessment.reasons[0])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_delta_card(delta_note: str, unscheduled_note: str) -> None:
    """Render compact deltas from before to after."""

    st.markdown(
        f"""
        <div class="score-tile">
            <div class="tile-title">Plan Delta</div>
            <div class="tile-score" style="font-size:1.45rem;color:#1f4e79;">{escape(delta_note)}</div>
            <div class="tile-note">{escape(unscheduled_note)}</div>
            <div class="tile-note">Negative score change is healthier.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_reason_list(reasons: list[str]) -> None:
    """Render a markdown list for risk explanations."""

    reason_lines = "\n".join(f"- {reason}" for reason in reasons)
    st.markdown(reason_lines)


def _render_change_summary(
    *,
    before: BurnoutAssessment,
    after: BurnoutAssessment,
    before_unscheduled: list[dict[str, Any]],
    after_unscheduled: list[dict[str, Any]],
) -> None:
    """Render human-readable explanation of why after-plan is healthier."""

    changes: list[str] = []
    if after.score < before.score:
        changes.append(f"Burnout score drops from {before.score} to {after.score}.")
    elif after.score > before.score:
        changes.append(f"Burnout score increases from {before.score} to {after.score}.")
    else:
        changes.append("Burnout score is unchanged.")

    before_heavy = len(before.metrics["heavy_days"])
    after_heavy = len(after.metrics["heavy_days"])
    if after_heavy != before_heavy:
        changes.append(f"Heavy-load days change from {before_heavy} to {after_heavy}.")

    before_late = before.metrics["late_night_blocks"]
    after_late = after.metrics["late_night_blocks"]
    if after_late != before_late:
        changes.append(f"Late-night blocks change from {before_late} to {after_late}.")

    if len(after_unscheduled) != len(before_unscheduled):
        changes.append(
            "Unscheduled tasks change from "
            f"{len(before_unscheduled)} to {len(after_unscheduled)}."
        )

    if not changes:
        changes.append("No major structural difference was detected between plans.")

    st.markdown("**What Changed and Why It Is Healthier**")
    st.markdown("\n".join(f"- {entry}" for entry in changes))


def _render_load_chart(before: BurnoutAssessment, after: BurnoutAssessment) -> None:
    """Render day-by-day workload bars."""

    load_df = pd.DataFrame(
        {
            "Before": [before.metrics["daily_hours"][day] for day in DAY_NAMES],
            "After": [after.metrics["daily_hours"][day] for day in DAY_NAMES],
        },
        index=DAY_NAMES,
    )
    st.markdown("**Daily Workload Distribution (Class + Work + Tasks)**")
    st.bar_chart(load_df, use_container_width=True)


def _render_task_comparison_table(
    *,
    tasks: list[dict[str, Any]],
    before_schedule: list[dict[str, Any]],
    after_schedule: list[dict[str, Any]],
) -> None:
    """Render per-task before/after placement summary."""

    before_map = _group_placements_by_title(before_schedule)
    after_map = _group_placements_by_title(after_schedule)

    task_titles = sorted(
        {
            *[task["title"] for task in tasks],
            *before_map.keys(),
            *after_map.keys(),
        }
    )

    rows = []
    for title in task_titles:
        rows.append(
            {
                "Task": title,
                "Before": _format_placement_chunks(before_map.get(title, [])),
                "After": _format_placement_chunks(after_map.get(title, [])),
            }
        )

    st.markdown("**Task Placement Before vs After**")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_schedule_grid(
    *,
    commitments: list[dict[str, Any]],
    scheduled_tasks: list[dict[str, Any]],
) -> None:
    """Render a weekly grid of commitments and tasks."""

    block_map = _group_blocks_by_day(commitments, scheduled_tasks)

    html_parts = ["<div class='week-grid'>"]
    for day in DAY_NAMES:
        html_parts.append("<section class='day-card'>")
        html_parts.append(f"<div class='day-label'>{escape(day)}</div>")

        day_blocks = block_map[day]
        if not day_blocks:
            html_parts.append("<div class='empty-day'>Recovery space</div>")
        else:
            for block in day_blocks:
                block_class = "fixed" if block["kind"] == "commitment" else "task"
                html_parts.append(
                    "<div class='block "
                    f"{block_class}'>"
                    f"<div class='block-time'>{escape(_format_time_range(block['start'], block['end']))}</div>"
                    f"<div class='block-title'>{escape(block['title'])}</div>"
                    "</div>"
                )

        html_parts.append("</section>")
    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_unscheduled_tasks(tasks: list[dict[str, Any]], *, empty_message: str) -> None:
    """Show unscheduled tasks table or success message."""

    if not tasks:
        st.success(empty_message)
        return

    st.warning(f"{len(tasks)} task(s) were not placed.")
    st.dataframe(pd.DataFrame(tasks), use_container_width=True, hide_index=True)


def _resolve_settings(payload: dict[str, Any]) -> dict[str, float]:
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


def _group_blocks_by_day(
    commitments: list[dict[str, Any]],
    scheduled_tasks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Combine commitments and tasks, grouped by day."""

    day_map: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for commitment in commitments:
        day = commitment.get("day", "Mon")
        if day not in DAY_ORDER:
            continue
        day_map[day].append(
            {
                "kind": "commitment",
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
                "kind": "task",
                "title": str(task["title"]),
                "start": float(task["start"]),
                "end": float(task["end"]),
            }
        )

    for day in DAY_NAMES:
        day_map[day].sort(key=lambda block: (block["start"], block["end"], block["title"]))

    return day_map


def _count_consecutive_heavy_blocks(blocks: list[dict[str, Any]]) -> int:
    """Find longest sequence of heavy blocks with minimal gaps."""

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


def _has_meaningful_break(blocks: list[dict[str, Any]]) -> bool:
    """Check for at least one break of 30+ minutes between blocks."""

    if len(blocks) < 2:
        return True

    for index in range(len(blocks) - 1):
        gap = blocks[index + 1]["start"] - blocks[index]["end"]
        if gap >= 0.5:
            return True
    return False


def _max_deadline_cluster(tasks: list[dict[str, Any]], *, window_size: int) -> int:
    """Return highest number of deadlines in any N-day window."""

    counts: dict[int, int] = defaultdict(int)
    for task in tasks:
        deadline_day = task.get("deadline_day")
        if deadline_day in DAY_ORDER:
            counts[DAY_ORDER[deadline_day]] += 1

    best = 0
    for start in range(len(DAY_NAMES)):
        window_total = 0
        for offset in range(window_size):
            window_total += counts.get(start + offset, 0)
        best = max(best, window_total)
    return best


def _risk_level(score: int) -> str:
    """Translate score to categorical burnout risk."""

    if score < 30:
        return "Low"
    if score < 60:
        return "Moderate"
    return "High"


def _format_time_range(start: float, end: float) -> str:
    """Human readable range for schedule block display."""

    return f"{_format_hour(start)} - {_format_hour(end)}"


def _format_hour(value: float) -> str:
    """Format decimal hour values into AM/PM strings."""

    hour = int(value)
    minute = int(round((value - hour) * 60))
    if minute == 60:
        hour += 1
        minute = 0
    hour = hour % 24

    suffix = "AM" if hour < 12 else "PM"
    normalized_hour = hour % 12 or 12
    return f"{normalized_hour}:{minute:02d} {suffix}"


def _group_placements_by_title(
    schedule: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Collect schedule chunks by task title."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in schedule:
        grouped[block["title"]].append(block)

    for chunks in grouped.values():
        chunks.sort(key=lambda item: (DAY_ORDER.get(item["day"], 0), item["start"]))

    return grouped


def _format_placement_chunks(chunks: list[dict[str, Any]]) -> str:
    """Render compact placement string for a list of chunks."""

    if not chunks:
        return "Not placed"

    formatted = [
        f"{chunk['day']} {_format_hour(chunk['start'])}-{_format_hour(chunk['end'])}"
        for chunk in chunks
    ]
    return "; ".join(formatted)
