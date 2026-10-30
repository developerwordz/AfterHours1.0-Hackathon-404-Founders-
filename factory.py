"""
factory.py — Factory simulation and multi-disruption state management for TexResQ (v2.0).
Owner: Ruhaan (ruhaan/backend)
"""

from copy import deepcopy
from datetime import datetime


def create_factory() -> dict:
    """
    Creates and returns the initial simulated textile factory state.
    Preserves the v1.0 schema completely.
    """
    return {
        "machines": {
            "M1": {
                "id": "M1",
                "name": "High-Speed Air-Jet Loom #1",
                "status": "RUNNING",          # RUNNING, IDLE, FAILED, MAINTENANCE
                "capacity_m_per_hr": 60.0,
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
                "supported_fabrics": ["denim_heavy"],
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
                "raw_material_per_m": 1.0,
                "deadline_hrs": 14.0,
                "assigned_machine_id": "M1",
                "status": "IN_PROGRESS",
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
                "deadline_hrs": 9.0,
                "assigned_machine_id": None,
                "status": "QUEUED",
                "penalty_per_hr_late": 350.0,
            },
        },
        "raw_materials": {
            "RM-COTTON": {"id": "RM-COTTON", "name": "Combed Cotton Yarn", "stock_kg": 400.0, "reserved_kg": 0.0},
            "RM-INDIGO": {"id": "RM-INDIGO", "name": "Indigo Denim Yarn", "stock_kg": 600.0, "reserved_kg": 0.0},
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
                "name": "Gujarat Spinners (Primary)",
                "type": "PRIMARY",
                "delivery_time_hrs": 12.0,
                "cost_per_kg": {"RM-COTTON": 3.5, "RM-INDIGO": 4.0, "RM-POLY": 2.8},
                "rush_fee_usd": 50.0,
            },
            "SUP-BACKUP": {
                "id": "SUP-BACKUP",
                "name": "Surat Express Mills (Backup)",
                "type": "BACKUP",
                "delivery_time_hrs": 3.0,
                "cost_per_kg": {"RM-COTTON": 6.0, "RM-INDIGO": 7.0, "RM-POLY": 5.0},
                "rush_fee_usd": 200.0,
            },
        },
        "incidents": [],
    }


