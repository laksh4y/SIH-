"""
cost_calculator.py — Total Landed Cost computation for SteelRoute AI.

Total Landed Cost = Cargo FOB Price
                  + Freight Cost
                  + Bunker Fuel Cost
                  + Port Charges
                  + Insurance
"""


def calculate_total_landed_cost(
    cargo_volume_mt,
    commodity_price_usd_mt,
    freight_rate_index,
    fuel_price_usd_mt,
    voyage_details,
    vessel_type,
    voyages_needed=1.0,
):
    """
    Calculate the complete Total Landed Cost for a shipment.

    Args:
        cargo_volume_mt: Actual cargo volume in metric tonnes
        commodity_price_usd_mt: FOB price of the commodity (USD/MT)
        freight_rate_index: BDI-derived freight rate index value
        fuel_price_usd_mt: Current bunker fuel price (USD/MT)
        voyage_details: Dict from route_engine.calculate_voyage()
        vessel_type: Vessel type string
        voyages_needed: Number of voyages needed to move total volume

    Returns:
        dict with itemized cost breakdown and total
    """

    # 1. Cargo FOB Cost
    cargo_fob_cost = cargo_volume_mt * commodity_price_usd_mt

    # 2. Freight Cost — convert BDI index to per-MT rate
    # BDI of 1000 ≈ $10/MT for Panamax; scale accordingly
    freight_rate_per_mt = freight_rate_index * 0.01
    freight_cost = cargo_volume_mt * freight_rate_per_mt

    # 3. Bunker Fuel Cost
    fuel_consumed = voyage_details["fuel_consumed_mt"] * voyages_needed
    fuel_cost = fuel_consumed * fuel_price_usd_mt

    # 4. Port Charges
    # Loading port charges (~$1.5/MT) + Discharge port charges (~$2.0/MT)
    # + Demurrage risk buffer based on congestion
    port_loading_cost = cargo_volume_mt * 1.5
    port_discharge_cost = cargo_volume_mt * 2.0
    total_port_charges = port_loading_cost + port_discharge_cost

    # 5. Insurance (0.15% of cargo FOB value)
    insurance_cost = cargo_fob_cost * 0.0015

    # 6. Vessel Hire Cost (daily hire × total days)
    from backend.data_loader import VESSEL_SPECS
    daily_hire = VESSEL_SPECS[vessel_type]["daily_hire_usd"]
    total_days = voyage_details["total_days"] * voyages_needed
    hire_cost = daily_hire * total_days

    # Total
    total_cost = (
        cargo_fob_cost
        + freight_cost
        + fuel_cost
        + total_port_charges
        + insurance_cost
        + hire_cost
    )

    # Per-MT breakdown
    cost_per_mt = total_cost / max(cargo_volume_mt, 1)

    return {
        "cargo_fob_cost": round(cargo_fob_cost, 2),
        "freight_cost": round(freight_cost, 2),
        "fuel_cost": round(fuel_cost, 2),
        "port_charges": round(total_port_charges, 2),
        "insurance_cost": round(insurance_cost, 2),
        "hire_cost": round(hire_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_mt": round(cost_per_mt, 2),
        "breakdown_pct": {
            "Cargo FOB": round(cargo_fob_cost / total_cost * 100, 1),
            "Freight": round(freight_cost / total_cost * 100, 1),
            "Fuel": round(fuel_cost / total_cost * 100, 1),
            "Port Charges": round(total_port_charges / total_cost * 100, 1),
            "Insurance": round(insurance_cost / total_cost * 100, 1),
            "Vessel Hire": round(hire_cost / total_cost * 100, 1),
        },
    }
