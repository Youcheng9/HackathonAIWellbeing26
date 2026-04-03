"""Regression tests for burnout scoring and personalized preferences."""

from __future__ import annotations

import unittest

from src.burnout.scorer import compute_burnout_score
from src.integration.pipeline import run_pipeline
from src.ui.views import build_baseline_schedule, assess_burnout, _resolve_settings


class BurnoutScoringTests(unittest.TestCase):
    """Verify shared burnout scoring stays aligned with the current app flow."""

    def test_personalized_thresholds_reduce_false_positive_risk(self) -> None:
        schedule = [
            {"title": "Night Study", "day": "Mon", "start": 20.0, "end": 23.5},
            {"title": "Essay Draft", "day": "Tue", "start": 19.0, "end": 22.5},
        ]
        tasks = [
            {"title": "Night Study", "duration": 3.5, "deadline_day": "Mon"},
            {"title": "Essay Draft", "duration": 3.5, "deadline_day": "Tue"},
        ]

        default_assessment = compute_burnout_score(schedule, tasks)
        personalized_assessment = compute_burnout_score(
            schedule,
            tasks,
            max_daily_hours=10.0,
            weekly_hours_threshold=20.0,
            late_night_cutoff=24.0,
            max_consecutive_blocks=5,
            min_breaks_per_day=0,
            deadline_cluster_days=3,
        )

        self.assertGreater(default_assessment["score"], personalized_assessment["score"])
        self.assertGreater(default_assessment["metrics"]["late_night_blocks"], 0)
        self.assertEqual(personalized_assessment["metrics"]["late_night_blocks"], 0)

    def test_deadline_cluster_window_respects_personalized_setting(self) -> None:
        schedule = [
            {"title": "Task A", "day": "Mon", "start": 9.0, "end": 10.0},
            {"title": "Task B", "day": "Wed", "start": 9.0, "end": 10.0},
            {"title": "Task C", "day": "Fri", "start": 9.0, "end": 10.0},
        ]
        tasks = [
            {"title": "Task A", "duration": 1.0, "deadline_day": "Mon"},
            {"title": "Task B", "duration": 1.0, "deadline_day": "Wed"},
            {"title": "Task C", "duration": 1.0, "deadline_day": "Fri"},
        ]

        narrow_window = compute_burnout_score(
            schedule,
            tasks,
            deadline_cluster_days=1,
        )
        wide_window = compute_burnout_score(
            schedule,
            tasks,
            deadline_cluster_days=4,
        )

        self.assertFalse(
            any("deadlines are clustered" in reason for reason in narrow_window["reasons"])
        )
        self.assertTrue(
            any("deadlines are clustered" in reason for reason in wide_window["reasons"])
        )


class BurnoutPipelineTests(unittest.TestCase):
    """Verify pipeline metadata exposes burnout analysis for the optimized plan."""

    def test_pipeline_returns_burnout_metadata_using_personalized_preferences(self) -> None:
        payload = {
            "tasks": [
                {"title": "Studio Work", "duration": 2.5, "deadline_day": "Mon"},
                {"title": "Reflection", "duration": 1.5, "deadline_day": "Tue"},
            ],
            "commitments": [
                {"title": "Late Shift", "day": "Mon", "start": 20.0, "end": 22.0},
            ],
            "sleep_window": {"start": 1.0, "end": 9.0},
            "preferences": {
                "max_daily_hours": 6.0,
                "preferred_study_start": 10.0,
                "preferred_study_end": 24.0,
                "slot_step": 0.5,
                "buffer_hours": 0.5,
                "weekly_hours_threshold": 18.0,
                "late_night_cutoff": 24.0,
                "max_consecutive_blocks": 4,
                "min_breaks_per_day": 0,
                "deadline_cluster_days": 3,
            },
        }

        result = run_pipeline(payload)
        metadata = result["metadata"]

        self.assertIsInstance(metadata["burnout_score"], int)
        self.assertIn(metadata["burnout_level"], {"Low", "Moderate", "High"})
        self.assertIsInstance(metadata["burnout_reasons"], list)
        self.assertIsInstance(metadata["burnout_metrics"], dict)
        self.assertEqual(metadata["burnout_metrics"]["late_night_cutoff"], 24.0)
        self.assertEqual(metadata["burnout_metrics"]["weekly_hours_threshold"], 18.0)
        self.assertEqual(metadata["burnout_metrics"]["min_breaks_per_day"], 0)
        self.assertEqual(metadata["insights"], metadata["burnout_reasons"])

    def test_optimizer_reduces_risk_against_baseline_when_commitments_are_heavy(self) -> None:
        payload = {
            "tasks": [
                {"title": "Essay Draft", "duration": 3.0, "deadline_day": "Sat"},
                {"title": "CS Project", "duration": 5.0, "deadline_day": "Wed"},
                {"title": "HW Set 4", "duration": 2.0, "deadline_day": "Thu"},
            ],
            "commitments": [
                {"title": "CS 101", "day": "Mon", "start": 9.0, "end": 10.5},
                {"title": "Work Shift", "day": "Tue", "start": 14.0, "end": 20.0},
                {"title": "Calculus", "day": "Thu", "start": 11.0, "end": 12.5},
                {"title": "Work Shift", "day": "Thu", "start": 14.0, "end": 20.0},
            ],
            "sleep_window": {"start": 23.0, "end": 7.0},
            "preferences": {
                "max_daily_hours": 8.0,
                "preferred_study_start": 7.0,
                "preferred_study_end": 22.0,
                "slot_step": 0.5,
                "buffer_hours": 1.0,
                "weekly_hours_threshold": 50.0,
                "late_night_cutoff": 23.0,
                "max_consecutive_blocks": 3,
                "min_breaks_per_day": 1,
                "deadline_cluster_days": 2,
            },
        }

        optimized = run_pipeline(payload)
        baseline = build_baseline_schedule(payload)
        settings = _resolve_settings(payload)

        baseline_assessment = assess_burnout(
            commitments=payload["commitments"],
            scheduled_tasks=baseline["scheduled_tasks"],
            tasks=payload["tasks"],
            unscheduled_tasks=baseline["unscheduled_tasks"],
            max_daily_hours=settings["max_daily_hours"],
            weekly_hours_threshold=settings["weekly_hours_threshold"],
            late_night_cutoff=settings["late_night_cutoff"],
            max_consecutive_blocks=int(settings["max_consecutive_blocks"]),
            min_breaks_per_day=int(settings["min_breaks_per_day"]),
            deadline_cluster_days=int(settings["deadline_cluster_days"]),
        )

        self.assertLessEqual(
            optimized["metadata"]["burnout_score"],
            baseline_assessment.score,
        )
