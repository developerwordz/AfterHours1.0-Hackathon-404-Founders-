
"""
supply_chain_agent.py
Material-specific supply networks, shipment simulation and autonomous
disruption recovery for TexResQ.

All supplier names, locations, routes, delivery times and incidents are
SIMULATED for the project demonstration.
"""

from datetime import datetime, timedelta
import random


# ============================================================
# SIMULATED GEOGRAPHY
# ============================================================

FACTORY_LOCATION = {
    "name": "TexResQ Factory — Mysuru",
    "lat": 12.2958,
    "lon": 76.6394,
}

# Each material has its own independent suppliers and locations.
NETWORK_DEFINITIONS = {
    "COTTON": {
        "network_id": "NET-COTTON",
        "material_id": "RM-COTTON",
        "material_name": "Cotton",
        "suppliers": [
            {
                "id": "COT-PRI",
                "name": "Coimbatore Cotton Works",
                "role": "PRIMARY",
                "city": "Coimbatore",
                "lat": 11.0168,
                "lon": 76.9558,
                "cost": 3.5,
                "eta": 9.0,
                "reliability": 96,
                "capacity": 2500.0,
            },
            {
                "id": "COT-SEC",
                "name": "Nagpur Fibre Traders",
                "role": "SECONDARY",
                "city": "Nagpur",
                "lat": 21.1458,
                "lon": 79.0882,
                "cost": 4.4,
                "eta": 15.0,
                "reliability": 94,
                "capacity": 3000.0,
            },
            {
                "id": "COT-EMG",
                "name": "Surat Emergency Cotton Depot",
                "role": "EMERGENCY",
                "city": "Surat",
                "lat": 21.1702,
                "lon": 72.8311,
                "cost": 6.2,
                "eta": 13.0,
                "reliability": 90,
                "capacity": 1200.0,
            },
        ],
    },

    "DYE": {
        "network_id": "NET-DYE",
        "material_id": "RM-DYE",
        "material_name": "Textile Dye",
        "suppliers": [
            {
                "id": "DYE-PRI",
                "name": "Ahmedabad Dye Industries",
                "role": "PRIMARY",
                "city": "Ahmedabad",
                "lat": 23.0225,
                "lon": 72.5714,
                "cost": 4.5,
                "eta": 14.0,
                "reliability": 97,
                "capacity": 1800.0,
            },
            {
                "id": "DYE-SEC",
                "name": "Vapi Colour Chemicals",
                "role": "SECONDARY",
                "city": "Vapi",
                "lat": 20.3710,
                "lon": 72.9049,
                "cost": 5.2,
                "eta": 11.0,
                "reliability": 95,
                "capacity": 1600.0,
            },
            {
                "id": "DYE-EMG",
                "name": "Mumbai Emergency Dye Supply",
                "role": "EMERGENCY",
                "city": "Mumbai",
                "lat": 19.0760,
                "lon": 72.8777,
                "cost": 7.0,
                "eta": 12.0,
                "reliability": 91,
                "capacity": 900.0,
            },
        ],
    },

    "POLYESTER": {
        "network_id": "NET-POLYESTER",
        "material_id": "RM-POLY",
        "material_name": "Polyester",
        "suppliers": [
            {
                "id": "POLY-PRI",
                "name": "Vadodara Polymer Textiles",
                "role": "PRIMARY",
                "city": "Vadodara",
                "lat": 22.3072,
                "lon": 73.1812,
                "cost": 2.8,
                "eta": 15.0,
                "reliability": 96,
                "capacity": 3000.0,
            },
            {
                "id": "POLY-SEC",
                "name": "Pune Synthetic Fibres",
                "role": "SECONDARY",
                "city": "Pune",
                "lat": 18.5204,
                "lon": 73.8567,
                "cost": 3.7,
                "eta": 10.0,
                "reliability": 95,
                "capacity": 2200.0,
            },
            {
                "id": "POLY-EMG",
                "name": "Bengaluru Emergency Filaments",
                "role": "EMERGENCY",
                "city": "Bengaluru",
                "lat": 12.9716,
                "lon": 77.5946,
                "cost": 5.0,
                "eta": 4.0,
                "reliability": 92,
                "capacity": 1000.0,
            },
        ],
    },
}


