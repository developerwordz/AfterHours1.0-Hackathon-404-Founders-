from recovery import verify_recovery


def machine_agent(factory, incident):
    machine_id = incident["machine_id"]
    machine = factory["machines"][machine_id]

    return {
        "agent": "Machine Agent",
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "status": machine["status"],
        "repair_hours": machine["maintenance_duration_hrs"],
        "required_spare_part": machine["required_spare_part"],
        "spare_part_available": incident["spare_part_in_stock"],
        "message": f"{machine['name']} has failed."
    }


def inventory_agent(factory, incident):
    available_materials = {}

    for material_id, material in factory["raw_materials"].items():
        available_materials[material_id] = {
            "available_kg": round(
                material["stock_kg"] - material["reserved_kg"], 2
            ),
            "name": material["name"]
        }

    return {
        "agent": "Inventory Agent",
        "materials": available_materials,
        "spare_parts": {
            part_id: part["in_stock"]
            for part_id, part in factory["spare_parts"].items()
        },
        "message": "Raw materials and spare parts checked."
    }


def production_agent(factory, incident):
    affected_orders = []

    for order_id in incident["affected_order_ids"]:
        order = factory["orders"][order_id]

        affected_orders.append({
            "order_id": order_id,
            "client": order["client"],
            "fabric_type": order["fabric_type"],
            "remaining_quantity_m": order["remaining_quantity_m"],
            "deadline_hrs": order["deadline_hrs"],
            "priority": order["priority"] if "priority" in order else None,
            "status": order["status"]
        })

    return {
        "agent": "Production Agent",
        "affected_orders": affected_orders,
        "message": f"{len(affected_orders)} order(s) affected by the failure."
    }


def sourcing_agent(factory, incident):
    suppliers = []

    for supplier_id, supplier in factory["suppliers"].items():
        suppliers.append({
            "supplier_id": supplier_id,
            "name": supplier["name"],
            "delivery_time_hrs": supplier["delivery_time_hrs"],
            "cost_per_kg": supplier["cost_per_kg"],
            "rush_fee_usd": supplier["rush_fee_usd"]
        })

    suppliers.sort(key=lambda item: item["delivery_time_hrs"])

    return {
        "agent": "Sourcing Agent",
        "suppliers": suppliers,
        "message": "Suppliers ranked by delivery time."
    }


def verification_agent(factory, order_id):
    return verify_recovery(factory, order_id)