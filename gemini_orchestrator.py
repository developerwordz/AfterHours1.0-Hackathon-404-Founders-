
import os
import json
import time

from dotenv import load_dotenv
from google import genai

from factory import create_factory, simulate_machine_failure, get_factory_summary
from recovery import generate_recovery_plan

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

factory = None
latest_incident = None


def get_factory_status() -> str:
    """Get the current factory status."""
    print("\n[TOOL CALLED] get_factory_status")

    return json.dumps(
        get_factory_summary(factory),
        indent=2
    )


def detect_machine_failure(machine_id: str) -> str:
    """Simulate a failure on a specified machine."""
    global latest_incident

    print(f"\n[TOOL CALLED] detect_machine_failure: {machine_id}")

    if machine_id not in factory["machines"]:
        return json.dumps({
            "error": f"Machine {machine_id} does not exist."
        })

    if factory["machines"][machine_id]["status"] == "FAILED":
        return json.dumps({
            "error": f"Machine {machine_id} has already failed."
        })

    latest_incident = simulate_machine_failure(factory, machine_id)

    return json.dumps(latest_incident, indent=2)


def analyse_recovery_options() -> str:
    """Generate and rank recovery plans for the latest disruption."""

    print("\n[TOOL CALLED] analyse_recovery_options")

    if latest_incident is None:
        return json.dumps({
            "error": "No machine failure has been detected yet."
        })

    recovery_report = generate_recovery_plan(
        factory,
        latest_incident
    )

    return json.dumps(recovery_report, indent=2)


def analyse_incident_with_gemini(factory, incident, recovery_report):

    prompt = f"""
    You are TexResQ, an AI textile factory operations orchestrator.

    Analyse this factory disruption using the supplied Python engine results.

    INCIDENT:
    {json.dumps(incident, indent=2)}

    RECOVERY ANALYSIS:
    {json.dumps(recovery_report, indent=2)}

    Explain:
    1. Which machine failed and which orders are affected.
    2. What recovery options were evaluated.
    3. Which plan is recommended for each affected order.
    4. Why the recommended plan was selected.
    5. Whether the deadline can be met.
    6. The additional cost.

    Use only the supplied data. Do not invent values.
    Do not execute any recovery plan.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    return response.text

def run_gemini_orchestrator():

    global factory, latest_incident

    # Start with a fresh factory for each demonstration.
    factory = create_factory()
    latest_incident = None

    chat = client.chats.create(
        model="gemini-3.5-flash-lite",
        config={
            "tools": [
                get_factory_status,
                detect_machine_failure,
                analyse_recovery_options
            ]
        }
    )

    prompt = """
    You are TexResQ, an AI textile factory operations orchestrator.

    The factory manager reports that machine M1 has failed.

    Follow this sequence:

    1. Call get_factory_status to inspect the factory.
    2. Call detect_machine_failure with machine_id M1.
    3. Call analyse_recovery_options to generate and rank recovery plans.

    Explain:
    - Which machine failed.
    - Which production orders are affected.
    - Which recovery options were evaluated.
    - Which plan is recommended and why.
    - Whether the recommended plan meets the deadline.
    - Its additional cost.

    Only use information returned by the Python tools.
    Do not execute any recovery plan.
    """

    print("\n========== TEXRESQ GEMINI ORCHESTRATOR ==========")

    start = time.perf_counter()

    response = chat.send_message(prompt)

    elapsed = time.perf_counter() - start

    print("\n========== GEMINI RECOVERY ANALYSIS ==========")

    if response.text:
        print(response.text)
    else:
        print(response)

    print(f"\nTotal orchestration time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    run_gemini_orchestrator()
