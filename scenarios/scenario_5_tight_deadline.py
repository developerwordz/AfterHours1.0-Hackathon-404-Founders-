"""
Scenario 5: Tight Production Deadline (Uniqlo Rush Order ORD-103 Under Failure)
- ORD-103 (500m poly_blend, tight 9.0h deadline) is running on M1, and M1 fails.
- Reassigning 500m to slower M2 (45m/hr) takes 11.11h (> 9.0h deadline).
- Demonstrates honest reporting when a tight deadline cannot be met, while minimizing late penalties.
"""
from scenarios import load_realistic_factory
from factory import simulate_machine_failure
from recovery import generate_factory_recovery_report


def run_scenario():
    factory = load_realistic_factory()
    # Set ORD-101 as completed so M1 is actively running the tight-deadline rush order ORD-103
    factory["orders"]["ORD-101"]["status"] = "COMPLETED"
    factory["orders"]["ORD-101"]["remaining_quantity_m"] = 0.0
    factory["orders"]["ORD-101"]["assigned_machine_id"] = None

    factory["orders"]["ORD-103"]["assigned_machine_id"] = "M1"
    factory["orders"]["ORD-103"]["status"] = "IN_PROGRESS"
    factory["machines"]["M1"]["assigned_order_id"] = "ORD-103"

    incident = simulate_machine_failure(factory, "M1")
    report = generate_factory_recovery_report(factory, [incident])
    return {
        "scenario_id": "SCEN-05",
        "name": "Tight Production Deadline (500m Rush Order on Failed M1, 9h Deadline)",
        "factory": factory,
        "incidents": [incident],
        "report": report,
    }


if __name__ == "__main__":
    res = run_scenario()
    print(f"[{res['scenario_id']}] {res['name']}")
    print("Feasibility:", res["report"]["overall_feasibility"])
    print("Assessment:", res["report"]["order_reports"]["ORD-103"]["honest_assessment"])