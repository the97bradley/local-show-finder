import json
from dataclasses import dataclass
from typing import List
from urllib.request import Request, urlopen


@dataclass
class Venue:
    name: str
    latitude: float
    longitude: float
    website: str | None = None


def _overpass_query(lat: float, lon: float, radius_m: int) -> str:
    return f"""
[out:json][timeout:25];
(
  nwr(around:{radius_m},{lat},{lon})["amenity"~"music_venue|theatre|arts_centre|nightclub|pub|bar"];
);
out center tags;
""".strip()


def discover_venues(latitude: float, longitude: float, radius_miles: float) -> List[Venue]:
    radius_m = int(max(1000, radius_miles * 1609.34))
    query = _overpass_query(latitude, longitude, radius_m)

    req = Request(
        "https://overpass-api.de/api/interpreter",
        data=query.encode("utf-8"),
        headers={"Content-Type": "text/plain", "User-Agent": "local-show-finder/0.1"},
        method="POST",
    )

    with urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    out: List[Venue] = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        if not name:
            continue

        lat = el.get("lat")
        lon = el.get("lon")
        center = el.get("center", {})
        if lat is None:
            lat = center.get("lat")
        if lon is None:
            lon = center.get("lon")
        if lat is None or lon is None:
            continue

        website = tags.get("website") or tags.get("contact:website")
        out.append(Venue(name=name, latitude=float(lat), longitude=float(lon), website=website))

    dedup: dict[str, Venue] = {}
    for v in out:
        key = v.name.lower()
        if key not in dedup:
            dedup[key] = v
    return list(dedup.values())
