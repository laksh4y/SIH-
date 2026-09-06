"""
run.py — Entry point for SteelRoute AI.
Starts the FastAPI server with uvicorn.
"""

import uvicorn
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 50)
    print("  SteelRoute AI -- Starting Server")
    print("  Intelligent Freight Forecasting")
    print("  Ministry of Steel - SIH26006")
    print("=" * 50)
    print()

    # Pre-generate synthetic data on first run
    print("Loading data...")
    from backend.data_loader import load_fuel_prices, load_commodity_prices
    load_fuel_prices()
    load_commodity_prices()
    print("[OK] Data loaded successfully.")
    print()

    print("Starting server at http://localhost:8000")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