# ============================================================
# SIMULATION HELPERS
# ============================================================

def _now(factory):
    value = factory.get("supply_simulation", {}).get("clock")
    if value:
        return datetime.fromisoformat(value)
    return datetime.now()


def _timestamp(factory):
    return _now(factory).isoformat(timespec="minutes")


def _supplier_lookup(factory, supplier_id):
    return factory.get("supply_chain_suppliers", {}).get(
        supplier_id, {}
    )


def _network_supplier_ids(network):
    return [
        item["id"]
        for item in network.get("supplier_options", [])
    ]


def _make_event(factory, network, event_type, description, severity="MEDIUM",
                shipment_id=None):
    event = {
        "incident_id": (
            f"SC-INC-{len(factory['transport_incidents']) + 1:04d}"
        ),
        "timestamp": _timestamp(factory),
        "network_id": network["network_id"],
        "material_name": network["material_name"],
        "event_type": event_type,
        "severity": severity,
        "description": description,
        "shipment_id": shipment_id,
        "status": "RECORDED",
    }

    factory["transport_incidents"].append(event)
    return event


def _make_intervention(factory, network, action, reason, old_supplier=None,
                       new_supplier=None, shipment_id=None):
    old = _supplier_lookup(factory, old_supplier) if old_supplier else {}
    new = _supplier_lookup(factory, new_supplier) if new_supplier else {}

    intervention = {
        "timestamp": _timestamp(factory),
        "network_id": network["network_id"],
        "material_id": network["material_id"],
        "material_name": network["material_name"],
        "action": action,
        "reason": reason,
        "previous_supplier_id": old_supplier,
        "previous_supplier_name": old.get("name", old_supplier),
        "replacement_supplier_id": new_supplier,
        "replacement_supplier_name": new.get("name", new_supplier),
        "shipment_id": shipment_id,
        "status": "COMPLETED",
    }

    factory["supply_chain_interventions"].append(intervention)
    network.setdefault("failover_history", []).append(intervention.copy())
    return intervention


def _route_for_supplier(supplier):
    return [
        [supplier["lat"], supplier["lon"]],
        [13.0827, 77.5833],
        [12.2958, 76.6394],
    ]


def _new_shipment(factory, network, supplier_id, quantity=None):
    supplier = _supplier_lookup(factory, supplier_id)
    if not supplier:
        return None

    clock = _now(factory)
    eta_hours = float(supplier.get("delivery_time_hrs", 10.0))
    quantity = float(quantity or random.choice([100, 150, 200, 250]))

    shipment_number = len(factory["shipments"]) + 1
    shipment_id = f"SHP-{shipment_number:04d}"

    shipment = {
        "shipment_id": shipment_id,
        "network_id": network["network_id"],
        "network_key": network["key"],
        "material_id": network["material_id"],
        "material_name": network["material_name"],
        "supplier_id": supplier_id,
        "supplier_name": supplier["name"],
        "supplier_city": supplier["city"],
        "origin_lat": supplier["lat"],
        "origin_lon": supplier["lon"],
        "destination": FACTORY_LOCATION["name"],
        "destination_lat": FACTORY_LOCATION["lat"],
        "destination_lon": FACTORY_LOCATION["lon"],
        "quantity_kg": quantity,
        "cost_per_kg": supplier["cost_per_kg"],
        "transport_id": f"TRK-{random.randint(1000, 9999)}",
        "status": "SCHEDULED",
        "created_at": clock.isoformat(timespec="minutes"),
        "depart_at": (clock + timedelta(hours=1)).isoformat(timespec="minutes"),
        "eta": (clock + timedelta(hours=1 + eta_hours)).isoformat(timespec="minutes"),
        "progress": 0.0,
        "route": _route_for_supplier(supplier),
        "route_version": 1,
        "last_event": "Shipment scheduled",
    }

    factory["shipments"].append(shipment)
    return shipment


def _get_network(factory, network_key):
    return factory["supply_networks"][network_key]


