
"""
ui/inventory.py
Inventory control tower for TexResQ.
"""

import streamlit as st

from inventory_agent import run_inventory_agent


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_kg(value):
    return f"{_number(value):,.1f} kg"


def _status_color(status):
    if status in ("HEALTHY", "REPLENISHMENT SCHEDULED"):
        return "success"

    if status == "LOW BUFFER":
        return "warning"

    return "error"


def _render_material_card(forecast):
    material_name = forecast["material_name"]
    status = forecast["status"]

    with st.container(border=True):

        st.markdown(f"### {material_name}")

        color = _status_color(status)

        if color == "success":
            st.success(status)
        elif color == "warning":
            st.warning(status)
        else:
            st.error(status)

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Physical Stock",
            _format_kg(forecast["physical_stock_kg"]),
        )

        col2.metric(
            "Reserved",
            _format_kg(forecast["reserved_stock_kg"]),
        )

        col3.metric(
            "Available",
            _format_kg(forecast["available_stock_kg"]),
        )

        st.divider()

        col1, col2 = st.columns(2)

        col1.metric(
            "Production Demand",
            _format_kg(forecast["production_demand_kg"]),
        )

        col2.metric(
            "Safety Stock",
            _format_kg(forecast["safety_stock_kg"]),
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Incoming Shipments",
            _format_kg(forecast["incoming_stock_kg"]),
        )

        col2.metric(
            "Projected Stock",
            _format_kg(forecast["projected_stock_kg"]),
        )

        st.progress(
            min(
                1.0,
                forecast["projected_available_kg"]
                / max(
                    1.0,
                    forecast["production_demand_kg"]
                    + forecast["safety_stock_kg"],
                ),
            )
        )

        st.caption(
            "Projected available stock after existing reservations "
            "and incoming deliveries."
        )

        if forecast["procurement_needed_kg"] > 0:
            st.error(
                "Uncovered shortage: "
                f"{_format_kg(forecast['procurement_needed_kg'])}"
            )

        elif status == "REPLENISHMENT SCHEDULED":
            st.success(
                "Automatic replenishment has been scheduled."
            )


def _render_order_forecast(forecasts):
    st.markdown("### Production Order Material Forecast")

    rows = []

    for material_id, forecast in forecasts.items():

        for order in forecast["orders"]:

            rows.append({
                "Order": order["order_id"],
                "Client": order["client"],
                "Fabric": order["fabric_type"],
                "Status": order["status"],
                "Remaining (m)": order["remaining_quantity_m"],
                "Material": forecast["material_name"],
                "Required (kg)": order["required_material_kg"],
                "Deadline (hrs)": order["deadline_hrs"],
            })

    if not rows:
        st.info("No active production demand found.")
        return

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def _render_delivery_risks(forecasts):
    st.markdown("### Delivery & Production Deadline Risk")

    risks_found = False

    for material_id, forecast in forecasts.items():

        risks = forecast.get("delivery_risks", [])

        for risk in risks:

            risks_found = True

            st.warning(
                f"**{risk['order_id']}** may miss its deadline. "
                f"Estimated finish: {risk['projected_finish_hrs']:.1f} hours; "
                f"deadline: {risk['deadline_hrs']:.1f} hours."
            )

    if not risks_found:
        st.success(
            "No delivery-related production deadline risks detected "
            "by the current estimate."
        )


def _render_procurement_log(factory):
    st.markdown("### Automatic Procurement History")

    records = factory.get("inventory_procurement_log", [])

    if not records:
        st.info("No automatic procurement orders have been created yet.")
        return

    for record in reversed(records):

        with st.expander(
            f"{record['procurement_id']} · "
            f"{record['material_name']} · "
            f"{_format_kg(record['quantity_kg'])}"
        ):

            col1, col2, col3 = st.columns(3)

            col1.metric("Shipment", record["shipment_id"])
            col2.metric("Supplier", record["supplier_name"])
            col3.metric(
                "Estimated Cost",
                f"${record['estimated_cost']:,.2f}",
            )

            st.write(f"**Status:** {record['status']}")
            st.write(f"**ETA:** {record['eta']}")


