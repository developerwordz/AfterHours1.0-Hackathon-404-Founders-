
import os
import json
import time

from dotenv import load_dotenv
from google import genai

from factory import (
    create_factory,
    simulate_machine_failure,
    get_factory_summary
)

from recovery import (
    generate_recovery_plan,
    generate_supplier_recovery_plan
)

from agents import (
    machine_agent,
    inventory_agent,
    production_agent,
    sourcing_agent,
    supplier_agent
)


load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL_NAME = "gemini-3.5-flash-lite"


# ============================================================
# 1. CREATE GEMINI TOOLS
# ============================================================


def create_factory_tools(factory, incident, execution_data):

    def record_event(agent_name, result):
        execution_data["events"].append({
            "agent": agent_name,
            "status": "Completed",
            "result": result
        })

    def get_factory_status() -> str:
        result = get_factory_summary(factory)
        record_event("Factory Inspector", result)
        return json.dumps(result, indent=2)

    def run_inventory_agent() -> str:
        result = inventory_agent(factory, incident)
        record_event("Inventory Agent", result)
        return json.dumps(result, indent=2)

    def run_sourcing_agent() -> str:
        result = sourcing_agent(factory, incident)
        record_event("Sourcing Agent", result)
        return json.dumps(result, indent=2)

    # MACHINE FAILURE TOOLS

    def run_machine_agent() -> str:
        result = machine_agent(factory, incident)
        record_event("Machine Agent", result)
        return json.dumps(result, indent=2)

    def run_production_agent() -> str:
        result = production_agent(factory, incident)
        record_event("Production Agent", result)
        return json.dumps(result, indent=2)

    def analyse_recovery_options() -> str:
        result = generate_recovery_plan(factory, incident)
        execution_data["recovery_report"] = result
        record_event(
            "Recovery Engine",
            {"message": "Machine recovery plans generated and ranked."}
        )
        return json.dumps(result, indent=2)

    # SUPPLIER FAILURE TOOLS

    def run_supplier_agent() -> str:
        result = supplier_agent(factory, incident)
        record_event("Supplier Agent", result)
        return json.dumps(result, indent=2)

    def analyse_supplier_impact() -> str:
        supplier_id = incident["supplier_id"]
        failed_supplier = factory["suppliers"][supplier_id]

        affected_materials = list(
            failed_supplier["cost_per_kg"].keys()
        )

        affected_orders = []

        for order_id, order in factory["orders"].items():
            if order.get("raw_material_id") in affected_materials:
                material_id = order["raw_material_id"]
                material = factory["raw_materials"][material_id]

                available_kg = (
                    material["stock_kg"] - material["reserved_kg"]
                )

                affected_orders.append({
                    "order_id": order_id,
                    "client": order["client"],
                    "material_id": material_id,
                    "remaining_quantity_m": order["remaining_quantity_m"],
                    "available_stock_kg": round(available_kg, 2),
                    "status": order["status"]
                })

        result = {
            "failed_supplier": failed_supplier["name"],
            "affected_materials": affected_materials,
            "potentially_affected_orders": affected_orders,
            "message": (
                f"Found {len(affected_orders)} orders using materials "
                f"previously supported by {failed_supplier['name']}."
            )
        }

        record_event("Supplier Impact Analyzer", result)
        return json.dumps(result, indent=2)
    
    def analyse_supplier_recovery_options() -> str:
        result = generate_supplier_recovery_plan(factory, incident)

        execution_data["recovery_report"] = result

        total_orders = result.get("orders_recovery", {})
        recovery_count = sum(
            1 for order in total_orders.values()
            if order.get("recommended_plan") is not None
        )

        record_event(
            "Supplier Recovery Engine",
            {
                "message": "Supplier recovery plans generated and ranked.",
                "orders_assessed": len(total_orders),
                "orders_with_recovery_options": recovery_count
            }
        )

        return json.dumps(result, indent=2)


    is_supplier_failure = (
        incident.get("incident_type") == "SUPPLIER_FAILURE"
        or "supplier_id" in incident
    )

    if is_supplier_failure:
        return [
            get_factory_status,
            run_inventory_agent,
            run_sourcing_agent,
            run_supplier_agent,
            analyse_supplier_impact,
            analyse_supplier_recovery_options
        ]

    return [
        get_factory_status,
        run_machine_agent,
        run_inventory_agent,
        run_production_agent,
        run_sourcing_agent,
        analyse_recovery_options
    ]




# ============================================================
# 2. GEMINI INCIDENT ANALYSIS
# ============================================================


