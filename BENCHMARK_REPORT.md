# TexResQ — Dataset, Validation & Benchmark Report

## 1. Factory Dataset & Modeling Assumptions (`data/factory_dataset.json`)
Our simulated facility models a 3-loom industrial weaving unit in the Surat-Navsari textile corridor:
- **M1 (Air-Jet Loom, 60 m/hr, $25/hr):** High-speed weaving for `cotton_twill` and `poly_blend`. 8h repair time; `bearing_set` in stock (1 unit, $180).
- **M2 (Versatile Rapier Loom, 45 m/hr, $20/hr):** Flexible backup loom supporting all 3 fabrics (`cotton_twill`, `denim_heavy`, `poly_blend`). Starts `IDLE`.
- **M3 (Heavy-Duty Projectile Loom, 35 m/hr, $30/hr):** Specialized for `denim_heavy` only. 10h repair time; `torsion_bar` out of stock (0 units).
- **Inventory & Suppliers:**
  - `ORD-101` (Zara Global) requires `600kg` of `RM-COTTON` (due in 14h, $500/hr late penalty), but only `400kg` is in warehouse stock (`200kg` shortfall).
  - **Primary Supplier (Gujarat Spinners):** Low cost ($3.50/kg cotton, $50 fee), slow delivery (`12.0h` ETA).
  - **Backup Supplier (Surat Express Mills):** Express cost ($6.00/kg cotton, $200 rush fee), fast delivery (`3.0h` ETA).
- **Parallel Weaving Assumption:** Existing warehouse stock (`400kg` = `400m`) begins weaving immediately once a compatible machine is ready. Supplier wait delay only stalls production if supplier ETA exceeds the time covered by in-stock yarn.

---

## 2. Reproducible Disruption Scenarios (`scenarios/`)

| Scenario ID | File | Disruption Triggered | TexResQ Recovery Outcome |
|---|---|---|---|
| **SCEN-01** | `scenario_1_machine_failure.py` | `M1` breaks down mid-order (`ORD-101`) | Reroutes `ORD-101` to `M2` + procures `200kg` cotton from Backup Supplier (`3h` ETA). Finishes in **13.33h** vs **14.0h** deadline (**Saved**). |
| **SCEN-02** | `scenario_2_material_shortage.py` | Cotton stock drops from `400kg` to `150kg` | Keeps `ORD-101` on fast `M1` (`60m/hr`) + orders `450kg` from Backup Supplier (`3h` ETA). Finishes in **10.5h** vs **14.0h** deadline (**Saved**). |
| **SCEN-03** | `scenario_3_supplier_delay.py` | `M1` in 8h maintenance + Primary Supplier delayed +8h (`20h` ETA) | Reroutes `ORD-101` to `M2` + switches to Backup Supplier (`3h` ETA). Finishes in **13.33h** vs **14.0h** deadline (**Saved**). |
| **SCEN-04** | `scenario_4_multiple_failures.py` | Simultaneous `M1` + `M3` breakdown (`M2` contention) | Prioritizes `ORD-101` (tighter 14h deadline, higher $500/hr penalty) on `M2` (**Saved**). `ORD-102` flagged at-risk (`M3` lacks `torsion_bar` spare part). |
| **SCEN-05** | `scenario_5_tight_deadline.py` | `M1` fails on rush order `ORD-103` (`500m`, tight `9.0h` deadline) | Honestly reports `9.0h` deadline cannot be met; reroutes to `M2` (`11.11h`, `2.11h` late) vs waiting for `M1` repair (`16.33h`, `7.33h` late), reducing late penalties by **$1,827**. |

---

## 3. Baseline (Reactive) vs. TexResQ (Agentic) Benchmark Results (`evaluation.py`)

- **Baseline Model:** Standard reactive factory operations—waits for assigned machine repair and orders shortfalls from the standard Primary Supplier.
- **TexResQ Model:** Multi-constraint optimization across compatible looms, spare parts, and express backup suppliers.

| Scenario | Baseline On-Time | TexResQ On-Time | Baseline Downtime | TexResQ Downtime | Baseline Cost | TexResQ Cost | Net Cost Savings |
|---|---|---|---|---|---|---|---|
| **SCEN-01:** M1 Breakdown | 0 / 1 | **1 / 1** | 8.0 hrs | **0.0 hrs** | $3,180.00 | **$1,666.60** | **+$1,513.40** |
| **SCEN-02:** Cotton Shortage | 0 / 1 | **1 / 1** | 9.5 hrs | **0.5 hrs** | $4,625.00 | **$3,150.00** | **+$1,475.00** |
| **SCEN-03:** Supplier Delay + Maint | 0 / 1 | **1 / 1** | 13.33 hrs | **0.0 hrs** | $5,665.00 | **$1,666.60** | **+$3,998.40** |
| **SCEN-04:** Dual Failure (M1+M3) | 0 / 2 | **1 / 2** | 18.0 hrs | **0.0 hrs** | $7,980.00 | **$1,666.60** | **+$6,313.40** |
| **SCEN-05:** Tight 9h Deadline | 0 / 1 | **0 / 1** *(Mitigated)* | 8.0 hrs | **0.0 hrs** | $2,953.50 | **$960.70** | **+$1,992.80** |
| **TOTAL (Across 5 Scenarios)** | **0 / 6 (0%)** | **4 / 6 (66.7%)** | **56.83 hrs** | **0.50 hrs** | **$24,403.50** | **$9,110.50** | **+$15,293.00** |

### Key Takeaways for Judges
1. **99.1% Reduction in Production Downtime:** From `56.83 hours` of line stoppages down to `0.50 hours`.
2. **62.7% Reduction in Disruption & Penalty Costs:** Saves **$15,293.00** across the 5 disruption scenarios.
3. **Zero Constraint Violations:** TexResQ never assigns incompatible fabrics, never double-books an idle machine during simultaneous failures, and refuses to execute repairs when spare parts are out of stock.