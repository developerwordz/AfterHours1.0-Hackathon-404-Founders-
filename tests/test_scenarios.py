
import sys
from pathlib import Path

# Allow Python to import files from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orchestrator import run_orchestrator, print_orchestrator_report


def test_orchestrator():
    factory = {
        "machines": {
            "M1": {
                "name": "Cotton Spinning Machine",
                "status": "failed",
                "maintenance_hours": 6,
                "current_order": "O1"
            }
        },
        "inventory": {
            "cotton_fabric": {"quantity": 160, "unit": "metres"},
            "spare_parts": {"quantity": 2, "unit": "units"}
        },
        "suppliers": {
            "S1": {
                "name": "Primary Supplier",
                "lead_time_hours": 8,
                "cost_per_metre": 100,
                "reliability": 0.95
            },
            "S2": {
                "name": "Backup Supplier",
                "lead_time_hours": 3,
                "cost_per_metre": 125,
                "reliability": 0.90
            }
        },
        "orders": {
            "O1": {
                "machine_id": "M1",
                "quantity": 100,
                "deadline_hours": 4,
                "priority": 1,
                "status": "in_production"
            }
        }
    }

    incident = {
        "incident_id": "INC001",
        "type": "machine_failure",
        "machine_id": "M1",
        "severity": "high",
        "description": "Unexpected machine breakdown"
    }

    result = run_orchestrator(factory, incident)

    assert "machine_report" in result
    assert "inventory_report" in result
    assert "production_report" in result
    assert "sourcing_report" in result

    assert result["machine_report"]["machine_id"] == "M1"
    assert len(result["production_report"]["affected_orders"]) == 1


if __name__ == "__main__":
    result = run_orchestrator(factory, incident)
    print_orchestrator_report(result)
