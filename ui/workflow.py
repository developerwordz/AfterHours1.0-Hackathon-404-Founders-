
"""
ui/workflow.py
TEXRESQ factory workflow control panel.
"""

import streamlit as st

from workflow_engine import (
    initialize_factory_workflow,
    run_factory_cycle,
    dispatch_completed_orders,
    get_workflow_summary,
)


def render_factory_workflow(factory):

    initialize_factory_workflow(factory)

    st.markdown("## ⚙️ Autonomous Factory Workflow")

    st.caption(
        "Run the connected inventory, logistics, production and "
        "quality workflow using the shared factory state."
    )

    summary = get_workflow_summary(factory)

    # --------------------------------------------------------
    # FACTORY METRICS
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Active Orders", summary["active_orders"])
    c2.metric("Running Machines", summary["running_machines"])
    c3.metric("Incoming Shipments", summary["incoming_shipments"])
    c4.metric("Finished Goods", f'{summary["finished_goods_m"]:,.1f} m')

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Completed Orders", summary["completed_orders"])
    c2.metric("Failed Machines", summary["failed_machines"])
    c3.metric("Ready to Dispatch", summary["ready_to_dispatch"])
    c4.metric("Dispatched Orders", summary["dispatched_orders"])

    st.divider()

    # --------------------------------------------------------
    # WORKFLOW CONTROLS
    # --------------------------------------------------------

    st.markdown("### Factory Simulation Controls")

    control1, control2, control3 = st.columns(3)

    with control1:
        if st.button(
            "▶ Run 1-Hour Factory Cycle",
            type="primary",
            use_container_width=True,
            key="workflow_run_cycle",
        ):
            try:
                result = run_factory_cycle(
                    factory,
                    hours=1.0,
                    auto_procure=True,
                )

                st.session_state["workflow_last_result"] = result

                st.success(
                    f'Factory cycle {result["cycle"]} completed.'
                )

            except Exception as exc:
                st.error(f"Factory cycle failed: {exc}")

    with control2:
        if st.button(
            "📦 Run Inventory Procurement",
            use_container_width=True,
            key="workflow_procurement",
        ):
            try:
                from inventory_agent import run_inventory_agent

                result = run_inventory_agent(
                    factory,
                    auto_procure=True,
                )

                st.session_state["workflow_last_inventory"] = result

                st.success(
                    f'{len(result["scheduled_shipments"])} '
                    "new shipment(s) scheduled."
                )

            except Exception as exc:
                st.error(f"Procurement failed: {exc}")

    with control3:
        if st.button(
            "🚚 Dispatch Completed Orders",
            use_container_width=True,
            key="workflow_dispatch",
        ):
            try:
                dispatched = dispatch_completed_orders(factory)

                if dispatched:
                    st.success(
                        f"{len(dispatched)} order(s) dispatched."
                    )
                else:
                    st.info("No completed orders are ready for dispatch.")

            except Exception as exc:
                st.error(f"Dispatch failed: {exc}")

    st.caption(
        "Each factory cycle advances simulated time, updates shipments, "
        "checks procurement, assigns eligible orders and produces batches."
    )

    st.divider()

    # --------------------------------------------------------
    # LATEST CYCLE
    # --------------------------------------------------------

    last_result = st.session_state.get("workflow_last_result")

    st.markdown("### Latest Factory Cycle")

    if not last_result:
        st.info(
            "No workflow cycle has been run in this session. "
            "Click 'Run 1-Hour Factory Cycle' to begin."
        )
    else:

        st.write(
            f'**Cycle:** {last_result["cycle"]} · '
            f'**Time advanced:** {last_result["hours_advanced"]} hour(s)'
        )

        disruption = last_result.get("disruption")

        if disruption:
            st.warning(f"Supply-chain disruption generated: {disruption}")
        else:
            st.success("No new supply-chain disruption during this cycle.")

        # Production results
        st.markdown("#### Production Results")

        production_rows = []

        for item in last_result.get("production_results", []):

            if not item.get("success"):
                production_rows.append({
                    "Machine": item.get("machine_id"),
                    "Result": "BLOCKED",
                    "Produced (m)": 0,
                    "Material Used (kg)": 0,
                    "Quality": item.get("reason", "Unknown"),
                })
                continue

            batch = item["batch"]

            production_rows.append({
                "Machine": item["machine_id"],
                "Order": batch["order_id"],
                "Batch": batch["batch_id"],
                "Result": "Produced",
                "Produced (m)": item["produced_quantity_m"],
                "Material Used (kg)": item["material_consumed_kg"],
                "Quality Score": batch["quality_score"],
                "Inspection": batch["inspection_status"],
            })

        if production_rows:
            st.dataframe(
                production_rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No machine produced a batch during this cycle.")

        # Procurement results
        st.markdown("#### Procurement Activity")

        scheduled = last_result.get(
            "inventory_before", {}
        ).get("scheduled_shipments", [])

        if scheduled:
            st.dataframe(
                [
                    {
                        "Shipment": item["shipment_id"],
                        "Material": item["material_name"],
                        "Supplier": item["supplier_name"],
                        "Quantity (kg)": item["quantity_kg"],
                        "ETA": item["eta"],
                    }
                    for item in scheduled
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("No new procurement shipment was required before this cycle.")

    st.divider()

    # --------------------------------------------------------
    # FINISHED GOODS
    # --------------------------------------------------------

    st.markdown("### Finished Goods Inventory")

    finished = factory.get("finished_goods", {})

    finished_rows = [
        {
            "Order": order_id,
            "Client": item.get("client"),
            "Fabric": item.get("fabric_type"),
            "Quantity (m)": item.get("quantity_m", 0),
            "Status": item.get("status"),
        }
        for order_id, item in finished.items()
        if float(item.get("quantity_m", 0)) > 0
        or item.get("status") == "DISPATCHED"
    ]

    if finished_rows:
        st.dataframe(
            finished_rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No accepted finished goods have been produced yet.")

    st.divider()

    # --------------------------------------------------------
    # DISPATCH HISTORY
    # --------------------------------------------------------

    st.markdown("### Dispatch History")

    dispatches = factory.get("dispatch_history", [])

    if dispatches:
        st.dataframe(
            dispatches,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No customer orders dispatched yet.")

    st.divider()

    # --------------------------------------------------------
    # RECENT WORKFLOW EVENTS
    # --------------------------------------------------------

    st.markdown("### Factory Event Timeline")

    events = factory.get("workflow_events", [])

    if events:
        recent = list(reversed(events[-15:]))

        st.dataframe(
            [
                {
                    "Time": item.get("timestamp"),
                    "Event": item.get("event_type"),
                    "Description": item.get("message"),
                }
                for item in recent
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Workflow events will appear here.")
