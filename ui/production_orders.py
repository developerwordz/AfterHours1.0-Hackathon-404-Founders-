
"""ui/production_orders.py — Production order tiles."""

from __future__ import annotations

import streamlit as st

from ui.tiles import (
    inject_tile_css,
    _tile_markup,
    _num,
    _esc,
    material_icon,
)


# ============================================================
# ORDER HELPERS
# ============================================================

def _get_material(factory, order):
    material_id = order.get("raw_material_id")

    material = factory.get(
        "raw_materials", {}
    ).get(material_id, {})

    remaining = _num(
        order.get("remaining_quantity_m", 0)
    )

    rate = _num(
        order.get("raw_material_per_m", 1)
    )

    return {
        "id": material_id or "UNKNOWN",
        "name": material.get(
            "name", material_id or "Unknown material"
        ),
        "required": remaining * rate,
        "stock": _num(material.get("stock_kg", 0)),
        "reserved": _num(material.get("reserved_kg", 0)),
    }


def _get_machine(factory, order):
    machine_id = order.get("assigned_machine_id")

    machine = factory.get(
        "machines", {}
    ).get(machine_id, {})

    return machine_id, machine


def _get_vendor(factory, order, material_id):
    """
    Find an explicitly assigned order vendor or an incoming
    shipment vendor. Never invent a vendor assignment.
    """

    suppliers = factory.get("suppliers", {})

    if isinstance(suppliers, list):
        suppliers = {
            s.get("id"): s
            for s in suppliers
            if s.get("id")
        }

    supplier_id = (
        order.get("supplier_id")
        or order.get("vendor_id")
    )

    if supplier_id:
        supplier = suppliers.get(supplier_id, {})
        if supplier:
            return (
                supplier.get("name", supplier_id),
                supplier_id,
            )

    shipments = factory.get("shipments", [])

    if isinstance(shipments, dict):
        shipments = list(shipments.values())

    active_statuses = {
        "SCHEDULED",
        "IN_TRANSIT",
        "IN TRANSIT",
        "REROUTED",
        "DELAYED",
        "PENDING",
    }

    for shipment in shipments:
        shipment_material = (
            shipment.get("material_id")
            or shipment.get("raw_material_id")
        )

        shipment_status = str(
            shipment.get("status", "")
        ).upper()

        if (
            shipment_material == material_id
            and shipment_status in active_statuses
        ):
            supplier_id = shipment.get("supplier_id")

            supplier_name = (
                shipment.get("supplier_name")
                or shipment.get("vendor_name")
            )

            if not supplier_name and supplier_id:
                supplier_name = suppliers.get(
                    supplier_id, {}
                ).get("name")

            return (
                supplier_name or supplier_id or "Assigned shipment vendor",
                supplier_id or "—",
            )

    return "Not assigned", "—"


def _get_incoming(factory, material_id):
    shipments = factory.get("shipments", [])

    if isinstance(shipments, dict):
        shipments = list(shipments.values())

    active_statuses = {
        "SCHEDULED",
        "IN_TRANSIT",
        "IN TRANSIT",
        "REROUTED",
        "DELAYED",
        "PENDING",
    }

    matching = []

    for shipment in shipments:
        shipment_material = (
            shipment.get("material_id")
            or shipment.get("raw_material_id")
        )

        status = str(
            shipment.get("status", "")
        ).upper()

        if (
            shipment_material == material_id
            and status in active_statuses
        ):
            matching.append(shipment)

    quantity = sum(
        _num(
            s.get("quantity_kg")
            or s.get("quantity")
            or s.get("amount_kg")
            or 0
        )
        for s in matching
    )

    return quantity, len(matching)


