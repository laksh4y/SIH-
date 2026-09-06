"""
forecasting.py — Freight rate forecasting engine for SteelRoute AI.
Uses Prophet on historical BDI data with vessel-type scaling.
Falls back to simple trend+seasonality if Prophet is unavailable.
"""

import numpy as np
import pandas as pd
from functools import lru_cache

from backend.data_loader import (
    load_bdi, load_fuel_prices, load_commodity_prices,
    VESSEL_BDI_MULTIPLIERS,
)

# ---------- Try importing Prophet ----------
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    print("[WARNING] Prophet not installed. Using fallback forecasting.")


# ---------- Fallback: simple seasonal forecast ----------

def _fallback_forecast(df, periods):
    """Simple forecast using last-year seasonality + linear trend."""
    df = df.copy().sort_values("ds")
    last_date = df["ds"].max()
    last_365 = df.tail(365)

    # Linear trend from last year
    y_vals = last_365["y"].values
    trend_slope = (y_vals[-1] - y_vals[0]) / max(len(y_vals), 1)

    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=periods, freq="D"
    )

    forecasts = []
    for i, dt in enumerate(future_dates):
        # Seasonal component: repeat last year's pattern
        seasonal_idx = i % len(y_vals)
        base = y_vals[seasonal_idx]
        trend = trend_slope * i
        predicted = base + trend

        forecasts.append({
            "ds": dt,
            "yhat": max(predicted, 50),
            "yhat_lower": max(predicted * 0.85, 30),
            "yhat_upper": predicted * 1.15,
        })

    return pd.DataFrame(forecasts)


# ---------- Prophet-based forecast ----------

@lru_cache(maxsize=8)
def _fit_prophet_model(series_key):
    """
    Fit and cache a Prophet model for a given series.
    series_key: 'bdi', 'fuel', or 'commodity'
    """
    if series_key == "bdi":
        df = load_bdi()
    elif series_key == "fuel":
        df = load_fuel_prices()
    elif series_key == "commodity":
        df = load_commodity_prices()
    else:
        raise ValueError(f"Unknown series: {series_key}")

    df = df[["ds", "y"]].copy()
    df["y"] = np.log(df["y"].clip(lower=1))  # log-transform

    m = Prophet(
        daily_seasonality=False,
        weekly_seasonality=False,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
    )
    m.fit(df)
    return m


def forecast_series(series_key, periods=90):
    """
    Forecast a time series forward by `periods` days.
    Returns DataFrame with: ds, yhat, yhat_lower, yhat_upper
    """
    if series_key == "bdi":
        df = load_bdi()
    elif series_key == "fuel":
        df = load_fuel_prices()
    elif series_key == "commodity":
        df = load_commodity_prices()
    else:
        raise ValueError(f"Unknown series: {series_key}")

    if not PROPHET_AVAILABLE:
        return _fallback_forecast(df, periods)

    m = _fit_prophet_model(series_key)
    future = m.make_future_dataframe(periods=periods)
    fcst = m.predict(future)

    # Exponentiate back from log space
    result = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    result["yhat"] = np.exp(result["yhat"])
    result["yhat_lower"] = np.exp(result["yhat_lower"])
    result["yhat_upper"] = np.exp(result["yhat_upper"])

    return result.tail(periods)


def forecast_freight_rate(vessel_type, periods=90):
    """
    Forecast freight rate for a specific vessel type.
    Applies the BDI multiplier to the base BDI forecast.
    """
    base_forecast = forecast_series("bdi", periods)
    multiplier = VESSEL_BDI_MULTIPLIERS.get(vessel_type, 1.0)

    result = base_forecast.copy()
    result["yhat"] = result["yhat"] * multiplier
    result["yhat_lower"] = result["yhat_lower"] * multiplier
    result["yhat_upper"] = result["yhat_upper"] * multiplier

    return result


def forecast_fuel_price(periods=90):
    """Forecast bunker fuel price (USD/MT) for next `periods` days."""
    return forecast_series("fuel", periods)


def forecast_commodity_price(periods=90):
    """Forecast coking coal FOB price (USD/MT) for next `periods` days."""
    return forecast_series("commodity", periods)


def get_forecast_summary(vessel_type, days_ahead=30):
    """
    Get a summary of the freight rate forecast at a specific day.
    Matches the signature from the team's original forecasting.py.
    """
    curve = forecast_freight_rate(vessel_type, days_ahead)
    target = curve.iloc[-1]
    return {
        "predicted_rate": round(float(target["yhat"]), 2),
        "lower_bound": round(float(target["yhat_lower"]), 2),
        "upper_bound": round(float(target["yhat_upper"]), 2),
        "target_date": target["ds"].strftime("%Y-%m-%d"),
    }
