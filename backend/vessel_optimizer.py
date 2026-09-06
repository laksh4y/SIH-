"""
vessel_optimizer.py — Full vessel chartering optimization engine.
Combines feasibility filtering, forecasting, cost calculation, timing optimization,
risk analysis, and idle scenario management.
"""

import numpy as np

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
    Filter vessels by port draft, LOA, and beam constraints, plus cargo capacity.
    Checks both origin and destination port infrastructure limitations.
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
    max_allowed_loa = min(
        float(origin.get("max_loa_m", 999)),
        float(dest.get("max_loa_m", 999)),
    )
    max_allowed_beam = min(
        float(origin.get("max_beam_m", 999)),
        float(dest.get("max_beam_m", 999)),
    )

    feasible = []
    rejected = []

    for vessel_name, specs in VESSEL_SPECS.items():
        reasons = []
        if specs["max_draft"] > max_allowed_draft:
            reasons.append(f"Draft {specs['max_draft']}m exceeds limit {max_allowed_draft}m")
        if specs.get("loa_m", 0) > max_allowed_loa:
            reasons.append(f"LOA {specs['loa_m']}m exceeds limit {max_allowed_loa}m")
        if specs.get("beam_m", 0) > max_allowed_beam:
            reasons.append(f"Beam {specs['beam_m']}m exceeds limit {max_allowed_beam}m")

        if reasons:
            rejected.append({"vessel_type": vessel_name, "reasons": reasons})
        else:
            feasible.append(vessel_name)

    return feasible, rejected


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


# =========================================================================
#  (c) Idle Scenario Management
# =========================================================================

def find_low_demand_windows(daily_rates, window_size=14, top_n=3):
    """
    Identify the top N lowest-demand (cheapest) windows of `window_size` days.
    Low rates correspond to low market demand — ideal periods for vessel
    repositioning or spot-market employment.
    """
    if len(daily_rates) < window_size:
        return []

    windows = []
    for i in range(len(daily_rates) - window_size + 1):
        segment = daily_rates[i:i + window_size]
        avg = sum(segment) / window_size
        windows.append({
            "start_day": i + 1,
            "end_day": i + window_size,
            "avg_rate": round(avg, 2),
        })

    windows.sort(key=lambda w: w["avg_rate"])
    return windows[:top_n]


def generate_idle_strategies(best_window, total_forecast_days, vessel_type, voyage_days):
    """
    Generate actionable idle-scenario management strategies.
    Suggests what to do with the vessel before/after the optimal charter window.
    """
    strategies = []
    gap_before = best_window["start_day"] - 1  # days before optimal window

    if gap_before > 15:
        strategies.append({
            "type": "spot_market",
            "icon": "💼",
            "title": "Spot Market Employment",
            "description": (
                f"The optimal charter window begins on Day {best_window['start_day']}. "
                f"Consider deploying the {vessel_type} on the spot market for the "
                f"first {gap_before} days to generate revenue and avoid idle time."
            ),
            "priority": "high",
        })
    elif gap_before > 5:
        strategies.append({
            "type": "positioning",
            "icon": "📍",
            "title": "Optimized Positioning",
            "description": (
                f"Use the {gap_before}-day gap before the optimal window to "
                f"reposition the vessel closer to the loading port, reducing "
                f"deadheading distance and ensuring timely arrival."
            ),
            "priority": "medium",
        })

    gap_after = total_forecast_days - best_window["end_day"]
    if gap_after > voyage_days * 1.5:
        strategies.append({
            "type": "return_cargo",
            "icon": "🔄",
            "title": "Backhaul / Return Cargo",
            "description": (
                f"After discharge at the Indian East Coast port (~Day {best_window['end_day'] + int(voyage_days)}), "
                f"seek backhaul cargo (e.g., iron ore exports from India) to avoid "
                f"empty ballast return, reducing deadheading costs by up to 40%."
            ),
            "priority": "high",
        })

    strategies.append({
        "type": "contract_timing",
        "icon": "📅",
        "title": "Staggered Chartering",
        "description": (
            f"If total cargo volume requires multiple voyages, stagger charter "
            f"contracts across predicted low-rate windows rather than booking "
            f"all voyages at once, maximizing savings from rate fluctuations."
        ),
        "priority": "medium",
    })

    return strategies


# =========================================================================
#  (d) Risk Mitigation & Early Warnings
# =========================================================================

