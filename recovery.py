"""
recovery.py — Recovery Engine 2.0: Multi-disruption & factory-wide recovery for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""

from copy import deepcopy
from scheduler import calculate_production_time, check_machine_capacity


def _calculate_material_shortfall(factory: dict, order: dict) -> dict:
    """Checks if raw materials in stock are sufficient for the remaining order."""
    rm_id = order["raw_material_id"]
    rm_data = factory["raw_materials"][rm_id]
    available_kg = max(0.0, rm_data["stock_kg"] - rm_data["reserved_kg"])
    required_kg = round(order["remaining_quantity_m"] * order.get("raw_material_per_m", 1.0), 2)
    shortfall_kg = max(0.0, round(required_kg - available_kg, 2))

    return {
        "raw_material_id": rm_id,
        "required_kg": required_kg,
        "available_kg": available_kg,
        "shortfall_kg": shortfall_kg,
        "has_enough_material": shortfall_kg == 0.0,
    }


def evaluate_recovery_plan(factory: dict, plan: dict) -> dict:
    """
    Evaluates a single candidate recovery plan for feasibility, timing, deadline adherence,
    and total additional operational/procurement/penalty cost.
    """
    order = factory["orders"][plan["order_id"]]
    machine = factory["machines"][plan["target_machine_id"]]
    mat_info = _calculate_material_shortfall(factory, order)
    cap_check = check_machine_capacity(order, machine)

    notes = []
    feasible = True

    # 1. Check Machine Compatibility & Availability
    if not cap_check["can_accept_order"]:
        feasible = False
        notes.append(cap_check["reason"])

    # 2. Check Spare Parts & Maintenance Delay if using a FAILED or MAINTENANCE machine
    machine_ready_delay_hrs = 0.0
    repair_cost_usd = 0.0
    if plan["strategy_type"] == "WAIT_FOR_REPAIR" or machine["status"] in ("FAILED", "MAINTENANCE"):
        part_id = machine["required_spare_part"]
        part = factory["spare_parts"].get(part_id, {})
        if machine["status"] == "FAILED" and part.get("in_stock", 0) <= 0:
            feasible = False
            notes.append(f"Missing required spare part '{part_id}' in inventory.")
        else:
            machine_ready_delay_hrs = machine["maintenance_duration_hrs"]
            if machine["status"] == "FAILED":
                repair_cost_usd = part.get("cost_usd", 0.0)
                notes.append(f"Uses 1x '{part_id}' (${repair_cost_usd}) + {machine_ready_delay_hrs}h repair.")
            else:
                notes.append(f"Waits {machine_ready_delay_hrs}h for ongoing maintenance on {machine['id']}.")

    # 3. Check Raw Material & Supplier Procurement
    supplier_delay_hrs = 0.0
    procurement_cost_usd = 0.0
    shortfall_kg = mat_info["shortfall_kg"]

    if shortfall_kg > 0:
        supplier_id = plan.get("supplier_id")
        if not supplier_id:
            feasible = False
            notes.append(
                f"Raw material shortfall of {shortfall_kg}kg ({mat_info['raw_material_id']}) "
                "and no supplier specified in plan."
            )
        else:
            supplier = factory["suppliers"][supplier_id]
            supplier_delay_hrs = supplier["delivery_time_hrs"]
            unit_cost = supplier["cost_per_kg"][mat_info["raw_material_id"]]
            procurement_cost_usd = round(shortfall_kg * unit_cost + supplier["rush_fee_usd"], 2)
            notes.append(
                f"Procures {shortfall_kg}kg {mat_info['raw_material_id']} from {supplier['name']} "
                f"(${procurement_cost_usd}, ETA {supplier_delay_hrs}h)."
            )
    else:
        notes.append(f"Sufficient {mat_info['raw_material_id']} in stock ({mat_info['available_kg']}kg available).")

    # 4. Calculate Production Time, Total Duration & Costs
    if feasible:
        production_hrs = calculate_production_time(order, machine)
        in_stock_meters = mat_info["available_kg"] / order.get("raw_material_per_m", 1.0)
        hrs_covered_by_stock = round(in_stock_meters / machine["capacity_m_per_hr"], 2)

        material_wait_hrs = max(0.0, supplier_delay_hrs - (machine_ready_delay_hrs + hrs_covered_by_stock))
        start_delay_hrs = round(machine_ready_delay_hrs + material_wait_hrs, 2)

        total_time_hrs = round(start_delay_hrs + production_hrs, 2)
        operating_cost_usd = round(production_hrs * machine["operating_cost_per_hr"], 2)
    else:
        production_hrs = 0.0
        start_delay_hrs = float("inf")
        total_time_hrs = float("inf")
        operating_cost_usd = 0.0

    deadline_hrs = order["deadline_hrs"]
    meets_deadline = feasible and (total_time_hrs <= deadline_hrs)
    hours_late = max(0.0, round(total_time_hrs - deadline_hrs, 2)) if feasible else float("inf")

    late_penalty_usd = (
        round(hours_late * order.get("penalty_per_hr_late", 0.0), 2)
        if (feasible and not meets_deadline)
        else 0.0
    )
    total_additional_cost_usd = (
        round(repair_cost_usd + procurement_cost_usd + operating_cost_usd + late_penalty_usd, 2)
        if feasible
        else float("inf")
    )

    if feasible:
        if meets_deadline:
            notes.append(
                f"MEETS DEADLINE: Finishes in {total_time_hrs}h vs {deadline_hrs}h deadline "
                f"({round(deadline_hrs - total_time_hrs, 2)}h buffer)."
            )
        else:
            notes.append(
                f"MISSES DEADLINE by {hours_late}h ({total_time_hrs}h vs {deadline_hrs}h). "
                f"Penalty: ${late_penalty_usd}."
            )

    plan.update({
        "feasible": feasible,
        "meets_deadline": meets_deadline,
        "production_time_hrs": production_hrs,
        "delay_hrs": start_delay_hrs,
        "total_time_hrs": total_time_hrs,
        "deadline_hrs": deadline_hrs,
        "hours_late": hours_late,
        "cost_breakdown_usd": {
            "repair_cost": repair_cost_usd,
            "procurement_cost": procurement_cost_usd,
            "operating_cost": operating_cost_usd,
            "late_penalty": late_penalty_usd,
        },
        "additional_cost_usd": total_additional_cost_usd,
        "evaluation_notes": " | ".join(notes),
    })
    return plan


def compare_recovery_plans(plans: list) -> dict:
    """
    Compares a list of evaluated recovery plans and ranks them by:
    1. Feasibility
    2. Meeting the deadline
    3. Lowest total additional cost (including late penalties)
    4. Fastest completion time
    """
    if not plans:
        return {
            "order_can_be_saved": False,
            "recommended_plan": None,
            "ranked_plans": [],
            "honest_assessment": "No candidate recovery plans were generated.",
        }

    def sort_key(p):
        return (
            not p.get("feasible", False),
            not p.get("meets_deadline", False),
            p.get("additional_cost_usd", float("inf")),
            p.get("total_time_hrs", float("inf")),
        )

    ranked = sorted(plans, key=sort_key)
    best = ranked[0]
    order_can_be_saved = bool(best.get("feasible") and best.get("meets_deadline"))

    if order_can_be_saved:
        assessment = (
            f"ORDER SAVED: Plan '{best['plan_id']}' ({best['name']}) meets the {best['deadline_hrs']}h "
            f"deadline in {best['total_time_hrs']}h at an additional cost of ${best['additional_cost_usd']}."
        )
    elif best.get("feasible"):
        assessment = (
            f"WARNING — DEADLINE CANNOT BE MET: No feasible plan can meet the {best['deadline_hrs']}h deadline. "
            f"The best damage-mitigation option is '{best['plan_id']}' ({best['name']}), completing in "
            f"{best['total_time_hrs']}h ({best['hours_late']}h late) with total cost ${best['additional_cost_usd']}."
        )
    else:
        assessment = (
            "CRITICAL FAILURE: No feasible recovery plan exists "
            "(all machines incompatible/busy or missing required spare parts)."
        )

    return {
        "order_can_be_saved": order_can_be_saved,
        "recommended_plan": best if best.get("feasible") else None,
        "ranked_plans": ranked,
        "honest_assessment": assessment,
    }


def _generate_plans_for_order(factory: dict, order_id: str) -> dict:
    """Generates and compares all candidate recovery plans for a single order."""
    order = factory["orders"][order_id]
    current_machine_id = order.get("assigned_machine_id")
    mat_info = _calculate_material_shortfall(factory, order)
    needs_material = not mat_info["has_enough_material"]

    candidate_plans = []
    plan_counter = 1
    supplier_options = [None] if not needs_material else [None, "SUP-PRIMARY", "SUP-BACKUP"]

    for m_id, machine in factory["machines"].items():
        is_current_failed_or_maint = (
            m_id == current_machine_id and machine["status"] in ("FAILED", "MAINTENANCE")
        )

        # If this is the currently assigned machine and it failed/is in maintenance, generate WAIT_FOR_REPAIR plans
        if is_current_failed_or_maint:
            repair_sup_opts = [None] if not needs_material else ["SUP-PRIMARY", "SUP-BACKUP"]
            for sup_id in repair_sup_opts:
                sup_label = f" + Procure via {factory['suppliers'][sup_id]['name']}" if sup_id else ""
                plan = {
                    "plan_id": f"PLAN-{order_id}-{plan_counter:02d}",
                    "order_id": order_id,
                    "strategy_type": "WAIT_FOR_REPAIR",
                    "name": f"Repair {m_id} ({machine['maintenance_duration_hrs']}h){sup_label}",
                    "target_machine_id": m_id,
                    "supplier_id": sup_id,
                    "actions": [
                        f"Complete {machine['maintenance_duration_hrs']}h maintenance on {m_id}",
                        f"Resume {order_id} on {m_id}",
                    ] + ([f"Order {mat_info['shortfall_kg']}kg {mat_info['raw_material_id']} from {sup_id}"] if sup_id else []),
                }
                candidate_plans.append(evaluate_recovery_plan(factory, plan))
                plan_counter += 1
        else:
            # Machine is either another machine (reassignment) or the current healthy machine (material-only recovery)
            for sup_id in supplier_options:
                if m_id == current_machine_id:
                    strat_type = "PROCURE_MATERIAL" if sup_id else "CONTINUE_ON_MACHINE"
                    action_prefix = f"Keep {order_id} on {m_id} ({machine['name']})"
                else:
                    strat_type = "COMBINED_REASSIGN_AND_PROCURE" if sup_id else "REASSIGN_MACHINE"
                    action_prefix = f"Reassign to {m_id} ({machine['name']})"

                sup_label = (
                    f"Procure via {factory['suppliers'][sup_id]['name']}"
                    if sup_id
                    else ("In-Stock Material Only" if needs_material else "Use Existing Stock")
                )

                actions = []
                if m_id != current_machine_id:
                    actions.append(
                        f"Reroute remaining {order['remaining_quantity_m']}m of {order_id} "
                        f"from {current_machine_id or 'QUEUE'} to {m_id}"
                    )
                if sup_id:
                    actions.append(f"Order {mat_info['shortfall_kg']}kg {mat_info['raw_material_id']} from {sup_id}")
                if not actions:
                    actions.append(f"Continue {order_id} on {m_id} with existing stock")

                plan = {
                    "plan_id": f"PLAN-{order_id}-{plan_counter:02d}",
                    "order_id": order_id,
                    "strategy_type": strat_type,
                    "name": f"{action_prefix} + {sup_label}",
                    "target_machine_id": m_id,
                    "supplier_id": sup_id,
                    "actions": actions,
                }
                candidate_plans.append(evaluate_recovery_plan(factory, plan))
                plan_counter += 1

    return compare_recovery_plans(candidate_plans)


def generate_recovery_plan(factory: dict, incident: dict) -> dict:
    """
    Backwards-compatible single-incident recovery planner.
    Evaluates all orders affected by the given incident.
    """
    affected_order_ids = incident.get("affected_order_ids", [])
    recovery_report = {
        "incident_id": incident.get("incident_id", "INC-001"),
        "failed_machine_id": incident.get("machine_id"),
        "orders_recovery": {},
    }

    # Use a working copy so multi-order incidents don't double-book an IDLE machine
    working_factory = deepcopy(factory)
    for order_id in affected_order_ids:
        comparison = _generate_plans_for_order(working_factory, order_id)
        recovery_report["orders_recovery"][order_id] = comparison
        if comparison["recommended_plan"]:
            apply_recovery_plan(working_factory, comparison["recommended_plan"])

    return recovery_report


def generate_factory_recovery_report(factory: dict, incidents=None) -> dict:
    """
    Recovery Engine 2.0: Evaluates multiple incidents across the entire factory,
    resolving machine/material contention across all affected orders.

    Args:
        factory (dict): Current factory state.
        incidents (list | dict | None): List of incident dicts, a single incident dict,
                                        or None (uses factory['incidents']).

    Returns:
        dict: {
            "affected_orders": list[str],
            "affected_machines": list[str],
            "recommended_actions": list[str],
            "total_recovery_cost": float,
            "orders_saved": list[str],
            "orders_at_risk": list[str],
            "overall_feasibility": str, # "FULL_RECOVERY", "PARTIAL_RECOVERY", "UNRECOVERABLE", "NO_DISRUPTION"
            "order_reports": dict
        }
    """
    if incidents is None:
        incident_list = factory.get("incidents", [])
    elif isinstance(incidents, dict):
        incident_list = [incidents]
    else:
        incident_list = list(incidents)

    # Collect unique affected machines and orders across all incidents + current factory state
    affected_machines = []
    for inc in incident_list:
        if inc.get("machine_id") and inc["machine_id"] not in affected_machines:
            affected_machines.append(inc["machine_id"])
        for m_id in inc.get("affected_machine_ids", []):
            if m_id not in affected_machines:
                affected_machines.append(m_id)

    for m_id, m in factory["machines"].items():
        if m["status"] in ("FAILED", "MAINTENANCE") and m_id not in affected_machines:
            affected_machines.append(m_id)

    affected_orders = []
    for inc in incident_list:
        for o_id in inc.get("affected_order_ids", []):
            if o_id not in affected_orders:
                affected_orders.append(o_id)

    for o_id, o in factory["orders"].items():
        if o["status"] == "AT_RISK" and o_id not in affected_orders:
            affected_orders.append(o_id)

    if not affected_orders:
        return {
            "affected_orders": [],
            "affected_machines": affected_machines,
            "recommended_actions": [],
            "total_recovery_cost": 0.0,
            "orders_saved": [],
            "orders_at_risk": [],
            "overall_feasibility": "NO_DISRUPTION",
            "order_reports": {},
        }

    # Prioritize orders by urgency (tightest deadline first, then highest late penalty)
    affected_orders.sort(
        key=lambda oid: (
            factory["orders"][oid]["deadline_hrs"],
            -factory["orders"][oid].get("penalty_per_hr_late", 0.0),
        )
    )

    working_factory = deepcopy(factory)
    order_reports = {}
    recommended_actions = []
    total_recovery_cost = 0.0
    orders_saved = []
    orders_still_at_risk = []

    for order_id in affected_orders:
        comparison = _generate_plans_for_order(working_factory, order_id)
        order_reports[order_id] = comparison
        best_plan = comparison["recommended_plan"]

        if best_plan and best_plan.get("feasible"):
            # Lock resources in working_factory so subsequent orders cannot double-book the same idle machine/stock
            apply_recovery_plan(working_factory, best_plan)
            total_recovery_cost = round(total_recovery_cost + best_plan["additional_cost_usd"], 2)
            for act in best_plan["actions"]:
                recommended_actions.append(f"[{order_id}] {act}")

            if comparison["order_can_be_saved"]:
                orders_saved.append(order_id)
            else:
                orders_still_at_risk.append(order_id)
        else:
            orders_still_at_risk.append(order_id)
            recommended_actions.append(f"[{order_id}] NO FEASIBLE RECOVERY PLAN — Manual intervention required.")

    if len(orders_saved) == len(affected_orders):
        overall_feasibility = "FULL_RECOVERY"
    elif len(orders_saved) > 0 or any(
        order_reports[oid]["recommended_plan"] is not None for oid in affected_orders
    ):
        overall_feasibility = "PARTIAL_RECOVERY"
    else:
        overall_feasibility = "UNRECOVERABLE"

    return {
        "affected_orders": affected_orders,
        "affected_machines": affected_machines,
        "recommended_actions": recommended_actions,
        "total_recovery_cost": total_recovery_cost,
        "orders_saved": orders_saved,
        "orders_at_risk": orders_still_at_risk,
        "overall_feasibility": overall_feasibility,
        "order_reports": order_reports,
    }


def apply_recovery_plan(factory: dict, plan: dict) -> dict:
    """Executes an approved recovery plan by mutating the factory state."""
    if not plan or not plan.get("feasible", False):
        raise ValueError(f"Cannot apply infeasible plan '{plan.get('plan_id') if plan else None}'.")

    order_id = plan["order_id"]
    target_machine_id = plan["target_machine_id"]
    order = factory["orders"][order_id]
    old_machine_id = order["assigned_machine_id"]
    target_machine = factory["machines"][target_machine_id]

    changes = []

    if plan["strategy_type"] == "WAIT_FOR_REPAIR":
        part_id = target_machine["required_spare_part"]
        if target_machine["status"] == "FAILED":
            factory["spare_parts"][part_id]["in_stock"] -= 1
            changes.append(f"Consumed 1x '{part_id}'.")
        target_machine["status"] = "MAINTENANCE"
        changes.append(f"Placed {target_machine_id} into MAINTENANCE.")
    else:
        if old_machine_id and old_machine_id != target_machine_id:
            factory["machines"][old_machine_id]["assigned_order_id"] = None
            if factory["machines"][old_machine_id]["status"] == "FAILED":
                factory["machines"][old_machine_id]["status"] = "MAINTENANCE"
            changes.append(f"Unassigned {order_id} from {old_machine_id}.")

        target_machine["assigned_order_id"] = order_id
        target_machine["status"] = "RUNNING"
        order["assigned_machine_id"] = target_machine_id
        changes.append(f"Assigned {order_id} to {target_machine_id} (status: RUNNING).")

    mat_info = _calculate_material_shortfall(factory, order)
    rm_id = mat_info["raw_material_id"]
    rm_entry = factory["raw_materials"][rm_id]

    if mat_info["shortfall_kg"] > 0 and plan.get("supplier_id"):
        sup = factory["suppliers"][plan["supplier_id"]]
        rm_entry["stock_kg"] += mat_info["shortfall_kg"]
        changes.append(f"Procured {mat_info['shortfall_kg']}kg of {rm_id} from {sup['name']}.")

    rm_entry["reserved_kg"] += mat_info["required_kg"]
    changes.append(f"Reserved {mat_info['required_kg']}kg of {rm_id} for {order_id}.")

    order["status"] = "REASSIGNED" if plan["meets_deadline"] else "DELAYED"
    changes.append(f"Updated {order_id} status to '{order['status']}'.")

    return {
        "applied_plan_id": plan["plan_id"],
        "order_id": order_id,
        "new_order_status": order["status"],
        "assigned_machine_id": order["assigned_machine_id"],
        "estimated_completion_hrs": plan["total_time_hrs"],
        "deadline_hrs": order["deadline_hrs"],
        "meets_deadline": plan["meets_deadline"],
        "state_changes": changes,
    }


def verify_recovery(factory: dict, order_id: str) -> dict:
    """Closed-loop check confirming that the order has an active machine and locked raw material."""
    order = factory["orders"][order_id]
    machine_id = order["assigned_machine_id"]
    machine = factory["machines"].get(machine_id) if machine_id else None
    rm = factory["raw_materials"][order["raw_material_id"]]
    required_kg = round(order["remaining_quantity_m"] * order.get("raw_material_per_m", 1.0), 2)

    machine_valid = machine is not None and machine["status"] in ("RUNNING", "MAINTENANCE")
    material_locked = rm["reserved_kg"] >= required_kg
    status_resolved = order["status"] in ("REASSIGNED", "DELAYED", "IN_PROGRESS", "COMPLETED")

    verified = bool(machine_valid and material_locked and status_resolved)

    return {
        "order_id": order_id,
        "verified": verified,
        "checks": {
            "machine_assigned_and_active": machine_valid,
            "raw_material_reserved": material_locked,
            "order_no_longer_at_risk": status_resolved,
        },
        "current_machine": machine_id,
        "order_status": order["status"],
        "summary": (
            f"VERIFIED: {order_id} is locked on {machine_id} with {required_kg}kg {rm['id']} reserved."
            if verified
            else f"VERIFICATION FAILED for {order_id}: check machine or material reservation."
        ),
    }


if __name__ == "__main__":
    from factory import create_factory, simulate_multiple_failures

    print("=== RECOVERY ENGINE 2.0 TEST: Simultaneous M1 + M3 Failure ===")
    f = create_factory()
    incidents = simulate_multiple_failures(f, ["M1", "M3"])
    report = generate_factory_recovery_report(f, incidents)

    print("Affected Machines:", report["affected_machines"])
    print("Affected Orders:  ", report["affected_orders"])
    print("Orders Saved:     ", report["orders_saved"])
    print("Orders At Risk:   ", report["orders_at_risk"])
    print("Total Cost ($):   ", report["total_recovery_cost"])
    print("Feasibility:      ", report["overall_feasibility"])
    print("\nRecommended Factory-Wide Actions:")
    for act in report["recommended_actions"]:
        print(" -", act)