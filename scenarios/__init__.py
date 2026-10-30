"""
scenarios/__init__.py — Exports all 5 reproducible disruption scenarios for TexResQ.
"""
import json
from pathlib import Path
from factory import create_factory

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "factory_dataset.json"


def load_realistic_factory() -> dict:
    """Loads the realistic factory dataset from JSON (or falls back to create_factory)."""
    if DATASET_PATH.exists():
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.pop("metadata", None)
            return data
    return create_factory()