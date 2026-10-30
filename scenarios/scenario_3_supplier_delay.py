"""
Scenario 3: Primary Supplier Delay + Machine Maintenance
- M1 enters 8h maintenance AND Primary Supplier (Gujarat Spinners) is delayed by +8h (20h ETA).
- Forces the engine to reroute to M2 AND switch to Backup Supplier (Surat Express Mills, 3h ETA).
"""
from scenarios import load_realistic_factory
from factory import simulate_machine_maintenance, simulate_supplier_delay
from recovery import generate_factory_recovery_report


def run_scenario():
    factory = load_realistic_factory()
    inc1 = simulate_machine_maintenance(factory, "M1", duration_hrs=8.0)
    inc2 = simulate_supplier_delay(factory, "SUP-PRIMARY", extra_delay_hrs=8.0)
    report = generate_factory_recovery_report(factory, [inc1, inc2])
    return {
        "scenario_id": "SCEN-03",
        "name": "Primary Supplier Delay (+8h) during M1 Maintenance",
        "factory": factory,
        "incidents": [inc1, inc2],
        "report": report,
    }


if __name__ == "__main__":
    res = run_scenario()
    print(f"[{res['scenario_id']}] {res['name']}")
    print("Orders Saved:", res["report"]["orders_saved"], "| Total Cost: $", res["report"]["total_recovery_cost"])