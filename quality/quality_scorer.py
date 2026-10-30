"""
quality_scorer.py
TEXRESQ — Batch Quality Scoring Engine
"""

from datetime import datetime


# ============================================================
# QUALITY SCORING CONFIGURATION
# ============================================================

QUALITY_WEIGHTS = {
    "gsm_consistency": 0.25,
    "dimensional_accuracy": 0.20,
    "color_consistency": 0.15,
    "tensile_strength": 0.20,
    "defect_density": 0.20,
}


# ============================================================
# GRADE CLASSIFICATION
# ============================================================

def get_quality_grade(score: float) -> str:
    if score >= 95:
        return "A"
    elif score >= 90:
        return "B"
    elif score >= 80:
        return "C"
    elif score >= 70:
        return "D"
    else:
        return "F"


def get_quality_status(score: float) -> str:
    if score >= 85:
        return "PASSED"
    elif score >= 70:
        return "REVIEW_REQUIRED"
    else:
        return "REJECTED"


# ============================================================
# BATCH QUALITY SCORING
# ============================================================

def calculate_quality_score(
    batch_id: str,
    machine_id: str,
    fabric_type: str,
    metrics: dict,
) -> dict:

    """
    Calculates the overall quality score of a textile batch.

    All metrics must be normalized scores between 0 and 100.
    Higher scores always represent better quality.

    Returns a structured quality inspection report.
    """

    if not isinstance(metrics, dict):
        raise TypeError("Metrics must be provided as a dictionary.")

    missing_metrics = set(QUALITY_WEIGHTS) - set(metrics)

    if missing_metrics:
        raise ValueError(
            f"Missing quality metrics: {sorted(missing_metrics)}"
        )

    normalized_metrics = {}

    for metric, value in metrics.items():

        if metric not in QUALITY_WEIGHTS:
            continue

        if isinstance(value, bool):
            raise ValueError(f"{metric} must be numeric.")

        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{metric} must be numeric.")

        if not 0 <= value <= 100:
            raise ValueError(
                f"{metric} must be between 0 and 100."
            )

        normalized_metrics[metric] = value

    # Weighted quality calculation
    weighted_score = sum(
        normalized_metrics[metric] * weight
        for metric, weight in QUALITY_WEIGHTS.items()
    )

    final_score = round(weighted_score, 2)

    grade = get_quality_grade(final_score)
    status = get_quality_status(final_score)

    return {
        "batch_id": batch_id,
        "machine_id": machine_id,
        "fabric_type": fabric_type,

        "quality_score": final_score,
        "grade": grade,
        "inspection_status": status,

        "metrics": normalized_metrics,
        "weights": QUALITY_WEIGHTS.copy(),

        "inspection_timestamp": datetime.now().isoformat(
            timespec="seconds"
        ),
    }