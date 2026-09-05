import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from functools import lru_cache

# Constants
BDI_URL = "https://raw.githubusercontent.com/ajoposor/Baltic-Dry-Index/master/Old_Data_Baltic_Dry_Index.csv"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAN_DATA_PATH = os.path.join(BASE_DIR, "bdi_clean.csv")
PLOT_PATH = os.path.join(BASE_DIR, "bdi_forecast_plot.png")

# Vessel scaling multipliers (approximate ratios for index proxy)
# Assuming Panamax is 1.0, Capesize is more expensive, Handysize is cheaper.
VESSEL_MULTIPLIERS = {
    "Capesize": 1.5,
    "Panamax": 1.0,
    "Supramax": 0.8,
    "Handysize": 0.6
}

def prepare_data():
    """
    Downloads raw BDI data (1985-2013 proxy), cleans it to a gap-free daily calendar,
    handles missing values, and saves it to bdi_clean.csv.
    """
    if not os.path.exists(CLEAN_DATA_PATH):
        print("Downloading and cleaning historical BDI data...")
        df = pd.read_csv(BDI_URL)
        # The columns are 'x' (date) and 'y' (price)
        df['Date'] = pd.to_datetime(df['x'])
        df = df.rename(columns={'y': 'Price'})
        df = df.set_index('Date')
        
        # Create gap-free daily calendar
        idx = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(idx)
        df = df.ffill().bfill() # fill NaNs
        
        df_clean = df.reset_index().rename(columns={'index': 'ds', 'Price': 'y'})
        df_clean = df_clean[['ds', 'y']]
        df_clean.to_csv(CLEAN_DATA_PATH, index=False)
        return df_clean
    else:
        return pd.read_csv(CLEAN_DATA_PATH)

@lru_cache(maxsize=4)
def get_model(vessel_type):
    """
    Retrieves the dataset, applies vessel multiplier, fits Prophet on log(rate),
    and caches the model per vessel type to avoid refitting.
    """
    df = prepare_data()
    df['ds'] = pd.to_datetime(df['ds'])
    
    # Scale base BDI by vessel type volatility/level multipliers
    multiplier = VESSEL_MULTIPLIERS.get(vessel_type, 1.0)
    df['y'] = df['y'] * multiplier
    
    # Log transform to prevent negative forecasts
    df['y'] = np.log(df['y'])
    
    m = Prophet(daily_seasonality=False, yearly_seasonality=True)
    m.fit(df)
    return m

def forecast_curve(vessel_type, days_ahead):
    """
    Returns the full forecasted curve for a specific vessel type up to days_ahead.
    Useful for Lakshay's 'best entry timing' logic and Priya's rate chart.
    """
    m = get_model(vessel_type)
    future = m.make_future_dataframe(periods=days_ahead)
    fcst = m.predict(future)
    
    # Exponentiate to transform log values back to raw values
    fcst['yhat'] = np.exp(fcst['yhat'])
    fcst['yhat_lower'] = np.exp(fcst['yhat_lower'])
    fcst['yhat_upper'] = np.exp(fcst['yhat_upper'])
    
    return fcst[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days_ahead)

def forecast_rates(vessel_type, days_ahead):
    """
    Returns the specific rate forecast (predicted, lower, upper) for a target day ahead.
    This matches the specific signature the task calls for.
    """
    curve = forecast_curve(vessel_type, days_ahead)
    target = curve.iloc[-1]
    return {
        "predicted_rate": float(target['yhat']),
        "lower_bound": float(target['yhat_lower']),
        "upper_bound": float(target['yhat_upper']),
        "target_date": target['ds'].strftime("%Y-%m-%d")
    }

def generate_plot():
    """
    Generates a forecast plot showing history and 90-day forecast.
    """
    print("Generating forecast plot...")
    m = get_model("Panamax")
    future = m.make_future_dataframe(periods=90)
    fcst = m.predict(future)
    
    fig = m.plot(fcst)
    plt.title("Baltic Dry Index - 90-Day Forecast (Log Scale Fit)")
    plt.xlabel("Date")
    plt.ylabel("Log(Freight Rate)")
    fig.savefig(PLOT_PATH)
    print(f"Plot saved to {PLOT_PATH}")

if __name__ == "__main__":
    # Test execution and generate artifacts
    prepare_data()
    generate_plot()
    
    print("\nTesting 30, 60, 90 day forecasts for Panamax:")
    print("30 days:", forecast_rates("Panamax", 30))
    print("60 days:", forecast_rates("Panamax", 60))
    print("90 days:", forecast_rates("Panamax", 90))
    
    print("\nTesting vessel types at 30 days:")
    for v in ["Capesize", "Panamax", "Supramax", "Handysize"]:
        print(f"{v}: {forecast_rates(v, 30)['predicted_rate']:.2f}")
