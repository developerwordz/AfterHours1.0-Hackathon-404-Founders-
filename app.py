from recovery import generate_recovery_plan
from gemini_orchestrator import analyse_incident_with_gemini
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from factory import (
    create_factory,
    get_factory_summary,
    simulate_machine_failure
)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="TEXRESQ | Factory Control Tower",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "factory" not in st.session_state:
    st.session_state.factory = create_factory()

if "latest_incident" not in st.session_state:
    st.session_state.latest_incident = None

factory = st.session_state.factory

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("🏭 TEXRESQ")
    st.caption("FACTORY MANAGEMENT SYSTEM")
    st.divider()

    st.markdown("### NAVIGATION")
    st.markdown("📊 Factory Overview")
    st.markdown("⚠️ Incident Management")
    st.markdown("🤖 AI Recovery Centre")
    st.markdown("📋 Production Orders")

    st.divider()
    st.caption("SYSTEM STATUS")
    st.success("Backend Connected")
    st.caption("Gemini integration available")

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("🏭 TEXRESQ")
st.caption("AUTONOMOUS TEXTILE FACTORY | OPERATIONS CONTROL TOWER")

st.divider()

# --------------------------------------------------
# FACTORY OVERVIEW
# --------------------------------------------------

st.subheader("Factory Overview")

machines = factory["machines"]
orders = factory["orders"]

total_machines = len(machines)

running_machines = sum(
    1 for m in machines.values()
    if m["status"] == "RUNNING"
)

active_orders = sum(
    1 for o in orders.values()
    if o["status"] in ["IN_PROGRESS", "QUEUED", "AT_RISK"]
)

active_incidents = len(factory["incidents"])
if "recovery_report" not in st.session_state:
    st.session_state.recovery_report = None

if "gemini_analysis" not in st.session_state:
    st.session_state.gemini_analysis = None
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Machines", total_machines)
c2.metric("Running Machines", running_machines)
c3.metric("Active Orders", active_orders)
c4.metric("Active Incidents", active_incidents)

st.divider()

# --------------------------------------------------
# MACHINE MONITORING
# --------------------------------------------------

st.subheader("Machine Monitoring")

columns = st.columns(len(machines))

for column, (machine_id, machine) in zip(columns, machines.items()):

    with column:
        with st.container(border=True):

            st.markdown(f"### {machine_id}")
            st.markdown(f"**{machine['name']}**")

            status = machine["status"]

            if status == "RUNNING":
                st.success("RUNNING")
            elif status == "IDLE":
                st.info("IDLE")
            elif status == "FAILED":
                st.error("FAILED")
            else:
                st.warning(status)

            st.caption(
                f"Capacity: {machine['capacity_m_per_hr']} m/hr"
            )

            assigned = machine.get("assigned_order_id") or "None"

            st.caption(f"Assigned order: {assigned}")

st.divider()

# --------------------------------------------------
# INCIDENT MANAGEMENT
# --------------------------------------------------

st.subheader("⚠️ Incident Management")

with st.container(border=True):

    st.markdown("### Simulate Machine Failure")

    st.caption(
        "Trigger a controlled disruption to test "
        "TexResQ's autonomous recovery capabilities."
    )

    machine_options = list(factory["machines"].keys())

    selected_machine = st.selectbox(
        "Select machine",
        machine_options,
        format_func=lambda x: (
            f"{x} — {factory['machines'][x]['name']}"
        )
    )

    if st.button("🚨 Simulate Failure", type="primary"):

        if factory["machines"][selected_machine]["status"] == "FAILED":
            st.warning("This machine has already failed.")

        else:
            incident = simulate_machine_failure(
                factory,
                selected_machine
            )

            st.session_state.latest_incident = incident

            st.success(
                f"Failure detected on {selected_machine}!"
            )

            st.rerun()

# Display latest incident

