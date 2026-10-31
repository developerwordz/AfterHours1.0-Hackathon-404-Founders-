
"""
inventory_agent.py
Inventory forecasting and autonomous procurement for TexResQ.

All suppliers, lead times, costs and shipments are simulated.
"""

from datetime import timedelta
from supply_chain_agent import (
    initialize_supply_chain,
    FACTORY_LOCATION,
)


# ============================================================
# MATERIAL NETWORK MAPPING
# ============================================================

MATERIAL_NETWORKS = {
    "RM-COTTON": "COTTON",
    "RM-INDIGO": "INDIGO",
    "RM-POLY": "POLYESTER",
    "RM-DYE": "DYE",
}

SAFETY_STOCK_PERCENT = 0.10
MINIMUM_SAFETY_STOCK_KG = 25.0

# Simulated suppliers dedicated to indigo denim yarn.
# RM-INDIGO is yarn, not textile dye.
INDIGO_SUPPLIERS = [
    {
        "id": "IND-PRI",
        "name": "Erode Indigo Yarn Mills",
        "role": "PRIMARY",
        "city": "Erode",
        "lat": 11.3410,
        "lon": 77.7172,
        "cost": 4.0,
        "eta": 8.0,
        "reliability": 97,
        "capacity": 1800.0,
    },
    {
        "id": "IND-SEC",
        "name": "Ahmedabad Denim Fibres",
        "role": "SECONDARY",
        "city": "Ahmedabad",
        "lat": 23.0225,
        "lon": 72.5714,
        "cost": 4.8,
        "eta": 14.0,
        "reliability": 95,
        "capacity": 2200.0,
    },
    {
        "id": "IND-EMG",
        "name": "Bengaluru Indigo Emergency Supply",
        "role": "EMERGENCY",
        "city": "Bengaluru",
        "lat": 12.9716,
        "lon": 77.5946,
        "cost": 6.5,
        "eta": 4.0,
        "reliability": 91,
        "capacity": 800.0,
    },
]


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_inventory_networks(factory):
    """Initialize the existing supply networks and add the indigo network."""

    initialize_supply_chain(factory)

    factory.setdefault("inventory_procurement_log", [])
    factory.setdefault("inventory_forecast_history", [])

    factory["supply_chain_suppliers"].setdefault(
        "IND-PRI",
        {
            "id": "IND-PRI",
            "name": "Erode Indigo Yarn Mills",
            "role": "PRIMARY",
            "city": "Erode",
            "lat": 11.3410,
            "lon": 77.7172,
            "cost_per_kg": 4.0,
            "delivery_time_hrs": 8.0,
            "reliability_score": 97,
            "max_supply_kg": 1800.0,
            "committed_supply_kg": 0.0,
            "status": "ACTIVE",
        },
    )

    factory["supply_chain_suppliers"].setdefault(
        "IND-SEC",
        {
            "id": "IND-SEC",
            "name": "Ahmedabad Denim Fibres",
            "role": "SECONDARY",
            "city": "Ahmedabad",
            "lat": 23.0225,
            "lon": 72.5714,
            "cost_per_kg": 4.8,
            "delivery_time_hrs": 14.0,
            "reliability_score": 95,
            "max_supply_kg": 2200.0,
            "committed_supply_kg": 0.0,
            "status": "ACTIVE",
        },
    )

    factory["supply_chain_suppliers"].setdefault(
        "IND-EMG",
        {
            "id": "IND-EMG",
            "name": "Bengaluru Indigo Emergency Supply",
            "role": "EMERGENCY",
            "city": "Bengaluru",
            "lat": 12.9716,
            "lon": 77.5946,
            "cost_per_kg": 6.5,
            "delivery_time_hrs": 4.0,
            "reliability_score": 91,
            "max_supply_kg": 800.0,
            "committed_supply_kg": 0.0,
            "status": "ACTIVE",
        },
    )

    factory["supply_networks"].setdefault(
        "INDIGO",
        {
            "key": "INDIGO",
            "network_id": "NET-INDIGO",
            "material_id": "RM-INDIGO",
            "material_name": "Indigo Denim Yarn",
            "supplier_options": [
                {"id": "IND-PRI", "role": "PRIMARY"},
                {"id": "IND-SEC", "role": "SECONDARY"},
                {"id": "IND-EMG", "role": "EMERGENCY"},
            ],
            "active_supplier_id": "IND-PRI",
            "active_source_role": "PRIMARY",
            "status": "OPERATIONAL",
            "failover_history": [],
            "last_failover_at": None,
        },
    )

    return factory


# ============================================================
# TIME AND SHIPMENT HELPERS
# ============================================================

def _simulation_now(factory):
    clock = factory.get("supply_simulation", {}).get("clock")

    if clock:
        from datetime import datetime
        return datetime.fromisoformat(clock)

    from datetime import datetime
    return datetime.now()


