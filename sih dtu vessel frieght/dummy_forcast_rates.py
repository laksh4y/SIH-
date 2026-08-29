import random

def forecast_rates(vessel_type, days_ahead):
    """TEMPORARY dummy version — returns fake rates for testing.
    Replace with Divyam's real forecast_rates() once ready."""
    base_rates = {
        "Handysize": 12000,
        "Supramax": 15000,
        "Panamax": 20000,
        "Capesize": 28000,
    }
    base = base_rates.get(vessel_type, 15000)
    # add small random variation so ranking logic has something to compare
    return base + random.randint(-2000, 2000)