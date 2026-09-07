"""On-demand OpenStreetMap/OSRM routing with an offline distance fallback."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from time import monotonic
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import os
import hashlib

import redis

_geocode_cache: dict[str, tuple[float, tuple[float, float]]] = {}
_CACHE_SECONDS = 24 * 60 * 60
_USER_AGENT = os.getenv("ROUTING_USER_AGENT", "FleetFlow/1.0 (local development)")
_GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def _traffic_estimate(duration_minutes: int) -> dict:
    """A transparent local estimate; public OSRM has no live traffic feed."""
    hour = datetime.now().hour
    if 8 <= hour < 11 or 17 <= hour < 21:
        level, multiplier = "High", 0.30
    elif 7 <= hour < 8 or 11 <= hour < 17 or 21 <= hour < 22:
        level, multiplier = "Moderate", 0.12
    else:
        level, multiplier = "Low", 0.03
    delay = round(duration_minutes * multiplier)
    return {"traffic_level": level, "traffic_delay_minutes": delay, "adjusted_duration_minutes": duration_minutes + delay}


def format_duration(minutes: int) -> str:
    """Format minutes for people while retaining numeric values for APIs."""
    days, remainder = divmod(max(0, minutes), 24 * 60)
    hours, remaining_minutes = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} day" + ("s" if days != 1 else ""))
    if hours:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if remaining_minutes or not parts:
        parts.append(f"{remaining_minutes} min")
    return " ".join(parts)


def _json(url: str) -> object:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=8) as response:  # nosec B310 - fixed service URLs below
        return json.loads(response.read().decode("utf-8"))


def geocode(place: str) -> tuple[float, float]:
    cached = _geocode_cache.get(place.casefold())
    if cached and monotonic() - cached[0] < _CACHE_SECONDS:
        return cached[1]
    query = urlencode({"q": place, "format": "jsonv2", "limit": 1})
    results = _json(f"https://nominatim.openstreetmap.org/search?{query}")
    if not results:
        raise ValueError(f"Location not found: {place}")
    location = results[0]
    coordinates = (float(location["lat"]), float(location["lon"]))
    _geocode_cache[place.casefold()] = (monotonic(), coordinates)
    return coordinates


def _straight_line_km(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*origin, *destination))
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(value))


def _route_option(route: dict, index: int) -> dict:
    return {
        "id": index,
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_minutes": max(1, round(route["duration"] / 60)),
        "geometry": route["geometry"],
    }


def _decode_google_polyline(encoded: str) -> list[list[float]]:
    """Convert Google's encoded polyline into GeoJSON longitude/latitude pairs."""
    coordinates, index, latitude, longitude = [], 0, 0, 0
    while index < len(encoded):
        values = []
        for _ in range(2):
            shift, value = 0, 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                value |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            values.append(~(value >> 1) if value & 1 else value >> 1)
        latitude += values[0]
        longitude += values[1]
        coordinates.append([longitude / 1e5, latitude / 1e5])
    return coordinates


def _google_duration_minutes(value: str | None) -> int:
    return max(1, round(float((value or "0s").removesuffix("s")) / 60))


def _google_route(start: str, end: str, route_type: str) -> dict:
    """Use Google Routes API for live traffic and fuel-efficient routing."""
    preference = route_type.strip().casefold()
    request = {
        "origin": {"address": start},
        "destination": {"address": end},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL" if preference in {"traffic avoidance", "fuel-efficient route"} else "TRAFFIC_AWARE",
        "computeAlternativeRoutes": preference == "shortest route",
    }
    if preference == "fuel-efficient route":
        request.update({
            "requestedReferenceRoutes": ["FUEL_EFFICIENT"],
            "extraComputations": ["FUEL_CONSUMPTION"],
            "emissionType": "DIESEL",
        })

    payload = json.dumps(request).encode("utf-8")
    api_request = Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=payload,
        headers={
            "X-Goog-Api-Key": _GOOGLE_MAPS_API_KEY,
            "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.staticDuration,routes.polyline.encodedPolyline,routes.routeLabels,routes.travelAdvisory.fuelConsumptionMicroliters",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(api_request, timeout=12) as response:  # nosec B310 - fixed Google Routes API URL
        routes = json.loads(response.read().decode("utf-8")).get("routes", [])
    if not routes:
        raise ValueError("Google Maps did not return a route")

    if preference == "fuel-efficient route":
        selected = next((route for route in routes if "FUEL_EFFICIENT" in route.get("routeLabels", [])), routes[0])
    elif preference == "shortest route":
        selected = min(routes, key=lambda route: route.get("distanceMeters", float("inf")))
    else:
        selected = min(routes, key=lambda route: _google_duration_minutes(route.get("duration")))

    duration_minutes = _google_duration_minutes(selected.get("duration"))
    static_minutes = _google_duration_minutes(selected.get("staticDuration"))
    delay = max(0, duration_minutes - static_minutes)
    delay_ratio = delay / max(static_minutes, 1)
    traffic_level = "High" if delay_ratio >= 0.25 else "Moderate" if delay_ratio >= 0.08 else "Low"
    return {
        "distance_km": round(selected["distanceMeters"] / 1000, 2),
        "duration_minutes": duration_minutes,
        "eta": (datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)).isoformat(),
        "geometry": {"type": "LineString", "coordinates": _decode_google_polyline(selected["polyline"]["encodedPolyline"])},
        "route_type": route_type,
        "route_mode_note": None,
        "fallback": False,
        "alternatives": [],
        "selected_alternative": 0,
        "toll_gates_estimate": max(0, round(selected["distanceMeters"] / 1000 / 120)),
        "traffic_level": traffic_level,
        "traffic_delay_minutes": delay,
        "adjusted_duration_minutes": duration_minutes,
        "duration_display": format_duration(duration_minutes),
        "adjusted_duration_display": format_duration(duration_minutes),
        "fuel_consumption_microliters": selected.get("travelAdvisory", {}).get("fuelConsumptionMicroliters"),
        "routing_provider": "Google Maps",
    }