def _incoming_shipments(factory, material_id):
    """Count all shipments that have not yet arrived or been cancelled."""

    active_statuses = {
        "SCHEDULED",
        "IN TRANSIT",
        "REROUTED",
        "DELAYED",
    }

    return [
        shipment
        for shipment in factory.get("shipments", [])
        if shipment.get("material_id") == material_id
        and shipment.get("status") in active_statuses
    ]


def _incoming_quantity(factory, material_id):
    return sum(
        float(shipment.get("quantity_kg", 0))
        for shipment in _incoming_shipments(factory, material_id)
    )


def _safety_stock(demand):
    if demand <= 0:
        return 0.0

    return round(
        max(
            MINIMUM_SAFETY_STOCK_KG,
            demand * SAFETY_STOCK_PERCENT,
        ),
        2,
    )


# ============================================================
# PRODUCTION DEMAND
# ============================================================

def calculate_production_demand(factory, material_id):
    """
    Calculates demand from all unfinished production orders.

    Existing reserved stock is already part of physical stock.
    Therefore, it is NOT subtracted a second time here.
    """

    demand = 0.0
    order_breakdown = []

    for order_id, order in factory.get("orders", {}).items():

        if order.get("raw_material_id") != material_id:
            continue

        if order.get("status") == "COMPLETED":
            continue

        remaining = max(
            0.0,
            float(order.get("remaining_quantity_m", 0)),
        )

        consumption = float(
            order.get("raw_material_per_m", 1.0)
        )

        required = remaining * consumption
        demand += required

        order_breakdown.append({
            "order_id": order_id,
            "client": order.get("client", "Unknown"),
            "fabric_type": order.get("fabric_type", "Unknown"),
            "status": order.get("status", "UNKNOWN"),
            "remaining_quantity_m": round(remaining, 2),
            "consumption_per_m": consumption,
            "required_material_kg": round(required, 2),
            "deadline_hrs": float(order.get("deadline_hrs", 0)),
            "assigned_machine_id": order.get("assigned_machine_id"),
        })

    return round(demand, 2), order_breakdown


# ============================================================
# SUPPLIER SELECTION
# ============================================================

def _select_procurement_supplier(factory, network_key, quantity):
    network = factory["supply_networks"].get(network_key)

    if not network:
        return None

    candidates = []

    for option in network.get("supplier_options", []):

        supplier_id = option["id"]
        supplier = factory["supply_chain_suppliers"].get(supplier_id)

        if not supplier:
            continue

        if supplier.get("status") != "ACTIVE":
            continue

        outstanding_quantity = sum(
            float(shipment.get("quantity_kg", 0))
            for shipment in factory.get("shipments", [])
            if shipment.get("supplier_id") == supplier_id
            and shipment.get("status") in (
                "SCHEDULED",
                "IN TRANSIT",
                "REROUTED",
                "DELAYED",
            )
        )

        capacity = (
            float(supplier.get("max_supply_kg", 0))
            - outstanding_quantity
        )

        if capacity < quantity:
            continue

        cost = float(supplier.get("cost_per_kg", 999))
        eta = float(supplier.get("delivery_time_hrs", 999))
        reliability = float(supplier.get("reliability_score", 0))

        score = (
            0.35 * cost / 10.0
            + 0.25 * eta / 24.0
            + 0.40 * (100.0 - reliability) / 100.0
        )

        candidates.append((score, supplier_id))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])

    return candidates[0][1]


# ============================================================
# PROCUREMENT SCHEDULING
# ============================================================

