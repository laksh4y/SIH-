"""
route_engine.py — Route lookup and voyage calculations.
Calculates voyage duration, fuel consumption, and port time.
"""

from backend.data_loader import load_routes, load_ports_dict, VESSEL_SPECS


_routes_cache = None
_ports_cache = None


def _get_routes():
    global _routes_cache
    if _routes_cache is None:
        _routes_cache = load_routes()
    return _routes_cache


def _get_ports():
    global _ports_cache
    if _ports_cache is None:
        _ports_cache = load_ports_dict()
    return _ports_cache


def find_route(origin_id, dest_id):
    """Find a route between two ports. Returns route dict or None."""
    routes = _get_routes()
    match = routes[
        (routes["origin_port_id"] == origin_id) &
        (routes["dest_port_id"] == dest_id)
    ]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def get_all_routes_for_dest(dest_id):
    """Get all routes arriving at a destination port."""
    routes = _get_routes()
    return routes[routes["dest_port_id"] == dest_id].to_dict(orient="records")


def calculate_voyage(origin_id, dest_id, vessel_type):
    """
    Calculate voyage details for a given route and vessel type.

    Returns:
        dict with: sea_days, port_days_origin, port_days_dest, total_days,
                   fuel_consumed_mt, distance_nm
    """
    route = find_route(origin_id, dest_id)
    if route is None:
        return None

    vessel = VESSEL_SPECS.get(vessel_type)
    if vessel is None:
        return None

    ports = _get_ports()
    origin_port = ports.get(origin_id, {})
    dest_port = ports.get(dest_id, {})

    distance_nm = route["distance_nm"]
    speed = vessel["speed_knots"]

    # Sea transit time
    sea_days = distance_nm / (speed * 24)

    # Port time = cargo loading/unloading + congestion
    # Assume full cargo = vessel max_dwt
    cargo_mt = vessel["max_dwt"]

    origin_handling_rate = float(origin_port.get("cargo_handling_rate_tpd", 1500))
    dest_handling_rate = float(dest_port.get("cargo_handling_rate_tpd", 1500))

    port_days_origin = (cargo_mt / origin_handling_rate) + float(
        origin_port.get("typical_congestion_days", 2)
    )
    port_days_dest = (cargo_mt / dest_handling_rate) + float(
        dest_port.get("typical_congestion_days", 2)
    )

    total_days = sea_days + port_days_origin + port_days_dest

    # Fuel consumption (only during sea transit, reduced in port)
    fuel_at_sea = vessel["fuel_consumption_mt_day"] * sea_days
    fuel_in_port = vessel["fuel_consumption_mt_day"] * 0.15 * (
        port_days_origin + port_days_dest
    )
    fuel_consumed_mt = fuel_at_sea + fuel_in_port

    return {
        "distance_nm": distance_nm,
        "sea_days": round(sea_days, 1),
        "port_days_origin": round(port_days_origin, 1),
        "port_days_dest": round(port_days_dest, 1),
        "total_days": round(total_days, 1),
        "fuel_consumed_mt": round(fuel_consumed_mt, 1),
        "cargo_mt": cargo_mt,
        "route_id": route["route_id"],
        "cargo_type": route.get("cargo_type", "Bulk"),
    }
