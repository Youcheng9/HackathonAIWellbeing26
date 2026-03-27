from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from src.burnout.rules import RULES
from src.burnout.scorer import compute_burnout_score
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
                    radial-gradient(circle at 8% -10%, rgba(34, 139, 120, 0.12), transparent 32%),
                    linear-gradient(180deg, #f6faf8 0%, #fcfaf4 100%);
                color-scheme: light;
            }
            html, body, .stApp {
                font-family: "Trebuchet MS", "Gill Sans", "Verdana", sans-serif;
            }
            h1, h2, h3, h4 {
                font-family: "Georgia", "Palatino Linotype", serif;
                letter-spacing: 0.2px;
            }
            [data-testid="stToolbar"] {
                display: none !important;
            }
            .hero-shell {
                border: 1px solid rgba(44, 104, 86, 0.25);
                background: linear-gradient(120deg, #e3f4ee 0%, #fbf0df 100%);
                border-radius: 18px;
                padding: 1.4rem 1.5rem;
                margin-bottom: 1rem;
                animation: riseIn .6s ease;
            }
            .hero-title {
                font-size: 2.45rem;
                font-weight: 700;
                line-height: 1.05;
                margin-bottom: 0.45rem;
                color: #183f34;
                text-align: left;
            }
            .hero-subtitle {
                font-size: 1.02rem;
                color: #21483d;
                line-height: 1.45;
                text-align: left;
            }
            .score-tile {
                border: 2px solid rgba(44, 104, 86, 0.22);
                border-radius: 14px;
                padding: 1rem 1.1rem;
                background: rgba(255, 255, 255, 0.8);
                animation: riseIn .55s ease;
                min-height: 132px;
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
                line-height: 1.35;
            }
            .reason-panel {
                border: 1px solid rgba(44, 104, 86, 0.22);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.86);
                padding: 0.75rem 0.9rem;
                min-height: 140px;
            }
            .reason-title {
                font-weight: 700;
                margin-bottom: 0.45rem;
                color: #1f3e34;
            }
            .reason-line {
                margin: 0.22rem 0;
                line-height: 1.35;
                color: #2f2f2f;
                font-size: 0.95rem;
            }
            .calendar-shell {
                border: 1px solid rgba(37, 69, 60, 0.2);
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.9);
                padding: 0.8rem 0.8rem 0.5rem 0.8rem;
            }
            .calendar-board {
                display: grid;
                grid-template-columns: 70px repeat(7, minmax(0, 1fr));
                border: 1px solid rgba(21, 49, 40, 0.18);
                border-radius: 10px;
                overflow: hidden;
                min-height: 760px;
            }
            .calendar-corner {
                border-right: 1px solid rgba(21, 49, 40, 0.14);
                border-bottom: 1px solid rgba(21, 49, 40, 0.14);
                background: #f3f7f5;
            }
            .calendar-header {
                border-left: 1px solid rgba(21, 49, 40, 0.14);
                border-bottom: 1px solid rgba(21, 49, 40, 0.14);
                background: #f3f7f5;
                padding: 0.35rem 0.3rem;
                text-align: center;
            }
            .calendar-day-name {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.45px;
                color: #35584d;
                font-weight: 700;
            }
            .calendar-date {
                font-size: 1rem;
                font-weight: 700;
                color: #1d302b;
                margin-top: 0.1rem;
            }
            .calendar-time-col {
                position: relative;
                border-right: 1px solid rgba(21, 49, 40, 0.14);
                background: #fdfefd;
                min-height: 700px;
            }
            .calendar-time-label {
                position: absolute;
                left: 6px;
                transform: translateY(-50%);
                font-size: 0.68rem;
                color: #52635c;
                white-space: nowrap;
            }
            .calendar-day-col {
                position: relative;
                min-height: 700px;
                border-left: 1px solid rgba(21, 49, 40, 0.14);
                background: repeating-linear-gradient(
                    to bottom,
                    rgba(24, 49, 41, 0.08) 0,
                    rgba(24, 49, 41, 0.08) 1px,
                    transparent 1px,
                    transparent calc(100% / 18)
                );
            }
            .calendar-event {
                position: absolute;
                left: 4px;
                right: 4px;
                border-radius: 8px;
                padding: 0.28rem 0.35rem;
                font-size: 0.7rem;
                line-height: 1.22;
                overflow: hidden;
                border: 1px solid rgba(0, 0, 0, 0.08);
            }
            .calendar-event.task {
                background: #dcecff;
                border-left: 4px solid #2b6cb0;
                color: #1d3f63;
            }
            .calendar-event.fixed {
                background: #ffe8d2;
                border-left: 4px solid #c05621;
                color: #5a2f13;
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
                .calendar-shell {
                    overflow-x: auto;
                }
                .calendar-board {
                    min-width: 1050px;
                }
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
            <div class="hero-title">BalanceAI</div>
            <div class="hero-subtitle">
                Burnout-aware schedule planner for students.
                Add commitments and tasks, then compare baseline vs AI-optimized weekly plans.
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
        weekly_hours_threshold=settings["weekly_hours_threshold"],
        late_night_cutoff=settings["late_night_cutoff"],
        max_consecutive_blocks=int(settings["max_consecutive_blocks"]),
        min_breaks_per_day=int(settings["min_breaks_per_day"]),
        deadline_cluster_days=int(settings["deadline_cluster_days"]),
    )
    after_assessment = _assessment_from_pipeline_metadata(optimized_result)
    if after_assessment is None:
        after_assessment = assess_burnout(
            commitments=payload.get("commitments", []),
            scheduled_tasks=after_schedule,
            tasks=payload.get("tasks", []),
            unscheduled_tasks=after_unscheduled,
            max_daily_hours=settings["max_daily_hours"],
            weekly_hours_threshold=settings["weekly_hours_threshold"],
            late_night_cutoff=settings["late_night_cutoff"],
            max_consecutive_blocks=int(settings["max_consecutive_blocks"]),
            min_breaks_per_day=int(settings["min_breaks_per_day"]),
            deadline_cluster_days=int(settings["deadline_cluster_days"]),
        )

    st.subheader("2) Burnout Risk")
    _render_score_cards(before_assessment, after_assessment)

    st.markdown("**Top Risk Reasons**")
    reasons_left, reasons_right = st.columns(2)
    with reasons_left:
        _render_reason_panel("Before", before_assessment.reasons)
    with reasons_right:
        _render_reason_panel("After", after_assessment.reasons)

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

    schedule_cards_tab, calendar_tab = st.tabs(["Schedule Cards", "Calendar"])
    with schedule_cards_tab:
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

    with calendar_tab:
        _render_calendar_workspace(
            commitments=payload.get("commitments", []),
            before_schedule=before_schedule,
            after_schedule=after_schedule,
        )


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


