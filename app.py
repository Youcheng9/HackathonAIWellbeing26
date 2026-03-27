"""Streamlit entrypoint for the BalanceAI demo app."""

from __future__ import annotations

import streamlit as st

from src.integration.pipeline import run_pipeline
from src.ui.forms import load_sample_payload, render_input_panel
from src.ui.views import inject_theme, render_header, render_results


def _run_and_store(payload: dict) -> None:
    """Execute the integration pipeline and persist the latest result."""

    result = run_pipeline(payload)
    st.session_state["latest_payload"] = payload
    st.session_state["latest_result"] = result
    st.session_state["latest_error"] = None


def main() -> None:
    """Render the Streamlit UI."""

    st.set_page_config(
        page_title="BalanceAI | Burnout-Safe Scheduler",
        page_icon="B",
        layout="wide",
    )

    inject_theme()
    render_header()

    sample_payload = load_sample_payload()
    payload, run_clicked = render_input_panel(sample_payload)

    if "latest_result" not in st.session_state:
        try:
            _run_and_store(sample_payload)
        except ValueError as exc:  # pragma: no cover - defensive fallback
            st.session_state["latest_error"] = str(exc)

    if run_clicked:
        try:
            _run_and_store(payload)
        except ValueError as exc:
            st.session_state["latest_error"] = str(exc)

    latest_error = st.session_state.get("latest_error")
    if latest_error:
        st.error(latest_error)
        st.info("Fix the highlighted input values, then run analysis again.")
        return

    latest_payload = st.session_state.get("latest_payload", payload)
    latest_result = st.session_state.get("latest_result")
    if latest_result:
        render_results(payload=latest_payload, optimized_result=latest_result)


if __name__ == "__main__":
    main()
