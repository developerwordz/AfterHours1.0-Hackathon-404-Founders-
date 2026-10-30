
"""
quality_agent.py
TEXRESQ — Autonomous Quality Corrective Agent

Analyzes monitoring alerts, selects corrective actions,
applies simulated maintenance, and records interventions.
"""

from datetime import datetime

from quality.quality_monitor import analyze_machine_quality
from factory import apply_machine_quality_maintenance


# ============================================================
# AGENT CONFIGURATION
# ============================================================

MINIMUM_WEAR_FOR_MAINTENANCE = 16.0
CRITICAL_SCORE_THRESHOLD = 70.0


# ============================================================
# ROOT CAUSE ANALYSIS
# ============================================================

def identify_quality_problem(report: dict) -> dict:
    """
    Identifies the most affected quality metric.

    This is rule-based diagnosis using simulated measurements.
    It does not claim to identify a physical fault with certainty.
    """

    problem_metrics = report.get("problem_metrics", [])

    if not problem_metrics:
        return {
            "primary_problem": "GENERAL_QUALITY_DECLINE",
            "description": (
                "Overall quality has declined without one "
                "dominant metric being identified."
            ),
        }

    # Select metric with the greatest deterioration
    worst_metric = max(
        problem_metrics,
        key=lambda item: item["decline"]
    )

    descriptions = {
        "gsm_consistency": (
            "Fabric weight consistency is deteriorating."
        ),

        "dimensional_accuracy": (
            "Fabric dimensional accuracy is deteriorating."
        ),

        "color_consistency": (
            "Fabric colour consistency is deteriorating."
        ),

        "tensile_strength": (
            "Fabric tensile strength is deteriorating."
        ),

        "defect_density": (
            "The normalized defect-quality score is deteriorating."
        ),
    }

    return {
        "primary_problem": worst_metric["metric"],
        "description": descriptions.get(
            worst_metric["metric"],
            "A quality metric is deteriorating."
        ),
        "decline": worst_metric["decline"],
        "baseline": worst_metric["baseline"],
        "recent": worst_metric["recent"],
    }


# ============================================================
# CORRECTIVE ACTION SELECTION
# ============================================================

def select_corrective_action(
    report: dict,
    diagnosis: dict
) -> dict:
    """
    Selects a corrective action based on quality deterioration
    and the machine's simulated condition.

    Current available intervention:
    - Simulated quality maintenance.

    More specific actions can be introduced as the simulation
    gains additional process controls and telemetry.
    """

    machine_wear = report.get("machine_wear", 0)
    latest_score = report.get("latest_quality_score", 100)

    if (
        machine_wear >= MINIMUM_WEAR_FOR_MAINTENANCE
        or latest_score < CRITICAL_SCORE_THRESHOLD
        or report["severity"] == "CRITICAL"
    ):

        return {
            "action": "QUALITY_MAINTENANCE",
            "reason": (
                f"Quality deterioration detected. "
                f"Machine wear is {machine_wear}% and "
                f"latest quality score is {latest_score}."
            ),
            "automatic": True,
        }

    # For a mild issue, request additional monitoring
    return {
        "action": "INCREASED_MONITORING",
        "reason": (
            "Quality deterioration requires observation, "
            "but current conditions do not justify maintenance."
        ),
        "automatic": False,
    }


# ============================================================
# PROCESS QUALITY ALERT
# ============================================================

def process_quality_alert(
    factory: dict,
    machine_id: str
) -> dict:
    """
    Main entry point for the autonomous quality agent.

    Workflow:
    1. Analyze machine quality.
    2. Check whether an alert exists.
    3. Diagnose the quality problem.
    4. Select a corrective action.
    5. Apply the action when appropriate.
    6. Record the decision and intervention.
    """

    # --------------------------------------------------------
    # 1. Analyze quality
    # --------------------------------------------------------

    report = analyze_machine_quality(
        factory,
        machine_id
    )

    if report["analysis_status"] == "INSUFFICIENT_DATA":
        return {
            "agent_status": "WAITING_FOR_DATA",
            "machine_id": machine_id,
            "message": report["message"],
        }

    # --------------------------------------------------------
    # 2. No quality alert
    # --------------------------------------------------------

    if not report["alert"]:
        return {
            "agent_status": "HEALTHY",
            "machine_id": machine_id,
            "message": report["message"],
            "quality_score": report["latest_quality_score"],
        }

    # --------------------------------------------------------
    # 3. Prevent duplicate interventions for the same batch
    # --------------------------------------------------------

    latest_batch_id = report["latest_batch_id"]

    previous_intervention = next(
        (
            intervention
            for intervention in factory.get(
                "quality_interventions", []
            )
            if (
                intervention.get("machine_id") == machine_id
                and intervention.get("triggering_batch_id")
                == latest_batch_id
            )
        ),
        None
    )

    if previous_intervention:
        return {
            "agent_status": "ALREADY_PROCESSED",
            "machine_id": machine_id,
            "triggering_batch_id": latest_batch_id,
            "message": (
                "This batch has already triggered a "
                "quality intervention."
            ),
            "intervention": previous_intervention,
        }

    # --------------------------------------------------------
    # 4. Diagnose quality problem
    # --------------------------------------------------------

    diagnosis = identify_quality_problem(report)

    # --------------------------------------------------------
    # 5. Select corrective action
    # --------------------------------------------------------

    decision = select_corrective_action(
        report,
        diagnosis
    )

    # --------------------------------------------------------
    # 6. Apply corrective action
    # --------------------------------------------------------

    intervention = None

    if decision["action"] == "QUALITY_MAINTENANCE":

        intervention = apply_machine_quality_maintenance(
            factory,
            machine_id,
            reason=decision["reason"]
        )

        intervention["triggering_batch_id"] = latest_batch_id
        intervention["diagnosis"] = diagnosis
        intervention["severity"] = report["severity"]

        intervention["agent_decision"] = decision

    # --------------------------------------------------------
    # 7. Return agent report
    # --------------------------------------------------------

    return {
        "agent_status": (
            "ACTION_APPLIED"
            if intervention
            else "MONITORING_REQUIRED"
        ),

        "machine_id": machine_id,
        "machine_name": report["machine_name"],

        "triggering_batch_id": latest_batch_id,

        "quality_analysis": report,
        "diagnosis": diagnosis,
        "decision": decision,

        "intervention": intervention,

        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),

        "message": (
            "Corrective maintenance successfully simulated."
            if intervention
            else "Agent recommends continued monitoring."
        ),
    }


# ============================================================
# FACTORY-WIDE AGENT EXECUTION
# ============================================================

def run_quality_agent(factory: dict) -> dict:
    """
    Runs the quality agent against all factory machines.
    """

    results = []

    for machine_id in factory["machines"]:

        result = process_quality_alert(
            factory,
            machine_id
        )

        results.append(result)

    actions_applied = sum(
        1 for result in results
        if result["agent_status"] == "ACTION_APPLIED"
    )

    return {
        "timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),

        "machines_processed": len(results),
        "actions_applied": actions_applied,
        "agent_results": results,
    }
