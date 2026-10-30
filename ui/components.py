
import streamlit as st


def render_agent_timeline(agents_completed=None):

    agents = [
        (
            "Machine Agent",
            "Detected machine failure and assessed repair requirements."
        ),
        (
            "Inventory Agent",
            "Checked raw material stock and spare part availability."
        ),
        (
            "Production Agent",
            "Identified affected orders and evaluated deadlines."
        ),
        (
            "Sourcing Agent",
            "Compared primary and backup supplier options."
        ),
        (
            "Recovery Engine",
            "Generated and ranked recovery plans."
        ),
        (
            "Gemini Orchestrator",
            "Analysed recovery options and explained its recommendation."
        ),
        (
            "Verification Agent",
            "Verified the executed recovery against factory constraints."
        )
    ]

    completed = agents_completed or []

    st.markdown("### Agent Activity")

    for name, description in agents:

        is_completed = name in completed

        status = "🟢 Completed" if is_completed else "⚪ Waiting"

        with st.container(border=True):

            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{name}**")
                st.caption(description)

            with col2:
                st.markdown(status)
