"""
test_recovery.py — Automated pytest suite for TexResQ Recovery Engine 2.0.
Owner: Ruhaan (ruhaan/backend)
"""

import pytest
from factory import (
    create_factory,
    simulate_machine_failure,
    simulate_raw_material_shortage,
    simulate_supplier_delay,
    simulate_multiple_failures,
    simulate_machine_maintenance,
)
from recovery import (
    generate_recovery_plan,
    generate_factory_recovery_report,
    apply_recovery_plan,
    verify_recovery,
)


def test_1_m1_failure_m2_reassignment():
    """Scenario 1: M1 failure -> ORD-101 reassigned to M2 + backup supplier meets deadline."""
    f = create_factory()
    inc = simulate_machine_failure(f, "M1")
    report = generate_factory_recovery_report(f, inc)

    assert "ORD-101" in report["orders_saved"]
    best_plan = report["order_reports"]["ORD-101"]["recommended_plan"]
    assert best_plan["target_machine_id"] == "M2"
    assert best_plan["supplier_id"] == "SUP-BACKUP"
    assert best_plan["meets_deadline"] is True

    # Execute and verify closed loop
    apply_recovery_plan(f, best_plan)
    verification = verify_recovery(f, "ORD-101")
    assert verification["verified"] is True


def test_2_m3_failure_spare_part_unavailable():
    """Scenario 2: M3 fails -> torsion_bar has 0 in stock, so WAIT_FOR_REPAIR on M3 is infeasible."""
    f = create_factory()
    inc = simulate_machine_failure(f, "M3")
    report = generate_recovery_plan(f, inc)

    plans = report["orders_recovery"]["ORD-102"]["ranked_plans"]
    m3_repair_plans = [p for p in plans if p["strategy_type"] == "WAIT_FOR_REPAIR"]
    assert len(m3_repair_plans) > 0
    for p in m3_repair_plans:
        assert p["feasible"] is False
        assert "torsion_bar" in p["evaluation_notes"]

    # Meanwhile, M2 is compatible with denim_heavy and saves ORD-102
    assert report["orders_recovery"]["ORD-102"]["order_can_be_saved"] is True
    assert report["orders_recovery"]["ORD-102"]["recommended_plan"]["target_machine_id"] == "M2"


def test_3_cotton_shortage_backup_sourcing():
    """Scenario 3: Cotton stock drops to 100kg while M1 is still healthy -> procures from Backup Supplier."""
    f = create_factory()
    inc = simulate_raw_material_shortage(f, "RM-COTTON", new_stock_kg=100.0)
    report = generate_factory_recovery_report(f, inc)

    assert "ORD-101" in report["affected_orders"]
    assert "ORD-101" in report["orders_saved"]
    best_plan = report["order_reports"]["ORD-101"]["recommended_plan"]
    # Can stay on M1 (60m/hr) and order from SUP-BACKUP (3h ETA)
    assert best_plan["supplier_id"] == "SUP-BACKUP"
    assert best_plan["meets_deadline"] is True


def test_4_two_simultaneous_failures():
    """Scenario 4: M1 and M3 fail simultaneously -> M2 cannot run both at once!"""
    f = create_factory()
    incidents = simulate_multiple_failures(f, ["M1", "M3"])
    report = generate_factory_recovery_report(f, incidents)

    assert set(report["affected_machines"]) == {"M1", "M3"}
    assert set(report["affected_orders"]) == {"ORD-101", "ORD-102"}

    # ORD-101 has tighter deadline (14h vs 16h) so it gets M2 and is saved.
    # ORD-102 cannot use M2 (now busy) and cannot repair M3 (0 torsion_bar in stock)!
    assert "ORD-101" in report["orders_saved"]
    assert "ORD-102" in report["orders_at_risk"]
    assert report["overall_feasibility"] == "PARTIAL_RECOVERY"


def test_5_no_compatible_machine_available():
    """Scenario 5: M3 fails while M2 is already busy, and M3 has no spare parts -> No feasible plan."""
    f = create_factory()
    # Make M2 busy with ORD-103
    f["machines"]["M2"]["status"] = "RUNNING"
    f["machines"]["M2"]["assigned_order_id"] = "ORD-103"

    inc = simulate_machine_failure(f, "M3")
    report = generate_factory_recovery_report(f, inc)

    # M1 cannot weave denim_heavy, M2 is busy, M3 has no torsion_bar
    assert report["order_reports"]["ORD-102"]["recommended_plan"] is None
    assert report["overall_feasibility"] == "UNRECOVERABLE"


def test_6_no_supplier_can_meet_deadline():
    """Scenario 6: Both suppliers are delayed -> feasible plan exists, but deadline cannot be met."""
    f = create_factory()
    simulate_machine_failure(f, "M1")
    simulate_supplier_delay(f, "SUP-PRIMARY", extra_delay_hrs=10.0)
    simulate_supplier_delay(f, "SUP-BACKUP", extra_delay_hrs=15.0)

    report = generate_factory_recovery_report(f)
    ord_rep = report["order_reports"]["ORD-101"]

    assert ord_rep["order_can_be_saved"] is False
    assert ord_rep["recommended_plan"] is not None
    assert ord_rep["recommended_plan"]["feasible"] is True
    assert ord_rep["recommended_plan"]["meets_deadline"] is False
    assert "WARNING — DEADLINE CANNOT BE MET" in ord_rep["honest_assessment"]


def test_7_infeasible_plans_cannot_execute():
    """Scenario 7: Calling apply_recovery_plan on an infeasible plan raises ValueError."""
    f = create_factory()
    inc = simulate_machine_failure(f, "M1")
    report = generate_recovery_plan(f, inc)

    infeasible_plans = [
        p for p in report["orders_recovery"]["ORD-101"]["ranked_plans"] if not p["feasible"]
    ]
    assert len(infeasible_plans) > 0

    with pytest.raises(ValueError, match="Cannot apply infeasible plan"):
        apply_recovery_plan(f, infeasible_plans[0])