def _get_cost(factory, order, material, vendor_id):
    """
    Indicative remaining-order cost.

    Material price is taken from the assigned vendor when available.
    Otherwise, the lowest active legacy supplier price is used as
    a benchmark, not as a confirmed vendor quote.
    """

    suppliers = factory.get("suppliers", {})

    if isinstance(suppliers, list):
        suppliers = {
            s.get("id"): s
            for s in suppliers
            if s.get("id")
        }

    unit_price = None

    if vendor_id in suppliers:
        prices = suppliers[vendor_id].get(
            "cost_per_kg", {}
        )

        if isinstance(prices, dict):
            unit_price = prices.get(material["id"])

    benchmark_used = False

    if unit_price is None:
        available_prices = []

        for supplier in suppliers.values():
            if supplier.get("status", "ACTIVE") != "ACTIVE":
                continue

            prices = supplier.get("cost_per_kg", {})

            if isinstance(prices, dict):
                price = prices.get(material["id"])

                if price is not None:
                    available_prices.append(
                        _num(price)
                    )

        if available_prices:
            unit_price = min(available_prices)
            benchmark_used = True

    material_cost = (
        material["required"] * _num(unit_price)
        if unit_price is not None
        else None
    )

    machine_id, machine = _get_machine(
        factory, order
    )

    remaining = _num(
        order.get("remaining_quantity_m", 0)
    )

    capacity = _num(
        machine.get("capacity_m_per_hr", 0)
    )

    operating_rate = _num(
        machine.get("operating_cost_per_hr", 0)
    )

    production_hours = (
        remaining / capacity
        if capacity > 0
        else 0
    )

    operating_cost = production_hours * operating_rate

    total_cost = (
        material_cost + operating_cost
        if material_cost is not None
        else None
    )

    return {
        "unit_price": unit_price,
        "material_cost": material_cost,
        "production_hours": production_hours,
        "operating_cost": operating_cost,
        "total": total_cost,
        "benchmark": benchmark_used,
    }


def _money(value):
    if value is None:
        return "Unavailable"

    return f"${value:,.2f}"


# ============================================================
# ORDER STATUS
# ============================================================

_ORDER_COLORS = {
    "IN_PROGRESS": "#17634f",
    "RUNNING": "#17634f",
    "QUEUED": "#805d20",
    "AT_RISK": "#7d292d",
    "DELAYED": "#7d292d",
    "REASSIGNED": "#66508a",
    "COMPLETED": "#17634f",
}


_ORDER_ICONS = {
    "IN_PROGRESS": "🏭",
    "RUNNING": "🏭",
    "QUEUED": "📋",
    "AT_RISK": "⚠️",
    "DELAYED": "⏰",
    "REASSIGNED": "🔄",
    "COMPLETED": "✅",
}


# ============================================================
# PRODUCTION ORDER TILE
# ============================================================

def production_order_tile(factory, order_id, order):

    status = str(
        order.get("status", "UNKNOWN")
    ).upper()

    color = _ORDER_COLORS.get(
        status, "#344454"
    )

    icon = _ORDER_ICONS.get(
        status, "📦"
    )

    total = _num(
        order.get("total_quantity_m", 0)
    )

    completed = _num(
        order.get("completed_quantity_m", 0)
    )

    remaining = _num(
        order.get("remaining_quantity_m", 0)
    )

    progress = (
        completed / total
        if total > 0
        else 0
    )

    progress = max(0, min(progress, 1))

    material = _get_material(
        factory, order
    )

    machine_id, machine = _get_machine(
        factory, order
    )

    vendor_name, vendor_id = _get_vendor(
        factory, order, material["id"]
    )

    incoming_kg, shipment_count = _get_incoming(
        factory, material["id"]
    )

    cost = _get_cost(
        factory, order, material, vendor_id
    )

    deadline = order.get(
        "deadline_hrs", "—"
    )

    available = max(
        0,
        material["stock"] - material["reserved"]
    )

    material_status = (
        "SUFFICIENT STOCK"
        if available >= material["required"]
        else "SHORTAGE / PROCUREMENT"
    )

    client = order.get(
        "client", "Unknown client"
    )

    fabric = str(
        order.get("fabric_type", "Unknown fabric")
    ).replace("_", " ").title()

    # Hover panel rows
    rows = [
        ("Client", client),
        ("Fabric type", fabric),
        ("Status", status.replace("_", " ")),
        ("Total quantity", f"{total:,.0f} m"),
        ("Completed", f"{completed:,.0f} m"),
        ("Remaining", f"{remaining:,.0f} m"),
        ("Progress", f"{progress * 100:.1f}%"),

        ("Deadline", f"{deadline} hrs"),
        (
            "Late penalty",
            _money(
                order.get("penalty_per_hr_late")
            ) + " / hr"
        ),

        ("Assigned machine", machine_id or "Not assigned"),
        (
            "Machine name",
            machine.get("name", "—")
        ),

        ("Required material", material["name"]),
        ("Material ID", material["id"]),
        (
            "Consumption rate",
            f"{_num(order.get('raw_material_per_m', 1)):g} kg / m"
        ),
        (
            "Material required",
            f"{material['required']:,.1f} kg"
        ),
        (
            "Physical stock",
            f"{material['stock']:,.1f} kg"
        ),
        (
            "Reserved stock",
            f"{material['reserved']:,.1f} kg"
        ),
        (
            "Unreserved stock",
            f"{available:,.1f} kg"
        ),
        (
            "Incoming material",
            f"{incoming_kg:,.1f} kg"
        ),
        (
            "Incoming shipments",
            str(shipment_count)
        ),
        (
            "Material status",
            material_status
        ),

        ("Vendor", vendor_name),
        ("Vendor ID", vendor_id),

        (
            "Estimated production time",
            f"{cost['production_hours']:.2f} hrs"
        ),
        (
            "Estimated material cost",
            _money(cost["material_cost"])
        ),
        (
            "Estimated operating cost",
            _money(cost["operating_cost"])
        ),
        (
            "Estimated total cost",
            _money(cost["total"])
        ),
    ]

    if cost["benchmark"]:
        rows.append(
            (
                "Pricing note",
                "Lowest active supplier benchmark"
            )
        )

    markup = _tile_markup(
        color=color,
        failed=status in {"AT_RISK", "DELAYED"},
        tile_id=order_id,
        badge=status.replace("_", " "),
        icon=icon,
        name=client,
        meta=(
            f"{fabric} · {remaining:,.0f} m remaining"
        ),
        gauge=progress,
        peek_rows=rows,
        hint="PRODUCTION ORDER DETAILS",
    )

    with st.container(key=f"tile_order_{order_id}"):
        st.html(markup)


