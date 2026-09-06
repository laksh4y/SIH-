"""
vessel_optimizer.py — Full vessel chartering optimization engine.
Combines feasibility filtering, forecasting, cost calculation, and timing optimization.
"""

from backend.data_loader import load_ports_dict, VESSEL_SPECS
from backend.route_engine import calculate_voyage
from backend.forecasting import (
    forecast_freight_rate,
    forecast_fuel_price,
    forecast_commodity_price,
)
from backend.cost_calculator import calculate_total_landed_cost


def get_feasible_vessels(origin_id, dest_id, cargo_volume_mt):
    """
    Filter vessels by port draft constraints and cargo capacity.
    Based on the team's original logic in port_data.py / vessel_simultor.py.
    """
    ports = load_ports_dict()
    origin = ports.get(origin_id)
    dest = ports.get(dest_id)

    if not origin or not dest:
        return []

    max_allowed_draft = min(
        float(origin["max_draft_m"]),
        float(dest["max_draft_m"]),
    )

    feasible = []
    for vessel_name, specs in VESSEL_SPECS.items():
        if specs["max_draft"] <= max_allowed_draft:
            feasible.append(vessel_name)

    return feasible


def find_best_chartering_window(daily_rates, window_size=7):
    """
    Find the cheapest window of `window_size` consecutive days.
    Ported from the team's vessel_simultor.py find_best_window().
    """
    if len(daily_rates) < window_size:
        return {
            "start_day": 1,
            "end_day": len(daily_rates),
            "avg_rate": round(sum(daily_rates) / max(len(daily_rates), 1), 2),
        }

    best_start, best_avg = 0, float("inf")
    for i in range(len(daily_rates) - window_size + 1):
        avg = sum(daily_rates[i:i + window_size]) / window_size
        if avg < best_avg:
            best_avg = avg
            best_start = i

    return {
        "start_day": best_start + 1,
        "end_day": best_start + window_size,
        "avg_rate": round(best_avg, 2),
    }


def optimize(origin_id, dest_id, cargo_volume_mt, target_days_ahead=90):
    """
    Full optimization pipeline:
    1. Filter feasible vessels
    2. For each vessel, calculate voyage + forecast costs
    3. Compute Total Landed Cost
    4. Find optimal chartering window
    5. Rank and return top 3

    Returns:
        dict with recommendations, forecasts, and metadata
    """
    feasible = get_feasible_vessels(origin_id, dest_id, cargo_volume_mt)

    if not feasible:
        return {
            "error": "No vessel type fits the given port constraints and cargo volume.",
            "recommendations": [],
            "feasible_vessels": [],
        }

    # Get forecasts (shared across all vessels for fuel & commodity)
    fuel_forecast = forecast_fuel_price(target_days_ahead)
    commodity_forecast = forecast_commodity_price(target_days_ahead)

    avg_fuel_price = float(fuel_forecast["yhat"].mean())
    avg_commodity_price = float(commodity_forecast["yhat"].mean())

    recommendations = []

    for vessel_type in feasible:
        # Voyage details
        voyage = calculate_voyage(origin_id, dest_id, vessel_type)
        if voyage is None:
            continue

        # Freight rate forecast for this vessel
        freight_forecast = forecast_freight_rate(vessel_type, target_days_ahead)
        daily_rates = freight_forecast["yhat"].tolist()

        # Average freight rate
        avg_freight_rate = float(freight_forecast["yhat"].mean())

        # Optimal chartering window
        best_window = find_best_chartering_window(daily_rates, window_size=7)

        # Actual cargo volume per voyage
        cargo_per_voyage = min(cargo_volume_mt, VESSEL_SPECS[vessel_type]["max_dwt"])
        voyages_needed = cargo_volume_mt / cargo_per_voyage

        # Total Landed Cost at average forecast rates
        cost_breakdown = calculate_total_landed_cost(
            cargo_volume_mt=cargo_volume_mt,
            commodity_price_usd_mt=avg_commodity_price,
            freight_rate_index=avg_freight_rate,
            fuel_price_usd_mt=avg_fuel_price,
            voyage_details=voyage,
            vessel_type=vessel_type,
            voyages_needed=voyages_needed,
        )

        # Cost at optimal window (lower rates)
        optimal_cost = calculate_total_landed_cost(
            cargo_volume_mt=cargo_volume_mt,
            commodity_price_usd_mt=avg_commodity_price,
            freight_rate_index=best_window["avg_rate"],
            fuel_price_usd_mt=avg_fuel_price,
            voyage_details=voyage,
            vessel_type=vessel_type,
            voyages_needed=voyages_needed,
        )

        savings = cost_breakdown["total_cost"] - optimal_cost["total_cost"]

        recommendations.append({
            "vessel_type": vessel_type,
            "voyage": voyage,
            "cost_breakdown": cost_breakdown,
            "optimal_cost": optimal_cost,
            "best_window": best_window,
            "potential_savings": round(savings, 2),
            "avg_freight_rate": round(avg_freight_rate, 2),
            "freight_forecast_dates": [
                d.strftime("%Y-%m-%d") for d in freight_forecast["ds"]
            ],
            "freight_forecast_values": [round(v, 2) for v in daily_rates],
            "freight_forecast_lower": [
                round(v, 2) for v in freight_forecast["yhat_lower"].tolist()
            ],
            "freight_forecast_upper": [
                round(v, 2) for v in freight_forecast["yhat_upper"].tolist()
            ],
        })

    # Rank by total cost (lowest first)
    recommendations.sort(key=lambda r: r["cost_breakdown"]["total_cost"])

    # Mark best
    for i, rec in enumerate(recommendations):
        rec["rank"] = i + 1
        rec["is_recommended"] = i == 0

    return {
        "recommendations": recommendations[:3],  # top 3
        "all_feasible_vessels": feasible,
        "origin_id": origin_id,
        "dest_id": dest_id,
        "cargo_volume_mt": cargo_volume_mt,
        "forecast_horizon_days": target_days_ahead,
        "avg_fuel_price": round(avg_fuel_price, 2),
        "avg_commodity_price": round(avg_commodity_price, 2),
        "fuel_forecast": {
            "dates": [d.strftime("%Y-%m-%d") for d in fuel_forecast["ds"]],
            "values": [round(v, 2) for v in fuel_forecast["yhat"].tolist()],
        },
        "commodity_forecast": {
            "dates": [d.strftime("%Y-%m-%d") for d in commodity_forecast["ds"]],
            "values": [round(v, 2) for v in commodity_forecast["yhat"].tolist()],
        },
    }
