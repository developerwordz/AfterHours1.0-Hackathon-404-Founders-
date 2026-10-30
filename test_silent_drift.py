"""
test_silent_drift.py — Automated pytest suite for the "Silent Drift and the Deadline" hurdle.
"""

from factory import create_factory
from silent_drift import (
    detect_silent_drift,
    arbitrate_production_vs_quality,
    run_silent_drift_hurdle_demo,
)


def test_hint_1_silent_drift_inside_normal_limits():
    """
    Hint 1: Every individual reading is strictly inside normal limits (Temp <= 85C, Tension <= 120N),
    yet coupled drift is caught and predicts a defective batch (< 80 grade) within hours.
    """
    telemetry = [
        {"hour": 1, "temp_c": 68.0, "tension_n": 96.0},
        {"hour": 2, "temp_c": 71.0, "tension_n": 100.0},
        {"hour": 3, "temp_c": 74.0, "tension_n": 104.0},
        {"hour": 4, "temp_c": 77.0, "tension_n": 108.0},
        {"hour": 5, "temp_c": 79.5, "tension_n": 111.5},
        {"hour": 6, "temp_c": 82.0, "tension_n": 115.0},
    ]
    res = detect_silent_drift(telemetry, machine_id="M1")

    assert res["all_readings_within_normal_limits"] is True
    assert res["silent_drift_detected"] is True
    assert res["joint_correlation"] > 0.95
    assert res["projected_grade_in_3h"] < 80.0
    assert res["hours_until_defective_batch"] <= 3.0


def test_hint_2_rule_based_arbitration_and_flip_on_new_data():
    """
    Hint 2: Production wants to SHIP and Quality wants to HOLD.
    The rule settles the conflict in favor of Quality under high silent drift,
    and automatically flips to Production when new data changes the risk-cost balance.
    """
    demo = run_silent_drift_hurdle_demo()

    # Phase 1: High coupled drift -> Quality (HOLD_AND_RECALIBRATE) wins
    arb_1 = demo["phase_1_silent_drift"]["arbitration"]
    assert arb_1["agent_a_production"]["vote"] == "CONTINUE_AND_SHIP"
    assert arb_1["agent_b_quality"]["vote"] == "HOLD_AND_RECALIBRATE"
    assert arb_1["winning_decision"] == "HOLD_AND_RECALIBRATE"

    # Phase 2: New stabilized telemetry arrives -> Flips to Production (CONTINUE_AND_SHIP)
    arb_2 = demo["phase_2_new_data_flip"]["arbitration"]
    assert arb_2["winning_decision"] == "CONTINUE_AND_SHIP"


def test_hint_3_counterfactual_flip_threshold_accuracy():
    """
    Hint 3: Manager can see why the call went one way and the exact threshold that would flip it.
    Verifies that crossing the reported flip threshold actually flips the decision!
    """
    f = create_factory()
    f["orders"]["ORD-101"]["deadline_hrs"] = 11.5  # 2.5h hold causes 1.0h late delivery

    telemetry = [
        {"hour": 1, "temp_c": 68.0, "tension_n": 96.0},
        {"hour": 2, "temp_c": 71.0, "tension_n": 100.0},
        {"hour": 3, "temp_c": 74.0, "tension_n": 104.0},
        {"hour": 4, "temp_c": 77.0, "tension_n": 108.0},
        {"hour": 5, "temp_c": 79.5, "tension_n": 111.5},
        {"hour": 6, "temp_c": 82.0, "tension_n": 115.0},
    ]
    drift = detect_silent_drift(telemetry, machine_id="M1")
    arb = arbitrate_production_vs_quality(f, "ORD-101", drift)

    # Initially Quality wins
    assert arb["winning_decision"] == "HOLD_AND_RECALIBRATE"
    assert "why_call_went_this_way" in arb["manager_explanation"]
    assert "what_would_have_flipped_it" in arb["manager_explanation"]

    # Extract the exact counterfactual penalty flip threshold reported to the manager
    flip_penalty = arb["counterfactual_flip_thresholds"]["late_penalty_per_hr_flip_threshold_usd"]
    assert flip_penalty is not None

    # Now set the order's late penalty slightly ABOVE that exact counterfactual flip threshold
    f["orders"]["ORD-101"]["penalty_per_hr_late"] = flip_penalty + 50.0
    arb_flipped = arbitrate_production_vs_quality(f, "ORD-101", drift)

    # Decision must flip to CONTINUE_AND_SHIP!
    assert arb_flipped["winning_decision"] == "CONTINUE_AND_SHIP"