def simulate_machine_failure(factory: dict, machine_id: str) -> dict:
    """Scenario 1: Simulates a breakdown on a single machine (M1, M2, or M3)."""
    if machine_id not in factory["machines"]:
        raise ValueError(f"Machine '{machine_id}' not found. Valid IDs: {list(factory['machines'].keys())}")

    machine = factory["machines"][machine_id]
    machine["status"] = "FAILED"

    affected_orders = []
    for order in factory["orders"].values():
        if order["assigned_machine_id"] == machine_id and order["status"] != "COMPLETED":
            order["status"] = "AT_RISK"
            affected_orders.append(deepcopy(order))

    spare_part_id = machine["required_spare_part"]
    spare_part_info = factory["spare_parts"].get(spare_part_id, {})

    incident = {
        "incident_id": f"INC-{len(factory['incidents']) + 1:03d}",
        "type": "MACHINE_FAILURE",
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


def simulate_machine_maintenance(factory: dict, machine_id: str, duration_hrs: float = None) -> dict:
    """Scenario 5: Places a machine into scheduled/unscheduled temporary maintenance."""
    if machine_id not in factory["machines"]:
        raise ValueError(f"Machine '{machine_id}' not found.")

    machine = factory["machines"][machine_id]
    machine["status"] = "MAINTENANCE"
    if duration_hrs is not None:
        machine["maintenance_duration_hrs"] = float(duration_hrs)

    affected_orders = []
    for order in factory["orders"].values():
        if order["assigned_machine_id"] == machine_id and order["status"] != "COMPLETED":
            order["status"] = "AT_RISK"
            affected_orders.append(deepcopy(order))

    spare_part_id = machine["required_spare_part"]
    spare_part_info = factory["spare_parts"].get(spare_part_id, {})

    incident = {
        "incident_id": f"INC-{len(factory['incidents']) + 1:03d}",
        "type": "MACHINE_MAINTENANCE",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "new_status": "MAINTENANCE",
        "estimated_repair_hrs": machine["maintenance_duration_hrs"],
        "required_spare_part": spare_part_id,
        "spare_part_in_stock": spare_part_info.get("in_stock", 0) > 0,
        "affected_order_ids": [o["id"] for o in affected_orders],
        "affected_orders": affected_orders,
    }
    factory["incidents"].append(incident)
    return incident


def simulate_raw_material_shortage(factory: dict, material_id: str, new_stock_kg: float = 0.0) -> dict:
    """Scenario 2: Reduces raw material stock (e.g. damaged batch or inventory drop) and flags affected orders."""
    if material_id not in factory["raw_materials"]:
        raise ValueError(f"Raw material '{material_id}' not found. Valid IDs: {list(factory['raw_materials'].keys())}")

    rm = factory["raw_materials"][material_id]
    old_stock = rm["stock_kg"]
    rm["stock_kg"] = max(0.0, float(new_stock_kg))
    available = max(0.0, rm["stock_kg"] - rm["reserved_kg"])

    affected_orders = []
    affected_machines = []
    for order in factory["orders"].values():
        if order["raw_material_id"] == material_id and order["status"] != "COMPLETED":
            req_kg = order["remaining_quantity_m"] * order.get("raw_material_per_m", 1.0)
            if req_kg > available:
                order["status"] = "AT_RISK"
                affected_orders.append(deepcopy(order))
                if order["assigned_machine_id"]:
                    affected_machines.append(order["assigned_machine_id"])

    incident = {
        "incident_id": f"INC-{len(factory['incidents']) + 1:03d}",
        "type": "RAW_MATERIAL_SHORTAGE",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "material_id": material_id,
        "previous_stock_kg": old_stock,
        "new_stock_kg": rm["stock_kg"],
        "machine_id": affected_machines[0] if affected_machines else None,
        "affected_machine_ids": affected_machines,
        "affected_order_ids": [o["id"] for o in affected_orders],
        "affected_orders": affected_orders,
    }
    factory["incidents"].append(incident)
    return incident


def simulate_supplier_delay(factory: dict, supplier_id: str, extra_delay_hrs: float) -> dict:
    """Scenario 3: Delays a supplier's delivery time and identifies orders with material shortfalls."""
    if supplier_id not in factory["suppliers"]:
        raise ValueError(f"Supplier '{supplier_id}' not found. Valid IDs: {list(factory['suppliers'].keys())}")

    supplier = factory["suppliers"][supplier_id]
    old_eta = supplier["delivery_time_hrs"]
    supplier["delivery_time_hrs"] = round(old_eta + float(extra_delay_hrs), 2)

    affected_orders = []
    for order in factory["orders"].values():
        if order["status"] != "COMPLETED":
            rm = factory["raw_materials"][order["raw_material_id"]]
            avail_kg = max(0.0, rm["stock_kg"] - rm["reserved_kg"])
            req_kg = order["remaining_quantity_m"] * order.get("raw_material_per_m", 1.0)
            if req_kg > avail_kg:
                order["status"] = "AT_RISK"
                affected_orders.append(deepcopy(order))

    incident = {
        "incident_id": f"INC-{len(factory['incidents']) + 1:03d}",
        "type": "SUPPLIER_DELAY",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "previous_delivery_hrs": old_eta,
        "new_delivery_hrs": supplier["delivery_time_hrs"],
        "machine_id": affected_orders[0]["assigned_machine_id"] if affected_orders else None,
        "affected_order_ids": [o["id"] for o in affected_orders],
        "affected_orders": affected_orders,
    }
    factory["incidents"].append(incident)
    return incident


def simulate_multiple_failures(factory: dict, machine_ids: list) -> list:
    """Scenario 4: Fails multiple machines simultaneously and returns the list of generated incidents."""
    if not machine_ids:
        raise ValueError("machine_ids list cannot be empty.")
    incidents = []
    for m_id in machine_ids:
        incidents.append(simulate_machine_failure(factory, m_id))
    return incidents


def get_factory_summary(factory: dict) -> dict:
    """Generates a high-level summary of the current factory state."""
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