def _render_incoming_shipments(factory):
    st.markdown("### Incoming Raw Material Shipments")

    active_statuses = {
        "SCHEDULED",
        "IN TRANSIT",
        "REROUTED",
        "DELAYED",
    }

    shipments = [
        shipment
        for shipment in factory.get("shipments", [])
        if shipment.get("status") in active_statuses
    ]

    if not shipments:
        st.info("There are currently no incoming shipments.")
        return

    rows = []

    for shipment in shipments:

        rows.append({
            "Shipment": shipment.get("shipment_id"),
            "Material": shipment.get("material_name"),
            "Supplier": shipment.get("supplier_name"),
            "Quantity (kg)": _number(
                shipment.get("quantity_kg")
            ),
            "Status": shipment.get("status"),
            "ETA": shipment.get("eta"),
            "Purpose": shipment.get(
                "shipment_purpose",
                "Supply network shipment",
            ),
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )


def render_inventory_dashboard(factory):

    st.title("📦 Inventory Intelligence & Autonomous Procurement")

    st.caption(
        "Demand forecasting, inventory coverage, shortage detection "
        "and automatic material replenishment."
    )

    # Automatic forecast and procurement.
    result = run_inventory_agent(
        factory,
        auto_procure=True,
    )

    forecasts = result["forecasts"]

    # --------------------------------------------------------
    # REFRESH / SIMULATION CONTROLS
    # --------------------------------------------------------

    control_col, info_col = st.columns([1, 3])

    with control_col:
        if st.button(
            "🔄 Refresh Inventory Forecast",
            use_container_width=True,
        ):
            st.rerun()

    with info_col:
        st.caption(
            "Automatic procurement runs whenever this dashboard loads. "
            "Existing incoming shipments are counted before new orders "
            "are scheduled."
        )

    st.divider()

    # --------------------------------------------------------
    # EXECUTIVE METRICS
    # --------------------------------------------------------

    total_materials = len(forecasts)

    shortage_count = sum(
        1 for item in forecasts.values()
        if item["status"] == "SHORTAGE"
        or item["procurement_needed_kg"] > 0
    )

    incoming_total = sum(
        item["incoming_stock_kg"]
        for item in forecasts.values()
    )

    demand_total = sum(
        item["production_demand_kg"]
        for item in forecasts.values()
    )

    metric_cols = st.columns(4)

    metric_cols[0].metric(
        "Tracked Materials",
        total_materials,
    )

    metric_cols[1].metric(
        "Materials Requiring Attention",
        shortage_count,
    )

    metric_cols[2].metric(
        "Total Production Demand",
        _format_kg(demand_total),
    )

    metric_cols[3].metric(
        "Incoming Materials",
        _format_kg(incoming_total),
    )

    st.divider()

    # --------------------------------------------------------
    # MATERIAL INVENTORY CARDS
    # --------------------------------------------------------

    st.markdown("## Material Inventory Status")

    material_items = list(forecasts.values())

    for start in range(0, len(material_items), 2):

        cols = st.columns(2)

        for col, forecast in zip(
            cols,
            material_items[start:start + 2],
        ):

            with col:
                _render_material_card(forecast)

    st.divider()

    # --------------------------------------------------------
    # PRODUCTION DEMAND
    # --------------------------------------------------------

    _render_order_forecast(forecasts)

    st.divider()

    # --------------------------------------------------------
    # DELIVERY RISK
    # --------------------------------------------------------

    _render_delivery_risks(forecasts)

    st.divider()

    # --------------------------------------------------------
    # PROCUREMENT FAILURES
    # --------------------------------------------------------

    if result["procurement_failures"]:

        st.markdown("### ⚠️ Procurement Exceptions")

        for failure in result["procurement_failures"]:

            st.error(
                f"{failure['material_id']}: "
                f"{_format_kg(failure['quantity_kg'])} could not be scheduled. "
                f"{failure['reason']}"
            )

    # --------------------------------------------------------
    # SHIPMENTS
    # --------------------------------------------------------

    _render_incoming_shipments(factory)

    st.divider()

    # --------------------------------------------------------
    # PROCUREMENT AUDIT
    # --------------------------------------------------------

    _render_procurement_log(factory)

    st.divider()

    st.caption(
        "TEXRESQ INVENTORY CONTROL · "
        "Procurement shipments are simulated and are not real purchase orders."
    )
