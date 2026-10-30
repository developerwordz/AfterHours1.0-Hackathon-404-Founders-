
"""
ui/supply_chain.py
Interactive geographic supply-chain dashboard for TexResQ.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium

from supply_chain_agent import (
    initialize_supply_chain,
    get_supply_chain_summary,
    advance_simulation,
    reroute_shipment,
    switch_supplier,
    FACTORY_LOCATION,
)


# ============================================================
# DISPLAY HELPERS
# ============================================================

STATUS_COLORS = {
    "SCHEDULED": "blue",
    "IN TRANSIT": "green",
    "REROUTED": "purple",
    "DELAYED": "orange",
    "DELIVERED": "darkgreen",
    "DECLINED": "red",
    "CANCELLED": "gray",
}


def _supplier(factory, supplier_id):
    return factory.get("supply_chain_suppliers", {}).get(
        supplier_id, {}
    )


def _network_supplier_options(network):
    return network.get("supplier_options", [])


def _render_map(factory, selected_network_key):
    network = factory["supply_networks"][selected_network_key]
    active_id = network.get("active_supplier_id")

    map_object = folium.Map(
    location=[FACTORY_LOCATION["lat"], FACTORY_LOCATION["lon"]],
    zoom_start=6,
    tiles="OpenStreetMap",
    control_scale=True,
)

    # Factory marker
    folium.Marker(
        [FACTORY_LOCATION["lat"], FACTORY_LOCATION["lon"]],
        tooltip="TexResQ Factory — Mysuru",
        popup="<b>TexResQ Factory</b><br>Mysuru, Karnataka",
        icon=folium.Icon(color="black", icon="industry", prefix="fa"),
    ).add_to(map_object)

    # Supplier pins and route lines
    for option in _network_supplier_options(network):
        supplier_id = option["id"]
        supplier = _supplier(factory, supplier_id)

        if not supplier:
            continue

        is_active = supplier_id == active_id
        status = supplier.get("status", "UNKNOWN")

        if status != "ACTIVE":
            color = "red"
        elif is_active:
            color = "green"
        else:
            color = "cadetblue"

        folium.Marker(
            [supplier["lat"], supplier["lon"]],
            tooltip=f"{supplier['name']} — {option['role']}",
            popup=(
                f"<b>{supplier['name']}</b><br>"
                f"City: {supplier['city']}<br>"
                f"Role: {option['role']}<br>"
                f"Status: {status}<br>"
                f"Cost: ${supplier['cost_per_kg']}/kg<br>"
                f"ETA: {supplier['delivery_time_hrs']} hours"
            ),
            icon=folium.Icon(color=color, icon="industry", prefix="fa"),
        ).add_to(map_object)

        # Show available supplier corridors.
        route = [
            [supplier["lat"], supplier["lon"]],
            [FACTORY_LOCATION["lat"], FACTORY_LOCATION["lon"]],
        ]

        folium.PolyLine(
            route,
            color=color,
            weight=5 if is_active else 2,
            opacity=0.8 if is_active else 0.35,
            dash_array=None if is_active else "7, 10",
            tooltip=(
                f"{option['role']} route"
                + (" — ACTIVE" if is_active else "")
            ),
        ).add_to(map_object)

    # Plot shipment positions along their route.
    for shipment in factory.get("shipments", []):
        if shipment["network_key"] != selected_network_key:
            continue

        if shipment["status"] not in (
            "IN TRANSIT", "REROUTED", "DELAYED"
        ):
            continue

        route = shipment.get("route", [])
        if len(route) < 2:
            continue

        progress = max(
            0.0, min(100.0, float(shipment.get("progress", 0)))
        ) / 100.0

        # Interpolate between the first and final route points.
        start = route[0]
        end = route[-1]
        current_lat = start[0] + (end[0] - start[0]) * progress
        current_lon = start[1] + (end[1] - start[1]) * progress

        color = STATUS_COLORS.get(shipment["status"], "blue")

        folium.PolyLine(
            route,
            color=color,
            weight=4,
            opacity=0.9,
            tooltip=f"{shipment['shipment_id']} — {shipment['status']}",
        ).add_to(map_object)

        folium.CircleMarker(
            [current_lat, current_lon],
            radius=8,
            color=color,
            fill=True,
            fill_opacity=1,
            tooltip=(
                f"{shipment['shipment_id']} | "
                f"{shipment['quantity_kg']} kg | "
                f"{shipment['status']}"
            ),
        ).add_to(map_object)

    return map_object


def _render_supplier_details(factory, network):
    st.markdown("#### Supplier sources")

    for option in network.get("supplier_options", []):
        supplier = _supplier(factory, option["id"])
        if not supplier:
            continue

        active = option["id"] == network.get("active_supplier_id")
        status = supplier.get("status", "UNKNOWN")

        with st.container(border=True):
            left, right = st.columns([3, 1])

            with left:
                st.markdown(
                    f"**{supplier['name']}**"
                    + ("  ·  ACTIVE SOURCE" if active else "")
                )
                st.caption(
                    f"{option['role']} · {supplier['city']} · "
                    f"${supplier['cost_per_kg']}/kg · "
                    f"{supplier['delivery_time_hrs']}h ETA"
                )

            with right:
                if status == "ACTIVE":
                    st.success("ACTIVE")
                else:
                    st.error(status)


def _render_shipments(factory, network_key):
    shipments = [
        item for item in factory.get("shipments", [])
        if item["network_key"] == network_key
    ]

    st.markdown("#### Shipment tracker")

    if not shipments:
        st.info("No shipments recorded for this material.")
        return

    for shipment in reversed(shipments[-12:]):
        status = shipment["status"]
        color = STATUS_COLORS.get(status, "gray")

        with st.container(border=True):
            top_left, top_right = st.columns([3, 1])

            with top_left:
                st.markdown(
                    f"**{shipment['shipment_id']}** · "
                    f"{shipment['supplier_name']}"
                )
                st.caption(
                    f"{shipment['quantity_kg']:.0f} kg · "
                    f"Transport {shipment['transport_id']} · "
                    f"Origin: {shipment['supplier_city']}"
                )

            with top_right:
                st.markdown(f"**{status}**")

            if status in ("IN TRANSIT", "REROUTED", "DELAYED"):
                st.progress(
                    int(max(0, min(100, shipment.get("progress", 0))))
                )

            st.caption(
                f"ETA: {shipment['eta']} · "
                f"{shipment.get('last_event', '')}"
            )


def _render_incidents(factory):
    st.markdown("#### Transport and supplier incidents")

    incidents = factory.get("transport_incidents", [])

    if not incidents:
        st.info("No disruptions have occurred in this simulation yet.")
        return

    for event in reversed(incidents[-12:]):
        with st.container(border=True):
            st.markdown(
                f"**{event['event_type']}** · "
                f"{event['material_name']} · {event['severity']}"
            )
            st.write(event["description"])
            st.caption(
                f"{event['timestamp']} · {event.get('incident_id', '')}"
            )


# ============================================================
# MAIN DASHBOARD
# ============================================================

def render_supply_chain_dashboard(factory, simulate_supplier_failure=None):
    """
    Main dashboard.

    simulate_supplier_failure is optional to remain compatible with
    older app.py versions that passed this callback.
    """

    initialize_supply_chain(factory)

    st.title("Material Supply Chain Control Tower")
    st.caption(
        "Geographic supplier networks, shipment monitoring and "
        "autonomous disruption recovery."
    )

    summary = get_supply_chain_summary(factory)
    simulation = factory["supply_simulation"]

    # --------------------------------------------------------
    # Simulation clock and KPI row
    # --------------------------------------------------------

    st.markdown(
        f"**Simulation time:** `{simulation['clock']}`  "
        f"· Elapsed: `{simulation['elapsed_hours']} hours`"
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Networks", summary["total_networks"])
    c2.metric("Operational", summary["operational"])
    c3.metric("Degraded", summary["degraded"])
    c4.metric("In transit", summary["in_transit"])
    c5.metric("Disrupted shipments", summary["delayed"] + summary["declined"])

    st.divider()

    # --------------------------------------------------------
    # Simulation controls
    # --------------------------------------------------------

    st.markdown("## Simulation controls")

    left, middle, right = st.columns([2, 2, 3])

    with left:
        if st.button(
            "Advance 2 hours",
            type="primary",
            use_container_width=True,
            key="sc_advance_2",
        ):
            event = advance_simulation(factory, hours=2)
            if event:
                st.session_state["sc_last_event"] = event
            st.rerun()

    with middle:
        if st.button(
            "Advance 8 hours",
            use_container_width=True,
            key="sc_advance_8",
        ):
            event = None
            for _ in range(4):
                event = advance_simulation(factory, hours=2) or event
            if event:
                st.session_state["sc_last_event"] = event
            st.rerun()

    with right:
        st.caption(
            "Each time advance moves shipments forward and gives the "
            "disruption engine a chance to generate an incident."
        )

    last_event = st.session_state.get("sc_last_event")
    if last_event:
        st.info(f"Latest generated event: {last_event}")

    st.divider()

    # --------------------------------------------------------
    # Material network tabs
    # --------------------------------------------------------

    st.markdown("## Material-specific networks")

    tab_cotton, tab_dye, tab_poly = st.tabs(
        ["Cotton network", "Dye network", "Polyester network"]
    )

    tab_config = [
        (tab_cotton, "COTTON"),
        (tab_dye, "DYE"),
        (tab_poly, "POLYESTER"),
    ]

    for tab, network_key in tab_config:
        with tab:
            network = factory["supply_networks"][network_key]
            active_id = network.get("active_supplier_id")
            active_supplier = _supplier(factory, active_id)

            st.markdown(f"### {network['material_name']} supply route")

            metric1, metric2, metric3 = st.columns(3)
            metric1.metric(
                "Active source",
                active_supplier.get("name", "No active source"),
            )
            metric2.metric(
                "Source role",
                network.get("active_source_role") or "NONE",
            )
            metric3.metric("Network status", network["status"])

            map_object = _render_map(factory, network_key)
            st_folium(
                map_object,
                use_container_width=True,
                height=440,
                key=f"supply_map_{network_key}",
            )

            st.caption(
                "Green route = active source. Dashed routes = alternatives. "
                "Moving circles = active shipments. All locations and routes "
                "are simulated."
            )

            _render_supplier_details(factory, network)
            _render_shipments(factory, network_key)

    st.divider()

    # --------------------------------------------------------
    # Manual disruption controls
    # --------------------------------------------------------

    st.markdown("## Test autonomous recovery")

    st.caption(
        "Manually trigger a supplier outage or transport disruption to "
        "demonstrate the agent's decision-making."
    )

    network_keys = list(factory["supply_networks"].keys())

    selected_network_key = st.selectbox(
        "Choose material network",
        network_keys,
        format_func=lambda key: (
            factory["supply_networks"][key]["material_name"]
        ),
        key="sc_manual_network",
    )

    selected_network = factory["supply_networks"][selected_network_key]

    active_shipments = [
        item for item in factory["shipments"]
        if item["network_key"] == selected_network_key
        and item["status"] not in ("DELIVERED", "DECLINED", "CANCELLED")
    ]

    active_supplier_id = selected_network.get("active_supplier_id")
    active_supplier = _supplier(factory, active_supplier_id)

    action_col1, action_col2 = st.columns(2)

    with action_col1:
        st.markdown("**Supplier failure**")
        st.caption(
            "The active source becomes unavailable. The agent evaluates "
            "the other suppliers in this material network."
        )

        if st.button(
            "Trigger active supplier outage",
            use_container_width=True,
            key="sc_manual_supplier_failure",
            disabled=not active_supplier_id,
        ):
            result = switch_supplier(
                factory,
                selected_network_key,
                active_supplier_id,
                "Manual supplier outage triggered by the dashboard operator.",
            )

            if result:
                st.session_state["sc_last_event"] = (
                    f"Supplier failover: {result['previous_supplier_name']} "
                    f"→ {result['replacement_supplier_name'] or 'No replacement'}"
                )
            st.rerun()

    with action_col2:
        st.markdown("**Transport disruption**")
        st.caption(
            "A roadblock is detected. The agent reroutes the shipment "
            "without changing its supplier."
        )

        if st.button(
            "Trigger roadblock and reroute",
            use_container_width=True,
            key="sc_manual_reroute",
            disabled=not active_shipments,
        ):
            shipment = active_shipments[0]
            reroute_shipment(
                factory,
                shipment,
                "Manual roadblock simulation. Agent selected an alternate corridor.",
            )
            st.session_state["sc_last_event"] = (
                f"{shipment['shipment_id']} rerouted; "
                f"supplier retained: {shipment['supplier_name']}."
            )
            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Global shipment overview
    # --------------------------------------------------------

    st.markdown("## Shipment overview")

    all_shipments = factory.get("shipments", [])

    if all_shipments:
        shipment_rows = [
            {
                "Shipment": item["shipment_id"],
                "Material": item["material_name"],
                "Supplier": item["supplier_name"],
                "Origin": item["supplier_city"],
                "Quantity (kg)": item["quantity_kg"],
                "Status": item["status"],
                "ETA": item["eta"],
                "Transport": item["transport_id"],
            }
            for item in reversed(all_shipments)
        ]

        st.dataframe(
            shipment_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No shipments yet.")

    st.divider()

    # --------------------------------------------------------
    # Incident history
    # --------------------------------------------------------

    st.markdown("## Incident history")
    _render_incidents(factory)

    st.divider()

    # --------------------------------------------------------
    # Agent intervention history
    # --------------------------------------------------------

    st.markdown("## Autonomous agent intervention log")

    interventions = factory.get("supply_chain_interventions", [])

    if not interventions:
        st.info(
            "No agent interventions yet. Advance the simulation or "
            "trigger a disruption above."
        )
    else:
        for event in reversed(interventions[-25:]):
            with st.container(border=True):
                st.markdown(
                    f"**{event['material_name']} · {event['action']}**"
                )
                st.write(event["reason"])

                previous = event.get("previous_supplier_name")
                replacement = event.get("replacement_supplier_name")

                if previous or replacement:
                    st.caption(
                        f"Source: {previous or 'None'} → "
                        f"{replacement or 'None'}"
                    )

                if event.get("shipment_id"):
                    st.caption(f"Shipment: {event['shipment_id']}")

                st.caption(event["timestamp"])