if st.session_state.latest_incident:

    incident = st.session_state.latest_incident

    st.markdown("#### Latest Incident")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Failed Machine",
        incident["machine_id"]
    )

    col2.metric(
        "Affected Orders",
        len(incident["affected_order_ids"])
    )

    col3.metric(
        "Repair Estimate",
        f"{incident['estimated_repair_hrs']} hrs"
    )

    affected = incident["affected_order_ids"]

    st.error(
        f"Machine {incident['machine_id']} has failed. "
        f"Affected orders: {', '.join(affected) if affected else 'None'}"
    )

    if incident.get("required_spare_part"):
        st.caption(
            f"Required spare part: {incident['required_spare_part']}"
        )


st.divider()

# --------------------------------------------------
# AI RECOVERY CENTRE
# --------------------------------------------------

st.subheader("🤖 AI Recovery Centre")

if st.session_state.latest_incident is None:

    st.info("Waiting for a factory disruption. Simulate a machine failure to activate AI recovery.")

else:

    incident = st.session_state.latest_incident

    st.markdown("### Incident Analysis")
    st.write(
        f"Analysing failure of **{incident['machine_id']}** "
        f"and its affected production orders."
    )

    if st.button("🧠 Analyse Recovery Options", type="primary"):

        with st.spinner("Recovery Engine evaluating possible plans..."):

            recovery_report = generate_recovery_plan(
                factory,
                incident
            )

            st.session_state.recovery_report = recovery_report

        with st.spinner("Gemini is analysing the recovery options..."):

            gemini_analysis = analyse_incident_with_gemini(
                factory,
                incident,
                recovery_report
            )

            st.session_state.gemini_analysis = gemini_analysis

    # Display Gemini analysis
    if st.session_state.get("gemini_analysis"):

        st.markdown("### Gemini AI Analysis")

        with st.container(border=True):
            st.markdown(st.session_state.gemini_analysis)

    # Display recovery plans
    if st.session_state.get("recovery_report"):

        report = st.session_state.recovery_report

        st.markdown("### Recovery Plan Comparison")

        for order_id, comparison in report["orders_recovery"].items():

            st.markdown(f"#### Order: {order_id}")

            st.info(comparison["honest_assessment"])

            for index, plan in enumerate(
                comparison["ranked_plans"],
                start=1
            ):

                with st.expander(
                    f"{index}. {plan['name']}",
                    expanded=(index == 1)
                ):

                    col1, col2, col3 = st.columns(3)

                    col1.metric(
                        "Feasible",
                        "Yes" if plan["feasible"] else "No"
                    )

                    col2.metric(
                        "Meets Deadline",
                        "Yes" if plan["meets_deadline"] else "No"
                    )

                    col3.metric(
                        "Additional Cost",
                        f"${plan['additional_cost_usd']:,.2f}"
                    )

                    st.write(
                        f"**Estimated completion:** "
                        f"{plan['total_time_hrs']} hours"
                    )

                    st.write(
                        f"**Evaluation:** {plan['evaluation_notes']}"
                    )

st.divider()

# --------------------------------------------------
# PRODUCTION ORDERS
# --------------------------------------------------


st.subheader("📋 Production Orders")

for order_id, order in orders.items():

    with st.container(border=True):

        col1, col2, col3, col4 = st.columns(4)

        col1.markdown(f"**{order_id}**")
        col1.caption(order["client"])

        col2.metric(
            "Remaining",
            f"{order['remaining_quantity_m']} m"
        )

        col3.metric(
            "Deadline",
            f"{order['deadline_hrs']} hrs"
        )

        col4.write(f"Status: **{order['status']}**")

st.divider()

# --------------------------------------------------
# RAW MATERIAL INVENTORY
# --------------------------------------------------

st.subheader("📦 Raw Material Inventory")

inventory_columns = st.columns(
    len(factory["raw_materials"])
)

for column, (material_id, material) in zip(
    inventory_columns,
    factory["raw_materials"].items()
):

    available = (
        material["stock_kg"] - material["reserved_kg"]
    )

    with column:

        with st.container(border=True):

            st.markdown(f"**{material['name']}**")

            st.metric(
                "Available Stock",
                f"{available:.1f} kg"
            )

            st.caption(f"Material ID: {material_id}")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "TEXRESQ | AI-POWERED FACTORY RESILIENCE SYSTEM"
)
