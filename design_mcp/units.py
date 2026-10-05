"""Explicit conversions for bounded generic scalar quantities."""

from __future__ import annotations

import math

UNIT_DEFINITIONS = {
    "mm": ("length", 0.001, "m"), "m": ("length", 1.0, "m"),
    "mm2": ("area", 0.000001, "m2"), "m2": ("area", 1.0, "m2"),
    "mm3": ("volume", 0.000000001, "m3"), "m3": ("volume", 1.0, "m3"),
    "g": ("mass", 0.001, "kg"), "kg": ("mass", 1.0, "kg"),
    "V": ("voltage", 1.0, "V"), "A": ("current", 1.0, "A"),
    "W": ("power", 1.0, "W"), "Wh": ("energy", 1.0, "Wh"),
    "N": ("force", 1.0, "N"),
}


def normalize_quantity(value: float, unit: str) -> dict:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not isinstance(unit, str)
            or unit not in UNIT_DEFINITIONS):
        raise ValueError("Expected a finite numeric value and a supported explicit unit.")
    dimension, factor, canonical_unit = UNIT_DEFINITIONS[unit]
    canonical_value = value * factor
    if not math.isfinite(canonical_value):
        raise ValueError("Normalized value exceeds supported range.")
    return {"value": float(value), "unit": unit, "dimension": dimension,
            "canonical_value": canonical_value, "canonical_unit": canonical_unit,
            "derivation": "CALCULATED_UNIT_CONVERSION"}


def convert_quantity(value: float, from_unit: str, to_unit: str) -> dict:
    source = normalize_quantity(value, from_unit)
    if not isinstance(to_unit, str) or to_unit not in UNIT_DEFINITIONS:
        raise ValueError("Target unit is unsupported.")
    target_dimension, factor, _ = UNIT_DEFINITIONS[to_unit]
    if source["dimension"] != target_dimension:
        raise ValueError("Cannot convert between different dimensions.")
    converted = source["canonical_value"] / factor
    if not math.isfinite(converted):
        raise ValueError("Converted value exceeds supported range.")
    return {"input": source, "value": converted, "unit": to_unit,
            "derivation": "CALCULATED_UNIT_CONVERSION"}
