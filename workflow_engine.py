
"""
workflow_engine.py
TEXRESQ end-to-end factory workflow.

Inventory -> Supply Chain -> Production -> Quality
-> Finished Goods -> Dispatch -> New Customer Orders

Includes:
- Automatic customer order generation
- Inventory forecasting and procurement
- Production scheduling
- Quality inspection
- Preventive machine maintenance
- Finished goods management
- Automatic dispatch

All operations are simulated.
"""

import random
from datetime import datetime

from factory import (
    generate_quality_metrics,
    apply_machine_quality_maintenance,
    WEAR_PER_BATCH,
    MAX_WEAR,
)

from inventory_agent import (
    initialize_inventory_networks,
    run_inventory_agent,
)

from supply_chain_agent import advance_simulation


# ============================================================
# CONFIGURATION
# ============================================================

QUALITY_ACCEPTANCE_THRESHOLD = 88.0

MAINTENANCE_WEAR_THRESHOLD = min(
    MAX_WEAR,
    WEAR_PER_BATCH * 3,
)

# Generate one new customer order every 4 simulated hours.
CUSTOMER_ORDER_INTERVAL_HOURS = 4

CUSTOMER_ORDER_CATALOG = {
    "cotton_twill": {
        "raw_material_id": "RM-COTTON",
        "raw_material_per_m": 1.0,
        "penalty_per_hr_late": 500.0,
    },
    "denim_heavy": {
        "raw_material_id": "RM-INDIGO",
        "raw_material_per_m": 1.2,
        "penalty_per_hr_late": 400.0,
    },
    "poly_blend": {
        "raw_material_id": "RM-POLY",
        "raw_material_per_m": 0.8,
        "penalty_per_hr_late": 350.0,
    },
}

CUSTOMER_NAMES = [
    "Zara Global",
    "Levi Strauss",
    "Uniqlo Asia",
    "H&M Textiles",
    "Urban Threads",
    "Fashion Forward",
    "Global Apparel Co.",
]


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_factory_workflow(factory):
    """Initialize workflow state without resetting existing progress."""

    initialize_inventory_networks(factory)

    factory.setdefault("finished_goods", {})
    factory.setdefault("dispatch_history", [])
    factory.setdefault("workflow_events", [])
    factory.setdefault("workflow_cycle_count", 0)
    factory.setdefault("batches", [])
    factory.setdefault("quality_history", [])
    factory.setdefault("quality_interventions", [])
    factory.setdefault("next_batch_number", 1)

    # Persistent timer for automatic customer orders.
    factory.setdefault("customer_order_elapsed_hours", 0.0)

    return factory


def _simulation_time(factory):
    clock = factory.get("supply_simulation", {}).get("clock")

    if clock:
        return clock

    return datetime.now().isoformat(timespec="minutes")


def _record(factory, event_type, message, details=None):
    event = {
        "timestamp": _simulation_time(factory),
        "event_type": event_type,
        "message": message,
        "details": details or {},
    }

    factory.setdefault("workflow_events", []).append(event)

    return event


# ============================================================
# AUTOMATIC CUSTOMER ORDER GENERATION
# ============================================================

def generate_automatic_customer_orders(factory, hours):
    """
    Generate a new customer order every 4 simulated hours.

    Orders are added to factory['orders'] with QUEUED status.

    The elapsed timer is stored in factory state, so Streamlit
    reruns do not generate duplicate orders.
    """

    factory["customer_order_elapsed_hours"] = (
        float(factory.get("customer_order_elapsed_hours", 0))
        + float(hours)
    )

    generated_orders = []

    while (
        factory["customer_order_elapsed_hours"]
        >= CUSTOMER_ORDER_INTERVAL_HOURS
    ):

        factory["customer_order_elapsed_hours"] -= (
            CUSTOMER_ORDER_INTERVAL_HOURS
        )

        # Find the next unique order number.
        existing_numbers = []

        for order_id in factory.get("orders", {}):

            try:
                number = int(str(order_id).split("-")[-1])
                existing_numbers.append(number)

            except (ValueError, IndexError):
                continue

        next_number = max(existing_numbers, default=100) + 1

        order_id = f"ORD-{next_number:03d}"

        # Select fabric type.
        fabric_type = random.choice(
            list(CUSTOMER_ORDER_CATALOG.keys())
        )

        fabric_info = CUSTOMER_ORDER_CATALOG[fabric_type]

        # Generate customer order quantity.
        quantity = random.choice([
            300.0,
            400.0,
            500.0,
            600.0,
            700.0,
        ])

        # Generate deadline.
        deadline = random.choice([
            24.0,
            30.0,
            36.0,
            48.0,
        ])

        order = {
            "id": order_id,

            "client": random.choice(CUSTOMER_NAMES),

            "fabric_type": fabric_type,

            "total_quantity_m": quantity,
            "completed_quantity_m": 0.0,
            "remaining_quantity_m": quantity,
            "rejected_quantity_m": 0.0,

            "raw_material_id": fabric_info["raw_material_id"],
            "raw_material_per_m": fabric_info["raw_material_per_m"],

            "deadline_hrs": deadline,

            "assigned_machine_id": None,

            "status": "QUEUED",
            "dispatch_status": "PENDING",

            "penalty_per_hr_late": fabric_info[
                "penalty_per_hr_late"
            ],
        }

        factory.setdefault("orders", {})[order_id] = order

        generated_orders.append(order)

        _record(
            factory,
            "NEW_CUSTOMER_ORDER",
            (
                f"New customer order {order_id} received: "
                f"{quantity:.0f} m of {fabric_type}."
            ),
            order,
        )

    return generated_orders