def schedule_procurement(factory, material_id, quantity_kg):
    """
    Creates a shipment using the existing supply-chain shipment schema.

    The shipment is visible to the existing geographic map and is advanced
    by supply_chain_agent.advance_simulation().
    Physical stock is NOT changed here.
    """

    if quantity_kg <= 0:
        return None

    network_key = MATERIAL_NETWORKS.get(material_id)

    if not network_key:
        return None

    network = factory["supply_networks"].get(network_key)

    if not network:
        return None

    supplier_id = _select_procurement_supplier(
        factory,
        network_key,
        quantity_kg,
    )

    if not supplier_id:
        return None

    supplier = factory["supply_chain_suppliers"][supplier_id]

    now = _simulation_now(factory)
    eta_hours = float(supplier["delivery_time_hrs"])

    shipment_number = len(factory.get("shipments", [])) + 1
    shipment_id = f"SHP-{shipment_number:04d}"

    shipment = {
        "shipment_id": shipment_id,
        "network_id": network["network_id"],
        "network_key": network_key,
        "material_id": material_id,
        "material_name": network["material_name"],
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "supplier_city": supplier["city"],
        "origin_lat": supplier["lat"],
        "origin_lon": supplier["lon"],
        "destination": FACTORY_LOCATION["name"],
        "destination_lat": FACTORY_LOCATION["lat"],
        "destination_lon": FACTORY_LOCATION["lon"],
        "quantity_kg": round(float(quantity_kg), 2),
        "cost_per_kg": float(supplier["cost_per_kg"]),
        "transport_id": f"TRK-{__import__('random').randint(1000, 9999)}",
        "status": "SCHEDULED",
        "created_at": now.isoformat(timespec="minutes"),
        "depart_at": (
            now + timedelta(hours=1)
        ).isoformat(timespec="minutes"),
        "eta": (
            now + timedelta(hours=1 + eta_hours)
        ).isoformat(timespec="minutes"),
        "progress": 0.0,
        "route": [
            [supplier["lat"], supplier["lon"]],
            [13.0827, 77.5833],
            [FACTORY_LOCATION["lat"], FACTORY_LOCATION["lon"]],
        ],
        "route_version": 1,
        "last_event": "Automatic inventory replenishment scheduled",

        # Inventory-specific metadata
        "shipment_purpose": "INVENTORY_REPLENISHMENT",
        "procurement_status": "OPEN",
        "procurement_material_id": material_id,
    }

    factory.setdefault("shipments", []).append(shipment)

    supplier["committed_supply_kg"] = round(
        float(supplier.get("committed_supply_kg", 0))
        + quantity_kg,
        2,
    )

    procurement_record = {
        "procurement_id": f"PO-{len(factory['inventory_procurement_log']) + 1:04d}",
        "shipment_id": shipment_id,
        "material_id": material_id,
        "material_name": network["material_name"],
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "quantity_kg": round(float(quantity_kg), 2),
        "cost_per_kg": float(supplier["cost_per_kg"]),
        "estimated_cost": round(
            float(quantity_kg) * float(supplier["cost_per_kg"]),
            2,
        ),
        "created_at": now.isoformat(timespec="minutes"),
        "eta": shipment["eta"],
        "status": "SCHEDULED",
    }

    factory["inventory_procurement_log"].append(
        procurement_record
    )

    return shipment


# ============================================================
# ORDER DELIVERY RISK
# ============================================================

def _estimate_order_production_hours(factory, order):
    remaining = float(order.get("remaining_quantity_m", 0))
    machine_id = order.get("assigned_machine_id")

    if machine_id:
        machine = factory.get("machines", {}).get(machine_id, {})
        capacity = float(machine.get("capacity_m_per_hr", 0))

        if capacity > 0:
            return remaining / capacity

    # For queued orders, estimate using the fastest compatible machine.
    fabric = order.get("fabric_type")
    capacities = []

    for machine in factory.get("machines", {}).values():
        if fabric in machine.get("supported_fabrics", []):
            capacity = float(machine.get("capacity_m_per_hr", 0))
            if capacity > 0:
                capacities.append(capacity)

    if capacities:
        return remaining / max(capacities)

    return None


def _order_delivery_risks(factory, material_id, estimated_arrival_hours):
    risks = []

    for order_id, order in factory.get("orders", {}).items():

        if order.get("raw_material_id") != material_id:
            continue

        if order.get("status") == "COMPLETED":
            continue

        production_hours = _estimate_order_production_hours(
            factory,
            order,
        )

        deadline = float(order.get("deadline_hrs", 0))

        if production_hours is None or deadline <= 0:
            continue

        projected_finish = estimated_arrival_hours + production_hours

        if projected_finish > deadline:
            risks.append({
                "order_id": order_id,
                "deadline_hrs": round(deadline, 2),
                "estimated_arrival_hrs": round(
                    estimated_arrival_hours, 2
                ),
                "estimated_production_hrs": round(
                    production_hours, 2
                ),
                "projected_finish_hrs": round(
                    projected_finish, 2
                ),
                "delay_risk_hrs": round(
                    projected_finish - deadline, 2
                ),
            })

    return risks


# ============================================================
# INVENTORY FORECAST
# ============================================================