def analyze_risk(freight_forecast, fuel_forecast, commodity_forecast,
                 origin_port, dest_port):
    """
    Comprehensive risk analysis covering:
    - Market volatility (width of confidence bands)
    - Port congestion risk
    - Price trend direction
    - Seasonal risk indicators
    """
    alerts = []

    # --- Freight Rate Volatility ---
    yhat = freight_forecast["yhat"].values
    upper = freight_forecast["yhat_upper"].values
    lower = freight_forecast["yhat_lower"].values
    band_width = np.mean(upper - lower)
    mean_rate = np.mean(yhat)
    volatility_pct = (band_width / max(mean_rate, 1)) * 100

    if volatility_pct > 40:
        severity = "critical"
        alerts.append({
            "type": "volatility",
            "severity": "critical",
            "icon": "🔴",
            "title": "Critical Market Volatility",
            "description": (
                f"Freight rate confidence band is ±{volatility_pct:.0f}% of the mean. "
                f"Extremely high uncertainty detected. Strongly recommend locking "
                f"in charter rates via a fixed-period contract immediately."
            ),
        })
    elif volatility_pct > 25:
        alerts.append({
            "type": "volatility",
            "severity": "warning",
            "icon": "🟡",
            "title": "Elevated Market Volatility",
            "description": (
                f"Freight rate uncertainty is ±{volatility_pct:.0f}% of the mean. "
                f"Consider hedging via Forward Freight Agreements (FFAs) or "
                f"chartering within the predicted low-rate window."
            ),
        })
    else:
        alerts.append({
            "type": "volatility",
            "severity": "info",
            "icon": "🟢",
            "title": "Stable Market Conditions",
            "description": (
                f"Freight rate volatility is low (±{volatility_pct:.0f}%). "
                f"Market conditions are favorable for chartering."
            ),
        })

    # --- Freight Rate Trend ---
    first_quarter = np.mean(yhat[:len(yhat) // 4])
    last_quarter = np.mean(yhat[-(len(yhat) // 4):])
    trend_change = ((last_quarter - first_quarter) / max(first_quarter, 1)) * 100

    if trend_change > 15:
        alerts.append({
            "type": "trend",
            "severity": "warning",
            "icon": "📈",
            "title": "Rising Freight Rates Detected",
            "description": (
                f"Rates are forecast to increase by ~{trend_change:.0f}% over the "
                f"analysis period. Charter early to lock in current lower rates."
            ),
        })
    elif trend_change < -15:
        alerts.append({
            "type": "trend",
            "severity": "info",
            "icon": "📉",
            "title": "Declining Freight Rates Detected",
            "description": (
                f"Rates are forecast to decrease by ~{abs(trend_change):.0f}%. "
                f"Consider delaying chartering to benefit from lower future rates."
            ),
        })

    # --- Port Congestion Risk ---
    origin_congestion = float(origin_port.get("typical_congestion_days", 0))
    dest_congestion = float(dest_port.get("typical_congestion_days", 0))

    if dest_congestion >= 4:
        alerts.append({
            "type": "congestion",
            "severity": "warning",
            "icon": "⚓",
            "title": f"High Port Congestion: {dest_port.get('port_name', 'Destination')}",
            "description": (
                f"Destination port has an average wait time of {dest_congestion:.0f} days. "
                f"Factor demurrage costs into your budget and consider alternate "
                f"discharge ports with shorter waiting times."
            ),
        })
    if origin_congestion >= 4:
        alerts.append({
            "type": "congestion",
            "severity": "warning",
            "icon": "⚓",
            "title": f"High Port Congestion: {origin_port.get('port_name', 'Origin')}",
            "description": (
                f"Origin port has an average wait time of {origin_congestion:.0f} days. "
                f"Plan loading schedules carefully to minimize vessel idle time."
            ),
        })

    # --- Fuel Price Risk ---
    fuel_values = fuel_forecast["yhat"].values
    fuel_first = np.mean(fuel_values[:len(fuel_values) // 4])
    fuel_last = np.mean(fuel_values[-(len(fuel_values) // 4):])
    fuel_trend = ((fuel_last - fuel_first) / max(fuel_first, 1)) * 100

    if fuel_trend > 10:
        alerts.append({
            "type": "fuel",
            "severity": "warning",
            "icon": "⛽",
            "title": "Rising Bunker Fuel Prices",
            "description": (
                f"Bunker fuel (VLSFO) prices are forecast to rise ~{fuel_trend:.0f}% "
                f"over the period. Consider bunker fuel hedging or pre-purchasing "
                f"fuel at current rates."
            ),
        })

    # --- Volatility Score (0-100) ---
    volatility_score = min(round(volatility_pct * 2), 100)

    return {
        "alerts": alerts,
        "volatility_score": volatility_score,
        "volatility_pct": round(volatility_pct, 1),
        "trend_change_pct": round(trend_change, 1),
        "fuel_trend_pct": round(fuel_trend, 1),
        "origin_congestion_days": origin_congestion,
        "dest_congestion_days": dest_congestion,
    }


# =========================================================================
#  Main Optimization Pipeline
# =========================================================================

def optimize(origin_id, dest_id, cargo_volume_mt, target_days_ahead=90):
    """
    Full optimization pipeline:
    1. Filter feasible vessels (draft + LOA + beam)
    2. For each vessel, calculate voyage + forecast costs
    3. Compute Total Landed Cost
    4. Find optimal chartering window
    5. Rank and return top 3
    6. Run risk analysis (d)
    7. Generate idle management strategies (c)

    Returns:
        dict with recommendations, forecasts, risk analysis, idle strategies, and metadata
    """
    feasible, rejected = get_feasible_vessels(origin_id, dest_id, cargo_volume_mt)

    if not feasible:
        return {
            "error": "No vessel type fits the given port constraints and cargo volume.",
            "recommendations": [],
            "feasible_vessels": [],
            "rejected_vessels": rejected,
        }

    # Get port data for risk analysis
    ports = load_ports_dict()
    origin_port = ports.get(origin_id, {})
    dest_port = ports.get(dest_id, {})

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

        # Low demand windows (for idle management)
        low_demand = find_low_demand_windows(daily_rates, window_size=14, top_n=3)

        # Idle strategies
        idle_strategies = generate_idle_strategies(
            best_window, target_days_ahead, vessel_type, voyage["total_days"]
        )

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
            "low_demand_windows": low_demand,
            "idle_strategies": idle_strategies,
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

    # Risk analysis (uses the best vessel's freight forecast)
    risk_analysis = {}
    if recommendations:
        best_freight = forecast_freight_rate(
            recommendations[0]["vessel_type"], target_days_ahead
        )
        risk_analysis = analyze_risk(
            best_freight, fuel_forecast, commodity_forecast,
            origin_port, dest_port,
        )

    return {
        "recommendations": recommendations[:3],  # top 3
        "all_feasible_vessels": feasible,
        "rejected_vessels": rejected,
        "risk_analysis": risk_analysis,
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
