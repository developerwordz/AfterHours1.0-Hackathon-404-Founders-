"""
factory.py — Factory simulation and state management for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""

from copy import deepcopy
from datetime import datetime


def create_factory() -> dict:
    """
    Creates and returns the initial simulated textile factory state.

    Returns:
        dict: Complete factory state containing machines, orders,
              raw_materials, spare_parts, suppliers, and incident_log.
    """
    return {
        "machines": {
            "M1": {
                "id": "M1",
                "name": "High-Speed Air-Jet Loom #1",
                "status": "RUNNING",          # RUNNING, IDLE, FAILED, MAINTENANCE
                "capacity_m_per_hr": 60.0,    # Meters of fabric produced per hour
                "supported_fabrics": ["cotton_twill", "poly_blend"],
                "operating_cost_per_hr": 25.0,
                "maintenance_duration_hrs": 8.0,
                "required_spare_part": "bearing_set",
                "assigned_order_id": "ORD-101",
            },
            "M2": {
                "id": "M2",
                "name": "Versatile Rapier Loom #2",
                "status": "IDLE",
                "capacity_m_per_hr": 45.0,
                "supported_fabrics": ["cotton_twill", "denim_heavy", "poly_blend"],
                "operating_cost_per_hr": 20.0,
                "maintenance_duration_hrs": 6.0,
                "required_spare_part": "rapier_gripper",
                "assigned_order_id": None,
            },
            "M3": {
                "id": "M3",
                "name": "Heavy-Duty Projectile Loom #3",
                "status": "RUNNING",
                "capacity_m_per_hr": 35.0,
                "supported_fabrics": ["denim_heavy"],  # Cannot weave cotton_twill!
                "operating_cost_per_hr": 30.0,
                "maintenance_duration_hrs": 10.0,
                "required_spare_part": "torsion_bar",
                "assigned_order_id": "ORD-102",
            },
        },
        "orders": {
            "ORD-101": {
                "id": "ORD-101",
                "client": "Zara Global",
                "fabric_type": "cotton_twill",
                "total_quantity_m": 900.0,
                "completed_quantity_m": 300.0,
                "remaining_quantity_m": 600.0,
                "raw_material_id": "RM-COTTON",
                "raw_material_per_m": 1.0,    # 1 kg of yarn per 1m of fabric
                "deadline_hrs": 14.0,         # Due in 14 hours
                "assigned_machine_id": "M1",
                "status": "IN_PROGRESS",      # IN_PROGRESS, AT_RISK, REASSIGNED, DELAYED, COMPLETED
                "penalty_per_hr_late": 500.0,
            },
            "ORD-102": {
                "id": "ORD-102",
                "client": "Levi Strauss",
                "fabric_type": "denim_heavy",
                "total_quantity_m": 700.0,
                "completed_quantity_m": 350.0,
                "remaining_quantity_m": 350.0,
                "raw_material_id": "RM-INDIGO",
                "raw_material_per_m": 1.2,
                "deadline_hrs": 16.0,
                "assigned_machine_id": "M3",
                "status": "IN_PROGRESS",
                "penalty_per_hr_late": 400.0,
            },
            "ORD-103": {
                "id": "ORD-103",
                "client": "Uniqlo Asia",
                "fabric_type": "poly_blend",
                "total_quantity_m": 500.0,
                "completed_quantity_m": 0.0,
                "remaining_quantity_m": 500.0,
                "raw_material_id": "RM-POLY",
                "raw_material_per_m": 0.8,
                "deadline_hrs": 9.0,          # Tight deadline! (Used to test tight/unsaveable scenarios)
                "assigned_machine_id": None,
                "status": "QUEUED",
                "penalty_per_hr_late": 350.0,
            },
        },
        "raw_materials": {
            # Note: ORD-101 needs 600kg of RM-COTTON, but we only have 400kg in stock!
            # This forces recovery plans to also check raw material procurement.
            "RM-COTTON": {"id": "RM-COTTON", "name": "Combed Cotton Yarn", "stock_kg": 400.0, "reserved_kg": 0.0},
            "RM-INDIGO": {"id": "RM-INDIGO", "name": "Indigo Denim Yarn", "stock_kg": 600.0, "reserved_kg": 420.0},
            "RM-POLY":   {"id": "RM-POLY",   "name": "Polyester Filament", "stock_kg": 500.0, "reserved_kg": 0.0},
        },
        "spare_parts": {
            "bearing_set":    {"id": "bearing_set",    "name": "High-Speed Rotor Bearing", "in_stock": 1, "cost_usd": 180.0},
            "rapier_gripper": {"id": "rapier_gripper", "name": "Carbon Rapier Gripper",    "in_stock": 2, "cost_usd": 120.0},
            "torsion_bar":    {"id": "torsion_bar",    "name": "Projectile Torsion Bar",   "in_stock": 0, "cost_usd": 450.0},
        },
        
"suppliers": {
    "SUP-PRIMARY": {
        "id": "SUP-PRIMARY",
        "name": "Gujarat Spinners",
        "type": "PRIMARY",
        "tier": 1,
        "status": "ACTIVE",
        "reliability_score": 96,
        "delivery_time_hrs": 12.0,
        "cost_per_kg": {
            "RM-COTTON": 3.5,
            "RM-INDIGO": 4.0,
            "RM-POLY": 2.8
        },
        "rush_fee_usd": 50.0,
        "max_supply_kg": 5000
    },

    "SUP-BACKUP": {
        "id": "SUP-BACKUP",
        "name": "Surat Express Mills",
        "type": "BACKUP",
        "tier": 2,
        "status": "ACTIVE",
        "reliability_score": 99,
        "delivery_time_hrs": 3.0,
        "cost_per_kg": {
            "RM-COTTON": 6.0,
            "RM-INDIGO": 7.0,
            "RM-POLY": 5.0
        },
        "rush_fee_usd": 200.0,
        "max_supply_kg": 3000
    },

    "SUP-EMERGENCY": {
        "id": "SUP-EMERGENCY",
        "name": "Mumbai Emergency Textile Supply",
        "type": "EMERGENCY",
        "tier": 3,
        "status": "ACTIVE",
        "reliability_score": 90,
        "delivery_time_hrs": 1.5,
        "cost_per_kg": {
            "RM-COTTON": 9.0,
            "RM-INDIGO": 10.0,
            "RM-POLY": 8.0
        },
        "rush_fee_usd": 400.0,
        "max_supply_kg": 1500
    }
},

        "incidents": [],
    }


def simulate_machine_failure(factory: dict, machine_id: str) -> dict:
    """
    Simulates a breakdown on the specified machine, updates factory state,
    and identifies all affected production orders.

    Args:
        factory (dict): The current factory state dictionary.
        machine_id (str): ID of the machine to fail (e.g., 'M1').

    Returns:
        dict: An incident report dictionary containing the failed machine details,
              affected orders, and updated factory summary.

    Raises:
        ValueError: If machine_id does not exist in factory['machines'].
    """
    if machine_id not in factory["machines"]:
        raise ValueError(f"Machine '{machine_id}' not found in factory. Valid IDs: {list(factory['machines'].keys())}")

    machine = factory["machines"][machine_id]
    machine["status"] = "FAILED"

    # Find all orders assigned to this failed machine
    affected_orders = []
    for order_id, order in factory["orders"].items():
        if order["assigned_machine_id"] == machine_id and order["status"] != "COMPLETED":
            order["status"] = "AT_RISK"
            affected_orders.append(deepcopy(order))

    spare_part_id = machine["required_spare_part"]
    spare_part_info = factory["spare_parts"].get(spare_part_id, {})

    incident = {
        "incident_id": f"INC-{len(factory['incidents']) + 1:03d}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "new_status": machine["status"],
        "estimated_repair_hrs": machine["maintenance_duration_hrs"],
        "required_spare_part": spare_part_id,
        "spare_part_in_stock": spare_part_info.get("in_stock", 0) > 0,
        "affected_order_ids": [o["id"] for o in affected_orders],
        "affected_orders": affected_orders,
    }

    factory["incidents"].append(incident)
    return incident


def simulate_supplier_failure(factory: dict, supplier_id: str) -> dict:
    """
    Simulates a supplier disruption and updates supplier status.
    """

    if supplier_id not in factory["suppliers"]:
        raise ValueError(f"Supplier '{supplier_id}' not found.")

    supplier = factory["suppliers"][supplier_id]

    if supplier["status"] == "FAILED":
        raise ValueError(f"Supplier '{supplier_id}' has already failed.")

    supplier["status"] = "FAILED"

    incident = {
        "incident_id": f"SUP-INC-{len(factory.get('supplier_incidents', [])) + 1:03d}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "incident_type": "SUPPLIER_FAILURE",
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "supplier_tier": supplier["tier"],
        "status": "OPEN"
    }

    if "supplier_incidents" not in factory:
        factory["supplier_incidents"] = []

    factory["supplier_incidents"].append(incident)

    return incident

def get_factory_summary(factory: dict) -> dict:
    """
    Generates a clean, high-level summary of the current factory state
    for AI agents and dashboard rendering.

    Args:
        factory (dict): The current factory state dictionary.

    Returns:
        dict: Summary counts and status lists for machines, orders, and stock.
    """
    machines = factory["machines"]
    orders = factory["orders"]

    return {
        "total_machines": len(machines),
        "machines_by_status": {
            "RUNNING": [m["id"] for m in machines.values() if m["status"] == "RUNNING"],
            "IDLE": [m["id"] for m in machines.values() if m["status"] == "IDLE"],
            "FAILED": [m["id"] for m in machines.values() if m["status"] == "FAILED"],
            "MAINTENANCE": [m["id"] for m in machines.values() if m["status"] == "MAINTENANCE"],
        },
        "orders_by_status": {
            "IN_PROGRESS": [o["id"] for o in orders.values() if o["status"] == "IN_PROGRESS"],
            "QUEUED": [o["id"] for o in orders.values() if o["status"] == "QUEUED"],
            "AT_RISK": [o["id"] for o in orders.values() if o["status"] == "AT_RISK"],
            "REASSIGNED": [o["id"] for o in orders.values() if o["status"] == "REASSIGNED"],
            "DELAYED": [o["id"] for o in orders.values() if o["status"] == "DELAYED"],
        },
        "raw_materials_available_kg": {
            rm_id: rm["stock_kg"] - rm["reserved_kg"]
            for rm_id, rm in factory["raw_materials"].items()
        },
        "spare_parts_available": {
            sp_id: sp["in_stock"]
            for sp_id, sp in factory["spare_parts"].items()
        },
        "active_incidents_count": len(factory["incidents"]),
    }


if __name__ == "__main__":
    print("=== MILESTONE 1 TEST: factory.py ===")
    f = create_factory()
    print("Initial Summary:", get_factory_summary(f))
    print("\nSimulating failure on M1...")
    inc = simulate_machine_failure(f, "M1")
    print("Incident Generated:", inc["incident_id"], "| Affected Orders:", inc["affected_order_ids"])
    print("Updated Summary:", get_factory_summary(f))