def forecast_inventory(factory):
    initialize_inventory_networks(factory)

    forecasts = {}

    for material_id, material in factory.get(
        "raw_materials", {}
    ).items():

        demand, order_breakdown = calculate_production_demand(
            factory,
            material_id,
        )

        physical_stock = float(material.get("stock_kg", 0))
        reserved_stock = float(material.get("reserved_kg", 0))

        # Reserved stock is part of physical stock.
        available_stock = max(
            0.0,
            physical_stock - reserved_stock,
        )

        incoming = _incoming_quantity(factory, material_id)
        safety = _safety_stock(demand)

        projected_stock = physical_stock + incoming
        projected_available = max(
            0.0,
            projected_stock - reserved_stock,
        )

        # Calculate the purchase quantity without subtracting reservations
        # twice. Reservations are already included in physical stock.
        procurement_needed = max(
            0.0,
            demand + safety - projected_stock,
        )

        open_shipments = _incoming_shipments(
            factory,
            material_id,
        )

        earliest_arrival_hours = None

        if open_shipments:
            now = _simulation_now(factory)
            eta_values = []

            for shipment in open_shipments:
                try:
                    eta = __import__("datetime").datetime.fromisoformat(
                        shipment["eta"]
                    )
                    eta_values.append(
                        max(0.0, (eta - now).total_seconds() / 3600)
                    )
                except (KeyError, ValueError, TypeError):
                    pass

            if eta_values:
                earliest_arrival_hours = min(eta_values)

        if procurement_needed > 0:
            status = "SHORTAGE"
        elif projected_available < safety:
            status = "LOW BUFFER"
        else:
            status = "HEALTHY"

        forecasts[material_id] = {
            "material_id": material_id,
            "material_name": material.get("name", material_id),
            "physical_stock_kg": round(physical_stock, 2),
            "reserved_stock_kg": round(reserved_stock, 2),
            "available_stock_kg": round(available_stock, 2),
            "production_demand_kg": round(demand, 2),
            "safety_stock_kg": round(safety, 2),
            "incoming_stock_kg": round(incoming, 2),
            "projected_stock_kg": round(projected_stock, 2),
            "projected_available_kg": round(
                projected_available, 2
            ),
            "procurement_needed_kg": round(
                procurement_needed, 2
            ),
            "incoming_shipments": open_shipments,
            "earliest_arrival_hours": earliest_arrival_hours,
            "status": status,
            "orders": order_breakdown,
        }

    return forecasts


# ============================================================
# AUTONOMOUS INVENTORY AGENT
# ============================================================

def run_inventory_agent(factory, auto_procure=True):
    """
    Forecasts every material and schedules uncovered shortages.

    Idempotency:
    Every run recalculates incoming stock from the shipment tracker.
    Existing open shipments reduce the uncovered shortage, preventing
    duplicate purchase shipments on Streamlit reruns.
    """

    initialize_inventory_networks(factory)

    forecasts = forecast_inventory(factory)
    scheduled = []
    failures = []

    if auto_procure:

        for material_id, forecast in forecasts.items():

            quantity = float(
                forecast["procurement_needed_kg"]
            )

            if quantity <= 0:
                continue

            shipment = schedule_procurement(
                factory,
                material_id,
                quantity,
            )

            if shipment:
                scheduled.append(shipment)

                # Update this run's forecast so the UI immediately reflects
                # the newly scheduled shipment.
                forecast["incoming_stock_kg"] = round(
                    forecast["incoming_stock_kg"] + quantity,
                    2,
                )

                forecast["projected_stock_kg"] = round(
                    forecast["projected_stock_kg"] + quantity,
                    2,
                )

                forecast["projected_available_kg"] = round(
                    max(
                        0.0,
                        forecast["projected_stock_kg"]
                        - forecast["reserved_stock_kg"],
                    ),
                    2,
                )

                forecast["procurement_needed_kg"] = 0.0
                forecast["status"] = "REPLENISHMENT SCHEDULED"
                now = _simulation_now(factory)
                from datetime import datetime

                shipment_eta = datetime.fromisoformat(shipment["eta"])

                forecast["earliest_arrival_hours"] = max(
                    0.0,
                    (shipment_eta - now).total_seconds() / 3600,
                )

                forecast["incoming_shipments"].append(shipment)

            else:
                failures.append({
                    "material_id": material_id,
                    "quantity_kg": quantity,
                    "reason": (
                        "No active supplier has sufficient available capacity."
                    ),
                })

    # Attach delivery risk estimates.
    for material_id, forecast in forecasts.items():

        arrival_hours = forecast.get("earliest_arrival_hours")

        if arrival_hours is None and forecast["incoming_shipments"]:
            arrival_hours = 0.0

        if arrival_hours is None:
            arrival_hours = 0.0

        forecast["delivery_risks"] = _order_delivery_risks(
            factory,
            material_id,
            arrival_hours,
        )

    result = {
        "forecasts": forecasts,
        "scheduled_shipments": scheduled,
        "procurement_failures": failures,
        "timestamp": _simulation_now(factory).isoformat(
            timespec="minutes"
        ),
    }

    factory["inventory_forecast_history"].append({
        "timestamp": result["timestamp"],
        "materials_checked": len(forecasts),
        "shipments_scheduled": len(scheduled),
        "failures": len(failures),
    })

    return result


# ============================================================
# MANUAL FORECAST ONLY
# ============================================================

def run_inventory_forecast(factory):
    """Runs forecasting without scheduling new procurement."""

    initialize_inventory_networks(factory)

    return forecast_inventory(factory)
