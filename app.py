
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from factory import (
    create_factory,
    simulate_machine_failure,
    simulate_supplier_failure
)

from gemini_orchestrator import run_gemini_orchestrator
from orchestrator import execute_approved_plan

from recovery import (
    apply_supplier_recovery_plan,
    verify_supplier_recovery
)

from ui.styling import apply_theme
from ui.components import render_agent_timeline


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
# STYLING
# --------------------------------------------------

apply_theme()


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

defaults = {
    # Factory
    "factory": create_factory(),

    # Machine recovery
    "latest_incident": None,
    "recovery_report": None,
    "gemini_analysis": None,
    "agent_events": [],
    "orchestration_time": None,

    # Supplier recovery
    "supplier_latest_incident": None,
    "supplier_recovery_report": None,
    "supplier_gemini_analysis": None,
    "supplier_agent_events": [],
    "supplier_orchestration_time": None,
    "supplier_execution_results": {},
    "supplier_incident_history": []
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

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
    st.markdown("🚚 Supply Chain Control Tower")
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
    1 for machine in machines.values()
    if machine["status"] == "RUNNING"
)

active_orders = sum(
    1 for order in orders.values()
    if order["status"] in ["IN_PROGRESS", "QUEUED", "AT_RISK"]
)

active_incidents = (
    len(factory["incidents"])
    + len(factory.get("supplier_incidents", []))
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Machines", total_machines)
c2.metric("Running Machines", running_machines)
c3.metric("Active Orders", active_orders)
c4.metric("Total Incidents", active_incidents)

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
# DYNAMIC SUPPLY CHAIN CONTROL TOWER
# --------------------------------------------------

st.subheader("🚚 Dynamic Supply Chain Control Tower")

suppliers = factory["suppliers"]

tier_columns = st.columns(3)

tier_config = [
    (1, "PRIMARY SUPPLIER", "Lowest cost"),
    (2, "BACKUP SUPPLIER", "Faster delivery"),
    (3, "EMERGENCY SUPPLIER", "Rapid emergency sourcing"),
]

for column, (tier, tier_label, description) in zip(
    tier_columns, tier_config
):
    supplier = next(
        (
            s for s in suppliers.values()
            if s.get("tier") == tier
        ),
        None
    )

    with column:
        with st.container(border=True):

            st.markdown(f"### Tier {tier}")
            st.caption(tier_label)

            if supplier is None:
                st.warning("No supplier configured.")
                continue

            st.markdown(f"**{supplier['name']}**")

            if supplier["status"] == "ACTIVE":
                st.success("ACTIVE")
            else:
                st.error(supplier["status"])

            st.caption(description)

            st.metric(
                "Reliability",
                f"{supplier['reliability_score']}%"
            )

            st.metric(
                "Delivery Time",
                f"{supplier['delivery_time_hrs']} hrs"
            )

            committed = supplier.get("committed_supply_kg", 0.0)
            capacity = supplier.get("max_supply_kg", 0.0)
            remaining = max(0, capacity - committed)

            st.metric(
                "Available Capacity",
                f"{remaining:,.0f} kg"
            )

            st.caption(
                f"Committed: {committed:,.0f} / {capacity:,.0f} kg"
            )

            st.progress(
                min(committed / capacity, 1.0)
                if capacity > 0 else 0.0
            )

            with st.expander("Supplier Pricing"):
                for material_id, price in supplier["cost_per_kg"].items():
                    st.write(f"**{material_id}:** ${price}/kg")

                st.write(
                    f"Rush fee: ${supplier['rush_fee_usd']:,.2f}"
                )


# --------------------------------------------------
# SUPPLIER DISRUPTION SIMULATION
# --------------------------------------------------

st.markdown("### ⚠️ Supplier Disruption Simulation")

st.caption(
    "Simulate supplier failures to test supplier discovery "
    "and recovery-plan generation."
)

active_suppliers = {
    supplier_id: supplier
    for supplier_id, supplier in suppliers.items()
    if supplier.get("status") == "ACTIVE"
}

if active_suppliers:

    selected_supplier = st.selectbox(
        "Select supplier to disrupt",
        list(active_suppliers.keys()),
        format_func=lambda supplier_id: (
            f"{supplier_id} — {suppliers[supplier_id]['name']} "
            f"(Tier {suppliers[supplier_id]['tier']})"
        ),
        key="supplier_failure_selection"
    )

    if st.button(
        "🚨 Simulate Supplier Failure",
        key="simulate_supplier_failure"
    ):

        try:
            supplier_incident = simulate_supplier_failure(
                factory,
                selected_supplier
            )

            # Save supplier incident independently
            st.session_state.supplier_latest_incident = supplier_incident

            # Clear previous supplier analysis
            st.session_state.supplier_recovery_report = None
            st.session_state.supplier_gemini_analysis = None
            st.session_state.supplier_agent_events = []
            st.session_state.supplier_orchestration_time = None
            st.session_state.supplier_execution_results = {}

            # Preserve incident history
            st.session_state.setdefault(
                "supplier_incident_history", []
            ).append(supplier_incident)

            st.success(
                f"{supplier_incident['supplier_name']} "
                "has been marked as FAILED."
            )

            st.rerun()

        except Exception as e:
            st.error(f"Supplier failure simulation failed: {e}")

else:
    st.warning("All configured suppliers are currently unavailable.")


# --------------------------------------------------
# SUPPLIER INCIDENT HISTORY
# --------------------------------------------------

supplier_incidents = factory.get("supplier_incidents", [])

if supplier_incidents:

    st.markdown("### Supplier Disruption History")

    for incident in reversed(supplier_incidents):

        with st.container(border=True):

            st.markdown(
                f"**{incident['incident_id']} — "
                f"{incident['supplier_name']}**"
            )

            st.error(
                f"Tier {incident['supplier_tier']} | "
                f"{incident['incident_type']} | "
                f"{incident['status']}"
            )

            st.caption(
                f"Timestamp: {incident['timestamp']}"
            )

st.divider()


# --------------------------------------------------
# INCIDENT MANAGEMENT - MACHINE FAILURE
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
        format_func=lambda machine_id: (
            f"{machine_id} — {factory['machines'][machine_id]['name']}"
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

            # Clear previous machine analysis
            st.session_state.recovery_report = None
            st.session_state.gemini_analysis = None
            st.session_state.agent_events = []
            st.session_state.orchestration_time = None

            # Clear previous machine approval results
            for key in list(st.session_state.keys()):
                if key.startswith("approved_"):
                    del st.session_state[key]

            st.success(
                f"Failure detected on {selected_machine}!"
            )

            st.rerun()


# --------------------------------------------------
# LATEST MACHINE INCIDENT
# --------------------------------------------------

if st.session_state.latest_incident:

    incident = st.session_state.latest_incident

    st.markdown("#### Latest Machine Incident")

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
# MACHINE AI RECOVERY CENTRE
# --------------------------------------------------

st.subheader("🤖 Machine AI Recovery Centre")

if st.session_state.latest_incident is None:

    st.info(
        "No active machine incident. "
        "Simulate a machine failure to activate machine recovery."
    )

else:

    incident = st.session_state.latest_incident

    st.markdown("### Machine Incident Analysis")

    st.write(
        f"Analysing failure of **{incident['machine_id']}** "
        f"and its affected production orders."
    )

    if st.button("🧠 Analyse Machine Recovery Options", type="primary"):

        try:
            with st.spinner("AI agents investigating machine disruption..."):

                result = run_gemini_orchestrator(
                    factory,
                    incident
                )

                st.session_state.gemini_analysis = result["analysis"]
                st.session_state.agent_events = result["events"]
                st.session_state.recovery_report = result["recovery_report"]
                st.session_state.orchestration_time = result["elapsed_seconds"]

        except Exception as e:
            st.error(f"AI orchestration failed: {e}")

        st.rerun()


    if st.session_state.gemini_analysis:

        st.markdown("### Gemini AI Analysis")

        with st.container(border=True):
            st.markdown(st.session_state.gemini_analysis)


    if st.session_state.orchestration_time is not None:

        st.metric(
            "Orchestration Time",
            f"{st.session_state.orchestration_time} seconds"
        )


    # MACHINE RECOVERY PLAN COMPARISON

    if st.session_state.recovery_report:

        report = st.session_state.recovery_report

        st.markdown("### Machine Recovery Plan Comparison")

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

    elif st.session_state.gemini_analysis:

        st.warning(
            "Gemini completed its analysis, but no machine recovery report "
            "was returned. Check whether the orchestrator invoked "
            "the recovery analysis tool."
        )


# --------------------------------------------------
# MACHINE AGENT ACTIVITY TIMELINE
# --------------------------------------------------

st.markdown("### Machine Agent Activity")

render_agent_timeline(
    st.session_state.get("agent_events", [])
)

st.divider()


# --------------------------------------------------
# MACHINE HUMAN APPROVAL & EXECUTION
# --------------------------------------------------

st.subheader("⚡ Machine Recovery Execution")

if st.session_state.get("recovery_report"):

    report = st.session_state.recovery_report

    for order_id, comparison in report["orders_recovery"].items():

        st.markdown(f"### Recovery for {order_id}")

        plans = comparison["ranked_plans"]

        feasible_plans = [
            plan for plan in plans
            if plan["feasible"]
        ]

        if not feasible_plans:
            st.error("No feasible recovery plan available.")
            continue

        selected_plan = st.selectbox(
            "Select recovery plan",
            feasible_plans,
            format_func=lambda plan: (
                f"{plan['plan_id']} — {plan['name']} "
                f"(${plan['additional_cost_usd']:,.2f})"
            ),
            key=f"plan_{order_id}"
        )

        st.write(
            f"**Deadline:** "
            f"{'Met' if selected_plan['meets_deadline'] else 'Missed'}"
        )

        st.write(
            f"**Estimated completion:** "
            f"{selected_plan['total_time_hrs']} hours"
        )

        st.write(
            f"**Additional cost:** "
            f"${selected_plan['additional_cost_usd']:,.2f}"
        )

        approval_key = f"approved_{order_id}"

        if st.button(
            f"Approve & Execute {order_id}",
            type="primary",
            key=f"execute_{order_id}"
        ):

            try:
                result = execute_approved_plan(
                    factory,
                    selected_plan
                )

                st.session_state[approval_key] = result

                st.success("Recovery action executed!")

                st.rerun()

            except Exception as e:
                st.error(f"Execution failed: {e}")


        if approval_key in st.session_state:

            result = st.session_state[approval_key]

            st.markdown("#### Verification Results")

            verification = result["verification"]

            if verification["verified"]:
                st.success("Recovery successfully verified!")
            else:
                st.error("Recovery verification failed.")

            st.json(verification)

            st.markdown("#### Execution Receipt")
            st.json(result["execution_receipt"])

else:

    st.info(
        "Generate machine recovery plans before executing a recovery."
    )


st.divider()


# --------------------------------------------------
# SUPPLIER AI RECOVERY CENTRE
# --------------------------------------------------

st.subheader("🚚 Supplier AI Recovery Centre")

supplier_incident = st.session_state.supplier_latest_incident

if supplier_incident is None:

    st.info(
        "No active supplier incident. "
        "Simulate a supplier failure to activate supplier recovery."
    )

else:

    failed_supplier_id = supplier_incident["supplier_id"]
    failed_supplier = factory["suppliers"][failed_supplier_id]

    st.markdown("### Supplier Incident Analysis")

    c1, c2, c3 = st.columns(3)

    c1.metric("Failed Supplier", failed_supplier_id)
    c2.metric("Supplier Tier", failed_supplier["tier"])
    c3.metric("Incident ID", supplier_incident["incident_id"])

    st.error(
        f"{failed_supplier['name']} is unavailable. "
        "TexResQ is investigating supply-chain impact."
    )

    if st.button(
        "🧠 Analyse Supplier Recovery Options",
        type="primary",
        key="analyse_supplier_recovery"
    ):

        try:
            with st.spinner("Gemini agents analysing supplier disruption..."):

                result = run_gemini_orchestrator(
                    factory,
                    supplier_incident
                )

                st.session_state.supplier_gemini_analysis = result["analysis"]
                st.session_state.supplier_agent_events = result["events"]
                st.session_state.supplier_recovery_report = result["recovery_report"]
                st.session_state.supplier_orchestration_time = result["elapsed_seconds"]

        except Exception as e:
            st.error(f"Supplier AI orchestration failed: {e}")

        st.rerun()


    # SUPPLIER GEMINI ANALYSIS

    if st.session_state.supplier_gemini_analysis:

        st.markdown("### Gemini Supplier Analysis")

        with st.container(border=True):
            st.markdown(st.session_state.supplier_gemini_analysis)


    # SUPPLIER ORCHESTRATION METRICS

    if st.session_state.supplier_orchestration_time is not None:

        st.metric(
            "Supplier Analysis Time",
            f"{st.session_state.supplier_orchestration_time} seconds"
        )


    # SUPPLIER RECOVERY COMPARISON

    supplier_report = st.session_state.supplier_recovery_report

    if supplier_report:

        st.markdown("### Supplier Recovery Comparison")

        orders_recovery = supplier_report.get("orders_recovery", {})

        total_proposed_cost = 0.0
        total_proposed_quantity = 0.0

        for order_id, comparison in orders_recovery.items():

            st.markdown(f"#### {order_id} — {comparison['client']}")

            st.info(comparison["honest_assessment"])

            st.write(
                f"**Material:** {comparison['material_id']} | "
                f"**Shortfall:** {comparison['shortfall_kg']} kg | "
                f"**Stock coverage:** "
                f"{comparison['stock_coverage_hrs'] if comparison['stock_coverage_hrs'] is not None else 'N/A'} hrs"
            )

            recommended = comparison.get("recommended_plan")

            if recommended is None:
                st.success("Existing inventory is sufficient. No procurement needed.")
                continue

            total_proposed_cost += recommended["procurement_cost_usd"]
            total_proposed_quantity += recommended["quantity_kg"]

            plans = comparison.get("ranked_plans", [])

            # VISUAL SUPPLIER COMPARISON CARDS

            supplier_columns = st.columns(len(plans)) if plans else []

            for index, plan in enumerate(plans):

                with supplier_columns[index]:

                    with st.container(border=True):

                        if plan["plan_id"] == recommended["plan_id"]:
                            st.success("RECOMMENDED")
                        else:
                            st.caption("ALTERNATIVE")

                        st.markdown(f"### {plan['supplier_name']}")

                        st.caption(
                            f"Tier {plan['supplier_tier']} · "
                            f"{plan['supplier_id']}"
                        )

                        st.metric(
                            "Procurement Cost",
                            f"${plan['procurement_cost_usd']:,.2f}"
                        )

                        st.metric(
                            "Delivery",
                            f"{plan['delivery_time_hrs']} hrs"
                        )

                        st.metric(
                            "Reliability",
                            f"{plan['reliability_score']}%"
                        )

                        st.metric(
                            "Available Capacity",
                            f"{plan['remaining_capacity_kg']:,.0f} kg"
                        )

                        st.caption(
                            f"Quantity: {plan['quantity_kg']} kg"
                        )

                        st.caption(
                            "Protects current stock"
                            if plan["protects_stock"]
                            else "Stock-out risk"
                        )

                        st.caption(plan["evaluation_notes"])


            # HUMAN APPROVAL

            st.markdown("##### Human Approval")

            feasible_plans = [
                plan for plan in plans
                if plan["feasible"]
            ]

            if not feasible_plans:
                st.error("No feasible replacement supplier available.")
                continue

            selected_supplier_plan = st.selectbox(
                "Choose supplier recovery plan",
                feasible_plans,
                index=next(
                    (
                        index for index, plan in enumerate(feasible_plans)
                        if plan["plan_id"] == recommended["plan_id"]
                    ),
                    0
                ),
                format_func=lambda plan: (
                    f"{plan['supplier_name']} | "
                    f"{plan['delivery_time_hrs']}h | "
                    f"${plan['procurement_cost_usd']:,.2f}"
                ),
                key=f"supplier_plan_{order_id}"
            )

            st.warning(
                "This is a simulated procurement action. "
                "Approval will update the factory's in-memory inventory "
                "and supplier commitment."
            )

            execution_key = f"supplier_execution_results"

            existing_execution = st.session_state[
                execution_key
            ].get(order_id)

            if existing_execution:

                st.success("Supplier recovery execution recorded.")

                verification = existing_execution["verification"]

                if verification["verified"]:
                    st.success("Supplier recovery VERIFIED.")
                else:
                    st.error("Supplier recovery verification FAILED.")

                st.markdown("##### Verification Checks")

                for check_name, passed in verification["checks"].items():

                    if passed:
                        st.success(f"✓ {check_name.replace('_', ' ').title()}")
                    else:
                        st.error(f"✗ {check_name.replace('_', ' ').title()}")

                st.markdown("##### Execution Receipt")
                st.json(existing_execution["execution_receipt"])

            else:

                if st.button(
                    f"Approve & Execute Supplier Recovery — {order_id}",
                    type="primary",
                    key=f"execute_supplier_{order_id}"
                ):

                    try:

                        execution = apply_supplier_recovery_plan(
                            factory,
                            selected_supplier_plan,
                            supplier_incident
                        )

                        if not execution["success"]:
                            st.error(execution.get("message", "Execution failed."))

                        else:

                            verification = verify_supplier_recovery(
                                factory,
                                order_id
                            )

                            st.session_state.supplier_execution_results[
                                order_id
                            ] = {
                                "execution_receipt": execution["execution_receipt"],
                                "state_changes": execution["state_changes"],
                                "verification": verification
                            }

                            st.rerun()

                    except Exception as e:
                        st.error(
                            f"Supplier recovery execution failed: {e}"
                        )


        # TOTAL SUPPLIER RECOVERY METRICS

        st.divider()
        st.markdown("### Supplier Recovery Summary")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Proposed Procurement",
            f"{total_proposed_quantity:,.0f} kg"
        )

        c2.metric(
            "Estimated Total Cost",
            f"${total_proposed_cost:,.2f}"
        )

        c3.metric(
            "Orders Assessed",
            len(orders_recovery)
        )


    # SUPPLIER AGENT TIMELINE

    st.markdown("### Supplier Agent Activity")

    render_agent_timeline(
        st.session_state.supplier_agent_events
    )

    if (
        st.session_state.supplier_gemini_analysis
        and not st.session_state.supplier_recovery_report
    ):
        st.warning(
            "Gemini completed its analysis, but no supplier recovery "
            "report was returned. Check the Supplier Recovery Engine tool."
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