# ============================================================
# INITIALIZATION
# ============================================================

def initialize_supply_chain(factory):
    """
    Safely adds supply-chain simulation state to an existing factory.
    Can be called repeatedly without resetting simulation progress.
    """

    factory.setdefault("raw_materials", {})
    factory.setdefault("supply_chain_interventions", [])
    factory.setdefault("transport_incidents", [])
    factory.setdefault("shipments", [])
    factory.setdefault("supply_chain_suppliers", {})
    factory.setdefault("supply_networks", {})

    factory["raw_materials"].setdefault(
        "RM-DYE",
        {
            "id": "RM-DYE",
            "name": "Industrial Textile Dye",
            "stock_kg": 300.0,
            "reserved_kg": 0.0,
        },
    )

    for network_key, definition in NETWORK_DEFINITIONS.items():
        supplier_options = []

        for source in definition["suppliers"]:
            supplier_id = source["id"]

            supplier = factory["supply_chain_suppliers"].setdefault(
                supplier_id,
                {
                    "id": supplier_id,
                    "name": source["name"],
                    "role": source["role"],
                    "city": source["city"],
                    "lat": source["lat"],
                    "lon": source["lon"],
                    "cost_per_kg": source["cost"],
                    "delivery_time_hrs": source["eta"],
                    "reliability_score": source["reliability"],
                    "max_supply_kg": source["capacity"],
                    "committed_supply_kg": 0.0,
                    "status": "ACTIVE",
                },
            )

            supplier_options.append({
                "id": supplier_id,
                "role": source["role"],
            })

        network = factory["supply_networks"].setdefault(
            network_key,
            {
                "key": network_key,
                "network_id": definition["network_id"],
                "material_id": definition["material_id"],
                "material_name": definition["material_name"],
                "supplier_options": supplier_options,
                "active_supplier_id": definition["suppliers"][0]["id"],
                "active_source_role": "PRIMARY",
                "status": "OPERATIONAL",
                "failover_history": [],
                "last_failover_at": None,
            },
        )

        network.setdefault("key", network_key)
        network.setdefault("network_id", definition["network_id"])
        network.setdefault("material_id", definition["material_id"])
        network.setdefault("material_name", definition["material_name"])
        network.setdefault("supplier_options", supplier_options)
        network.setdefault(
            "active_supplier_id", definition["suppliers"][0]["id"]
        )
        network.setdefault("active_source_role", "PRIMARY")
        network.setdefault("status", "OPERATIONAL")
        network.setdefault("failover_history", [])
        network.setdefault("last_failover_at", None)

    factory.setdefault(
        "supply_simulation",
        {
            "clock": datetime.now().isoformat(timespec="minutes"),
            "elapsed_hours": 0,
            "ticks": 0,
        },
    )

    # Create one initial shipment per network, only on first initialization.
    if not factory["shipments"]:
        for network_key, network in factory["supply_networks"].items():
            _new_shipment(
                factory,
                network,
                network["active_supplier_id"],
            )

    return factory["supply_networks"]


# ============================================================
# DEMAND CALCULATION
# ============================================================

def calculate_material_demand(factory, material_id):
    total_required = 0.0

    for order in factory.get("orders", {}).values():
        if order.get("raw_material_id") != material_id:
            continue
        if order.get("status") == "COMPLETED":
            continue

        remaining = max(0.0, float(order.get("remaining_quantity_m", 0)))
        consumption = float(order.get("raw_material_per_m", 1.0))
        total_required += remaining * consumption

    material = factory.get("raw_materials", {}).get(material_id, {})
    stock = float(material.get("stock_kg", 0))
    reserved = float(material.get("reserved_kg", 0))
    available = max(0.0, stock - reserved)

    return {
        "required_kg": round(total_required, 2),
        "available_kg": round(available, 2),
        "shortfall_kg": round(max(0.0, total_required - available), 2),
    }


# ============================================================
# SUPPLIER FAILOVER
# ============================================================

