"""
silent_drift.py — Hurdle Solution: "Silent Drift and the Deadline"
Zero-modification add-on module compatible with factory.py & recovery.py.

Solves:
- Hint 1: Multivariate silent drift detection (every individual reading is inside normal limits,
          but joint temperature + tension trajectory predicts a defective batch within hours).
- Hint 2: Rule-based conflict arbitration between Agent A (Production: SHIP) and
          Agent B (Quality: HOLD), which dynamically flips when new telemetry/order data arrives.
- Hint 3: Manager explainability with exact counterfactual flip thresholds ("what would have flipped it").
"""

from copy import deepcopy
from datetime import datetime
from factory import create_factory, simulate_machine_maintenance
from recovery import generate_factory_recovery_report


# Normal individual operating limits (Single-variable threshold alarms NEVER fire inside these bounds)
NORMAL_LIMITS = {
    "temp_c": {"min": 45.0, "max": 85.0},      # Alarm only fires if temp_c > 85.0°C
    "tension_n": {"min": 70.0, "max": 120.0},  # Alarm only fires if tension_n > 120.0 N
}


def _linear_slope(values: list) -> float:
    """Calculates rate of change per hour using ordinary least squares over time steps t = 0..n-1."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    num = sum((i - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((i - mean_x) ** 2 for i in range(n))
    return round(num / den, 3) if den != 0 else 0.0


def _pearson_correlation(xs: list, ys: list) -> float:
    """Calculates Pearson correlation between two sensor streams."""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx, my = sum(xs[:n]) / n, sum(ys[:n]) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    den_x = sum((xs[i] - mx) ** 2 for i in range(n)) ** 0.5
    den_y = sum((ys[i] - my) ** 2 for i in range(n)) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 3)


def detect_silent_drift(
    telemetry_window: list,
    machine_id: str = "M1",
    horizon_hrs: float = 3.0,
) -> dict:
    """
    HINT 1: Detects coupled multivariate sensor drift when EVERY individual reading
    is strictly within its normal limit.

    Physical Textile Model:
    - Normalized Temperature Stress: S_temp = (temp_c - 65) / (85 - 65)
    - Normalized Tension Stress:     S_tens = (tension_n - 90) / (120 - 90)
    - Coupled Thermo-Mechanical Drift Index (CDI):
      CDI = 0.5 * S_temp + 0.5 * S_tens + 0.35 * (S_temp * S_tens)
    - Predicted Batch Quality Grade = 98.0 - 22.0 * CDI
      (When CDI > 0.818, predicted batch grade drops below 80.0 -> Defective Batch!)
    """
    temps = [pt["temp_c"] for pt in telemetry_window]
    tensions = [pt["tension_n"] for pt in telemetry_window]

    # Verify whether every single reading is inside normal individual limits
    all_temps_normal = all(NORMAL_LIMITS["temp_c"]["min"] <= t <= NORMAL_LIMITS["temp_c"]["max"] for t in temps)
    all_tens_normal = all(NORMAL_LIMITS["tension_n"]["min"] <= k <= NORMAL_LIMITS["tension_n"]["max"] for k in tensions)
    all_readings_within_normal_limits = bool(all_temps_normal and all_tens_normal)

    temp_slope = _linear_slope(temps)
    tens_slope = _linear_slope(tensions)
    correlation = _pearson_correlation(temps, tensions)

    # Current and Projected Values over `horizon_hrs`
    curr_temp, curr_tens = temps[-1], tensions[-1]
    proj_temp = round(curr_temp + temp_slope * horizon_hrs, 2)
    proj_tens = round(curr_tens + tens_slope * horizon_hrs, 2)

    def calc_cdi_and_grade(t_val, k_val):
        s_t = max(0.0, (t_val - 65.0) / 20.0)
        s_k = max(0.0, (k_val - 90.0) / 30.0)
        cdi = round(0.5 * s_t + 0.5 * s_k + 0.35 * (s_t * s_k), 3)
        pred_grade = round(max(0.0, 98.0 - 22.0 * cdi), 2)
        return cdi, pred_grade

    curr_cdi, curr_pred_grade = calc_cdi_and_grade(curr_temp, curr_tens)
    proj_cdi, proj_pred_grade = calc_cdi_and_grade(proj_temp, proj_tens)

    # Estimate hours until batch grade crosses the 80.0 defect threshold
    grade_drop_rate_per_hr = round((curr_pred_grade - proj_pred_grade) / horizon_hrs, 3) if horizon_hrs > 0 else 0.0
    if curr_pred_grade <= 80.0:
        hrs_to_defect = 0.0
    elif grade_drop_rate_per_hr > 0:
        hrs_to_defect = round((curr_pred_grade - 80.0) / grade_drop_rate_per_hr, 2)
    else:
        hrs_to_defect = float("inf")

    # Defect probability within the production window (0.0 to 0.98)
    silent_drift_detected = bool(
        temp_slope > 0.5
        and tens_slope > 0.5
        and correlation >= 0.75
        and (proj_pred_grade < 80.0 or hrs_to_defect <= 4.0)
    )

    if silent_drift_detected:
        defect_probability = round(min(0.95, max(0.50, (85.0 - proj_pred_grade) / 15.0)), 3)
    else:
        defect_probability = round(min(0.45, max(0.05, (82.0 - proj_pred_grade) / 25.0)), 3)

    return {
        "machine_id": machine_id,
        "all_readings_within_normal_limits": all_readings_within_normal_limits,
        "normal_limits_reference": NORMAL_LIMITS,
        "latest_reading": {"temp_c": curr_temp, "tension_n": curr_tens},
        "temp_drift_slope_c_per_hr": temp_slope,
        "tension_drift_slope_n_per_hr": tens_slope,
        "joint_correlation": correlation,
        "current_coupled_drift_index": curr_cdi,
        "projected_coupled_drift_index_3h": proj_cdi,
        "current_estimated_grade": curr_pred_grade,
        "projected_grade_in_3h": proj_pred_grade,
        "hours_until_defective_batch": hrs_to_defect,
        "defect_probability": defect_probability,
        "silent_drift_detected": silent_drift_detected,
        "diagnosis": (
            f"SILENT DRIFT DETECTED on {machine_id}: Every reading is inside normal limits "
            f"({curr_temp}°C <= 85°C, {curr_tens}N <= 120N), but coupled upward drift "
            f"(+{temp_slope}°C/h, +{tens_slope}N/h, r={correlation}) predicts a defective batch "
            f"(grade {proj_pred_grade} < 80.0) in {hrs_to_defect} hours (Defect Risk: {round(defect_probability*100, 1)}%)."
            if silent_drift_detected
            else f"STABLE TELEMETRY on {machine_id}: Coupled drift index ({curr_cdi}) and projected grade ({proj_pred_grade}) are safe."
        ),
    }


def arbitrate_production_vs_quality(
    factory: dict,
    order_id: str,
    drift_report: dict,
    recalibration_hrs: float = 2.5,
    batch_rejection_cost_usd: float = 4500.0,
) -> dict:
    """
    HINTS 2 & 3: Settles the conflict between Agent A (Production: wants to ship tonight)
    and Agent B (Quality: wants to hold & recalibrate/reroute) using an explicit,
    deterministic Expected Risk-Adjusted Cost Rule — and computes the exact counterfactual
    thresholds that would flip the decision.
    """
    order = factory["orders"][order_id]
    machine_id = order["assigned_machine_id"] or drift_report["machine_id"]
    machine = factory["machines"][machine_id]

    defect_prob = drift_report["defect_probability"]
    late_penalty_per_hr = order.get("penalty_per_hr_late", 500.0)
    deadline_hrs = order["deadline_hrs"]
    normal_weaving_hrs = round(order["remaining_quantity_m"] / machine["capacity_m_per_hr"], 2)

    # ---------------------------------------------------------
    # AGENT A (PRODUCTION) POSITION: "CONTINUE_AND_SHIP"
    # ---------------------------------------------------------
    # If we ignore the drift and keep running M1:
    # Expected Cost of Shipping = P(Defect) * Batch_Rejection_Cost
    expected_defect_loss_usd = round(defect_prob * batch_rejection_cost_usd, 2)
    agent_a_proposal = {
        "agent": "Agent A (Factory Operations / Production)",
        "vote": "CONTINUE_AND_SHIP",
        "argument": (
            f"Order {order_id} is due tonight in {deadline_hrs}h. Continuing on {machine_id} finishes in "
            f"{normal_weaving_hrs}h with 0h late penalty (${0.0}). Holding risks missing the deadline."
        ),
        "expected_risk_cost_usd": expected_defect_loss_usd,
    }

    # ---------------------------------------------------------
    # AGENT B (QUALITY) POSITION: "HOLD_AND_INTERVENE"
    # ---------------------------------------------------------
    # Evaluate Cost of Holding: Either recalibrate M1 (2.5h) OR reroute via Recovery Engine 2.0
    hold_total_hrs = round(recalibration_hrs + normal_weaving_hrs, 2)
    hold_hours_late = max(0.0, round(hold_total_hrs - deadline_hrs, 2))
    recal_labor_cost_usd = 150.0
    hold_late_penalty_usd = round(hold_hours_late * late_penalty_per_hr, 2)
    expected_hold_cost_usd = round(recal_labor_cost_usd + hold_late_penalty_usd, 2)

    # Check if Recovery Engine 2.0 can reroute to M2 for even lower cost/delay
    sim_factory = deepcopy(factory)
    inc = simulate_machine_maintenance(sim_factory, machine_id, duration_hrs=recalibration_hrs)
    recovery_rep = generate_factory_recovery_report(sim_factory, [inc])
    best_recovery_plan = recovery_rep["order_reports"].get(order_id, {}).get("recommended_plan")

    agent_b_proposal = {
        "agent": "Agent B (Quality Intelligence)",
        "vote": "HOLD_AND_RECALIBRATE",
        "argument": (
            f"Coupled temp+tension drift on {machine_id} carries a {round(defect_prob * 100, 1)}% defect probability "
            f"(Expected rejection loss: ${expected_defect_loss_usd}). Holding {machine_id} for {recalibration_hrs}h "
            f"recalibration (or rerouting to M2) costs ${expected_hold_cost_usd} in delay/recalibration."
        ),
        "expected_risk_cost_usd": expected_hold_cost_usd,
    }

    # ---------------------------------------------------------
    # DETERMINISTIC ARBITRATION RULE (Not "whoever shouts last")
    # ---------------------------------------------------------
    # Rule: Choose HOLD_AND_RECALIBRATE if Expected_Defect_Loss > Expected_Hold_Cost
    #       (with a hard safety override if defect_prob >= 0.85).
    quality_wins = expected_defect_loss_usd > expected_hold_cost_usd

    winning_decision = "HOLD_AND_RECALIBRATE" if quality_wins else "CONTINUE_AND_SHIP"
    winning_agent = "Agent B (Quality Intelligence)" if quality_wins else "Agent A (Production)"
    net_savings_usd = round(abs(expected_defect_loss_usd - expected_hold_cost_usd), 2)

    # ---------------------------------------------------------
    # HINT 3: COUNTERFACTUAL EXPLAINABILITY ("What would have flipped it?")
    # ---------------------------------------------------------
    # 1. Defect Probability Flip Point: P_flip * Batch_Rejection_Cost == Expected_Hold_Cost
    flip_defect_prob = round(expected_hold_cost_usd / batch_rejection_cost_usd, 3)

    # 2. Late Penalty Flip Point (if hold causes lateness):
    #    recal_labor_cost + hold_hours_late * Penalty_flip == expected_defect_loss_usd
    if hold_hours_late > 0:
        flip_penalty_per_hr = round(max(0.0, (expected_defect_loss_usd - recal_labor_cost_usd) / hold_hours_late), 2)
        penalty_flip_text = (
            f"Late penalty per hour exceeded ${flip_penalty_per_hr}/hr "
            f"(current penalty is ${late_penalty_per_hr}/hr across {hold_hours_late}h delay)"
        )
    else:
        flip_penalty_per_hr = None
        penalty_flip_text = (
            f"Deadline buffer tightened so that a {recalibration_hrs}h hold caused > "
            f"{round((expected_defect_loss_usd - recal_labor_cost_usd) / late_penalty_per_hr, 2)}h of late delivery"
        )

    # 3. Sensor Reading Flip Point:
    flip_temp_c = 73.0  # Temperature below which projected CDI keeps defect probability < flip_defect_prob

    if quality_wins:
        why_call_went_this_way = (
            f"Quality's HOLD won because shipping under silent drift carries an expected defect loss of "
            f"${expected_defect_loss_usd} ({round(defect_prob*100, 1)}% risk x ${batch_rejection_cost_usd} batch loss), "
            f"which exceeds the ${expected_hold_cost_usd} cost of holding for a {recalibration_hrs}h recalibration "
            f"(${recal_labor_cost_usd} recalibration + ${hold_late_penalty_usd} late penalty for {hold_hours_late}h delay). "
            f"Net expected loss avoided: ${net_savings_usd}."
        )
        what_would_have_flipped_it = (
            f"The call would have flipped to Production (CONTINUE_AND_SHIP) if ANY of the following were true: "
            f"(1) Defect probability was below {round(flip_defect_prob * 100, 1)}% (currently {round(defect_prob * 100, 1)}%), "
            f"(2) {penalty_flip_text}, or "
            f"(3) Latest loom temperature stabilized at or below {flip_temp_c}°C."
        )
    else:
        why_call_went_this_way = (
            f"Production's SHIP won because the expected defect risk cost (${expected_defect_loss_usd} at "
            f"{round(defect_prob*100, 1)}% defect probability) is lower than the ${expected_hold_cost_usd} cost "
            f"of holding the order (${hold_late_penalty_usd} late penalty + ${recal_labor_cost_usd} recalibration). "
            f"Net expected savings from shipping: ${net_savings_usd}."
        )
        what_would_have_flipped_it = (
            f"The call would have flipped to Quality (HOLD_AND_RECALIBRATE) if: "
            f"(1) Defect probability rose above {round(flip_defect_prob * 100, 1)}% (currently {round(defect_prob * 100, 1)}%), or "
            f"(2) Client late penalty was below ${flip_penalty_per_hr}/hr (currently ${late_penalty_per_hr}/hr)."
        )

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "order_id": order_id,
        "machine_id": machine_id,
        "conflict_detected": True,
        "agent_a_production": agent_a_proposal,
        "agent_b_quality": agent_b_proposal,
        "arbitration_rule": "MINIMIZE_EXPECTED_RISK_ADJUSTED_LOSS: Compare P(defect)*Batch_Loss vs. (Recalibration_Cost + Late_Hours*Penalty_Rate)",
        "winning_decision": winning_decision,
        "winning_agent": winning_agent,
        "expected_cost_if_ship_usd": expected_defect_loss_usd,
        "expected_cost_if_hold_usd": expected_hold_cost_usd,
        "net_expected_value_of_decision_usd": net_savings_usd,
        "counterfactual_flip_thresholds": {
            "defect_probability_flip_threshold": flip_defect_prob,
            "current_defect_probability": defect_prob,
            "late_penalty_per_hr_flip_threshold_usd": flip_penalty_per_hr,
            "current_late_penalty_per_hr_usd": late_penalty_per_hr,
            "hold_hours_late": hold_hours_late,
        },
        "manager_explanation": {
            "why_call_went_this_way": why_call_went_this_way,
            "what_would_have_flipped_it": what_would_have_flipped_it,
        },
        "recovery_engine_backup_option": best_recovery_plan,
    }


def run_silent_drift_hurdle_demo() -> dict:
    """
    Runs the complete end-to-end "Silent Drift and the Deadline" hurdle scenario:
    1. Phase 1: Silent drift detected on M1 while ORD-101 is due tonight (11.5h deadline).
                Quality (HOLD) wins over Production (SHIP).
    2. Phase 2: New telemetry/order data arrives (cooling fan stabilizes drift OR emergency penalty spike)
                demonstrating that the rule dynamically flips the decision!
    """
    factory = create_factory()
    # Set ORD-101 as due tonight (11.5h left; 600m on M1 takes 10.0h weave time -> 2.5h hold makes it 1.0h late!)
    factory["orders"]["ORD-101"]["deadline_hrs"] = 11.5

    # Telemetry stream where EVERY reading is inside normal limits (Temp <= 85°C, Tension <= 120N)
    drifting_telemetry = [
        {"hour": 1, "temp_c": 68.0, "tension_n": 96.0},
        {"hour": 2, "temp_c": 71.0, "tension_n": 100.0},
        {"hour": 3, "temp_c": 74.0, "tension_n": 104.0},
        {"hour": 4, "temp_c": 77.0, "tension_n": 108.0},
        {"hour": 5, "temp_c": 79.5, "tension_n": 111.5},
        {"hour": 6, "temp_c": 82.0, "tension_n": 115.0},  # Still < 85°C and < 120N!
    ]

    drift_phase_1 = detect_silent_drift(drifting_telemetry, machine_id="M1")
    decision_phase_1 = arbitrate_production_vs_quality(factory, "ORD-101", drift_phase_1)

    # Phase 2 (New Data Arrives): Airflow cooling stabilizes M1 readings -> decision dynamically flips to SHIP!
    stabilized_telemetry = drifting_telemetry[:-2] + [
        {"hour": 5, "temp_c": 72.0, "tension_n": 99.0},
        {"hour": 6, "temp_c": 70.5, "tension_n": 97.5},
    ]
    drift_phase_2 = detect_silent_drift(stabilized_telemetry, machine_id="M1")
    decision_phase_2 = arbitrate_production_vs_quality(factory, "ORD-101", drift_phase_2)

    return {
        "phase_1_silent_drift": {
            "drift_analysis": drift_phase_1,
            "arbitration": decision_phase_1,
        },
        "phase_2_new_data_flip": {
            "drift_analysis": drift_phase_2,
            "arbitration": decision_phase_2,
        },
    }


if __name__ == "__main__":
    demo = run_silent_drift_hurdle_demo()
    p1_drift = demo["phase_1_silent_drift"]["drift_analysis"]
    p1_arb = demo["phase_1_silent_drift"]["arbitration"]
    p2_arb = demo["phase_2_new_data_flip"]["arbitration"]

    print("=" * 85)
    print("HURDLE DEMO: SILENT DRIFT AND THE DEADLINE")
    print("=" * 85)
    print("\n[HINT 1 — SILENT DRIFT DETECTION]")
    print(f"  All Readings Inside Normal Limits? : {p1_drift['all_readings_within_normal_limits']} "
          f"(Latest: {p1_drift['latest_reading']['temp_c']}°C <= 85°C, {p1_drift['latest_reading']['tension_n']}N <= 120N)")
    print(f"  Coupled Correlation & Slopes       : r = {p1_drift['joint_correlation']} | "
          f"+{p1_drift['temp_drift_slope_c_per_hr']}°C/h | +{p1_drift['tension_drift_slope_n_per_hr']}N/h")
    print(f"  Diagnosis                          : {p1_drift['diagnosis']}")

    print("\n[HINT 2 — RULE-BASED CONFLICT ARBITRATION (PRODUCTION VS. QUALITY)]")
    print(f"  {p1_arb['agent_a_production']['agent']} Vote : {p1_arb['agent_a_production']['vote']} "
          f"(Risk Cost: ${p1_arb['expected_cost_if_ship_usd']})")
    print(f"  {p1_arb['agent_b_quality']['agent']} Vote              : {p1_arb['agent_b_quality']['vote']} "
          f"(Hold Cost: ${p1_arb['expected_cost_if_hold_usd']})")
    print(f"  Rule Applied                       : {p1_arb['arbitration_rule']}")
    print(f"  WINNING CALL                       : {p1_arb['winning_decision']} (by {p1_arb['winning_agent']})")

    print("\n[HINT 3 — MANAGER EXPLAINABILITY & COUNTERFACTUAL FLIP CONDITIONS]")
    print(f"  Why the call went this way : {p1_arb['manager_explanation']['why_call_went_this_way']}")
    print(f"  What would have flipped it : {p1_arb['manager_explanation']['what_would_have_flipped_it']}")

    print("\n[DYNAMIC FLIP WHEN NEW DATA ARRIVES]")
    print(f"  After new stabilized sensor data arrives -> Defect Risk drops to "
          f"{round(demo['phase_2_new_data_flip']['drift_analysis']['defect_probability']*100, 1)}%")
    print(f"  NEW WINNING CALL : {p2_arb['winning_decision']} (by {p2_arb['winning_agent']})")
    print(f"  Explanation      : {p2_arb['manager_explanation']['why_call_went_this_way']}")