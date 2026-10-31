
from quality.quality_scorer import QUALITY_WEIGHTS


MIN_BATCHES_REQUIRED = 4
DECLINE_THRESHOLD = 4.0
CRITICAL_QUALITY_SCORE = 85.0

QUALITY_METRICS = list(QUALITY_WEIGHTS.keys())


def get_latest_intervention(factory, machine_id):
    """Find the most recent quality maintenance intervention."""

    interventions = [
        intervention
        for intervention in factory.get("quality_interventions", [])
        if intervention.get("machine_id") == machine_id
        and intervention.get("action") == "QUALITY_MAINTENANCE"
    ]

    return interventions[-1] if interventions else None


def get_batches_after_maintenance(factory, machine_id):
    """Return batches produced after the latest maintenance."""

    history = [
        batch
        for batch in factory.get("quality_history", [])
        if batch.get("machine_id") == machine_id
    ]

    intervention = get_latest_intervention(factory, machine_id)

    if intervention is None:
        return history

    triggering_batch_id = intervention.get("triggering_batch_id")

    if not triggering_batch_id:
        return history

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

    return history[triggering_index + 1:]


def get_batch_metrics(batch):
    """
    Safely retrieve metrics from a batch.

    Supports both 'metrics' and 'quality_metrics'.
    Returns None if the batch does not contain all required metrics.
    """

    metrics = batch.get("metrics")

    if not isinstance(metrics, dict):
        metrics = batch.get("quality_metrics")

    if not isinstance(metrics, dict):
        return None

    cleaned_metrics = {}

    for metric in QUALITY_METRICS:
        value = metrics.get(metric)

        if value is None:
            return None

        try:
            cleaned_metrics[metric] = float(value)
        except (TypeError, ValueError):
            return None

    return cleaned_metrics


def get_batch_sort_key(batch):
    """Sort batches safely by their machine batch number."""

    batch_number = batch.get("machine_batch_number")

    if batch_number is not None:
        try:
            return int(batch_number)
        except (TypeError, ValueError):
            pass

    batch_id = str(batch.get("batch_id", "BAT-0"))

    try:
        return int(batch_id.split("-")[-1])
    except (ValueError, IndexError):
        return 0


def calculate_metric_trends(batches):
    """Compare the first two batches against the latest three."""

    baseline_batches = batches[:2]
    recent_batches = batches[-3:]

    problem_metrics = []
    metric_trends = {}

    for metric in QUALITY_METRICS:

        baseline_values = [
            get_batch_metrics(batch)[metric]
            for batch in baseline_batches
        ]

        recent_values = [
            get_batch_metrics(batch)[metric]
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

    all_batches = get_batches_after_maintenance(factory, machine_id)

    all_batches.sort(key=get_batch_sort_key)

    # Keep only batches containing every required quality metric.
    # Older or incomplete batches are safely ignored.
    batches = [
        batch
        for batch in all_batches
        if get_batch_metrics(batch) is not None
        and batch.get("quality_score") is not None
    ]

    latest_intervention = get_latest_intervention(factory, machine_id)

    base_report = {
        "machine_id": machine_id,
        "machine_name": machine.get("name", machine_id),
        "batches_analyzed": len(batches),
        "latest_score": (
            batches[-1].get("quality_score") if batches else None
        ),
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
        "latest_batch_id": (
            batches[-1].get("batch_id") if batches else None
        ),
    }

    # Not enough valid batches to calculate trends.
    if len(batches) < MIN_BATCHES_REQUIRED:
        missing = MIN_BATCHES_REQUIRED - len(batches)

        return {
            **base_report,
            "status": "INSUFFICIENT_DATA",
            "analysis_status": "INSUFFICIENT_DATA",
            "severity": "INSUFFICIENT_DATA",
            "alert": False,
            "message": (
                f"Waiting for {missing} more valid batch(es) "
                "before evaluating quality trends."
            ),
        }

    baseline_batches = batches[:2]
    recent_batches = batches[-3:]

    baseline_average = sum(
        float(batch["quality_score"])
        for batch in baseline_batches
    ) / len(baseline_batches)

    recent_average = sum(
        float(batch["quality_score"])
        for batch in recent_batches
    ) / len(recent_batches)

    score_decline = round(
        baseline_average - recent_average,
        2
    )

    metric_trends, problem_metrics = calculate_metric_trends(batches)

    latest_batch_score = float(recent_batches[-1]["quality_score"])

    alert = (
        latest_batch_score < CRITICAL_QUALITY_SCORE
        or score_decline >= DECLINE_THRESHOLD
        or len(problem_metrics) > 0
    )

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
        "analysis_status": "ANALYZED",
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

    elif (
        reports
        and machines_with_insufficient_data == len(reports)
    ):
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