def _choose_alternative(factory, network, excluded_ids=None):
    excluded_ids = set(excluded_ids or [])
    candidates = []

    for option in network["supplier_options"]:
        supplier_id = option["id"]
        if supplier_id in excluded_ids:
            continue

        supplier = _supplier_lookup(factory, supplier_id)
        if not supplier or supplier.get("status") != "ACTIVE":
            continue

        capacity = (
            float(supplier.get("max_supply_kg", 0))
            - float(supplier.get("committed_supply_kg", 0))
        )
        if capacity <= 0:
            continue

        cost = float(supplier.get("cost_per_kg", 999))
        eta = float(supplier.get("delivery_time_hrs", 999))
        reliability = float(supplier.get("reliability_score", 0))

        # Lower is better. Cost, ETA and reliability all matter.
        score = (
            0.35 * cost / 10.0
            + 0.25 * eta / 24.0
            + 0.40 * (100 - reliability) / 100.0
        )

        candidates.append((score, supplier_id, capacity))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def switch_supplier(factory, network_key, failed_supplier_id, reason):
    initialize_supply_chain(factory)
    network = _get_network(factory, network_key)

    supplier = _supplier_lookup(factory, failed_supplier_id)
    if supplier:
        supplier["status"] = "FAILED"

    old_supplier_id = network.get("active_supplier_id")
    if old_supplier_id != failed_supplier_id:
        return None

    replacement_id = _choose_alternative(
        factory,
        network,
        excluded_ids={failed_supplier_id},
    )

    if replacement_id is None:
        network["active_supplier_id"] = None
        network["active_source_role"] = None
        network["status"] = "DISRUPTED"

        return _make_intervention(
            factory,
            network,
            "SUPPLIER_SWITCH_FAILED",
            reason + " No available alternative supplier had capacity.",
            old_supplier=old_supplier_id,
        )

    replacement = _supplier_lookup(factory, replacement_id)
    network["active_supplier_id"] = replacement_id
    network["active_source_role"] = replacement["role"]
    network["status"] = "DEGRADED"
    network["last_failover_at"] = _timestamp(factory)

    intervention = _make_intervention(
        factory,
        network,
        "SUPPLIER_SWITCH",
        reason,
        old_supplier=old_supplier_id,
        new_supplier=replacement_id,
    )

    # Create a replacement shipment from the new supplier.
    _new_shipment(factory, network, replacement_id)

    return intervention


def run_supply_chain_agent(factory, failed_supplier_id=None):
    """
    Backward-compatible supplier failover entry point.

    If failed_supplier_id is a new material-network supplier ID, only that
    network is affected. Legacy supplier IDs are handled separately by the
    original supplier-recovery workflow.
    """
    initialize_supply_chain(factory)
    interventions = []

    for network_key, network in factory["supply_networks"].items():
        active_id = network.get("active_supplier_id")

        if failed_supplier_id:
            if active_id != failed_supplier_id:
                continue
        else:
            active = _supplier_lookup(factory, active_id)
            if active.get("status") == "ACTIVE":
                continue

        result = switch_supplier(
            factory,
            network_key,
            active_id,
            f"Supplier {active_id} became unavailable.",
        )
        if result:
            interventions.append(result)

    return interventions


# ============================================================
# TRANSPORT REROUTING
# ============================================================

def reroute_shipment(factory, shipment, reason):
    """
    Changes the transport route without changing the supplier.
    This models roadblocks, weather and route restrictions.
    """
    network = _get_network(factory, shipment["network_key"])

    # A simulated alternative corridor via a different waypoint.
    old_route = shipment["route"]
    supplier = _supplier_lookup(factory, shipment["supplier_id"])

    if shipment.get("route_version", 1) % 2:
        waypoint = [14.1670, 75.0403]  # Simulated central Karnataka corridor
    else:
        waypoint = [11.8745, 75.3704]  # Simulated western corridor

    shipment["route"] = [
        [supplier["lat"], supplier["lon"]],
        waypoint,
        [12.2958, 76.6394],
    ]
    shipment["route_version"] = shipment.get("route_version", 1) + 1
    shipment["eta"] = (
        datetime.fromisoformat(shipment["eta"]) + timedelta(hours=2)
    ).isoformat(timespec="minutes")
    shipment["status"] = "REROUTED"
    shipment["last_event"] = reason

    _make_event(
        factory,
        network,
        "ROUTE_REROUTED",
        reason,
        "MEDIUM",
        shipment["shipment_id"],
    )

    _make_intervention(
        factory,
        network,
        "TRANSPORT_REROUTE",
        reason + " Supplier retained; alternate transport corridor selected.",
        old_supplier=shipment["supplier_id"],
        new_supplier=shipment["supplier_id"],
        shipment_id=shipment["shipment_id"],
    )

    return shipment


