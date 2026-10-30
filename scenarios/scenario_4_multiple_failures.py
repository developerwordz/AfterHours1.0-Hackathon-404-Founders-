"""
Scenario 4: Multiple Simultaneous Machine Failures (M1 & M3 Both Fail)
- Both active looms (M1 and M3) break down simultaneously.
- Only M2 is idle, creating resource contention between ORD-101 and ORD-102.
- M3 also lacks a 'torsion_bar' spare part in stock.
"""
from scenarios import load_realistic_factory
from factory import simulate_multiple_failures
from recovery import generate_factory_recovery_report


def run_scenario():
    factory = load_realistic_factory()
    incidents = simulate_multiple_failures(factory, ["M1", "M3"])
    report = generate_factory_recovery_report(factory, incidents)
    return {
        "scenario_id": "SCEN-04",
        "name": "Simultaneous Dual-Loom Breakdown (M1 + M3)",
        "factory": factory,
        "incidents": incidents,
        "report": report,
    }


if __name__ == "__main__":
    res = run_scenario()
    print(f"[{res['scenario_id']}] {res['name']}")
    print("Feasibility:", res["report"]["overall_feasibility"])
    print("Orders Saved:", res["report"]["orders_saved"], "| Orders At Risk:", res["report"]["orders_at_risk"])