# ============================================================
# PROCUREMENT SYNCHRONIZATION
# ============================================================

def _sync_procurement_records(factory):

    shipments = {
        item["shipment_id"]: item
        for item in factory.get("shipments", [])
        if item.get("shipment_id")
    }

    for record in factory.get("inventory_procurement_log", []):

        shipment = shipments.get(record.get("shipment_id"))

        if not shipment:
            continue

        status = shipment.get("status", "SCHEDULED")

        if status == "DELIVERED":
            record["status"] = "DELIVERED"

        elif status in ("CANCELLED", "DECLINED"):
            record["status"] = status

        elif status == "DELAYED":
            record["status"] = "DELAYED"

        else:
            record["status"] = status

        record["eta"] = shipment.get(
            "eta",
            record.get("eta"),
        )


# ============================================================
# PRODUCTION SCHEDULING
# ============================================================

def assign_queued_orders(factory):
    """
    Assign queued orders to compatible idle machines.

    Queued orders can only use unreserved stock.
    Existing running orders can consume their reserved stock.
    """

    assigned = []

    machines = factory.get("machines", {})
    orders = factory.get("orders", {})
    materials = factory.get("raw_materials", {})

    idle_machines = [
        (machine_id, machine)
        for machine_id, machine in machines.items()
        if machine.get("status") == "IDLE"
        and not machine.get("assigned_order_id")
    ]

    queued_orders = [
        (order_id, order)
        for order_id, order in orders.items()
        if order.get("status") == "QUEUED"
        and float(order.get("remaining_quantity_m", 0)) > 0
    ]

    queued_orders.sort(
        key=lambda item: float(
            item[1].get("deadline_hrs", 999999)
        )
    )

    for order_id, order in queued_orders:

        material_id = order.get("raw_material_id")
        material = materials.get(material_id)

        if not material:
            continue

        stock = float(material.get("stock_kg", 0))
        reserved = float(material.get("reserved_kg", 0))

        available_stock = max(0.0, stock - reserved)

        rate = float(order.get("raw_material_per_m", 1))

        if rate <= 0:
            continue

        compatible = [
            (machine_id, machine)
            for machine_id, machine in idle_machines
            if order.get("fabric_type")
            in machine.get("supported_fabrics", [])
        ]

        if not compatible:
            continue

        machine_id, machine = compatible[0]

        capacity = float(
            machine.get("capacity_m_per_hr", 0)
        )

        if capacity <= 0:
            continue

        first_batch_quantity = min(
            float(order.get("remaining_quantity_m", 0)),
            capacity,
        )

        required_stock = first_batch_quantity * rate

        if available_stock < required_stock:
            continue

        machine["assigned_order_id"] = order_id
        machine["status"] = "RUNNING"

        order["assigned_machine_id"] = machine_id
        order["status"] = "IN_PROGRESS"

        idle_machines.remove((machine_id, machine))

        assignment = {
            "order_id": order_id,
            "machine_id": machine_id,
        }

        assigned.append(assignment)

        _record(
            factory,
            "ORDER_ASSIGNED",
            f"{order_id} assigned to {machine_id}.",
            assignment,
        )

    return assigned


# ============================================================
# PREVENTIVE QUALITY MAINTENANCE
# ============================================================