# ============================================================
# SHIPMENT PROGRESS
# ============================================================

def _advance_shipments(factory):
    clock = _now(factory)

    for shipment in factory["shipments"]:
        if shipment["status"] in ("DELIVERED", "DECLINED", "CANCELLED"):
            continue

        depart = datetime.fromisoformat(shipment["depart_at"])
        eta = datetime.fromisoformat(shipment["eta"])

        if clock < depart:
            shipment["status"] = "SCHEDULED"
            shipment["progress"] = 0.0
        elif clock >= eta:
            shipment["status"] = "DELIVERED"
            shipment["progress"] = 100.0
            shipment["last_event"] = "Shipment delivered to Mysuru factory"

            material = factory["raw_materials"].setdefault(
                shipment["material_id"],
                {
                    "id": shipment["material_id"],
                    "name": shipment["material_name"],
                    "stock_kg": 0.0,
                    "reserved_kg": 0.0,
                },
            )
            material["stock_kg"] = round(
                float(material.get("stock_kg", 0))
                + float(shipment["quantity_kg"]),
                2,
            )
        else:
            total = max(1.0, (eta - depart).total_seconds())
            elapsed = max(0.0, (clock - depart).total_seconds())
            shipment["progress"] = round(
                min(99.0, 100.0 * elapsed / total), 1
            )
            if shipment["status"] not in ("DELAYED", "REROUTED"):
                shipment["status"] = "IN TRANSIT"


# ============================================================
# RANDOM DISRUPTION ENGINE
# ============================================================