# ============================================================
# PRODUCTION ORDER GRID
# ============================================================

def render_production_order_grid(
    factory,
    columns=3,
    show_completed=False,
):
    orders = factory.get("orders", {})

    if not orders:
        st.info("No production orders configured.")
        return

    active = []
    completed = []

    for order_id, order in orders.items():
        status = str(
            order.get("status", "")
        ).upper()

        if status == "COMPLETED":
            completed.append((order_id, order))
        else:
            active.append((order_id, order))

    displayed = active

    if show_completed:
        displayed = active + completed

    if not displayed:
        st.info("No production orders to display.")
        return

    columns = max(1, int(columns))

    for start in range(0, len(displayed), columns):

        row_items = displayed[
            start:start + columns
        ]

        cols = st.columns(
            columns,
            gap="medium",
        )

        for col, (order_id, order) in zip(
            cols,
            row_items,
        ):
            with col:
                production_order_tile(
                    factory,
                    order_id,
                    order,
                )


# ============================================================
# MAIN PAGE
# ============================================================

def render_production_orders(factory):

    inject_tile_css()

    st.title("📋 Production Orders")

    st.caption(
        "Monitor active orders, production progress, "
        "material requirements, vendors, deadlines and costs."
    )

    orders = factory.get("orders", {})

    active_orders = [
        order
        for order in orders.values()
        if str(order.get("status", "")).upper()
        != "COMPLETED"
    ]

    completed_orders = [
        order
        for order in orders.values()
        if str(order.get("status", "")).upper()
        == "COMPLETED"
    ]

    total_remaining = sum(
        _num(order.get("remaining_quantity_m", 0))
        for order in active_orders
    )

    at_risk = sum(
        1
        for order in active_orders
        if str(order.get("status", "")).upper()
        in {"AT_RISK", "DELAYED"}
    )

    queued = sum(
        1
        for order in active_orders
        if str(order.get("status", "")).upper()
        == "QUEUED"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Active Orders",
        len(active_orders),
    )

    c2.metric(
        "At Risk",
        at_risk,
    )

    c3.metric(
        "Queued",
        queued,
    )

    c4.metric(
        "Remaining Production",
        f"{total_remaining:,.0f} m",
    )

    st.divider()

    st.subheader("Ongoing Orders")

    st.caption(
        "Hover over any tile to view the complete order details."
    )

    render_production_order_grid(
        factory,
        columns=3,
        show_completed=False,
    )

    with st.expander(
        f"Completed Orders ({len(completed_orders)})"
    ):
        if completed_orders:
            render_production_order_grid(
                factory,
                columns=3,
                show_completed=True,
            )
        else:
            st.caption("No completed orders yet.")
