
import streamlit as st
import pandas as pd

from factory import simulate_batch_production
from quality.quality_monitor import monitor_factory_quality
from quality.quality_agent import run_quality_agent


def normalize_reports(reports):
    """
    Convert quality reports into a consistent dictionary:
    {
        machine_id: report
    }

    Supports both list and dictionary formats.
    """

    if isinstance(reports, dict):
        return reports

    normalized = {}

    if isinstance(reports, list):
        for index, report in enumerate(reports):

            if not isinstance(report, dict):
                continue

            machine_id = report.get(
                "machine_id",
                f"Machine {index + 1}"
            )

            normalized[machine_id] = report

    return normalized


def render_quality_dashboard(factory):

    machines = factory.get("machines", {})
    batches = factory.get("quality_history", [])
    interventions = factory.get("quality_interventions", [])

    st.title("📊 Quality Control Centre")
    st.caption(
        "Production quality monitoring, batch inspection, "
        "machine deterioration analysis and autonomous corrective action."
    )

    st.divider()

    # ========================================================
    # QUALITY SUMMARY
    # ========================================================

    quality_report = monitor_factory_quality(factory)

    reports = normalize_reports(
        quality_report.get("reports", [])
    )

    total_batches = len(batches)

    machines_monitored = quality_report.get(
        "machines_analyzed",
        len(reports)
    )

    active_alerts = quality_report.get(
        "machines_with_alerts",
        0
    )

    factory_status = quality_report.get(
        "factory_quality_status",
        "MONITORING"
    )

    rejected_batches = sum(
        1
        for batch in batches
        if batch.get("inspection_status") == "REJECTED"
    )

    average_quality = (
        sum(
            batch.get("quality_score", 0)
            for batch in batches
        ) / total_batches
        if total_batches else 0
    )

    metric_cols = st.columns(5)

    metric_cols[0].metric(
        "Batches Produced",
        total_batches
    )

    metric_cols[1].metric(
        "Average Quality",
        f"{average_quality:.2f}" if total_batches else "N/A"
    )

    metric_cols[2].metric(
        "Active Quality Alerts",
        active_alerts
    )

    metric_cols[3].metric(
        "Rejected Batches",
        rejected_batches
    )

    metric_cols[4].metric(
        "Factory Status",
        factory_status
    )

    st.divider()

    # ========================================================
    # BATCH PRODUCTION
    # ========================================================

    st.subheader("🏭 Batch Production Simulator")

    st.caption(
        "Produce a batch from an active machine and automatically "
        "generate its quality inspection report."
    )

    eligible_machines = {}

    for machine_id, machine in machines.items():

        assigned_order_id = machine.get("assigned_order_id")

        if machine.get("status") != "RUNNING":
            continue

        if not assigned_order_id:
            continue

        order = factory.get("orders", {}).get(
            assigned_order_id,
            {}
        )

        if order.get("status") in (
            "IN_PROGRESS",
            "REASSIGNED"
        ):
            eligible_machines[machine_id] = machine

    if eligible_machines:

        selected_machine_id = st.selectbox(
            "Select Production Machine",
            list(eligible_machines.keys()),
            format_func=lambda machine_id: (
                f"{machine_id} — "
                f"{eligible_machines[machine_id].get('name', machine_id)}"
            ),
            key="quality_production_machine"
        )

        selected_machine = eligible_machines[
            selected_machine_id
        ]

        st.info(
            f"Assigned order: "
            f"**{selected_machine.get('assigned_order_id')}**"
        )

        if st.button(
            "▶️ PRODUCE BATCH & RUN QUALITY INSPECTION",
            type="primary",
            use_container_width=True,
            key="produce_quality_batch"
        ):

            try:

                result = simulate_batch_production(
                    factory,
                    selected_machine_id
                )

                st.session_state["last_quality_batch"] = result

                st.success(
                    "Batch produced and quality inspection completed."
                )

                st.rerun()

            except Exception as error:

                st.error(
                    f"Batch production failed: {error}"
                )

    else:

        st.warning(
            "No eligible running machines with active production orders "
            "are available."
        )

    last_batch = st.session_state.get(
        "last_quality_batch"
    )

    if last_batch:

        with st.expander(
            "📋 Latest Batch Inspection Result",
            expanded=True
        ):

            result_cols = st.columns(4)

            result_cols[0].metric(
                "Batch ID",
                last_batch.get("batch_id", "N/A")
            )

            result_cols[1].metric(
                "Quality Score",
                f"{last_batch.get('quality_score', 0):.2f}"
            )

            result_cols[2].metric(
                "Grade",
                last_batch.get("grade", "N/A")
            )

            result_cols[3].metric(
                "Inspection",
                last_batch.get("inspection_status", "N/A")
            )

            st.json(last_batch)

    st.divider()

    # ========================================================
    # MACHINE QUALITY MONITORING
    # ========================================================

    st.subheader("⚙️ Machine Quality Monitoring")

    st.caption(
        "Track machine wear, production quality deterioration "
        "and metric-level deviations."
    )

    if not reports:

        st.info("No machine quality reports are available yet.")

    for machine_id, report in reports.items():

        machine = machines.get(machine_id, {})

        machine_name = machine.get(
            "name",
            machine_id
        )

        alert = report.get("alert", False)

        severity = report.get(
            "severity",
            "NONE"
        )

        with st.container(border=True):

            heading_col, status_col = st.columns([3, 1])

            with heading_col:

                st.markdown(f"### {machine_name}")

                st.caption(
                    f"Machine ID: {machine_id}"
                )

            with status_col:

                if alert:
                    st.error(f"⚠️ {severity} ALERT")

                elif report.get("status") == "INSUFFICIENT_DATA":
                    st.warning("INSUFFICIENT DATA")

                else:
                    st.success("HEALTHY")

            c1, c2, c3, c4 = st.columns(4)

            latest_score = report.get("latest_score")

            c1.metric(
                "Latest Quality Score",
                (
                    f"{latest_score:.2f}"
                    if isinstance(latest_score, (int, float))
                    else "N/A"
                )
            )

            c2.metric(
                "Machine Wear",
                f"{report.get('machine_wear', 0):.1f}%"
            )

            c3.metric(
                "Machine Condition",
                f"{report.get('machine_condition', 100):.1f}%"
            )

            c4.metric(
                "Batches Analyzed",
                report.get("batches_analyzed", 0)
            )

            st.write(
                report.get(
                    "message",
                    "No additional information."
                )
            )

            problem_metrics = report.get(
                "problem_metrics",
                []
            )

            if problem_metrics:

                st.markdown("**Detected Quality Problems**")

                if isinstance(problem_metrics, list):

                    for problem in problem_metrics:

                        if isinstance(problem, dict):

                            metric_name = problem.get(
                                "metric",
                                problem.get("name", "Unknown metric")
                            )

                            st.warning(
                                f"{metric_name}: "
                                f"{problem.get('message', problem.get('decline', 'Quality deterioration detected'))}"
                            )

                        else:

                            st.warning(str(problem))

                else:

                    st.warning(str(problem_metrics))

            trends = report.get(
                "metric_trends",
                {}
            )

            if trends:

                with st.expander(
                    "View Metric-Level Quality Trends"
                ):

                    st.json(trends)

            with st.expander(
                "View Complete Machine Analysis"
            ):

                st.json(report)

    st.divider()

    # ========================================================
    # BATCH QUALITY HISTORY
    # ========================================================

    st.subheader("📈 Batch Quality History")

    if batches:

        available_machine_ids = sorted(
            set(
                batch.get("machine_id")
                for batch in batches
                if batch.get("machine_id") is not None
            )
        )

        if available_machine_ids:

            selected_history_machine = st.selectbox(
                "Select Machine",
                available_machine_ids,
                key="quality_history_machine"
            )

            machine_batches = [
                batch
                for batch in batches
                if batch.get("machine_id") == selected_history_machine
            ]

            machine_batches.sort(
                key=lambda batch: batch.get(
                    "machine_batch_number",
                    0
                )
            )

            if machine_batches:

                scores = [
                    batch.get("quality_score", 0)
                    for batch in machine_batches
                ]

                st.markdown("**Quality Score Progression**")

                st.line_chart(scores)

                history_rows = []

                for batch in reversed(machine_batches):

                    history_rows.append({

                        "Batch ID": batch.get("batch_id"),

                        "Batch Number": batch.get(
                            "machine_batch_number"
                        ),

                        "Quality Score": batch.get(
                            "quality_score"
                        ),

                        "Grade": batch.get("grade"),

                        "Inspection": batch.get(
                            "inspection_status"
                        ),

                        "Wear Before": batch.get(
                            "wear_before",
                            batch.get("wear_level_before")
                        ),

                        "Wear After": batch.get(
                            "wear_after",
                            batch.get("wear_level_after")
                        )

                    })

                st.dataframe(
                    pd.DataFrame(history_rows),
                    use_container_width=True,
                    hide_index=True
                )

        else:

            st.info(
                "Batch records do not contain machine IDs."
            )

    else:

        st.info(
            "No production batches have been recorded yet."
        )

    st.divider()

    # ========================================================
    # AUTONOMOUS QUALITY AGENT
    # ========================================================

    st.subheader("🤖 Autonomous Quality Agent")

    st.write(
        "The Quality Agent analyzes machine deterioration, "
        "diagnoses quality problems and determines whether "
        "corrective maintenance or increased monitoring is required."
    )

    if st.button(
        "🧠 RUN AUTONOMOUS QUALITY AGENT",
        type="primary",
        use_container_width=True,
        key="run_quality_agent"
    ):

        try:

            with st.spinner(
                "Quality Agent analyzing machine telemetry "
                "and production history..."
            ):

                agent_result = run_quality_agent(factory)

                st.session_state[
                    "quality_agent_last_result"
                ] = agent_result

            st.success(
                "Quality Agent execution completed."
            )

            st.rerun()

        except Exception as error:

            st.error(
                f"Quality Agent execution failed: {error}"
            )

    agent_result = st.session_state.get(
        "quality_agent_last_result"
    )

    if agent_result is not None:

        st.markdown("#### Latest Agent Execution")

        st.json(agent_result)

    st.divider()

    # ========================================================
    # MAINTENANCE HISTORY
    # ========================================================

    st.subheader("🛠 Corrective Maintenance History")

    if interventions:

        intervention_rows = []

        for intervention in reversed(interventions):

            intervention_rows.append({

                "Intervention ID": intervention.get(
                    "intervention_id"
                ),

                "Machine ID": intervention.get(
                    "machine_id"
                ),

                "Type": intervention.get(
                    "intervention_type"
                ),

                "Reason": intervention.get(
                    "reason"
                ),

                "Wear Before": intervention.get(
                    "wear_before"
                ),

                "Wear After": intervention.get(
                    "wear_after"
                ),

                "Timestamp": intervention.get(
                    "timestamp"
                )

            })

        st.dataframe(
            pd.DataFrame(intervention_rows),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No quality-related maintenance interventions recorded yet."
        )

    st.caption(
        "TEXRESQ QUALITY INTELLIGENCE SYSTEM · "
        "AUTONOMOUS PRODUCTION QUALITY MONITORING"
    )
