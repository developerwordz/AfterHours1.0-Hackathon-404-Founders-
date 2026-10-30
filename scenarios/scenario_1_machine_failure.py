"""
Scenario 1: Single Machine Failure (M1 Air-Jet Loom Breakdown)
- M1 fails mid-order on ORD-101 (600m cotton_twill remaining, 14h deadline).
- Also requires 200kg additional RM-COTTON (400kg in stock vs 600kg needed).
"""
from scenarios import load_realistic_factory
from factory import simulate_machine_failure
from recovery import generate_factory_recovery_report


def run_scenario():
    factory = load_realistic_factory()
    incident = simulate_machine_failure(factory, "M1")
    report = generate_factory_recovery_report(factory, [incident])
    return {
        "scenario_id": "SCEN-01",
        "name": "Single Machine Failure (M1 Breakdown)",
        "factory": factory,
        "incidents": [incident],
        "report": report,
    }


if __name__ == "__main__":
    res = run_scenario()
    print(f"[{res['scenario_id']}] {res['name']}")
    print("Orders Saved:", res["report"]["orders_saved"], "| Total Cost: $", res["report"]["total_recovery_cost"])