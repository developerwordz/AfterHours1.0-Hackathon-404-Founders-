
from agents import (
    machine_agent,
    inventory_agent,
    production_agent,
    sourcing_agent,
    verification_agent
)


def run_orchestrator(factory, incident):
    """
    Coordinates specialist agents to analyse a factory disruption.
    """

    print("\n===================================")
    print("       TEXRESQ ORCHESTRATOR")
    print("===================================")

    # Step 1: Machine Agent
    print("\n[1/5] Machine Agent analysing failure...")
    machine_report = machine_agent(factory, incident)

    # Step 2: Inventory Agent
    print("[2/5] Inventory Agent checking stock...")
    inventory_report = inventory_agent(factory, incident)

    # Step 3: Production Agent
    print("[3/5] Production Agent analysing affected orders...")
    production_report = production_agent(factory, incident)

    # Step 4: Sourcing Agent
    print("[4/5] Sourcing Agent checking suppliers...")
    sourcing_report = sourcing_agent(factory, incident)

    # Step 5: Combine reports
    print("[5/5] Combining agent reports...")

    analysis = {
        "machine_report": machine_report,
        "inventory_report": inventory_report,
        "production_report": production_report,
        "sourcing_report": sourcing_report
    }

    print("\nAnalysis completed successfully.")

    return analysis


def print_orchestrator_report(analysis):
    """Displays the combined analysis in a readable format."""

    print("\n========== FACTORY ANALYSIS ==========")

    for agent_key, report in analysis.items():
        print(f"\n{report['agent']}")
        print("-" * 35)

        for key, value in report.items():
            if key != "agent":
                print(f"{key}: {value}")

    print("\n======================================")