def perform_preventive_maintenance(factory, machine_id):
    """
    Reset machine wear before it causes persistent quality rejection.
    """

    machine = factory["machines"].get(machine_id)

    if not machine:
        return None

    if machine.get("status") == "FAILED":
        return None

    wear = float(machine.get("wear_level", 0))

    if wear < MAINTENANCE_WEAR_THRESHOLD:
        return None

    intervention = apply_machine_quality_maintenance(
        factory,
        machine_id,
        reason=(
            "Automatic preventive maintenance: "
            "machine wear reached the quality protection threshold."
        ),
    )

    _record(
        factory,
        "PREVENTIVE_MAINTENANCE",
        f"{machine_id} received preventive quality maintenance.",
        intervention,
    )

    return intervention


# ============================================================
# BATCH PRODUCTION
# ============================================================

def produce_machine_batch(factory, machine_id, hours=1.0):
    """
    Produce one batch on a running machine.

    Material is consumed.
    Quality is inspected.
    Accepted fabric advances the order.
    Rejected fabric is recorded.
    """

    machine = factory["machines"].get(machine_id)

    if not machine:
        return {
            "success": False,
            "reason": "Machine not found.",
        }

    if machine.get("status") != "RUNNING":
        return {
            "success": False,
            "reason": "Machine is not running.",
        }

    order_id = machine.get("assigned_order_id")
    order = factory["orders"].get(order_id)

    if not order:
        return {
            "success": False,
            "reason": "No assigned production order.",
        }

    if order.get("status") not in ("IN_PROGRESS", "REASSIGNED"):
        return {
            "success": False,
            "reason": "Order is not ready for production.",
        }

    remaining = float(
        order.get("remaining_quantity_m", 0)
    )

    if remaining <= 0:
        return {
            "success": False,
            "reason": "Order has no remaining quantity.",
        }

    material_id = order.get("raw_material_id")
    material = factory["raw_materials"].get(material_id)

    if not material:
        return {
            "success": False,
            "reason": f"Material {material_id} not found.",
        }

    rate = float(order.get("raw_material_per_m", 1))

    if rate <= 0:
        return {
            "success": False,
            "reason": "Invalid material consumption rate.",
        }

    capacity = float(
        machine.get("capacity_m_per_hr", 0)
    )

    if capacity <= 0:
        return {
            "success": False,
            "reason": "Invalid machine capacity.",
        }

    physical_stock = float(
        material.get("stock_kg", 0)
    )

    requested_quantity = min(
        remaining,
        capacity * float(hours),
    )

    possible_quantity = physical_stock / rate

    produced_quantity = min(
        requested_quantity,
        possible_quantity,
    )

    if produced_quantity <= 0:
        return {
            "success": False,
            "reason": (
                f"Insufficient physical stock of {material_id}. "
                "Waiting for replenishment."
            ),
        }

    material_used = round(
        produced_quantity * rate,
        2,
    )

    # --------------------------------------------------------
    # MATERIAL CONSUMPTION
    # --------------------------------------------------------

    material["stock_kg"] = round(
        max(0, physical_stock - material_used),
        2,
    )

    reserved = float(
        material.get("reserved_kg", 0)
    )

    material["reserved_kg"] = round(
        max(0, reserved - material_used),
        2,
    )

    # --------------------------------------------------------
    # QUALITY INSPECTION
    # --------------------------------------------------------

    wear_before = float(
        machine.get("wear_level", 0)
    )

    metrics = generate_quality_metrics(wear_before)

    quality_score = round(
        sum(float(value) for value in metrics.values())
        / max(1, len(metrics)),
        2,
    )

    accepted = (
        quality_score >= QUALITY_ACCEPTANCE_THRESHOLD
    )

    inspection_status = (
        "ACCEPTED" if accepted else "REJECTED"
    )

    # --------------------------------------------------------
    # BATCH RECORD
    # --------------------------------------------------------

    batch_number = int(
        factory.get("next_batch_number", 1)
    )

    batch_id = f"BAT-{batch_number:03d}"

    batch = {
        "batch_id": batch_id,
        "order_id": order_id,
        "machine_id": machine_id,
        "machine_name": machine.get("name", machine_id),
        "fabric_type": order.get("fabric_type"),
        "produced_quantity_m": round(produced_quantity, 2),
        "material_id": material_id,
        "material_consumed_kg": material_used,
        "quality_metrics": metrics,
        "quality_score": quality_score,
        "grade": (
            "A" if quality_score >= 95
            else "B" if quality_score >= 90
            else "C" if accepted
            else "REJECT"
        ),
        "inspection_status": inspection_status,
        "workflow_inspection_status": inspection_status,
        "machine_wear_before": wear_before,
        "timestamp": _simulation_time(factory),
        "data_source": "SIMULATED",
    }

    factory["next_batch_number"] = batch_number + 1

    factory.setdefault("batches", []).append(batch)
    factory.setdefault("quality_history", []).append(batch)

    # --------------------------------------------------------
    # MACHINE WEAR
    # --------------------------------------------------------

    wear_after = min(
        MAX_WEAR,
        wear_before + WEAR_PER_BATCH,
    )

    machine["wear_level"] = wear_after

    machine["condition_score"] = round(
        100 - wear_after,
        2,
    )

    machine["batches_produced"] = (
        int(machine.get("batches_produced", 0)) + 1
    )

    batch["machine_wear_after"] = wear_after

    batch["machine_condition_after"] = (
        machine["condition_score"]
    )

    batch["machine_batch_number"] = (
        machine["batches_produced"]
    )

    # --------------------------------------------------------
    # ACCEPTED / REJECTED PRODUCTION
    # --------------------------------------------------------

    if accepted:

        order["completed_quantity_m"] = round(
            float(order.get("completed_quantity_m", 0))
            + produced_quantity,
            2,
        )

        order["remaining_quantity_m"] = round(
            max(0, remaining - produced_quantity),
            2,
        )

        finished = factory["finished_goods"].setdefault(
            order_id,
            {
                "order_id": order_id,
                "fabric_type": order.get("fabric_type"),
                "client": order.get("client"),
                "quantity_m": 0.0,
                "status": "ACCUMULATING",
            },
        )

        finished["quantity_m"] = round(
            float(finished.get("quantity_m", 0))
            + produced_quantity,
            2,
        )

    else:

        order["rejected_quantity_m"] = round(
            float(order.get("rejected_quantity_m", 0))
            + produced_quantity,
            2,
        )

    # --------------------------------------------------------
    # ORDER COMPLETION
    # --------------------------------------------------------

    completed = (
        float(order.get("remaining_quantity_m", 0)) <= 0.001
    )

    if completed:

        order["remaining_quantity_m"] = 0.0
        order["status"] = "COMPLETED"
        order["dispatch_status"] = "READY"
        order["assigned_machine_id"] = None

        finished = factory["finished_goods"].get(order_id)

        if finished:
            finished["status"] = "READY_FOR_DISPATCH"

        machine["assigned_order_id"] = None
        machine["status"] = "IDLE"

        _record(
            factory,
            "ORDER_COMPLETED",
            f"{order_id} completed production.",
            {
                "order_id": order_id,
                "completed_quantity_m": order.get(
                    "completed_quantity_m"
                ),
            },
        )

    # --------------------------------------------------------
    # PREVENTIVE MAINTENANCE
    # --------------------------------------------------------

    maintenance = None

    if not completed:
        maintenance = perform_preventive_maintenance(
            factory,
            machine_id,
        )

    # --------------------------------------------------------
    # EVENT AND RESULT
    # --------------------------------------------------------

    _record(
        factory,
        "BATCH_PRODUCED",
        (
            f"{batch_id}: {produced_quantity:.1f} m "
            f"{inspection_status.lower()} on {machine_id}."
        ),
        {
            "batch_id": batch_id,
            "order_id": order_id,
            "machine_id": machine_id,
            "quality_score": quality_score,
            "material_consumed_kg": material_used,
            "accepted": accepted,
        },
    )

    return {
        "success": True,
        "batch": batch,
        "produced_quantity_m": round(produced_quantity, 2),
        "material_consumed_kg": material_used,
        "accepted": accepted,
        "quality_score": quality_score,
        "order_remaining_m": order.get(
            "remaining_quantity_m"
        ),
        "order_completed": completed,
        "maintenance_performed": maintenance is not None,
        "maintenance": maintenance,
    }


