from factory import create_factory, simulate_batch_production

factory = create_factory()

report = simulate_batch_production(factory, "M1")

print("\n=== TEXRESQ PRODUCTION REPORT ===")
print("Batch:", report["batch_id"])
print("Machine:", report["machine_name"])
print("Fabric:", report["fabric_type"])
print("Quality Score:", report["quality_score"])
print("Grade:", report["grade"])
print("Status:", report["inspection_status"])
print("Metrics:", report["metrics"])

print("\nTotal batches:", len(factory["batches"]))