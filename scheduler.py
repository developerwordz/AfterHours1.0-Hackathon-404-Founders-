"""
scheduler.py — Production scheduling and feasibility logic for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""


def calculate_production_time(order: dict, machine: dict) -> float:
    """
    Calculates the hours required to produce the remaining quantity of an order
    on a specific machine (excluding maintenance or material wait times).

    Args:
        order (dict): Order dictionary from factory['orders'].
        machine (dict): Machine dictionary from factory['machines'].

    Returns:
        float: Production time in hours (rounded to 2 decimal places).

    Raises:
        ValueError: If machine capacity is <= 0 or remaining quantity < 0.
    """
    capacity = machine.get("capacity_m_per_hr", 0.0)
    remaining_qty = order.get("remaining_quantity_m", 0.0)

    if capacity <= 0:
        raise ValueError(f"Machine '{machine.get('id')}' has invalid capacity: {capacity}")
    if remaining_qty <= 0:
        return 0.0

    return round(remaining_qty / capacity, 2)


def check_machine_capacity(order: dict, machine: dict) -> dict:
    """
    Determines whether a machine is technically capable and available to take an order.
    Checks fabric compatibility, operational status, and current order assignment.

    Args:
        order (dict): Order dictionary.
        machine (dict): Machine dictionary.

    Returns:
        dict: {
            "compatible": bool,       # Can this loom weave this fabric type?
            "available_now": bool,    # Is the machine currently IDLE (or already running this order)?
            "can_accept_order": bool, # True if compatible and not busy with a different order
            "delay_before_start_hrs": float, # 0 if IDLE, maintenance_duration if FAILED
            "reason": str
        }
    """
    fabric_needed = order["fabric_type"]
    supported_fabrics = machine.get("supported_fabrics", [])

    # 1. Check technical capability (Not every machine can handle every order!)
    if fabric_needed not in supported_fabrics:
        return {
            "compatible": False,
            "available_now": False,
            "can_accept_order": False,
            "delay_before_start_hrs": float("inf"),
            "reason": f"Machine {machine['id']} supports {supported_fabrics}, cannot weave '{fabric_needed}'.",
        }

    status = machine["status"]
    assigned_order = machine.get("assigned_order_id")

    # 2. If machine is IDLE, it can start immediately
    if status == "IDLE":
        return {
            "compatible": True,
            "available_now": True,
            "can_accept_order": True,
            "delay_before_start_hrs": 0.0,
            "reason": f"Machine {machine['id']} is IDLE and compatible with '{fabric_needed}'.",
        }

    # 3. If machine is RUNNING a different order, it is busy
    if status == "RUNNING" and assigned_order not in (None, order["id"]):
        return {
            "compatible": True,
            "available_now": False,
            "can_accept_order": False,
            "delay_before_start_hrs": float("inf"),
            "reason": f"Machine {machine['id']} is busy running order '{assigned_order}'.",
        }

    # 4. If machine is FAILED or in MAINTENANCE, it can only start after repair
    if status in ("FAILED", "MAINTENANCE"):
        repair_hrs = machine.get("maintenance_duration_hrs", 0.0)
        return {
            "compatible": True,
            "available_now": False,
            "can_accept_order": True,  # Can accept if we wait for maintenance
            "delay_before_start_hrs": repair_hrs,
            "reason": f"Machine {machine['id']} is {status}; requires {repair_hrs} hrs maintenance before starting.",
        }

    return {
        "compatible": True,
        "available_now": True,
        "can_accept_order": True,
        "delay_before_start_hrs": 0.0,
        "reason": f"Machine {machine['id']} is already assigned to '{order['id']}'.",
    }


def check_deadline(order: dict, machine: dict, additional_delay_hrs: float = 0.0) -> dict:
    """
    Checks whether an order can be completed before its deadline on a specific machine,
    accounting for machine compatibility, repair delays, and optional supply delays.

    Args:
        order (dict): Order dictionary.
        machine (dict): Machine dictionary.
        additional_delay_hrs (float, optional): Extra wait time (e.g., supplier delivery). Defaults to 0.0.

    Returns:
        dict: {
            "feasible": bool,
            "meets_deadline": bool,
            "production_time_hrs": float,
            "start_delay_hrs": float,
            "total_time_hrs": float,
            "deadline_hrs": float,
            "slack_hrs": float,  # Positive = hours early, Negative = hours late
            "reason": str
        }
    """
    cap_check = check_machine_capacity(order, machine)
    deadline = order["deadline_hrs"]

    if not cap_check["can_accept_order"]:
        return {
            "feasible": False,
            "meets_deadline": False,
            "production_time_hrs": 0.0,
            "start_delay_hrs": cap_check["delay_before_start_hrs"],
            "total_time_hrs": float("inf"),
            "deadline_hrs": deadline,
            "slack_hrs": -float("inf"),
            "reason": cap_check["reason"],
        }

    prod_time = calculate_production_time(order, machine)
    # Machine repair and material wait can happen in parallel, or sequentially depending on strategy;
    # here start_delay is the max of machine readiness and external material delivery delay.
    start_delay = max(cap_check["delay_before_start_hrs"], additional_delay_hrs)
    total_time = round(start_delay + prod_time, 2)
    slack = round(deadline - total_time, 2)
    meets_deadline = total_time <= deadline

    reason = (
        f"Completes in {total_time}h (Delay: {start_delay}h + Weaving: {prod_time}h) vs {deadline}h deadline."
        if meets_deadline
        else f"Misses deadline by {abs(slack)}h (Total: {total_time}h vs Deadline: {deadline}h)."
    )

    return {
        "feasible": True,
        "meets_deadline": meets_deadline,
        "production_time_hrs": prod_time,
        "start_delay_hrs": start_delay,
        "total_time_hrs": total_time,
        "deadline_hrs": deadline,
        "slack_hrs": slack,
        "reason": reason,
    }


if __name__ == "__main__":
    from factory import create_factory, simulate_machine_failure

    print("=== TASK 2 TEST: scheduler.py ===")
    f = create_factory()
    simulate_machine_failure(f, "M1")
    ord_101 = f["orders"]["ORD-101"]

    for m_id, mach in f["machines"].items():
        res = check_deadline(ord_101, mach)
        print(f"Order {ord_101['id']} on {m_id} ({mach['status']}): meets_deadline={res['meets_deadline']} | {res['reason']}")