# ============================================================
# DISPATCH
# ============================================================

def dispatch_completed_orders(factory):
    """Dispatch finished goods belonging to completed orders."""

    dispatched = []

    for order_id, order in factory.get("orders", {}).items():

        if order.get("status") != "COMPLETED":
            continue

        if order.get("dispatch_status") == "DISPATCHED":
            continue

        finished = factory.get(
            "finished_goods", {}
        ).get(order_id)

        if not finished:
            continue

        quantity = float(
            finished.get("quantity_m", 0)
        )

        if quantity <= 0:
            continue

        dispatch_id = (
            f"DSP-{len(factory.get('dispatch_history', [])) + 1:04d}"
        )

        record = {
            "dispatch_id": dispatch_id,
            "order_id": order_id,
            "client": order.get("client"),
            "fabric_type": order.get("fabric_type"),
            "quantity_m": round(quantity, 2),
            "timestamp": _simulation_time(factory),
            "status": "DISPATCHED",
        }

        factory["dispatch_history"].append(record)

        finished["quantity_m"] = 0.0
        finished["status"] = "DISPATCHED"

        order["dispatch_status"] = "DISPATCHED"

        dispatched.append(record)

        _record(
            factory,
            "ORDER_DISPATCHED",
            (
                f"{order_id}: {quantity:.1f} m "
                f"dispatched to {order.get('client')}."
            ),
            record,
        )

    return dispatched


