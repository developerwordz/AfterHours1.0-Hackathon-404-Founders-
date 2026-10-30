from factory import create_factory, simulate_batch_production

factory = create_factory()

for machine_id in ["M1", "M3"]:
    report = simulate_batch_production(factory, machine_id)
    print(report)

print("Total batches:", len(factory["batches"]))

print("\n=== TEXRESQ PRODUCTION REPORT ===")
print("Batch:", report["batch_id"])
print("Machine:", report["machine_name"])
print("Fabric:", report["fabric_type"])
print("Quality Score:", report["quality_score"])
print("Grade:", report["grade"])
print("Status:", report["inspection_status"])
print("Metrics:", report["metrics"])

print("\nTotal batches:", len(factory["batches"]))