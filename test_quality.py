
from factory import (
    create_factory,
    simulate_batch_production,
)

from quality.quality_monitor import (
    analyze_machine_quality,
    monitor_factory_quality,
)

from quality.quality_agent import (
    process_quality_alert,
    run_quality_agent,
)


factory = create_factory()


# ============================================================
# STEP 1: GENERATE PRODUCTION BATCHES
# ============================================================

print("\n========== PRODUCTION SIMULATION ==========")

for i in range(8):

    report = simulate_batch_production(factory, "M1")

    print(
        f"{report['batch_id']} | "
        f"Score: {report['quality_score']} | "
        f"Grade: {report['grade']} | "
        f"Wear: {report['machine_wear_after']}%"
    )


# ============================================================
# STEP 2: RUN QUALITY MONITOR
# ============================================================

print("\n========== QUALITY MONITOR ==========")

monitor_report = analyze_machine_quality(
    factory,
    "M1"
)

print("Machine:", monitor_report["machine_name"])
print("Alert:", monitor_report["alert"])
print("Severity:", monitor_report.get("severity"))
print("Baseline:", monitor_report.get("baseline_quality_score"))
print("Recent Average:", monitor_report.get("recent_quality_score"))
print("Decline:", monitor_report.get("quality_score_decline"))
print("Problem Metrics:", monitor_report.get("problem_metrics"))


# ============================================================
# STEP 3: RUN CORRECTIVE AGENT
# ============================================================

print("\n========== QUALITY AGENT ==========")

agent_result = process_quality_alert(
    factory,
    "M1"
)

print("Agent Status:", agent_result["agent_status"])
print("Message:", agent_result["message"])

if agent_result.get("diagnosis"):
    print("Diagnosis:", agent_result["diagnosis"])

if agent_result.get("decision"):
    print("Decision:", agent_result["decision"])

if agent_result.get("intervention"):
    print("Intervention:", agent_result["intervention"])


# ============================================================
# STEP 4: PRODUCE A NEW BATCH AFTER MAINTENANCE
# ============================================================

if agent_result["agent_status"] == "ACTION_APPLIED":

    print("\n========== POST-MAINTENANCE VERIFICATION ==========")

    new_batch = simulate_batch_production(
        factory,
        "M1"
    )

    print("New Batch:", new_batch["batch_id"])
    print("New Quality Score:", new_batch["quality_score"])
    print("New Grade:", new_batch["grade"])
    print("Machine Wear:", new_batch["machine_wear_before"])
    print("Machine Condition:", new_batch["machine_condition_before"])


# ============================================================
# STEP 5: FACTORY-WIDE MONITORING
# ============================================================

print("\n========== FACTORY QUALITY SUMMARY ==========")

summary = monitor_factory_quality(factory)

print("Machines Analyzed:", summary["machines_analyzed"])
print("Machines With Alerts:", summary["machines_with_alerts"])
print("Factory Quality Status:", summary["factory_quality_status"])

print("\n========== TEST COMPLETE ==========")