def _generate_random_disruption(factory):
    active_shipments = [
        item for item in factory["shipments"]
        if item["status"] in ("SCHEDULED", "IN TRANSIT", "REROUTED")
    ]

    if not active_shipments:
        return None

    # One chance per simulation tick. Keep incidents occasional.
    if random.random() > 0.42:
        return None

    shipment = random.choice(active_shipments)
    network = _get_network(factory, shipment["network_key"])

    event_type = random.choice([
        "ROADBLOCK",
        "TRUCK_BREAKDOWN",
        "TRANSPORT_DECLINED",
        "WEATHER_DELAY",
        "SUPPLIER_OUTAGE",
    ])

    if event_type == "ROADBLOCK":
        reroute_shipment(
            factory,
            shipment,
            "Roadblock detected. Agent selected an alternate corridor.",
        )

    elif event_type == "TRUCK_BREAKDOWN":
        shipment["status"] = "DELAYED"
        shipment["eta"] = (
            datetime.fromisoformat(shipment["eta"])
            + timedelta(hours=3)
        ).isoformat(timespec="minutes")
        shipment["last_event"] = "Truck breakdown; replacement vehicle dispatched"

        _make_event(
            factory, network, event_type,
            "Truck breakdown reported. Replacement vehicle dispatched.",
            "HIGH", shipment["shipment_id"],
        )

        _make_intervention(
            factory, network, "TRANSPORT_REPLACEMENT",
            "Original truck broke down. Replacement vehicle assigned; supplier unchanged.",
            old_supplier=shipment["supplier_id"],
            new_supplier=shipment["supplier_id"],
            shipment_id=shipment["shipment_id"],
        )

    elif event_type == "TRANSPORT_DECLINED":
        shipment["status"] = "DECLINED"
        shipment["last_event"] = "Carrier declined the assigned transport"

        _make_event(
            factory, network, event_type,
            "Assigned carrier declined the transport request.",
            "HIGH", shipment["shipment_id"],
        )

        # Keep supplier; assign a new carrier and shipment.
        replacement = _new_shipment(
            factory,
            network,
            shipment["supplier_id"],
            shipment["quantity_kg"],
        )
        if replacement:
            replacement["last_event"] = "New carrier assigned after decline"
            _make_intervention(
                factory, network, "CARRIER_REASSIGNED",
                "Carrier declined the shipment. A new carrier was assigned; supplier unchanged.",
                old_supplier=shipment["supplier_id"],
                new_supplier=shipment["supplier_id"],
                shipment_id=replacement["shipment_id"],
            )

    elif event_type == "WEATHER_DELAY":
        shipment["status"] = "DELAYED"
        shipment["eta"] = (
            datetime.fromisoformat(shipment["eta"])
            + timedelta(hours=4)
        ).isoformat(timespec="minutes")
        shipment["last_event"] = "Severe weather caused a delivery delay"

        _make_event(
            factory, network, event_type,
            "Severe weather warning. Delivery ETA extended by four hours.",
            "MEDIUM", shipment["shipment_id"],
        )

        _make_intervention(
            factory, network, "ETA_ADJUSTMENT",
            "Weather disruption detected. ETA adjusted; shipment remains with the same supplier.",
            old_supplier=shipment["supplier_id"],
            new_supplier=shipment["supplier_id"],
            shipment_id=shipment["shipment_id"],
        )

    elif event_type == "SUPPLIER_OUTAGE":
        supplier_id = shipment["supplier_id"]
        supplier = _supplier_lookup(factory, supplier_id)
        supplier["status"] = "FAILED"

        _make_event(
            factory, network, event_type,
            f"{supplier['name']} reported an unexpected supply outage.",
            "CRITICAL", shipment["shipment_id"],
        )

        if network.get("active_supplier_id") == supplier_id:
            switch_supplier(
                factory,
                shipment["network_key"],
                supplier_id,
                "Supplier outage detected by autonomous monitoring.",
            )

        shipment["status"] = "CANCELLED"
        shipment["last_event"] = "Cancelled due to supplier outage"

    return event_type


def advance_simulation(factory, hours=2):
    """
    Advances simulated time only when explicitly called by the UI.
    Returns the disruption generated during this tick, if any.
    """
    initialize_supply_chain(factory)

    simulation = factory["supply_simulation"]
    simulation["clock"] = (
        _now(factory) + timedelta(hours=hours)
    ).isoformat(timespec="minutes")
    simulation["elapsed_hours"] += hours
    simulation["ticks"] += 1

    _advance_shipments(factory)
    disruption = _generate_random_disruption(factory)
    _advance_shipments(factory)

    # Keep each network supplied with a future shipment.
    for network_key, network in factory["supply_networks"].items():
        active_id = network.get("active_supplier_id")
        if not active_id:
            continue

        open_shipments = [
            item for item in factory["shipments"]
            if item["network_key"] == network_key
            and item["status"] not in (
                "DELIVERED", "DECLINED", "CANCELLED"
            )
        ]

        if len(open_shipments) == 0:
            _new_shipment(factory, network, active_id)

    return disruption


# ============================================================
# SUMMARY
# ============================================================

def get_supply_chain_summary(factory):
    initialize_supply_chain(factory)

    networks = factory["supply_networks"]
    shipments = factory["shipments"]

    return {
        "total_networks": len(networks),
        "operational": sum(
            n["status"] == "OPERATIONAL" for n in networks.values()
        ),
        "degraded": sum(
            n["status"] == "DEGRADED" for n in networks.values()
        ),
        "disrupted": sum(
            n["status"] == "DISRUPTED" for n in networks.values()
        ),
        "active_sources": {
            key: n.get("active_supplier_id")
            for key, n in networks.items()
        },
        "total_shipments": len(shipments),
        "in_transit": sum(
            s["status"] in ("IN TRANSIT", "REROUTED")
            for s in shipments
        ),
        "delayed": sum(s["status"] == "DELAYED" for s in shipments),
        "declined": sum(s["status"] == "DECLINED" for s in shipments),
        "delivered": sum(s["status"] == "DELIVERED" for s in shipments),
    }
