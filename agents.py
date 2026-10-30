
def machine_agent(factory, incident):
    """Checks which machine failed and what its current condition is."""
    machine_id = incident["machine_id"]
    machine = factory["machines"].get(machine_id)

    if machine is None:
        return {"status": "error", "message": f"Machine {machine_id} not found"}

    return {
        "agent": "Machine Agent",
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "machine_status": machine["status"],
        "maintenance_hours": machine["maintenance_hours"],
        "affected_order": machine.get("current_order"),
        "message": f"{machine_id} is {machine['status']} and needs inspection."
    }


def inventory_agent(factory, incident):
    """Checks available materials and spare parts."""
    return {
        "agent": "Inventory Agent",
        "inventory": factory["inventory"],
        "spare_parts_available": factory["inventory"]["spare_parts"]["quantity"],
        "message": "Inventory checked successfully."
    }


def production_agent(factory, incident):
    """Identifies orders affected by the machine failure."""
    machine_id = incident["machine_id"]
    affected_orders = []

    for order_id, order in factory["orders"].items():
        if order["machine_id"] == machine_id:
            affected_orders.append({
                "order_id": order_id,
                "quantity": order["quantity"],
                "deadline_hours": order["deadline_hours"],
                "priority": order["priority"],
                "status": order["status"]
            })

    return {
        "agent": "Production Agent",
        "affected_orders": affected_orders,
        "message": f"Found {len(affected_orders)} affected order(s)."
    }


def sourcing_agent(factory, incident):
    """Checks available suppliers for emergency material procurement."""
    suppliers = []

    for supplier_id, supplier in factory["suppliers"].items():
        suppliers.append({
            "supplier_id": supplier_id,
            "name": supplier["name"],
            "lead_time_hours": supplier["lead_time_hours"],
            "cost_per_metre": supplier["cost_per_metre"],
            "reliability": supplier["reliability"]
        })

    suppliers.sort(key=lambda supplier: supplier["lead_time_hours"])

    return {
        "agent": "Sourcing Agent",
        "suppliers": suppliers,
        "message": "Suppliers ranked by delivery time."
    }


def verification_agent(factory, recovery_plan):
    """Checks whether a recovery plan has passed backend verification."""
    from recovery import evaluate_recovery_plan

    return evaluate_recovery_plan(factory, recovery_plan)