# ============================================================
# COMPLETE FACTORY CYCLE
# ============================================================

def run_factory_cycle(factory, hours=1.0, auto_procure=True):
    """
    One factory cycle:

    1. Forecast and procure existing shortages.
    2. Advance simulated time and shipments.
    3. Generate new customer orders when due.
    4. Forecast inventory for new orders.
    5. Assign queued orders.
    6. Produce one batch per running machine.
    7. Dispatch completed orders.
    8. Update inventory after production.
    9. Assign newly available work.
    """

    hours = float(hours)

    if hours <= 0:
        raise ValueError("Cycle hours must be greater than zero.")

    initialize_factory_workflow(factory)

    factory["workflow_cycle_count"] += 1

    # 1. Procurement before production.
    inventory_before = run_inventory_agent(
        factory,
        auto_procure=auto_procure,
    )

    # 2. Advance simulated time and shipments.
    disruption = advance_simulation(
        factory,
        hours=hours,
    )

    _sync_procurement_records(factory)

    # 3. Generate automatic customer orders.
    new_customer_orders = generate_automatic_customer_orders(
        factory,
        hours,
    )

    # 4. Forecast after deliveries and new orders.
    # New orders are now included in material demand.
    inventory_after_delivery = run_inventory_agent(
        factory,
        auto_procure=auto_procure,
    )

    # 5. Assign queued orders.
    assignments = assign_queued_orders(factory)

    # 6. Produce on every running machine.
    production_results = []

    for machine_id, machine in list(
        factory.get("machines", {}).items()
    ):

        if (
            machine.get("status") == "RUNNING"
            and machine.get("assigned_order_id")
        ):

            result = produce_machine_batch(
                factory,
                machine_id,
                hours=hours,
            )

            production_results.append({
                "machine_id": machine_id,
                **result,
            })

    # 7. Dispatch completed orders.
    dispatched = dispatch_completed_orders(factory)

    # 8. Update inventory after consumption.
    inventory_after_production = run_inventory_agent(
        factory,
        auto_procure=auto_procure,
    )

    # 9. Assign work for the next cycle.
    next_assignments = assign_queued_orders(factory)

    return {
        "cycle": factory["workflow_cycle_count"],
        "hours_advanced": hours,

        "disruption": disruption,

        "inventory_before": inventory_before,
        "inventory_after_delivery": inventory_after_delivery,
        "inventory_after_production": inventory_after_production,

        "new_customer_orders": new_customer_orders,

        "assignments": assignments,
        "next_assignments": next_assignments,

        "production_results": production_results,

        "dispatched": dispatched,

        "shipments": factory.get("shipments", []),
    }


# ============================================================
# WORKFLOW SUMMARY
# ============================================================

def get_workflow_summary(factory):

    initialize_factory_workflow(factory)

    orders = factory.get("orders", {})
    machines = factory.get("machines", {})
    shipments = factory.get("shipments", [])
    finished = factory.get("finished_goods", {})

    return {
        "active_orders": sum(
            1 for order in orders.values()
            if order.get("status") != "COMPLETED"
        ),

        "completed_orders": sum(
            1 for order in orders.values()
            if order.get("status") == "COMPLETED"
        ),

        "running_machines": sum(
            1 for machine in machines.values()
            if machine.get("status") == "RUNNING"
        ),

        "failed_machines": sum(
            1 for machine in machines.values()
            if machine.get("status") == "FAILED"
        ),

        "incoming_shipments": sum(
            1 for shipment in shipments
            if shipment.get("status") in (
                "SCHEDULED",
                "IN TRANSIT",
                "REROUTED",
                "DELAYED",
            )
        ),

        "finished_goods_m": round(
            sum(
                float(item.get("quantity_m", 0))
                for item in finished.values()
            ),
            2,
        ),

        "ready_to_dispatch": sum(
            1 for order in orders.values()
            if order.get("dispatch_status") == "READY"
        ),

        "dispatched_orders": sum(
            1 for order in orders.values()
            if order.get("dispatch_status") == "DISPATCHED"
        ),

        "total_orders": len(orders),

        "total_batches": len(
            factory.get("batches", [])
        ),

        "customer_order_elapsed_hours": round(
            float(factory.get("customer_order_elapsed_hours", 0)),
            2,
        ),
    }