def analyse_incident_with_gemini(factory, incident, recovery_report):

    is_supplier_failure = (
        incident.get("incident_type") == "SUPPLIER_FAILURE"
        or "supplier_id" in incident
    )

    if is_supplier_failure:
        incident_description = "A supplier has failed."
        recovery_description = "Supplier impact analysis and alternatives."
    else:
        incident_description = "A machine has failed."
        recovery_description = "Machine recovery plans."

    prompt = f"""
You are TexResQ, an AI textile factory operations orchestrator.

Analyse the factory disruption using the supplied Python engine results.

FACTORY STATUS:
{json.dumps(get_factory_summary(factory), indent=2)}

INCIDENT:
{json.dumps(incident, indent=2)}

ANALYSIS RESULTS:
{json.dumps(recovery_report, indent=2)}

INCIDENT TYPE:
{incident_description}

ANALYSIS TYPE:
{recovery_description}

STRICT RULES:
- Use only the supplied data.
- Do not invent numerical values.
- Python results are authoritative.
- Do not execute recovery plans.
- Clearly distinguish recommendations from completed actions.

Explain:
1. What happened.
2. Which factory resources and orders are affected.
3. What alternatives are available.
4. Whether current inventory protects production.
5. What action should be taken next.
6. Remaining risks.

Present a clear operations report.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text or "Gemini returned an empty analysis."



# ============================================================
# 3. DYNAMIC GEMINI ORCHESTRATOR
# ============================================================

def run_gemini_orchestrator(factory, incident):

    if factory is None:
        raise ValueError("A valid factory instance must be supplied.")

    if incident is None:
        raise ValueError("An active incident must be supplied.")

    execution_data = {
        "events": [],
        "recovery_report": None
    }

    tools = create_factory_tools(
        factory,
        incident,
        execution_data
    )

    chat = client.chats.create(
        model=MODEL_NAME,
        config={"tools": tools}
    )

    prompt = is_supplier_failure = (
        incident.get("incident_type") == "SUPPLIER_FAILURE"
        or "supplier_id" in incident
    )

    if is_supplier_failure:
        
        prompt = """
You are TexResQ, an intelligent textile factory resilience orchestrator.

A SUPPLIER FAILURE has occurred.

Investigate the disruption using your available Python tools.

Follow this investigation in order:

1. Inspect factory status.
2. Check raw material inventory.
3. Inspect the supplier network.
4. Run the Supplier Agent.
5. Run the Supplier Impact Analyzer.
6. Run the Supplier Recovery Engine.

The Supplier Recovery Engine is authoritative for:
- Material shortfalls.
- Alternative supplier feasibility.
- Supplier capacity.
- Delivery time.
- Procurement cost.
- Stock protection.
- Recommended recovery plans.

Then explain:

- Which supplier failed and its tier.
- Which materials it supplied.
- Which orders are affected.
- Which orders are protected by existing inventory.
- The shortfall for each affected order.
- Available replacement suppliers.
- Comparison of delivery time, reliability and cost.
- Recommended recovery plan for each order.
- Why the recommended supplier was selected.
- Remaining supply-chain risks.

STRICT RULES:

- Use only Python tool results.
- Do not invent numerical values.
- Python recovery results are authoritative.
- Do not call machine failure tools.
- Do not execute recovery plans.
- Do not claim a supplier has been switched.
- Do not claim procurement has occurred.
- Clearly distinguish recommendations from completed actions.
- If an order has no material shortfall, do not recommend unnecessary procurement.

Provide a concise, professional factory operations report.
"""


    else:
        prompt = """
You are TexResQ, an intelligent textile factory resilience orchestrator.

A MACHINE FAILURE has occurred.

Investigate the disruption and generate recovery recommendations.

Follow this investigation:
1. Inspect factory status.
2. Run the Machine Agent.
3. Check inventory and spare parts.
4. Run the Production Agent.
5. Run the Sourcing Agent.
6. Run the Recovery Engine.

Explain:
- Which machine failed.
- Which orders are affected.
- Material and spare-part constraints.
- Recovery options evaluated.
- Recommended recovery plan for each order.
- Deadline feasibility and additional costs.
- Remaining risks.

Rules:
- Use only Python tool results.
- Do not invent numerical values.
- Python recovery results are authoritative.
- Do not execute recovery plans.
- Do not claim actions succeeded without confirmation.

Provide a concise factory operations report.
"""



    print("\n========== TEXRESQ DYNAMIC ORCHESTRATOR ==========")

    start = time.perf_counter()

    response = chat.send_message(prompt)

    elapsed = time.perf_counter() - start

    analysis = response.text or str(response)

    print("\n========== GEMINI ORCHESTRATION REPORT ==========")
    print(analysis)
    print(f"\nOrchestration time: {elapsed:.2f} seconds")

    return {
        "analysis": analysis,
        "events": execution_data["events"],
        "recovery_report": execution_data["recovery_report"],
        "elapsed_seconds": round(elapsed, 2)
    }



# ============================================================
# 4. STANDALONE DEMONSTRATION
# ============================================================

def run_standalone_demo():

    factory = create_factory()

    incident = simulate_machine_failure(
        factory,
        "M1"
    )

    run_gemini_orchestrator(
        factory,
        incident
    )


if __name__ == "__main__":
    run_standalone_demo()
