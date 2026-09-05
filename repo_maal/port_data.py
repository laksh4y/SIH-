import csv
PORT_DATA_CSV = """port_name,country,port_type,max_draft,max_loa,max_beam,cargo_handling_rate,data_source
Newcastle,Australia,origin,16.2,300,50,2000,verified
Houston,US,origin,13.1,275,44,1500,estimated
Nacala,Mozambique,origin,15.0,280,45,1200,estimated
Vostochny,Russia,origin,16.5,300,50,1800,estimated
Samarinda,Indonesia,origin,9.0,200,32,800,estimated
Paradip,India,destination,16.5,300,46,1800,verified
Vizag,India,destination,16.5,300,42,1700,verified
Gangavaram,India,destination,18.0,300,48,2000,verified
Gopalpur,India,destination,13.0,200,32,1000,estimated
Dhamra,India,destination,18.5,300,50,2000,estimated
Sagar-Sandheads,India,destination,8.5,172,24.3,900,verified
Haldia,India,destination,9.0,240,32.26,1000,verified
"""
with open("dummy_port_data.csv", "w") as f:
    f.write(PORT_DATA_CSV)

# load_port_data - SAME SIGNATURE as the recommendation_engine.py expects

def load_port_data(filename="dummy_port_data.csv"):
    """Returns a dict: {port_name: {column: value, ...}, ...}"""
    with open(filename) as f:
        return {row['port_name']: row for row in csv.DictReader(f)}

# VESSEL_SPECS - matches the values already used in recommendation_engine.py
# (keeping these identical across files avoids feasibility mismatches)

VESSEL_SPECS = {
    "Handysize": {"max_dwt": 40000, "max_draft": 10.5},
    "Supramax":  {"max_dwt": 60000, "max_draft": 12.0},
    "Panamax":   {"max_dwt": 80000, "max_draft": 14.5},
    "Capesize":  {"max_dwt": 180000, "max_draft": 18.0},
}



# get_feasible_vessels - SAME LOGIC/SIGNATURE as vessel_simulator.py

def get_feasible_vessels(origin, dest, cargo_volume, port_data):
    origin_p = port_data[origin]
    dest_p = port_data[dest]
    max_allowed_draft = min(float(origin_p['max_draft']), float(dest_p['max_draft']))
    return [v for v, s in VESSEL_SPECS.items()
            if s["max_draft"] <= max_allowed_draft and s["max_dwt"] >= cargo_volume]


# Test with example port pairs and cargo sizes (task 7)

if __name__ == "__main__":
    port_data = load_port_data("dummy_port_data.csv")

    test_cases = [
        ("Newcastle", "Vizag", 55000),
        ("Newcastle", "Paradip", 30000),
        ("Vostochny", "Haldia", 45000),
        ("Nacala", "Gangavaram", 70000),
    ]

    for origin, dest, cargo in test_cases:
        result = get_feasible_vessels(origin, dest, cargo, port_data)
        print(f"{origin} -> {dest}, {cargo}t: feasible vessels = {result}")
