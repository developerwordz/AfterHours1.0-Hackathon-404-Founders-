"""
Scenario 2: Raw Material Shortage (Quality Rejection on Cotton Yarn Batch)
- Warehouse stock of RM-COTTON drops from 400kg to 150kg due to moisture damage.
- M1 is still healthy (60m/hr), but ORD-101 now has a 450kg material shortfall.
"""
from scenarios import load_realistic_factory
from factory import simulate_raw_material_shortage
from recovery import generate_factory_recovery_report


def run_scenario():
    factory = load_realistic_factory()
    incident = simulate_raw_material_shortage(factory, "RM-COTTON", new_stock_kg=150.0)
    report = generate_factory_recovery_report(factory, [incident])
    return {
        "scenario_id": "SCEN-02",
        "name": "Raw Material Shortage (Cotton Stock Drop to 150kg)",
        "factory": factory,
        "incidents": [incident],
        "report": report,
    }


if __name__ == "__main__":
    res = run_scenario()
    print(f"[{res['scenario_id']}] {res['name']}")
    print("Orders Saved:", res["report"]["orders_saved"], "| Total Cost: $", res["report"]["total_recovery_cost"])