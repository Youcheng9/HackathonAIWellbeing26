"""FastAPI server for the React frontend."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.integration.pipeline import PipelineInput, run_pipeline
from src.ui.views import assess_burnout, build_baseline_schedule, _resolve_settings


app = FastAPI(title="BalanceAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    """Simple status endpoint for local frontend development."""

    return {"status": "ok"}


@app.post("/api/analyze")
def analyze_schedule(payload: PipelineInput) -> dict[str, Any]:
    """Analyze and optimize a schedule for the React frontend."""

    try:
        optimized_result = run_pipeline(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    before_plan = build_baseline_schedule(payload)
    settings = _resolve_settings(payload)

    before_assessment = assess_burnout(
        commitments=payload.get("commitments", []),
        scheduled_tasks=before_plan["scheduled_tasks"],
        tasks=payload.get("tasks", []),
        unscheduled_tasks=before_plan["unscheduled_tasks"],
        max_daily_hours=settings["max_daily_hours"],
        weekly_hours_threshold=settings["weekly_hours_threshold"],
        late_night_cutoff=settings["late_night_cutoff"],
        max_consecutive_blocks=int(settings["max_consecutive_blocks"]),
        min_breaks_per_day=int(settings["min_breaks_per_day"]),
        deadline_cluster_days=int(settings["deadline_cluster_days"]),
    )

    after_metadata = optimized_result["metadata"]
    after_assessment = {
        "score": after_metadata["burnout_score"],
        "level": after_metadata["burnout_level"],
        "reasons": after_metadata["burnout_reasons"],
        "metrics": after_metadata["burnout_metrics"],
    }

    return {
        "before_plan": before_plan,
        "after_plan": {
            "scheduled_tasks": optimized_result["optimized_schedule"],
            "unscheduled_tasks": optimized_result["unscheduled_tasks"],
        },
        "before_assessment": asdict(before_assessment),
        "after_assessment": after_assessment,
        "metadata": optimized_result["metadata"],
    }
