
import sys
from pathlib import Path

import streamlit as st

# ============================================================
# PROJECT PATH
# ============================================================

sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# PROJECT IMPORTS
# ============================================================

from factory import (
    create_factory,
    simulate_machine_failure,
    simulate_supplier_failure,
)

from supply_chain_agent import initialize_supply_chain
from ui.supply_chain import render_supply_chain_dashboard

from gemini_orchestrator import run_gemini_orchestrator

from recovery import (
    generate_supplier_recovery_plan,
    apply_supplier_recovery_plan,
    verify_supplier_recovery,
)

from orchestrator import execute_approved_plan

from ui.styling import apply_theme
from ui.components import render_agent_timeline

from ui.tiles import (
    inject_tile_css,
    render_machine_grid,
    inventory_tile,
)

from quality.dashboard import render_quality_dashboard


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="TEXRESQ | Autonomous Factory Control Tower",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
inject_tile_css()


# ============================================================
# ENTERPRISE CSS
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1650px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.015);
        transition: all 0.2s ease-in-out;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(56, 189, 248, 0.3);
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 16px;
        border-radius: 12px;
    }

    div[data-testid="stMetric"] label {
        font-size: 0.85rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        opacity: 0.7;
    }

    div[data-testid="stButton"] button {
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: all 0.2s ease-in-out;
    }

    div[data-testid="stButton"] button:hover {
        border-color: #38bdf8;
        color: #38bdf8;
        transform: translateY(-1px);
    }

    .machine-hero {
        text-align: center;
        padding: 30px 10px 20px;
        background: linear-gradient(
            180deg,
            rgba(56, 189, 248, 0.05) 0%,
            rgba(0,0,0,0) 100%
        );
        border-radius: 16px;
        margin-bottom: 1.5rem;
    }

    .machine-hero-icon {
        font-size: 64px;
        margin-bottom: 10px;
    }

    .machine-hero-id {
        font-size: 12px;
        letter-spacing: 3px;
        opacity: 0.6;
        text-transform: uppercase;
    }

    .machine-hero-name {
        font-size: clamp(24px, 4vw, 42px);
        font-weight: 800;
        margin-top: 4px;
    }

    .machine-hero-status {
        font-size: 16px;
        margin-top: 10px;
        font-weight: 500;
    }

    .status-badge {
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "factory": create_factory(),
    "selected_machine": None,
    "selected_material": None,
    "active_page": "Factory Floor",

    # Machine recovery
    "latest_incident": None,
    "recovery_report": None,
    "gemini_analysis": None,
    "agent_events": [],
    "orchestration_time": None,
    "machine_execution_results": {},

    # Supplier recovery
    "supplier_latest_incident": None,
    "supplier_recovery_report": None,
    "supplier_gemini_analysis": None,
    "supplier_agent_events": [],
    "supplier_orchestration_time": None,
    "supplier_execution_results": {},

    # Inventory
    "inventory_incidents": [],

    # Quality
    "quality_agent_last_result": None,
    "last_quality_batch": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

factory = st.session_state.factory

# Initialize the material-specific supply networks.
initialize_supply_chain(factory)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clear_machine_recovery():
    st.session_state.latest_incident = None
    st.session_state.recovery_report = None
    st.session_state.gemini_analysis = None
    st.session_state.agent_events = []
    st.session_state.orchestration_time = None
    st.session_state.machine_execution_results = {}


def clear_supplier_recovery():
    st.session_state.supplier_latest_incident = None
    st.session_state.supplier_recovery_report = None
    st.session_state.supplier_gemini_analysis = None
    st.session_state.supplier_agent_events = []
    st.session_state.supplier_orchestration_time = None
    st.session_state.supplier_execution_results = {}


def render_status(status):
    status = str(status).upper()

    if status in ("RUNNING", "ACTIVE", "VERIFIED", "RESOLVED"):
        st.success(f"● {status}")

    elif status in ("IDLE", "QUEUED", "AT_RISK", "WARNING"):
        st.warning(f"▲ {status}")

    elif status in ("FAILED", "OFFLINE", "OPEN"):
        st.error(f"■ {status}")

    else:
        st.info(f"ℹ {status}")


def simulate_inventory_shortage(material_id):
    material = factory["raw_materials"].get(material_id)

    if not material:
        return False, "Material not found."

    stock = number(material.get("stock_kg", 0))
    reserved = number(material.get("reserved_kg", 0))
    available = max(0, stock - reserved)

    if available <= 0:
        return False, "No unreserved inventory available."

    shortage = round(available * 0.25, 2)
    material["stock_kg"] = round(stock - shortage, 2)

    incident = {
        "incident_id": (
            f"INV-INC-{len(st.session_state.inventory_incidents) + 1:03d}"
        ),
        "incident_type": "INVENTORY_SHORTAGE",
        "material_id": material_id,
        "material_name": material.get("name", material_id),
        "quantity_lost_kg": shortage,
        "status": "OPEN",
    }

    st.session_state.inventory_incidents.append(incident)

    return True, incident


# ============================================================
# MACHINE PROFILE
# ============================================================

def render_machine_profile(machine_id):

    machine = factory["machines"].get(machine_id)

    if not machine:
        st.session_state.selected_machine = None
        st.rerun()

    status = str(machine.get("status", "UNKNOWN")).upper()

    status_icon = {
        "RUNNING": "🟢",
        "IDLE": "🟡",
        "FAILED": "🔴",
    }.get(status, "⚪")

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stHeader"] { display: none !important; }

        .block-container {
            max-width: 1400px;
            padding-top: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← RETURN TO FACTORY CONTROL FLOOR"):
        st.session_state.selected_machine = None
        st.rerun()

    st.markdown(
        f"""
        <div class="machine-hero">
            <div class="machine-hero-icon">⚙️</div>

            <div class="machine-hero-id">
                TEXRESQ // MACHINERY ASSET // {machine_id}
            </div>

            <div class="machine-hero-name">
                {machine.get('name', machine_id)}
            </div>

            <div class="machine-hero-status">
                {status_icon} OPERATIONAL STATUS: {status}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 Operational Telemetry")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Production Capacity",
        f"{machine.get('capacity_m_per_hr', 0)} m/hr",
    )

    col2.metric(
        "Assigned Production Order",
        machine.get("assigned_order_id") or "Unassigned",
    )

    col3.metric(
        "Maintenance Duration",
        f"{machine.get('maintenance_duration_hrs', 'N/A')} hrs",
    )

    st.divider()

    left_col, right_col = st.columns([1.3, 1], gap="large")

    with left_col:

        with st.container(border=True):

            st.markdown("#### 🛠 Technical Specifications")

            st.markdown("**Compatible Raw Materials**")

            compatible = machine.get("compatible_materials", [])

            if compatible:
                for mat in compatible:
                    st.markdown(f"- `{mat}`")
            else:
                st.caption("No specific material restrictions recorded.")

            st.markdown("**Required Maintenance Spare Part**")

            st.info(machine.get("required_spare_part", "Not specified"))

            st.markdown("**Health Status Verification**")

            render_status(status)

    with right_col:

        with st.container(border=True):

            st.markdown("#### ⚡ Asset Diagnostics & Control")

            if status != "FAILED":

                if st.button(
                    "⚠️ SIMULATE MACHINE FAILURE",
                    key=f"fail_{machine_id}",
                    use_container_width=True,
                ):

                    incident = simulate_machine_failure(
                        factory,
                        machine_id,
                    )

                    clear_machine_recovery()

                    st.session_state.latest_incident = incident

                    st.success(
                        f"Disruption successfully triggered on {machine_id}"
                    )

                    st.rerun()

            else:
                st.error(
                    "Asset is currently FAILED. "
                    "Open AI Recovery Centre to resolve."
                )

            with st.expander("🔍 Inspect Raw Asset JSON"):
                st.json(machine)

    incident = st.session_state.latest_incident

    if incident and incident.get("machine_id") == machine_id:

        st.divider()
        st.markdown("### 🚨 Active Incident Diagnostics")
        st.error(f"Critical fault detected on asset {machine_id}.")
        st.json(incident)

        if st.button(
            "🧠 Run Gemini Autonomous Recovery Orchestrator",
            type="primary",
            key=f"prof_run_{machine_id}",
        ):

            try:

                with st.spinner(
                    "Gemini agents analyzing telemetry and generating recovery paths..."
                ):

                    result = run_gemini_orchestrator(factory, incident)

                    st.session_state.gemini_analysis = result["analysis"]
                    st.session_state.agent_events = result["events"]
                    st.session_state.recovery_report = result["recovery_report"]
                    st.session_state.orchestration_time = result["elapsed_seconds"]

                st.success("Autonomous analysis complete!")
                st.rerun()

            except Exception as error:
                st.error(f"Orchestration failure: {error}")

        if st.session_state.gemini_analysis:

            st.markdown("#### 🤖 Gemini Operations Report")

            with st.container(border=True):
                st.markdown(st.session_state.gemini_analysis)

            st.caption(
                f"Orchestration Execution Time: "
                f"{st.session_state.orchestration_time}s"
            )

        report = st.session_state.recovery_report

        if report:

            st.markdown("#### 📋 Recommended Recovery Strategies")

            for order_id, comp in report.get("orders_recovery", {}).items():

                st.markdown(f"**Order ID: {order_id}**")
                st.info(comp.get("honest_assessment", ""))

                for idx, plan in enumerate(
                    comp.get("ranked_plans", []),
                    1,
                ):

                    with st.expander(
                        f"Plan {idx}: {plan.get('name', plan.get('plan_id'))}"
                    ):

                        mc1, mc2, mc3 = st.columns(3)

                        mc1.metric(
                            "Feasible",
                            "YES" if plan.get("feasible") else "NO",
                        )

                        mc2.metric(
                            "Deadline Met",
                            "MET" if plan.get("meets_deadline") else "MISSED",
                        )

                        mc3.metric(
                            "Additional Cost",
                            f"${number(plan.get('additional_cost_usd')):,.2f}",
                        )

                        st.write(
                            f"**Completion Time:** "
                            f"{plan.get('total_time_hrs', 'N/A')} hrs"
                        )

                        st.write(plan.get("evaluation_notes", ""))

        if st.session_state.agent_events:

            st.markdown("#### 🔄 Agent Coordination Timeline")

            render_agent_timeline(st.session_state.agent_events)

    st.divider()

    st.caption(
        f"TEXRESQ INDUSTRIAL AUTOMATION SYSTEM · "
        f"MACHINE CONTROL NODE: {machine_id}"
    )


# ============================================================
# SCREEN ROUTING
# ============================================================

if st.session_state.selected_machine is not None:

    if st.session_state.selected_machine in factory["machines"]:
        render_machine_profile(st.session_state.selected_machine)
        st.stop()

    else:
        st.session_state.selected_machine = None
        st.rerun()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.title("🏭 TEXRESQ")
    st.caption("FACTORY CONTROL TOWER")

    st.divider()
    st.markdown("### NAVIGATION")

    pages = [
        ("🏭", "Factory Floor"),
        ("📊", "Quality Control"),
        ("📦", "Inventory"),
        ("🚚", "Supply Chain"),
        ("🤖", "AI Recovery"),
        ("📋", "Production Orders"),
    ]

    for icon, page in pages:

        if st.button(
            f"{icon}  {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type=(
                "primary"
                if st.session_state.active_page == page
                else "secondary"
            ),
        ):

            st.session_state.active_page = page
            st.session_state.selected_machine = None
            st.rerun()

    st.divider()

    st.caption("SYSTEM STATUS")
    st.success("Factory backend connected")
    st.success("Gemini integration configured")

    st.divider()

    st.caption("ACTIVE DISRUPTIONS")

    machine_count = 1 if st.session_state.latest_incident else 0
    supplier_count = 1 if st.session_state.supplier_latest_incident else 0
    inventory_count = len(st.session_state.inventory_incidents)

    st.metric(
        "Open Simulations",
        machine_count + supplier_count + inventory_count,
    )


# ============================================================
# QUALITY CONTROL PAGE
# ============================================================

if st.session_state.active_page == "Quality Control":

    render_quality_dashboard(factory)
    st.stop()


# ============================================================
# SUPPLY CHAIN PAGE
# ============================================================

if st.session_state.active_page == "Supply Chain":

    st.title("🚚 Material-Specific Supply Chain Control")

    st.caption(
        "Autonomous supplier monitoring, material-specific sourcing "
        "and intelligent supplier failover."
    )

    render_supply_chain_dashboard(
        factory,
        simulate_supplier_failure,
    )

    st.stop()


# ============================================================
# DASHBOARD HEADER
# ============================================================

header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.title("TEXRESQ CONTROL TOWER")
    st.caption(
        "Autonomous Self-Recovering Textile Factory Operations Engine"
    )

with header_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.success("🟢 SYSTEM ONLINE & SECURE")

st.divider()


# ============================================================
# FACTORY DATA
# ============================================================

machines = factory["machines"]
orders = factory["orders"]
materials = factory["raw_materials"]
suppliers = factory["suppliers"]


# ============================================================
# EXECUTIVE METRICS
# ============================================================

running_machines = sum(
    1 for machine in machines.values()
    if machine.get("status") == "RUNNING"
)

failed_machines = sum(
    1 for machine in machines.values()
    if machine.get("status") == "FAILED"
)

active_orders = sum(
    1 for order in orders.values()
    if order.get("status") in (
        "IN_PROGRESS",
        "QUEUED",
        "AT_RISK",
    )
)

active_suppliers = sum(
    1 for supplier in suppliers.values()
    if supplier.get("status") == "ACTIVE"
)

metric_cols = st.columns(4)

metric_cols[0].metric(
    "Active Machinery",
    f"{running_machines}/{len(machines)}",
    delta=(
        f"{failed_machines} failed"
        if failed_machines
        else "All optimal"
    ),
    delta_color="inverse",
)

metric_cols[1].metric("Active Production Orders", active_orders)

metric_cols[2].metric(
    "Supplier Network Health",
    f"{active_suppliers}/{len(suppliers)}",
)

metric_cols[3].metric("Tracked Raw Materials", len(materials))

st.divider()


# ============================================================
# FACTORY FLOOR
# ============================================================

st.subheader("🏭 Factory Floor — Asset Grid")

st.caption(
    "Select any machine tile to inspect telemetry or simulate failures."
)

selected_machine_id = render_machine_grid(machines, columns=3)

if selected_machine_id:
    st.session_state.selected_machine = selected_machine_id
    st.rerun()

st.divider()


# ============================================================
# INVENTORY MANAGEMENT
# ============================================================

st.subheader("📦 Raw Material Inventory")

st.caption(
    "Real-time warehouse stock levels and stock availability monitoring."
)

mat_list = list(materials.items())
inv_cols_count = 3

for start_idx in range(0, len(mat_list), inv_cols_count):

    row_mats = mat_list[start_idx:start_idx + inv_cols_count]
    cols = st.columns(inv_cols_count)

    for col, (mat_id, mat_data) in zip(cols, row_mats):

        with col:

            if inventory_tile(mat_id, mat_data):
                st.session_state.selected_material = mat_id
                st.rerun()

if st.session_state.inventory_incidents:

    with st.expander("⚠️ Inventory Disruption History Log"):

        for inc in reversed(st.session_state.inventory_incidents):

            st.warning(
                f"**{inc['incident_id']}** · "
                f"{inc['material_name']} · "
                f"Loss: `{inc['quantity_lost_kg']} kg`"
            )

st.divider()


# ============================================================
# AI RECOVERY CENTRE
# ============================================================

st.title("🤖 AI Recovery Centre")

st.caption(
    "Autonomous multi-agent command hub for investigating disruptions, "
    "comparing plans, and approving execution."
)

machine_tab, supplier_tab = st.tabs(
    [
        "⚙ Machine Disruption Recovery",
        "🚚 Supply Chain Recovery",
    ]
)


# ============================================================
# MACHINE RECOVERY TAB
# ============================================================

with machine_tab:

    m_incident = st.session_state.latest_incident

    if m_incident is None:

        st.info(
            "No active machine incidents. Select a machine asset "
            "on the Factory Floor and simulate a failure to begin."
        )

    else:

        st.markdown("### Active Machine Incident Telemetry")

        mc1, mc2, mc3 = st.columns(3)

        mc1.metric(
            "Failed Asset ID",
            m_incident.get("machine_id", "Unknown"),
        )

        mc2.metric(
            "Impacted Orders",
            len(m_incident.get("affected_order_ids", [])),
        )

        mc3.metric(
            "Estimated Repair Window",
            f"{m_incident.get('estimated_repair_hrs', 0)} hrs",
        )

        st.error(
            f"Machine asset `{m_incident.get('machine_id')}` "
            f"is currently offline due to hardware/operational failure."
        )

        if st.button(
            "🧠 Execute Gemini Autonomous Orchestrator",
            type="primary",
            key="tab_run_machine_orch",
        ):

            try:

                with st.spinner(
                    "Gemini orchestrator coordinating recovery agents..."
                ):

                    result = run_gemini_orchestrator(
                        factory,
                        m_incident,
                    )

                    st.session_state.gemini_analysis = result["analysis"]
                    st.session_state.agent_events = result["events"]
                    st.session_state.recovery_report = result["recovery_report"]
                    st.session_state.orchestration_time = result["elapsed_seconds"]

                st.success("Autonomous analysis generated successfully!")
                st.rerun()

            except Exception as error:
                st.error(f"Analysis failed: {error}")

        if st.session_state.gemini_analysis:

            st.markdown("#### 📑 Gemini Diagnostic Summary")

            with st.container(border=True):
                st.markdown(st.session_state.gemini_analysis)

            st.caption(
                f"Orchestration Duration: "
                f"{st.session_state.orchestration_time} seconds"
            )

        report = st.session_state.recovery_report

        if report:

            st.markdown("#### ⚖️ Comparative Recovery Plan Evaluation")

            for order_id, comparison in report.get(
                "orders_recovery",
                {},
            ).items():

                st.markdown(f"##### Order: `{order_id}`")

                st.info(comparison.get("honest_assessment", ""))

                for plan_idx, plan in enumerate(
                    comparison.get("ranked_plans", []),
                    start=1,
                ):

                    with st.expander(
                        f"Strategy {plan_idx}: "
                        f"{plan.get('name', plan.get('plan_id'))}"
                    ):

                        pc1, pc2, pc3 = st.columns(3)

                        pc1.metric(
                            "Feasible",
                            "YES" if plan.get("feasible") else "NO",
                        )

                        pc2.metric(
                            "Deadline",
                            "MET" if plan.get("meets_deadline") else "MISSED",
                        )

                        pc3.metric(
                            "Extra Cost",
                            f"${number(plan.get('additional_cost_usd')):,.2f}",
                        )

                        st.write(
                            f"**Estimated Completion Time:** "
                            f"{plan.get('total_time_hrs', 'N/A')} hrs"
                        )

                        st.write(plan.get("evaluation_notes", ""))

            st.divider()

            st.markdown(
                "#### ✍️ Executive Human Approval & Execution Gateway"
            )

            for order_id, comparison in report.get(
                "orders_recovery",
                {},
            ).items():

                feasible_plans = [
                    plan
                    for plan in comparison.get("ranked_plans", [])
                    if plan.get("feasible")
                ]

                if not feasible_plans:

                    st.error(
                        f"No viable feasible recovery plans "
                        f"available for order `{order_id}`."
                    )

                    continue

                with st.container(border=True):

                    st.markdown(f"**Order ID: {order_id}**")

                    chosen_plan = st.selectbox(
                        "Select Approved Recovery Strategy",
                        feasible_plans,
                        format_func=lambda plan: (
                            f"{plan.get('plan_id')} · "
                            f"{plan.get('name')} · "
                            f"+${number(plan.get('additional_cost_usd')):,.2f}"
                        ),
                        key=f"exec_plan_select_{order_id}",
                    )

                    existing_res = (
                        st.session_state.machine_execution_results.get(order_id)
                    )

                    if existing_res:

                        verif = existing_res["verification"]

                        if verif.get("verified"):
                            st.success("✓ RECOVERY PLAN VERIFIED AND EXECUTED")
                        else:
                            st.error("✕ VERIFICATION FAILED")

                        with st.expander(
                            "View Execution Receipt & Verification"
                        ):

                            st.json(existing_res["execution_receipt"])
                            st.json(verif)

                    else:

                        if st.button(
                            f"🚀 Approve & Execute Plan for {order_id}",
                            type="primary",
                            key=f"exec_btn_{order_id}",
                        ):

                            try:

                                exec_res = execute_approved_plan(
                                    factory,
                                    chosen_plan,
                                )

                                st.session_state.machine_execution_results[
                                    order_id
                                ] = exec_res

                                st.success(
                                    f"Recovery plan for {order_id} executed successfully!"
                                )

                                st.rerun()

                            except Exception as error:
                                st.error(f"Execution error: {error}")

        if st.session_state.agent_events:

            st.markdown("#### 🔄 Agent Timeline Audit Trail")

            render_agent_timeline(st.session_state.agent_events)


# ============================================================
# SUPPLIER RECOVERY TAB
# ============================================================

with supplier_tab:

    s_incident = st.session_state.supplier_latest_incident

    if s_incident is None:

        st.info(
            "No active supplier disruption. Simulate a supplier failure "
            "in the Supply Chain page to begin."
        )

    else:

        failed_sup_id = s_incident["supplier_id"]
        failed_sup_obj = suppliers.get(failed_sup_id, {})

        st.markdown("### Active Supplier Incident Telemetry")

        sc1, sc2, sc3 = st.columns(3)

        sc1.metric("Failed Supplier", failed_sup_id)

        sc2.metric(
            "Supplier Tier",
            failed_sup_obj.get("tier", "N/A"),
        )

        sc3.metric(
            "Incident Reference",
            s_incident["incident_id"],
        )

        st.error(
            f"Supplier `{failed_sup_obj.get('name', failed_sup_id)}` "
            f"has suffered a catastrophic delivery outage."
        )

        if st.button(
            "🧠 Run Gemini Supply Chain Recovery",
            type="primary",
            key="tab_run_sup_orch",
        ):

            try:

                with st.spinner(
                    "Gemini agents investigating supply chain shortfall "
                    "and alternative routing..."
                ):

                    result = run_gemini_orchestrator(
                        factory,
                        s_incident,
                    )

                    st.session_state.supplier_gemini_analysis = result["analysis"]
                    st.session_state.supplier_agent_events = result["events"]

                    st.session_state.supplier_orchestration_time = (
                        result["elapsed_seconds"]
                    )

                    st.session_state.supplier_recovery_report = (
                        generate_supplier_recovery_plan(
                            factory,
                            s_incident,
                        )
                    )

                st.success("Supply chain analysis complete!")
                st.rerun()

            except Exception as error:
                st.error(f"Supplier analysis failed: {error}")

        if st.session_state.supplier_gemini_analysis:

            st.markdown("#### 📑 Gemini Operations Report")

            with st.container(border=True):
                st.markdown(
                    st.session_state.supplier_gemini_analysis
                )

            st.caption(
                f"Orchestration Duration: "
                f"{st.session_state.supplier_orchestration_time} seconds"
            )

        sup_report = st.session_state.supplier_recovery_report

        if sup_report:

            st.markdown(
                "#### 📦 Supply Chain Shortfall & Stock Coverage Analysis"
            )

            orders_rec = sup_report.get("orders_recovery", {})

            for ord_id, comp in orders_rec.items():

                st.markdown(
                    f"##### Order `{ord_id}` · "
                    f"Client: `{comp.get('client', 'Standard')}`"
                )

                rc1, rc2, rc3 = st.columns(3)

                rc1.metric(
                    "Material Shortfall",
                    f"{number(comp.get('shortfall_kg')):,.1f} kg",
                )

                cov = comp.get("stock_coverage_hrs")

                rc2.metric(
                    "Buffer Coverage",
                    f"{cov:.2f} hrs" if cov is not None else "N/A",
                )

                rc3.metric(
                    "Procurement Required",
                    "YES" if comp.get("procurement_required") else "NO",
                )

                st.info(comp.get("honest_assessment", ""))

                recommended = comp.get("recommended_plan")

                if recommended is None:

                    st.success(
                        "Warehouse buffer stock is sufficient. "
                        "No immediate procurement action required."
                    )

                    continue

                plans = comp.get("ranked_plans", [])

                for p_idx, plan in enumerate(plans, 1):

                    with st.expander(
                        f"Sourcing Option {p_idx}: "
                        f"{plan.get('supplier_name', plan.get('supplier_id'))}"
                    ):

                        pc1, pc2, pc3 = st.columns(3)

                        pc1.metric(
                            "Quantity",
                            f"{number(plan.get('quantity_kg')):,.1f} kg",
                        )

                        pc2.metric(
                            "Procurement Cost",
                            f"${number(plan.get('procurement_cost_usd')):,.2f}",
                        )

                        pc3.metric(
                            "Lead Time",
                            f"{plan.get('delivery_time_hrs', 'N/A')} hrs",
                        )

                        st.write(
                            f"**Feasible:** "
                            f"{'Yes' if plan.get('feasible') else 'No'}"
                        )

                        st.write(plan.get("notes", ""))
