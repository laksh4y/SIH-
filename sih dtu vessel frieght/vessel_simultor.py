import csv

def load_port_data(filename):
    with open(filename) as f:
        return {row['port_name']: row for row in csv.DictReader(f)}

VESSEL_SPECS = {
    "Handysize": {"max_dwt": 40000, "max_draft": 10.5},
    "Supramax":  {"max_dwt": 60000, "max_draft": 12.0},
    "Panamax":   {"max_dwt": 80000, "max_draft": 14.5},
    "Capesize":  {"max_dwt": 180000, "max_draft": 18.0},
}

def get_feasible_vessels(origin, dest, cargo_volume, port_data):
    origin_p = port_data[origin]
    dest_p = port_data[dest]
    max_allowed_draft = min(float(origin_p['max_draft']), float(dest_p['max_draft']))
    return [v for v, s in VESSEL_SPECS.items()
            if s["max_draft"] <= max_allowed_draft and s["max_dwt"] >= cargo_volume]


port_data = load_port_data('dummy_port_data.csv')  # placeholder for now
from forecasting import forecast_rates   # adjust filename to match yours

def recommend_vessel(origin, dest, cargo_volume, contract_duration):
    feasible = get_feasible_vessels(origin, dest, cargo_volume, port_data)
    if not feasible:
        return {"error": "No vessel type fits the given ports and cargo volume."}
    
    # get full day-by-day forecast ONCE per vessel type
    forecasts = {
        v: [forecast_rates(v, d)['predicted_rate'] for d in range(1, contract_duration + 1)]
        for v in feasible
    }
    
    # rank by average rate over the contract duration
    ranked = sorted(forecasts.items(), key=lambda x: sum(x[1]) / len(x[1]))
    best_vessel, best_daily_rates = ranked[0]
    
    best_timing = find_best_window(best_daily_rates, window=7)
    
    return {
        "recommended_vessel": best_vessel,
        "forecasted_rate": round(sum(best_daily_rates) / len(best_daily_rates), 2),
        "best_timing_window": best_timing,
    }

def find_best_window(daily_rates, window=7):
    best_start, best_avg = 0, float('inf')
    for i in range(len(daily_rates) - window + 1):
        avg = sum(daily_rates[i:i+window]) / window
        if avg < best_avg:
            best_avg, best_start = avg, i + 1
    return {"start_day": best_start, "end_day": best_start + window - 1, "avg_rate": round(best_avg, 2)}

if __name__ == "__main__":
    print("=== Vessel Recommendation Tool ===")
    origin = input("Enter origin port: ")
    dest = input("Enter destination port: ")
    cargo_volume = int(input("Enter cargo volume (tonnes): "))
    contract_duration = int(input("Enter contract duration (days): "))

    result = recommend_vessel(origin, dest, cargo_volume, contract_duration)

    print("\n--- Recommendation ---")
    print(result)
