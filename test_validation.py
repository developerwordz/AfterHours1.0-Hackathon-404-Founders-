"""
test_validation.py — Comprehensive validation & benchmark test suite for TexResQ.
Owner: Ruhaan (ruhaan/backend)
"""

import pytest
from scenarios import load_realistic_factory
from scenarios.scenario_1_machine_failure import run_scenario as scen_1
from scenarios.scenario_2_material_shortage import run_scenario as scen_2
from scenarios.scenario_3_supplier_delay import run_scenario as scen_3
from scenarios.scenario_4_multiple_failures import run_scenario as scen_4
from scenarios.scenario_5_tight_deadline import run_scenario as scen_5
from scheduler import calculate_production_time, check_machine_capacity, check_deadline
from recovery import (
    evaluate_recovery_plan,
    apply_recovery_plan,
    verify_recovery,
)
from evaluation import run_full_benchmark


def test_dataset_schema_compatibility():
    """Validates that data/factory_dataset.json matches the exact factory.py schema."""
    f = load_realistic_factory()
    assert set(f.keys()) == {"machines", "orders", "raw_materials", "spare_parts", "suppliers", "incidents"}
    assert len(f["machines"]) == 3
    assert len(f["orders"]) == 3
    assert len(f["suppliers"]) == 2


def test_machine_compatibility_constraints():
    """Validates that machines reject incompatible fabric types and busy assignments."""
    f = load_realistic_factory()
    # M3 only weaves denim_heavy, must reject cotton_twill (ORD-101)
    cap_m3 = check_machine_capacity(f["orders"]["ORD-101"], f["machines"]["M3"])
    assert cap_m3["compatible"] is False
    assert cap_m3["can_accept_order"] is False

    # M2 supports cotton_twill, denim_heavy, poly_blend and is IDLE
    cap_m2 = check_machine_capacity(f["orders"]["ORD-101"], f["machines"]["M2"])
    assert cap_m2["compatible"] is True
    assert cap_m2["available_now"] is True
    assert cap_m2["can_accept_order"] is True


def test_production_time_and_deadline_math():
    """Validates exact production time and deadline slack calculations."""
    f = load_realistic_factory()
    ord_101 = f["orders"]["ORD-101"]  # 600m remaining, 14.0h deadline

    # On M1 (60m/hr) -> 10.0 hours
    assert calculate_production_time(ord_101, f["machines"]["M1"]) == 10.0
    # On M2 (45m/hr) -> 13.33 hours
    assert calculate_production_time(ord_101, f["machines"]["M2"]) == 13.33

    dl_m2 = check_deadline(ord_101, f["machines"]["M2"])
    assert dl_m2["meets_deadline"] is True
    assert dl_m2["slack_hrs"] == 0.67


def test_inventory_and_recovery_cost_calculation():
    """Validates raw material shortfall detection and exact procurement + operating cost math."""
    f = load_realistic_factory()
    # ORD-101 needs 600kg RM-COTTON, 400kg in stock -> 200kg shortfall.
    # Plan without supplier must be marked infeasible.
    no_sup_plan = {
        "plan_id": "TEST-NO-SUP",
        "order_id": "ORD-101",
        "strategy_type": "REASSIGN_MACHINE",
        "name": "M2 without supplier",
        "target_machine_id": "M2",
        "supplier_id": None,
        "actions": [],
    }
    eval_no_sup = evaluate_recovery_plan(f, no_sup_plan)
    assert eval_no_sup["feasible"] is False

    # Plan with SUP-BACKUP: 200kg * $6.0/kg + $200 rush = $1400 procurement
    # Operating on M2: 13.33h * $20/hr = $266.60 -> Total = $1666.60
    backup_plan = {
        "plan_id": "TEST-BACKUP",
        "order_id": "ORD-101",
        "strategy_type": "COMBINED_REASSIGN_AND_PROCURE",
        "name": "M2 with Backup Supplier",
        "target_machine_id": "M2",
        "supplier_id": "SUP-BACKUP",
        "actions": [],
    }
    eval_backup = evaluate_recovery_plan(f, backup_plan)
    assert eval_backup["feasible"] is True
    assert eval_backup["meets_deadline"] is True
    assert eval_backup["cost_breakdown_usd"]["procurement_cost"] == 1400.0
    assert eval_backup["cost_breakdown_usd"]["operating_cost"] == 266.6
    assert eval_backup["additional_cost_usd"] == 1666.6


def test_execution_state_updates_and_verification():
    """Validates that apply_recovery_plan updates machine, stock, and order states and passes verify_recovery."""
    res = scen_1()
    f = res["factory"]
    best_plan = res["report"]["order_reports"]["ORD-101"]["recommended_plan"]

    receipt = apply_recovery_plan(f, best_plan)
    assert receipt["assigned_machine_id"] == "M2"
    assert f["machines"]["M2"]["status"] == "RUNNING"
    assert f["machines"]["M1"]["status"] == "MAINTENANCE"
    assert f["raw_materials"]["RM-COTTON"]["reserved_kg"] == 600.0

    ver = verify_recovery(f, "ORD-101")
    assert ver["verified"] is True
    assert all(ver["checks"].values())


def test_all_five_reproducible_scenarios():
    """Validates expected outcomes across all 5 standalone scenario files."""
    s1 = scen_1()
    assert s1["report"]["overall_feasibility"] == "FULL_RECOVERY"
    assert s1["report"]["orders_saved"] == ["ORD-101"]

    s2 = scen_2()
    assert s2["report"]["overall_feasibility"] == "FULL_RECOVERY"
    assert s2["report"]["orders_saved"] == ["ORD-101"]

    s3 = scen_3()
    assert s3["report"]["overall_feasibility"] == "FULL_RECOVERY"
    assert s3["report"]["orders_saved"] == ["ORD-101"]

    s4 = scen_4()
    assert s4["report"]["overall_feasibility"] == "PARTIAL_RECOVERY"
    assert s4["report"]["orders_saved"] == ["ORD-101"]
    assert s4["report"]["orders_at_risk"] == ["ORD-102"]

    s5 = scen_5()
    # Tight 9h deadline on 500m order cannot be met on M2 (11.11h), but plan is feasible (damage mitigation)
    assert s5["report"]["overall_feasibility"] == "PARTIAL_RECOVERY"
    rec_plan = s5["report"]["order_reports"]["ORD-103"]["recommended_plan"]
    assert rec_plan["feasible"] is True
    assert rec_plan["meets_deadline"] is False
    assert rec_plan["hours_late"] == 2.11


def test_baseline_vs_texresq_benchmark():
    """Validates that TexResQ outperforms Baseline on on-time delivery, downtime, cost, and violations."""
    bench = run_full_benchmark()
    agg = bench["aggregate"]

    assert agg["texresq_on_time"] > agg["baseline_on_time"]
    assert agg["texresq_downtime_hrs"] < agg["baseline_downtime_hrs"]
    assert agg["texresq_cost_usd"] < agg["baseline_cost_usd"]
    assert agg["texresq_violations"] == 0
    assert agg["total_cost_savings_usd"] > 5000.0