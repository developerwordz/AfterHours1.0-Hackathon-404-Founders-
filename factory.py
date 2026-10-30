
"""
factory.py — Factory simulation and state management for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""

from copy import deepcopy
from datetime import datetime
import random


# ============================================================
# QUALITY SIMULATION CONFIGURATION
# ============================================================

# How much machine wear increases after producing one batch.
WEAR_PER_BATCH = 8.0

# Maximum wear level.
MAX_WEAR = 100.0

# How strongly wear affects quality measurements.
WEAR_IMPACT = {
    "gsm_consistency": 0.30,
    "dimensional_accuracy": 0.35,
    "color_consistency": 0.20,
    "tensile_strength": 0.25,
    "defect_density": 0.40,
}


# ============================================================
# FACTORY INITIALIZATION
# ============================================================

def create_factory() -> dict:
    """
    Creates and returns the initial simulated textile factory state.
    """

    return {
        "machines": {
            "M1": {
                "id": "M1",
                "name": "High-Speed Air-Jet Loom #1",
                "status": "RUNNING",
                "capacity_m_per_hr": 60.0,
                "supported_fabrics": ["cotton_twill", "poly_blend"],
                "operating_cost_per_hr": 25.0,
                "maintenance_duration_hrs": 8.0,
                "required_spare_part": "bearing_set",
                "assigned_order_id": "ORD-101",

                # Quality condition tracking
                "condition_score": 100.0,
                "wear_level": 0.0,
                "batches_produced": 0,
            },

            "M2": {
                "id": "M2",
                "name": "Versatile Rapier Loom #2",
                "status": "IDLE",
                "capacity_m_per_hr": 45.0,
                "supported_fabrics": [
                    "cotton_twill",
                    "denim_heavy",
                    "poly_blend"
                ],
                "operating_cost_per_hr": 20.0,
                "maintenance_duration_hrs": 6.0,
                "required_spare_part": "rapier_gripper",
                "assigned_order_id": None,

                "condition_score": 100.0,
                "wear_level": 0.0,
                "batches_produced": 0,
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

                "condition_score": 100.0,
                "wear_level": 0.0,
                "batches_produced": 0,
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
            "RM-COTTON": {
                "id": "RM-COTTON",
                "name": "Combed Cotton Yarn",
                "stock_kg": 400.0,
                "reserved_kg": 0.0
            },

            "RM-INDIGO": {
                "id": "RM-INDIGO",
                "name": "Indigo Denim Yarn",
                "stock_kg": 600.0,
                "reserved_kg": 420.0
            },

            "RM-POLY": {
                "id": "RM-POLY",
                "name": "Polyester Filament",
                "stock_kg": 500.0,
                "reserved_kg": 0.0
            },
        },

        "spare_parts": {
            "bearing_set": {
                "id": "bearing_set",
                "name": "High-Speed Rotor Bearing",
                "in_stock": 1,
                "cost_usd": 180.0
            },

            "rapier_gripper": {
                "id": "rapier_gripper",
                "name": "Carbon Rapier Gripper",
                "in_stock": 2,
                "cost_usd": 120.0
            },

            "torsion_bar": {
                "id": "torsion_bar",
                "name": "Projectile Torsion Bar",
                "in_stock": 0,
                "cost_usd": 450.0
            },
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
            },
        },

        # Incident management
        "incidents": [],
        "supplier_incidents": [],

        # Centralized quality management
        "batches": [],
        "quality_history": [],
        "next_batch_number": 1,

        # Quality intervention audit trail
        "quality_interventions": [],
    }


# ============================================================
# MACHINE FAILURE
# ============================================================

def simulate_machine_failure(factory: dict, machine_id: str) -> dict:
    """
    Simulates a machine breakdown and identifies affected orders.
    """

    if machine_id not in factory["machines"]:
        raise ValueError(
            f"Machine '{machine_id}' not found. "
            f"Valid IDs: {list(factory['machines'].keys())}"
        )

    machine = factory["machines"][machine_id]
    machine["status"] = "FAILED"

    affected_orders = []

    for order_id, order in factory["orders"].items():

        if (
            order["assigned_machine_id"] == machine_id
            and order["status"] != "COMPLETED"
        ):
            order["status"] = "AT_RISK"
            affected_orders.append(deepcopy(order))

    spare_part_id = machine["required_spare_part"]

    spare_part_info = factory["spare_parts"].get(
        spare_part_id, {}
    )

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


# ============================================================
# SUPPLIER FAILURE
# ============================================================

def simulate_supplier_failure(factory: dict, supplier_id: str) -> dict:
    """
    Simulates a supplier disruption and updates supplier status.
    """

    if supplier_id not in factory["suppliers"]:
        raise ValueError(f"Supplier '{supplier_id}' not found.")

    supplier = factory["suppliers"][supplier_id]

    if supplier["status"] == "FAILED":
        raise ValueError(
            f"Supplier '{supplier_id}' has already failed."
        )

    supplier["status"] = "FAILED"

    incident = {
        "incident_id": (
            f"SUP-INC-{len(factory['supplier_incidents']) + 1:03d}"
        ),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "incident_type": "SUPPLIER_FAILURE",
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "supplier_tier": supplier["tier"],
        "status": "OPEN"
    }

    factory["supplier_incidents"].append(incident)

    return incident


# ============================================================
# FACTORY SUMMARY
# ============================================================

def get_factory_summary(factory: dict) -> dict:
    """
    Generates a high-level summary of the current factory state.
    """

    machines = factory["machines"]
    orders = factory["orders"]

    return {
        "total_machines": len(machines),

        "machines_by_status": {
            status: [
                m["id"] for m in machines.values()
                if m["status"] == status
            ]
            for status in [
                "RUNNING",
                "IDLE",
                "FAILED",
                "MAINTENANCE"
            ]
        },

        "orders_by_status": {
            status: [
                o["id"] for o in orders.values()
                if o["status"] == status
            ]
            for status in [
                "IN_PROGRESS",
                "QUEUED",
                "AT_RISK",
                "REASSIGNED",
                "DELAYED",
                "COMPLETED"
            ]
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
        "total_batches": len(factory["batches"]),
    }


# ============================================================
# QUALITY METRIC GENERATION
# ============================================================

def generate_quality_metrics(wear_level: float) -> dict:
    """
    Generates synthetic quality measurements.

    As machine wear increases, quality measurements decline.

    All measurements are normalized to 0-100, where higher
    values indicate better quality.

    NOTE: These are simulated values, not real sensor readings.
    """

    metrics = {}

    baseline_ranges = {
        "gsm_consistency": (94, 100),
        "dimensional_accuracy": (93, 100),
        "color_consistency": (94, 100),
        "tensile_strength": (93, 100),
        "defect_density": (94, 100),
    }

    for metric, (minimum, maximum) in baseline_ranges.items():

        # Generate baseline measurement
        baseline = random.uniform(minimum, maximum)

        # Calculate degradation based on machine wear
        degradation = wear_level * WEAR_IMPACT[metric]

        # Add small natural production variation
        variation = random.uniform(-1.5, 1.5)

        # Final measurement
        value = baseline - degradation + variation

        # Keep score within valid 0-100 range
        metrics[metric] = round(
            max(0.0, min(100.0, value)), 2
        )

    return metrics


# ============================================================
# BATCH PRODUCTION
# ============================================================

def simulate_batch_production(factory: dict, machine_id: str) -> dict:
    """
    Simulates one production batch and generates synthetic
    quality inspection measurements.

    Each batch increases machine wear, causing subsequent
    batches to gradually experience quality deterioration.
    """

    from quality.quality_scorer import calculate_quality_score

    # --------------------------------------------------------
    # 1. Find machine
    # --------------------------------------------------------

    machine = factory["machines"].get(machine_id)

    if machine is None:
        raise ValueError(
            f"Machine '{machine_id}' not found."
        )

    if machine["status"] != "RUNNING":
        raise ValueError(
            f"Machine '{machine_id}' is not running. "
            "Cannot produce a batch."
        )

    # --------------------------------------------------------
    # 2. Find assigned order
    # --------------------------------------------------------

    order_id = machine.get("assigned_order_id")
    order = factory["orders"].get(order_id)

    if order is None:
        raise ValueError(
            f"No valid order assigned to machine '{machine_id}'."
        )

    if order["status"] not in ("IN_PROGRESS", "REASSIGNED"):
        raise ValueError(
            f"Order '{order_id}' is not currently in production."
        )

    # --------------------------------------------------------
    # 3. Check fabric compatibility
    # --------------------------------------------------------

    fabric_type = order["fabric_type"]

    if fabric_type not in machine["supported_fabrics"]:
        raise ValueError(
            f"Machine '{machine_id}' does not support "
            f"fabric type '{fabric_type}'."
        )

    # --------------------------------------------------------
    # 4. Check remaining quantity
    # --------------------------------------------------------

    if order["remaining_quantity_m"] <= 0:
        raise ValueError(
            f"Order '{order_id}' has no remaining quantity."
        )

    # --------------------------------------------------------
    # 5. Read current machine condition
    # --------------------------------------------------------

    wear_before = machine["wear_level"]
    condition_before = machine["condition_score"]

    # --------------------------------------------------------
    # 6. Generate batch ID
    # --------------------------------------------------------

    batch_number = factory["next_batch_number"]
    batch_id = f"BAT-{batch_number:03d}"

    # --------------------------------------------------------
    # 7. Generate quality metrics
    # --------------------------------------------------------

    metrics = generate_quality_metrics(wear_before)

    # --------------------------------------------------------
    # 8. Calculate quality score
    # --------------------------------------------------------

    report = calculate_quality_score(
        batch_id=batch_id,
        machine_id=machine_id,
        fabric_type=fabric_type,
        metrics=metrics
    )

    # --------------------------------------------------------
    # 9. Update machine wear AFTER producing the batch
    # --------------------------------------------------------

    machine["wear_level"] = min(
        MAX_WEAR,
        wear_before + WEAR_PER_BATCH
    )

    machine["condition_score"] = round(
        100.0 - machine["wear_level"], 2
    )

    machine["batches_produced"] += 1

    # --------------------------------------------------------
    # 10. Add production and condition information
    # --------------------------------------------------------

    report.update({
        "order_id": order_id,
        "machine_name": machine["name"],
        "data_source": "SIMULATED",

        "machine_wear_before": round(wear_before, 2),
        "machine_wear_after": round(machine["wear_level"], 2),

        "machine_condition_before": round(condition_before, 2),
        "machine_condition_after": machine["condition_score"],

        "machine_batch_number": machine["batches_produced"],
    })

    # --------------------------------------------------------
    # 11. Store batch in central history
    # --------------------------------------------------------

    factory["next_batch_number"] += 1

    factory["batches"].append(report)
    factory["quality_history"].append(report)

    return report


# ============================================================
# QUALITY CORRECTIVE ACTION — MAINTENANCE
# ============================================================

def apply_machine_quality_maintenance(
    factory: dict,
    machine_id: str,
    reason: str = "Preventive quality maintenance"
) -> dict:
    """
    Simulates quality-related machine maintenance.

    Restores machine condition and reduces accumulated wear.

    This function can later be called by the quality agent
    when it decides maintenance is the appropriate action.
    """

    if machine_id not in factory["machines"]:
        raise ValueError(
            f"Machine '{machine_id}' not found."
        )

    machine = factory["machines"][machine_id]

    if machine["status"] == "FAILED":
        raise ValueError(
            "Cannot perform quality maintenance on a FAILED machine."
        )

    previous_wear = machine["wear_level"]
    previous_condition = machine["condition_score"]

    machine["wear_level"] = 0.0
    machine["condition_score"] = 100.0

    intervention = {
        "intervention_id": (
            f"QINT-{len(factory['quality_interventions']) + 1:03d}"
        ),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "machine_id": machine_id,
        "machine_name": machine["name"],
        "action": "QUALITY_MAINTENANCE",
        "reason": reason,
        "previous_wear": previous_wear,
        "new_wear": machine["wear_level"],
        "previous_condition": previous_condition,
        "new_condition": machine["condition_score"],
    }

    factory["quality_interventions"].append(intervention)

    return intervention


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    print("=== TEXRESQ FACTORY QUALITY SIMULATION ===")

    factory = create_factory()

    print("\nInitial Factory Summary:")
    print(get_factory_summary(factory))

    # Generate several batches on M1 to demonstrate deterioration.
    print("\n=== MACHINE M1: QUALITY DETERIORATION ===")

    for i in range(8):

        report = simulate_batch_production(factory, "M1")

        print(f"\nBatch: {report['batch_id']}")
        print(f"Quality Score: {report['quality_score']}")
        print(f"Grade: {report['grade']}")
        print(f"Status: {report['inspection_status']}")
        print(f"Wear Before: {report['machine_wear_before']}%")
        print(f"Wear After: {report['machine_wear_after']}%")
        print(f"Condition: {report['machine_condition_after']}%")

    # Generate a batch on M3 as well.
    print("\n=== MACHINE M3: QUALITY REPORT ===")

    report = simulate_batch_production(factory, "M3")

    print("Batch:", report["batch_id"])
    print("Machine:", report["machine_name"])
    print("Fabric:", report["fabric_type"])
    print("Quality Score:", report["quality_score"])
    print("Grade:", report["grade"])
    print("Status:", report["inspection_status"])

    print("\nTotal Batches:", len(factory["batches"]))

    # Demonstrate maintenance recovery.
    print("\n=== QUALITY MAINTENANCE TEST ===")

    intervention = apply_machine_quality_maintenance(
        factory,
        "M1",
        reason="Quality deterioration detected"
    )

    print("Intervention:", intervention["intervention_id"])
    print("Previous Wear:", intervention["previous_wear"])
    print("New Wear:", intervention["new_wear"])
    print("Restored Condition:", intervention["new_condition"])

    print("\n=== FACTORY SIMULATION COMPLETE ===")
