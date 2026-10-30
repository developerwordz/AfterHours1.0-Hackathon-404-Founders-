"""
recovery.py — Recovery plan generation, evaluation, and comparison for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""

from scheduler import calculate_production_time, check_machine_capacity


def _calculate_material_shortfall(factory: dict, order: dict) -> dict:
    """Helper to check if raw materials in stock are sufficient for the remaining order."""
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
    and total additional operational/procurement cost.

    Args:
        factory (dict): Current factory state.
        plan (dict): Candidate recovery plan dictionary.

    Returns:
        dict: The enriched plan dictionary with 'feasible', 'meets_deadline',
              'total_time_hrs', 'additional_cost_usd', and 'evaluation_notes'.
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

    # 2. Check Spare Parts if waiting for failed machine repair
    machine_ready_delay_hrs = 0.0
    repair_cost_usd = 0.0
    if plan["strategy_type"] == "WAIT_FOR_REPAIR":
        part_id = machine["required_spare_part"]
        part = factory["spare_parts"].get(part_id, {})
        if part.get("in_stock", 0) <= 0:
            feasible = False
            notes.append(f"Missing required spare part '{part_id}' in inventory.")
        else:
            machine_ready_delay_hrs = machine["maintenance_duration_hrs"]
            repair_cost_usd = part.get("cost_usd", 0.0)
            notes.append(f"Uses 1x '{part_id}' (${repair_cost_usd}) + {machine_ready_delay_hrs}h repair.")

    
    # 3. Check Raw Material & Supplier Procurement
    supplier_delay_hrs = 0.0
    procurement_cost_usd = 0.0
    shortfall_kg = mat_info["shortfall_kg"]

    if shortfall_kg > 0:
        supplier_id = plan.get("supplier_id")

        if not supplier_id:
            feasible = False
            notes.append(
                f"Raw material shortfall of {shortfall_kg}kg "
                f"({mat_info['raw_material_id']}) and no supplier specified."
            )

        elif supplier_id not in factory["suppliers"]:
            feasible = False
            notes.append(f"Supplier '{supplier_id}' does not exist.")

        else:
            supplier = factory["suppliers"][supplier_id]
            rm_id = mat_info["raw_material_id"]

            # Check supplier availability
            if supplier.get("status", "ACTIVE") != "ACTIVE":
                feasible = False
                notes.append(
                    f"Supplier {supplier['name']} is unavailable "
                    f"(status: {supplier.get('status')})."
                )

            # Check material support
            elif rm_id not in supplier.get("cost_per_kg", {}):
                feasible = False
                notes.append(
                    f"{supplier['name']} does not supply {rm_id}."
                )

            else:
                # Check remaining supplier capacity
                max_supply = supplier.get("max_supply_kg", float("inf"))
                committed = supplier.get("committed_supply_kg", 0.0)
                remaining_capacity = max(0.0, max_supply - committed)

                if shortfall_kg > remaining_capacity:
                    feasible = False
                    notes.append(
                        f"{supplier['name']} has insufficient capacity. "
                        f"Required: {shortfall_kg}kg, "
                        f"Available capacity: {remaining_capacity}kg."
                    )

                else:
                    supplier_delay_hrs = supplier["delivery_time_hrs"]

                    unit_cost = supplier["cost_per_kg"][rm_id]

                    procurement_cost_usd = round(
                        shortfall_kg * unit_cost
                        + supplier["rush_fee_usd"],
                        2
                    )

                    notes.append(
                        f"Procures {shortfall_kg}kg {rm_id} from "
                        f"{supplier['name']} "
                        f"(${procurement_cost_usd}, "
                        f"ETA {supplier_delay_hrs}h)."
                    )

    else:
        notes.append(
            f"Sufficient {mat_info['raw_material_id']} in stock "
            f"({mat_info['available_kg']}kg available)."
        )

    # 4. Calculate Production Time, Total Duration & Costs
    if feasible:
        production_hrs = calculate_production_time(order, machine)
        # Setup/waiting time before full completion:
        # Note: Existing stock (400kg = 400m) can start weaving immediately once machine is ready!
        # Wait delay only occurs if supplier delivery takes longer than weaving the in-stock material,
        # OR we conservatively take max(machine_ready_delay_hrs, supplier_delay_hrs) before final batch.
        in_stock_meters = mat_info["available_kg"] / order.get("raw_material_per_m", 1.0)
        hrs_covered_by_stock = round(in_stock_meters / machine["capacity_m_per_hr"], 2)

        # Effective wait time after machine is ready if supplier arrives after in-stock yarn runs out
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

    late_penalty_usd = round(hours_late * order.get("penalty_per_hr_late", 0.0), 2) if (feasible and not meets_deadline) else 0.0
    total_additional_cost_usd = round(repair_cost_usd + procurement_cost_usd + operating_cost_usd + late_penalty_usd, 2) if feasible else float("inf")

    if feasible:
        if meets_deadline:
            notes.append(f"MEETS DEADLINE: Finishes in {total_time_hrs}h vs {deadline_hrs}h deadline ({round(deadline_hrs - total_time_hrs, 2)}h buffer).")
        else:
            notes.append(f"MISSES DEADLINE by {hours_late}h ({total_time_hrs}h vs {deadline_hrs}h). Penalty: ${late_penalty_usd}.")

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
    Compares a list of evaluated recovery plans and ranks them.
    Ranking priority:
        1. Feasible plans over infeasible plans.
        2. Plans that meet the deadline over plans that miss the deadline.
        3. Lowest total additional cost (operational + procurement + penalties).
        4. Fastest total completion time.

    Args:
        plans (list): List of evaluated plan dictionaries.

    Returns:
        dict: {
            "order_can_be_saved": bool,
            "recommended_plan": dict or None,
            "ranked_plans": list,
            "honest_assessment": str
        }
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
            not p.get("feasible", False),        # False (0) comes before True (1)
            not p.get("meets_deadline", False),  # False (0) comes before True (1)
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
        assessment = "CRITICAL FAILURE: No feasible recovery plan exists (all machines incompatible/busy or missing spare parts)."

    return {
        "order_can_be_saved": order_can_be_saved,
        "recommended_plan": best if best.get("feasible") else None,
        "ranked_plans": ranked,
        "honest_assessment": assessment,
    }


def generate_recovery_plan(factory: dict, incident: dict) -> dict:
    """
    Generates, evaluates, and compares all possible recovery strategies for
    every order affected by a machine failure incident.

    Args:
        factory (dict): Current factory state dictionary.
        incident (dict): Incident dictionary returned by simulate_machine_failure().

    Returns:
        dict: Complete recovery report keyed by affected order_id, including
              all candidate plans, comparison results, and recommended actions.
    """
    failed_machine_id = incident["machine_id"]
    affected_order_ids = incident.get("affected_order_ids", [])

    recovery_report = {
        "incident_id": incident["incident_id"],
        "failed_machine_id": failed_machine_id,
        "orders_recovery": {},
    }

    for order_id in affected_order_ids:
        order = factory["orders"][order_id]
        mat_info = _calculate_material_shortfall(factory, order)
        needs_material = not mat_info["has_enough_material"]

        candidate_plans = []
        plan_counter = 1

        # Determine supplier options to test
        # Determine supplier options to test
       
        # Dynamically discover available suppliers
        available_suppliers = [
            supplier_id
            for supplier_id, supplier in factory["suppliers"].items()
            if supplier.get("status", "ACTIVE") == "ACTIVE"
            and order["raw_material_id"] in supplier.get("cost_per_kg", {})
        ]

        supplier_options = (
            [None] + available_suppliers
            if needs_material
            else [None]
        )


        # Strategy Group A: Reassign to other machines
        for m_id, machine in factory["machines"].items():
            if m_id == failed_machine_id:
                continue

            for sup_id in supplier_options:
                if sup_id is None and needs_material:
                    # Also generate the pure reassignment plan (without supplier) to show why it fails without material
                    strat_type = "REASSIGN_MACHINE"
                    sup_label = "In-Stock Material Only"
                elif sup_id is not None:
                    strat_type = "COMBINED_REASSIGN_AND_PROCURE"
                    sup_label = f"Procure via {factory['suppliers'][sup_id]['name']}"
                else:
                    strat_type = "REASSIGN_MACHINE"
                    sup_label = "Use Existing Stock"

                plan = {
                    "plan_id": f"PLAN-{order_id}-{plan_counter:02d}",
                    "order_id": order_id,
                    "strategy_type": strat_type,
                    "name": f"Reassign to {m_id} ({machine['name']}) + {sup_label}",
                    "target_machine_id": m_id,
                    "supplier_id": sup_id,
                    "actions": [
                        f"Reroute remaining {order['remaining_quantity_m']}m of {order['id']} from {failed_machine_id} to {m_id}"
                    ] + ([f"Order {mat_info['shortfall_kg']}kg {mat_info['raw_material_id']} from {sup_id}"] if sup_id else []),
                }
                candidate_plans.append(evaluate_recovery_plan(factory, plan))
                plan_counter += 1

        # Strategy Group B: Wait for failed machine maintenance (+ supplier options if needed)
        for sup_id in supplier_options:
            sup_label = f" + Procure via {factory['suppliers'][sup_id]['name']}" if sup_id else ""
            plan = {
                "plan_id": f"PLAN-{order_id}-{plan_counter:02d}",
                "order_id": order_id,
                "strategy_type": "WAIT_FOR_REPAIR",
                "name": f"Repair {failed_machine_id} ({factory['machines'][failed_machine_id]['maintenance_duration_hrs']}h){sup_label}",
                "target_machine_id": failed_machine_id,
                "supplier_id": sup_id,
                "actions": [
                    f"Complete {factory['machines'][failed_machine_id]['maintenance_duration_hrs']}h maintenance on {failed_machine_id}",
                    f"Resume {order['id']} on {failed_machine_id}",
                ] + ([f"Order {mat_info['shortfall_kg']}kg {mat_info['raw_material_id']} from {sup_id}"] if sup_id else []),
            }
            candidate_plans.append(evaluate_recovery_plan(factory, plan))
            plan_counter += 1

        comparison = compare_recovery_plans(candidate_plans)
        recovery_report["orders_recovery"][order_id] = comparison

    return recovery_report

def apply_recovery_plan(factory: dict, plan: dict) -> dict:
    """
    STAGE 3 (ACT): Executes an approved recovery plan by mutating the factory state
    (reassigning machines, consuming spare parts, reserving raw materials, and updating statuses).

    Args:
        factory (dict): Current factory state dictionary.
        plan (dict): An evaluated recovery plan dictionary from generate_recovery_plan().

    Returns:
        dict: Execution receipt summarizing state changes made to the factory.

    Raises:
        ValueError: If the plan is marked as infeasible.
    """
    if not plan.get("feasible", False):
        raise ValueError(f"Cannot apply infeasible plan '{plan.get('plan_id')}': {plan.get('evaluation_notes')}")

    order_id = plan["order_id"]
    target_machine_id = plan["target_machine_id"]
    order = factory["orders"][order_id]
    
    # Revalidate supplier before executing an approved plan
    mat_info = _calculate_material_shortfall(factory, order)
    supplier_id = plan.get("supplier_id")

    if mat_info["shortfall_kg"] > 0:
        if not supplier_id:
            raise ValueError("Cannot execute: raw material shortfall has no supplier.")

        supplier = factory["suppliers"].get(supplier_id)

        if not supplier or supplier.get("status", "ACTIVE") != "ACTIVE":
            raise ValueError(
                f"Cannot execute: supplier {supplier_id} is unavailable."
            )

        rm_id = mat_info["raw_material_id"]

        if rm_id not in supplier.get("cost_per_kg", {}):
            raise ValueError(
                f"Supplier {supplier_id} cannot supply {rm_id}."
            )

        remaining_capacity = (
            supplier.get("max_supply_kg", float("inf"))
            - supplier.get("committed_supply_kg", 0.0)
        )

        if mat_info["shortfall_kg"] > remaining_capacity:
            raise ValueError(
                f"Supplier {supplier_id} no longer has sufficient capacity."
            )

    old_machine_id = order["assigned_machine_id"]
    target_machine = factory["machines"][target_machine_id]

    changes = []

    # 1. Handle Machine Assignment & Maintenance Status
    if plan["strategy_type"] == "WAIT_FOR_REPAIR":
        part_id = target_machine["required_spare_part"]
        factory["spare_parts"][part_id]["in_stock"] -= 1
        target_machine["status"] = "MAINTENANCE"
        changes.append(f"Consumed 1x '{part_id}' and placed {target_machine_id} into MAINTENANCE.")
    else:
        # Reassigning to a different machine
        if old_machine_id and old_machine_id != target_machine_id:
            factory["machines"][old_machine_id]["assigned_order_id"] = None
            factory["machines"][old_machine_id]["status"] = "MAINTENANCE"
            changes.append(f"Unassigned {order_id} from {old_machine_id} (moved {old_machine_id} to MAINTENANCE).")

        target_machine["assigned_order_id"] = order_id
        target_machine["status"] = "RUNNING"
        order["assigned_machine_id"] = target_machine_id
        changes.append(f"Assigned {order_id} to {target_machine_id} (status: RUNNING).")

    # 2. Handle Raw Material Reservation & Supplier Procurement
    mat_info = _calculate_material_shortfall(factory, order)
    rm_id = mat_info["raw_material_id"]
    rm_entry = factory["raw_materials"][rm_id]

    if mat_info["shortfall_kg"] > 0 and plan.get("supplier_id"):
        sup = factory["suppliers"][plan["supplier_id"]]

        quantity = mat_info["shortfall_kg"]

        rm_entry["stock_kg"] += quantity

        sup["committed_supply_kg"] = (
            sup.get("committed_supply_kg", 0.0) + quantity
        )

        changes.append(
            f"Procured {quantity}kg of {rm_id} "
            f"from {sup['name']}."
        )

    rm_entry["reserved_kg"] += mat_info["required_kg"]
    changes.append(f"Reserved {mat_info['required_kg']}kg of {rm_id} for {order_id}.")

    # 3. Update Order Status
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
    """
    STAGE 4 (VERIFY): Closed-loop check confirming that the order has a working/repairing
    machine, sufficient reserved raw material, and a valid completion schedule.

    Args:
        factory (dict): Updated factory state after apply_recovery_plan().
        order_id (str): ID of the order to verify.

    Returns:
        dict: Verification report with boolean checks and overall pass/fail status.
    """
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
    from factory import create_factory, simulate_machine_failure

    print("=== TASK 3 TEST: recovery.py ===")
    f = create_factory()
    incident = simulate_machine_failure(f, "M1")
    report = generate_recovery_plan(f, incident)

    for ord_id, res in report["orders_recovery"].items():
        print(f"\n--- Recovery Analysis for {ord_id} ---")
        print("Assessment:", res["honest_assessment"])
        print("\nRanked Plans:")
        for idx, p in enumerate(res["ranked_plans"], 1):
            status = "✅ SAVES ORDER" if p["meets_deadline"] else ("⚠️ LATE" if p["feasible"] else "❌ INFEASIBLE")
            print(f"  {idx}. [{status}] {p['plan_id']}: {p['name']}")
            print(f"     Time: {p['total_time_hrs']}h (Deadline: {p['deadline_hrs']}h) | Cost: ${p['additional_cost_usd']}")
            print(f"     Notes: {p['evaluation_notes']}")