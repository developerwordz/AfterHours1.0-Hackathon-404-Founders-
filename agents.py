
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


def inventory_agent(factory, incident=None):
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


def sourcing_agent(factory, incident=None):
    suppliers = []

    for supplier_id, supplier in factory["suppliers"].items():
        suppliers.append({
            "supplier_id": supplier_id,
            "name": supplier["name"],
            "tier": supplier.get("tier"),
            "type": supplier.get("type"),
            "status": supplier.get("status", "ACTIVE"),
            "reliability_score": supplier.get("reliability_score"),
            "delivery_time_hrs": supplier["delivery_time_hrs"],
            "cost_per_kg": supplier["cost_per_kg"],
            "rush_fee_usd": supplier["rush_fee_usd"],
            "max_supply_kg": supplier.get("max_supply_kg"),
            "committed_supply_kg": supplier.get(
                "committed_supply_kg", 0.0
            )
        })

    suppliers.sort(
        key=lambda item: (
            item["status"] != "ACTIVE",
            item["tier"] or 99
        )
    )

    active_count = sum(
        1 for supplier in suppliers
        if supplier["status"] == "ACTIVE"
    )

    return {
        "agent": "Sourcing Agent",
        "suppliers": suppliers,
        "active_supplier_count": active_count,
        "failed_supplier_count": len(suppliers) - active_count,
        "message": (
            f"Inspected {len(suppliers)} suppliers. "
            f"{active_count} active and "
            f"{len(suppliers) - active_count} unavailable."
        )
    }


def supplier_agent(factory, incident):
    supplier_id = incident.get("supplier_id")
    supplier = factory["suppliers"].get(supplier_id)

    if supplier is None:
        return {
            "agent": "Supplier Agent",
            "error": f"Supplier {supplier_id} not found."
        }

    affected_materials = list(supplier["cost_per_kg"].keys())
    alternatives = []

    for alternative_id, alternative in factory["suppliers"].items():
        if alternative_id == supplier_id:
            continue

        if alternative.get("status", "ACTIVE") != "ACTIVE":
            continue

        shared_materials = [
            material_id
            for material_id in affected_materials
            if material_id in alternative.get("cost_per_kg", {})
        ]

        if shared_materials:
            alternatives.append({
                "supplier_id": alternative_id,
                "name": alternative["name"],
                "tier": alternative.get("tier"),
                "reliability_score": alternative.get("reliability_score"),
                "delivery_time_hrs": alternative["delivery_time_hrs"],
                "materials_supported": shared_materials
            })

    alternatives.sort(
        key=lambda item: item["tier"] or 99
    )

    return {
        "agent": "Supplier Agent",
        "failed_supplier": supplier["name"],
        "failed_supplier_id": supplier_id,
        "failed_tier": supplier.get("tier"),
        "affected_materials": affected_materials,
        "available_alternatives": alternatives,
        "message": (
            f"Investigated failure of {supplier['name']}. "
            f"Found {len(alternatives)} active alternative suppliers."
        )
    }


def verification_agent(factory, order_id):
    return verify_recovery(factory, order_id)
