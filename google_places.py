import os
import requests
import streamlit as st

def get_places_nearby(lat: float, lon: float, radius: int, query: str):
    api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
    if not api_key:
        return []

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "location": f"{lat},{lon}",
        "radius": str(radius),
        "key": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    if data.get("status") not in ("OK", "ZERO_RESULTS"):
        return []

    results = []
    for p in data.get("results", []):
        results.append({
            "Name": p.get("name", "Unknown"),
            "Address": p.get("formatted_address") or p.get("vicinity") or "",
            "Rating": p.get("rating", "N/A"),
            "Lat": p.get("geometry", {}).get("location", {}).get("lat"),
            "Lon": p.get("geometry", {}).get("location", {}).get("lng"),
            "Description": ", ".join(p.get("types", [])),
        })
    return results