def _build_route_uncached(start: str, end: str, route_type: str = "Fastest Route") -> dict:
    preference = route_type.strip().casefold()
    if preference not in {"fastest route", "shortest route", "traffic avoidance", "fuel-efficient route"}:
        raise ValueError("route_type must be Fastest Route, Shortest Route, Traffic Avoidance, or Fuel-Efficient Route")
    if _GOOGLE_MAPS_API_KEY:
        try:
            return _google_route(start, end, route_type)
        except Exception:
            # Retain the existing free routing fallback if Google is temporarily unavailable.
            pass

    origin, destination = geocode(start), geocode(end)
    coordinates = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    try:
        payload = _json(f"https://router.project-osrm.org/route/v1/driving/{coordinates}?overview=full&geometries=geojson&alternatives=true")
        options = [_route_option(item, index) for index, item in enumerate(payload["routes"])]
        if preference == "shortest route" or preference == "fuel-efficient route":
            selected = min(options, key=lambda option: (option["distance_km"], option["duration_minutes"]))
        else:
            selected = min(options, key=lambda option: (option["duration_minutes"], option["distance_km"]))
        distance_km = selected["distance_km"]
        duration_minutes = selected["duration_minutes"]
        details = _traffic_estimate(duration_minutes)
        adjusted_duration = details["adjusted_duration_minutes"]
        details["duration_display"] = format_duration(duration_minutes)
        details["adjusted_duration_display"] = format_duration(adjusted_duration)
        return {"source_coordinates": origin, "destination_coordinates": destination, "distance_km": distance_km, "duration_minutes": duration_minutes, "eta": (datetime.now(timezone.utc) + timedelta(minutes=adjusted_duration)).isoformat(), "geometry": selected["geometry"], "route_type": route_type, "route_mode_note": "Traffic Avoidance and Fuel-Efficient Route are simulated heuristics because public OSRM has no live traffic or fuel model." if preference in {"traffic avoidance", "fuel-efficient route"} else None, "fallback": False, "alternatives": [{key: value for key, value in option.items() if key != "geometry"} for option in options], "selected_alternative": selected["id"], "toll_gates_estimate": max(0, round(distance_km / 120)), **details}
    except Exception:
        distance_km = round(_straight_line_km(origin, destination), 2)
        duration_minutes = max(1, round(distance_km / 45 * 60))
        details = _traffic_estimate(duration_minutes)
        adjusted_duration = details["adjusted_duration_minutes"]
        details["duration_display"] = format_duration(duration_minutes)
        details["adjusted_duration_display"] = format_duration(adjusted_duration)
        return {"source_coordinates": origin, "destination_coordinates": destination, "distance_km": distance_km, "duration_minutes": duration_minutes, "eta": (datetime.now(timezone.utc) + timedelta(minutes=adjusted_duration)).isoformat(), "geometry": {"type": "LineString", "coordinates": [[origin[1], origin[0]], [destination[1], destination[0]]]}, "route_type": route_type, "fallback": True, "alternatives": [{"id": 0, "distance_km": distance_km, "duration_minutes": duration_minutes}], "selected_alternative": 0, "toll_gates_estimate": max(0, round(distance_km / 120)), **details}


def build_route(start: str, end: str, route_type: str = "Fastest Route") -> dict:
    """Return a route cached in Redis for five minutes, with safe local fallback."""
    key = "fleetflow:route:" + hashlib.sha256(f"{start.casefold()}|{end.casefold()}|{route_type.casefold()}".encode()).hexdigest()
    client = None
    try:
        client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True, socket_connect_timeout=0.25)
        cached = client.get(key)
        if cached:
            return json.loads(cached)
    except Exception:
        client = None
    result = _build_route_uncached(start, end, route_type)
    if client:
        try:
            client.setex(key, 300, json.dumps(result))
        except Exception:
            pass
    return result
