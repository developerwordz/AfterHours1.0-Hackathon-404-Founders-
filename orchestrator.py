from agents import (
    machine_agent,
    inventory_agent,
    production_agent,
    sourcing_agent,
    verification_agent
)

from recovery import (
    generate_recovery_plan,
    apply_recovery_plan
)


def run_orchestrator(factory, incident):
    """Analyse a factory disruption and generate recovery recommendations."""

    print("\n===================================")
    print("       TEXRESQ ORCHESTRATOR")
    print("===================================")

    print("\n[1/5] Machine Agent analysing failure...")
    machine_report = machine_agent(factory, incident)

    print("[2/5] Inventory Agent checking materials...")
    inventory_report = inventory_agent(factory, incident)

    print("[3/5] Production Agent analysing affected orders...")
    production_report = production_agent(factory, incident)

    print("[4/5] Sourcing Agent checking suppliers...")
    sourcing_report = sourcing_agent(factory, incident)

    print("[5/5] Recovery Engine generating and evaluating plans...")
    recovery_report = generate_recovery_plan(factory, incident)

    analysis = {
        "incident": incident,
        "machine_report": machine_report,
        "inventory_report": inventory_report,
        "production_report": production_report,
        "sourcing_report": sourcing_report,
        "recovery_report": recovery_report
    }

    print("\nAnalysis and recovery planning completed.")

    return analysis


def execute_approved_plan(factory, plan):
    """Execute a feasible plan after human approval, then verify the result."""

    if not plan.get("feasible", False):
        raise ValueError("Cannot execute an infeasible recovery plan.")

    print(f"\nExecuting approved plan: {plan['plan_id']}")

    receipt = apply_recovery_plan(factory, plan)

    print("Recovery action applied.")
    print("Running verification...")

    verification = verification_agent(factory, plan["order_id"])

    return {
        "execution_receipt": receipt,
        "verification": verification
    }


def print_orchestrator_report(analysis):
    print("\n========== TEXRESQ ANALYSIS ==========")

    for key in (
        "machine_report",
        "inventory_report",
        "production_report",
        "sourcing_report"
    ):
        report = analysis[key]

        print(f"\n{report['agent']}")
        print("-" * 40)

        for field, value in report.items():
            if field != "agent":
                print(f"{field}: {value}")

    print("\n========== RECOVERY RECOMMENDATIONS ==========")

    recovery = analysis["recovery_report"]

    for order_id, result in recovery["orders_recovery"].items():
        print(f"\nOrder: {order_id}")
        print(result["honest_assessment"])

        for index, plan in enumerate(result["ranked_plans"], start=1):
            print(
                f"\n{index}. {plan['plan_id']} — {plan['name']}"
            )
            print(f"   Feasible: {plan['feasible']}")
            print(f"   Meets deadline: {plan['meets_deadline']}")
            print(f"   Completion: {plan['total_time_hrs']} hours")
            print(f"   Additional cost: ${plan['additional_cost_usd']}")
            print(f"   Notes: {plan['evaluation_notes']}")

    print("\n==============================================")