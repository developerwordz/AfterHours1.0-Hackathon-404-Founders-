
from quality.quality_scorer import QUALITY_WEIGHTS


MIN_BATCHES_REQUIRED = 4
DECLINE_THRESHOLD = 4.0
CRITICAL_QUALITY_SCORE = 85.0

QUALITY_METRICS = list(QUALITY_WEIGHTS.keys())


def get_latest_intervention(factory, machine_id):
    """Find the most recent quality maintenance intervention for a machine."""

    interventions = [
        intervention
        for intervention in factory.get("quality_interventions", [])
        if intervention.get("machine_id") == machine_id
        and intervention.get("action") == "QUALITY_MAINTENANCE"
    ]

    if not interventions:
        return None

    return interventions[-1]


def get_batches_after_maintenance(factory, machine_id):
    """
    Return batches produced after the machine's latest maintenance.

    The batch that triggered maintenance is excluded.
    """

    history = [
        batch
        for batch in factory.get("quality_history", [])
        if batch.get("machine_id") == machine_id
    ]

    # No maintenance has occurred. Use the complete history.
    intervention = get_latest_intervention(factory, machine_id)

    if intervention is None:
        return history

    triggering_batch_id = intervention.get("triggering_batch_id")

    if not triggering_batch_id:
        return history

    # Find the batch that triggered the maintenance.
    triggering_index = next(
        (
            index
            for index, batch in enumerate(history)
            if batch.get("batch_id") == triggering_batch_id
        ),
        None
    )

    if triggering_index is None:
        return history

    # Only evaluate batches produced after maintenance.
    return history[triggering_index + 1:]


def calculate_metric_trends(batches):
    """Compare the first two batches against the latest three batches."""

    baseline_batches = batches[:2]
    recent_batches = batches[-3:]

    problem_metrics = []
    metric_trends = {}

    for metric in QUALITY_METRICS:

        baseline_values = [
            batch["metrics"][metric]
            for batch in baseline_batches
        ]

        recent_values = [
            batch["metrics"][metric]
            for batch in recent_batches
        ]

        baseline_average = sum(baseline_values) / len(baseline_values)
        recent_average = sum(recent_values) / len(recent_values)

        decline = round(baseline_average - recent_average, 2)

        metric_trends[metric] = {
            "baseline": round(baseline_average, 2),
            "recent": round(recent_average, 2),
            "decline": decline,
        }

        if decline >= DECLINE_THRESHOLD:
            problem_metrics.append({
                "metric": metric,
                "baseline": round(baseline_average, 2),
                "recent": round(recent_average, 2),
                "decline": decline,
            })

    return metric_trends, problem_metrics


def analyze_machine_quality(factory, machine_id):
    """Analyze quality trends for one machine."""

    machines = factory.get("machines", {})

    if machine_id not in machines:
        raise ValueError(f"Machine {machine_id} does not exist.")

    machine = machines[machine_id]

    # IMPORTANT: Analyze only batches after the latest maintenance.
    batches = get_batches_after_maintenance(factory, machine_id)

    batches.sort(
        key=lambda batch: batch.get(
            "machine_batch_number",
            int(batch.get("batch_id", "BAT-0").split("-")[-1])
        )
    )

    latest_intervention = get_latest_intervention(factory, machine_id)

    latest_score = (
        batches[-1].get("quality_score")
        if batches else None
    )

    base_report = {
        "machine_id": machine_id,
        "machine_name": machine.get("name", machine_id),
        "batches_analyzed": len(batches),
        "latest_score": latest_score,
        "machine_wear": machine.get("wear_level", 0),
        "machine_condition": machine.get("condition_score", 100),
        "latest_intervention": latest_intervention,
        "problem_metrics": [],
        "metric_trends": {},
        "baseline_average": None,
        "recent_average": None,
        "score_decline": 0,
        "alert": False,
        "analysis_status": "ANALYZED",
        "latest_batch_id": batches[-1].get("batch_id") if batches else None,
        "alert": False,
    }

    # Not enough post-maintenance data to evaluate a trend.
    if len(batches) < MIN_BATCHES_REQUIRED:

        return {
    **base_report,
    "status": "INSUFFICIENT_DATA",
    "analysis_status": "INSUFFICIENT_DATA",
    "severity": "INSUFFICIENT_DATA",
    "alert": False,
    "message": (
        f"Waiting for {MIN_BATCHES_REQUIRED - len(batches)} "
        "more batch(es) before evaluating quality trends."
    ),
}

    baseline_batches = batches[:2]
    recent_batches = batches[-3:]

    baseline_average = sum(
        batch["quality_score"]
        for batch in baseline_batches
    ) / len(baseline_batches)

    recent_average = sum(
        batch["quality_score"]
        for batch in recent_batches
    ) / len(recent_batches)

    score_decline = round(
        baseline_average - recent_average,
        2
    )

    metric_trends, problem_metrics = calculate_metric_trends(batches)

    # Determine whether quality deterioration is occurring.
    alert = (
        recent_batches[-1]["quality_score"] < CRITICAL_QUALITY_SCORE
        or score_decline >= DECLINE_THRESHOLD
        or len(problem_metrics) > 0
    )

    latest_batch_score = recent_batches[-1]["quality_score"]

    if latest_batch_score < 70 or score_decline >= 12:
        severity = "CRITICAL"

    elif latest_batch_score < 85 or score_decline >= 8:
        severity = "HIGH"

    elif alert:
        severity = "MEDIUM"

    else:
        severity = "NORMAL"

    return {
        **base_report,
        "status": "ALERT" if alert else "HEALTHY",
        "severity": severity,
        "alert": alert,
        "baseline_average": round(baseline_average, 2),
        "recent_average": round(recent_average, 2),
        "score_decline": score_decline,
        "problem_metrics": problem_metrics,
        "metric_trends": metric_trends,
        "latest_score": latest_batch_score,
        "message": (
            "Quality deterioration detected."
            if alert
            else "Machine quality is within acceptable limits."
        ),
    }


def monitor_factory_quality(factory):
    """Monitor quality across all factory machines."""

    machines = factory.get("machines", {})

    reports = []
    alerts = []

    for machine_id in machines:

        report = analyze_machine_quality(factory, machine_id)

        reports.append(report)

        if report["alert"]:
            alerts.append(report)

    machines_with_insufficient_data = sum(
        1
        for report in reports
        if report["status"] == "INSUFFICIENT_DATA"
    )

    if alerts:
        factory_status = "ATTENTION_REQUIRED"

    elif machines_with_insufficient_data == len(reports):
        factory_status = "MONITORING"

    else:
        factory_status = "HEALTHY"

    return {
        "machines_analyzed": len(reports),
        "machines_with_alerts": len(alerts),
        "machines_with_insufficient_data": machines_with_insufficient_data,
        "factory_quality_status": factory_status,
        "reports": reports,
        "alerts": alerts,
        "analysis_status": "ANALYZED",
    }
