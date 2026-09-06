"""
data_loader.py — Centralized data loading for SteelRoute AI.
Loads port, route, and BDI data from CSVs.
Generates synthetic fuel and commodity price data on first run.
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


def load_ports():
    """Load port data as a DataFrame and as a dict keyed by port_id."""
    df = pd.read_csv(os.path.join(DATA_DIR, "ports.csv"))
    return df


def load_ports_dict():
    """Return ports as {port_id: {column: value, ...}}."""
    df = load_ports()
    return df.set_index("port_id").to_dict(orient="index")


def load_routes():
    """Load shipping routes DataFrame."""
    return pd.read_csv(os.path.join(DATA_DIR, "routes.csv"))


def load_bdi():
    """Load cleaned BDI historical data."""
    df = pd.read_csv(os.path.join(DATA_DIR, "bdi_clean.csv"))
    df["ds"] = pd.to_datetime(df["ds"])
    
    # Shift dates so the dataset ends on 2026-09-01 for the hackathon
    target_end_date = pd.to_datetime("2026-09-01")
    delta = target_end_date - df["ds"].max()
    df["ds"] = df["ds"] + delta
    
    return df


def _generate_synthetic_series(start_date, end_date, base, amplitude,
                                trend_per_year, noise_std, seed=42):
    """Generate a synthetic daily price series with trend + seasonality + noise."""
    np.random.seed(seed)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    n = len(dates)

    # Linear trend
    years = np.arange(n) / 365.25
    trend = base + trend_per_year * years

    # Yearly seasonality (prices peak in winter for coal, summer for fuel)
    day_of_year = np.array([d.timetuple().tm_yday for d in dates])
    seasonality = amplitude * np.sin(2 * np.pi * day_of_year / 365.25)

    # Random walk noise
    noise = np.cumsum(np.random.normal(0, noise_std, n))
    noise = noise - np.linspace(noise[0], noise[-1], n)  # detrend the walk

    prices = trend + seasonality + noise
    prices = np.maximum(prices, base * 0.3)  # floor at 30% of base

    return pd.DataFrame({"ds": dates, "y": np.round(prices, 2)})


def load_fuel_prices():
    """Load or generate synthetic VLSFO bunker fuel prices (USD/MT)."""
    path = os.path.join(DATA_DIR, "fuel_prices.csv")
    if not os.path.exists(path):
        df = _generate_synthetic_series(
            start_date="2018-01-01",
            end_date="2026-09-01",
            base=450,       # USD/MT base price
            amplitude=80,   # seasonal swing
            trend_per_year=15,  # gradual increase
            noise_std=3.0,
            seed=101
        )
        df.to_csv(path, index=False)
        return df
    df = pd.read_csv(path)
    df["ds"] = pd.to_datetime(df["ds"])
    return df


def load_commodity_prices():
    """Load or generate synthetic coking coal FOB prices (USD/MT)."""
    path = os.path.join(DATA_DIR, "commodity_prices.csv")
    if not os.path.exists(path):
        df = _generate_synthetic_series(
            start_date="2018-01-01",
            end_date="2026-09-01",
            base=180,       # USD/MT base price
            amplitude=40,   # seasonal swing
            trend_per_year=8,   # gradual increase
            noise_std=2.5,
            seed=202
        )
        df.to_csv(path, index=False)
        return df
    df = pd.read_csv(path)
    df["ds"] = pd.to_datetime(df["ds"])
    return df


# Vessel specifications — single source of truth
# Matches the team's existing specs from port_data.py and vessel_simultor.py
VESSEL_SPECS = {
    "Capesize":  {"max_dwt": 180000, "max_draft": 18.0, "speed_knots": 13.5,
                  "fuel_consumption_mt_day": 55, "daily_hire_usd": 18000},
    "Panamax":   {"max_dwt": 80000,  "max_draft": 14.5, "speed_knots": 13.0,
                  "fuel_consumption_mt_day": 35, "daily_hire_usd": 13000},
    "Supramax":  {"max_dwt": 60000,  "max_draft": 12.0, "speed_knots": 12.5,
                  "fuel_consumption_mt_day": 28, "daily_hire_usd": 11000},
    "Handysize": {"max_dwt": 40000,  "max_draft": 10.5, "speed_knots": 11.5,
                  "fuel_consumption_mt_day": 22, "daily_hire_usd": 9000},
}

# BDI multipliers per vessel type (from team's forecasting.py)
VESSEL_BDI_MULTIPLIERS = {
    "Capesize": 1.5,
    "Panamax": 1.0,
    "Supramax": 0.8,
    "Handysize": 0.6,
}