def _assessment_from_pipeline_metadata(
    optimized_result: dict[str, Any],
) -> BurnoutAssessment | None:
    """Build a burnout assessment from pipeline metadata when available."""

    metadata = optimized_result.get("metadata", {})
    score = metadata.get("burnout_score")
    level = metadata.get("burnout_level")
    reasons = metadata.get("burnout_reasons")
    metrics = metadata.get("burnout_metrics")

    if score is None or level is None or reasons is None or metrics is None:
        return None

    return BurnoutAssessment(
        score=int(score),
        level=str(level),
        reasons=list(reasons),
        metrics=dict(metrics),
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


def _render_reason_panel(label: str, reasons: list[str]) -> None:
    """Render cleaner reason cards for burnout explanations."""

    reason_lines = "".join(
        f"<div class='reason-line'>{index}. {escape(reason)}</div>"
        for index, reason in enumerate(reasons, start=1)
    )
    st.markdown(
        f"""
        <div class="reason-panel">
            <div class="reason-title">{escape(label)}</div>
            {reason_lines}
        </div>
        """,
        unsafe_allow_html=True,
    )


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


def _render_calendar_workspace(
    *,
    commitments: list[dict[str, Any]],
    before_schedule: list[dict[str, Any]],
    after_schedule: list[dict[str, Any]],
) -> None:
    """Render a larger, date-based calendar view with plan selection."""

    st.markdown("**Weekly Calendar**")

    controls_left, controls_mid, controls_right = st.columns([2.2, 1.3, 1.5])
    with controls_left:
        selected_date = st.date_input(
            "Week reference date",
            value=_week_monday(date.today()),
            help="Any day in the week. The calendar will snap to Monday.",
            key="calendar_reference_date",
        )
    with controls_mid:
        selected_plan = st.radio(
            "Calendar version",
            options=["Before", "After"],
            index=1,
            horizontal=True,
            key="calendar_version_toggle",
        )
    with controls_right:
        include_commitments = st.checkbox(
            "Include classes/work",
            value=True,
            key="calendar_include_commitments",
        )

    week_start = _week_monday(selected_date)
    week_end = week_start + timedelta(days=6)
    st.caption(
        f"Showing week: {week_start.strftime('%b %d, %Y')} - {week_end.strftime('%b %d, %Y')}"
    )
    if st.button(
        f"Choose This Calendar ({selected_plan})",
        type="primary",
        use_container_width=True,
        key="choose_calendar_btn",
    ):
        st.session_state["chosen_calendar_plan"] = selected_plan
        st.success(f"{selected_plan} calendar selected.")

    chosen_plan = st.session_state.get("chosen_calendar_plan")
    if chosen_plan:
        st.caption(f"Current selected calendar: {chosen_plan}")

    selected_tasks = before_schedule if selected_plan == "Before" else after_schedule
    selected_commitments = commitments if include_commitments else []

    _render_large_week_calendar(
        week_start=week_start,
        commitments=selected_commitments,
        scheduled_tasks=selected_tasks,
    )


def _render_large_week_calendar(
    *,
    week_start: date,
    commitments: list[dict[str, Any]],
    scheduled_tasks: list[dict[str, Any]],
) -> None:
    """Render a large weekly timeline with date headers and hour rows."""

    calendar_start = 6.0
    calendar_end = 24.0
    total_hours = calendar_end - calendar_start
    hours = list(range(int(calendar_start), int(calendar_end)))

    day_blocks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for commitment in commitments:
        day = commitment.get("day")
        if day in DAY_ORDER:
            day_blocks[day].append(
                {
                    "kind": "fixed",
                    "title": str(commitment["title"]),
                    "start": float(commitment["start"]),
                    "end": float(commitment["end"]),
                }
            )
    for task in scheduled_tasks:
        day = task.get("day")
        if day in DAY_ORDER:
            day_blocks[day].append(
                {
                    "kind": "task",
                    "title": str(task["title"]),
                    "start": float(task["start"]),
                    "end": float(task["end"]),
                }
            )

    for day in DAY_NAMES:
        day_blocks[day].sort(key=lambda block: (block["start"], block["end"], block["title"]))

    html_parts = ["<section class='calendar-shell'><div class='calendar-board'>"]
    html_parts.append("<div class='calendar-corner'></div>")

    for day in DAY_NAMES:
        day_date = week_start + timedelta(days=DAY_ORDER[day])
        html_parts.append(
            "<div class='calendar-header'>"
            f"<div class='calendar-day-name'>{escape(day)}</div>"
            f"<div class='calendar-date'>{escape(day_date.strftime('%b %d'))}</div>"
            "</div>"
        )

    html_parts.append("<div class='calendar-time-col'>")
    for hour in hours:
        top_pct = ((hour - calendar_start) / total_hours) * 100
        html_parts.append(
            f"<div class='calendar-time-label' style='top:{top_pct:.3f}%;'>"
            f"{escape(_format_hour(float(hour)))}"
            "</div>"
        )
    html_parts.append("</div>")

    for day in DAY_NAMES:
        html_parts.append("<div class='calendar-day-col'>")
        for block in day_blocks[day]:
            clipped_start = max(block["start"], calendar_start)
            clipped_end = min(block["end"], calendar_end)
            if clipped_end <= calendar_start or clipped_start >= calendar_end:
                continue
            if clipped_end <= clipped_start:
                continue

            top_pct = ((clipped_start - calendar_start) / total_hours) * 100
            height_pct = max(((clipped_end - clipped_start) / total_hours) * 100, 2.5)
            html_parts.append(
                f"<div class='calendar-event {escape(block['kind'])}' "
                f"style='top:{top_pct:.3f}%; height:{height_pct:.3f}%;'>"
                f"<div>{escape(block['title'])}</div>"
                f"<div>{escape(_format_time_range(block['start'], block['end']))}</div>"
                "</div>"
            )
        html_parts.append("</div>")

    html_parts.append("</div></section>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _week_monday(raw_date: date) -> date:
    """Return Monday for the week containing the supplied date."""

    return raw_date - timedelta(days=raw_date.weekday())


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

