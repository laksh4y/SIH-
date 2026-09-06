# SteelRoute AI ⚓

**Intelligent Freight Forecasting & Vessel Optimization for the Ministry of Steel, India**

> 🏛️ SIH26006 · Smart Automation · Team Jaldi the layz · Delhi Technological University

---

## 🚀 What is SteelRoute AI?

SteelRoute AI is a full-stack, AI-powered decision support system that predicts global freight rates, optimizes vessel chartering, and provides actionable cost-saving recommendations for bulk cargo procurement from overseas to India's East Coast.

### Key Capabilities

| Feature | Description |
|---|---|
| **Freight Rate Forecasting** | Prophet ML on historical Baltic Dry Index data with vessel-type scaling |
| **Vessel Optimization** | Recommends the best vessel (Handysize, Supramax, Panamax, Capesize) by checking draft, LOA, and beam constraints |
| **Optimal Chartering Timing** | Identifies the cheapest 7-day window within the forecast horizon |
| **Risk Analysis** | Early warnings for market volatility, port congestion, and fuel price spikes |
| **Idle Scenario Management** | Identifies low-demand windows and suggests repositioning strategies to minimize deadheading |
| **Total Landed Cost** | 6-component cost breakdown (FOB + Freight + Fuel + Port + Insurance + Hire) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, FastAPI, Uvicorn |
| **Machine Learning** | Prophet (Meta), NumPy, Pandas |
| **Frontend** | Vanilla JS, HTML5, CSS3 |
| **Visualization** | Plotly.js, Leaflet.js |
| **Data** | CSV-based (BDI, Fuel Prices, Ports, Routes) |

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python run.py

# 3. Open dashboard
# → http://localhost:8000
```

---

## 📁 Project Structure

```
SIH-dtu-team-mindless-gamers/
├── backend/
│   ├── main.py                 # FastAPI app & API endpoints
│   ├── data_loader.py          # CSV data loading & vessel specs
│   ├── forecasting.py          # Prophet ML forecasting engine
│   ├── route_engine.py         # Voyage calculation & routing
│   ├── vessel_optimizer.py     # Optimization, risk analysis, idle mgmt
│   └── cost_calculator.py      # Total Landed Cost computation
├── frontend/
│   ├── index.html              # Dashboard UI
│   ├── app.js                  # Interactive charts & API integration
│   └── style.css               # Dark-mode glassmorphic design system
├── data/
│   ├── bdi_clean.csv           # Historical Baltic Dry Index
│   ├── fuel_prices.csv         # Bunker fuel price series
│   ├── commodity_prices.csv    # Coking coal FOB prices
│   ├── ports.csv               # Port infrastructure data
│   └── routes.csv              # Shipping route distances
├── run.py                      # Entry point
└── requirements.txt
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ports` | List all ports with metadata |
| `GET` | `/api/routes` | List all shipping routes |
| `GET` | `/api/vessels` | List vessel types and specs |
| `GET` | `/api/forecast/{series}` | Get freight/fuel/commodity forecast |
| `GET` | `/api/voyage` | Calculate voyage details |
| `GET` | `/api/feasibility` | Check vessel feasibility for a route |
| `POST` | `/api/optimize` | Full optimization with risk & idle analysis |
| `GET` | `/api/health` | Health check |

---

## 👥 Team Jaldi the layz — DTU Delhi

Built for Smart India Hackathon 2026 · Problem Statement SIH26006 · Ministry of Steel
