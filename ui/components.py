
import streamlit as st


def render_agent_timeline(events=None):

    st.markdown("### 🧠 Agent Activity")

    if not events:
        st.info(
            "No agent activity recorded yet. "
            "Run AI Recovery Analysis to activate the agents."
        )
        return

    st.caption(
        f"{len(events)} agent/tool operations recorded"
    )

    for index, event in enumerate(events, start=1):

        agent_name = event.get("agent", "Unknown Agent")
        status = event.get("status", "Unknown")
        result = event.get("result", {})

        with st.container(border=True):

            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**{index}. {agent_name}**")

            with col2:
                if status == "Completed":
                    st.success(status)
                else:
                    st.warning(status)

            with st.expander("View agent findings"):

                if isinstance(result, (dict, list)):
                    st.json(result)
                else:
                    st.write(result)
