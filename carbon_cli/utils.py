def grams_to_kg(g):
    return g / 1000.0


def normalize_unit_and_value(val, unit, weight_g):
    # Simple normalization: if unit is per kg* something, multiply by kg, else fallback
    if unit is None:
        return val, unit
    unit_lower = unit.lower().replace("/", "").replace(" ", "")
    if "kg" in unit_lower:
        total = val * grams_to_kg(weight_g)
        return total, "kg CO2e (for input mass)"
    elif "g" in unit_lower:
        total = val * weight_g
        return total, "g CO2e (for input mass)"
    elif "t" in unit_lower:
        total = val * (grams_to_kg(weight_g) / 1000)
        return total, "t CO2e (for input mass)"
    # Fallback: just multiply
    return val * grams_to_kg(weight_g), unit
