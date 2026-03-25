import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_shows.json"
PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "artist_profiles.json"


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _load_shows() -> List[Dict[str, Any]]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_profiles() -> Dict[str, List[str]]:
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _seed_tags_for_artist(name: str, explicit_tags: List[str], profiles: Dict[str, List[str]]) -> set[str]:
    if explicit_tags:
        return set(t.lower() for t in explicit_tags)
    return set(t.lower() for t in profiles.get(name.lower(), []))


def find_matches(
    latitude: float,
    longitude: float,
    radius_miles: float,
    favorite_artists: List[Dict[str, Any]],
    anchor_artist: Optional[str] = None,
) -> List[Dict[str, Any]]:
    shows = _load_shows()
    profiles = _load_profiles()
    seed_tags: Dict[str, set[str]] = {
        a["name"]: _seed_tags_for_artist(a["name"], a.get("vibe_tags", []), profiles)
        for a in favorite_artists
    }

    if anchor_artist:
        if anchor_artist in seed_tags:
            seed_tags = {anchor_artist: seed_tags[anchor_artist]}
        else:
            seed_tags = {
                anchor_artist: set(t.lower() for t in profiles.get(anchor_artist.lower(), []))
            }

    has_any_seed_tags = any(len(tags) > 0 for tags in seed_tags.values())

    out = []
    for s in shows:
        dist = _haversine_miles(latitude, longitude, s["latitude"], s["longitude"])
        if dist > radius_miles:
            continue

        artist_tags = set(t.lower() for t in s.get("vibe_tags", []))
        best_overlap = 0
        similar_to: List[str] = []
        for seed_name, tags in seed_tags.items():
            overlap = len(artist_tags.intersection(tags))
            if overlap > best_overlap:
                best_overlap = overlap
                similar_to = [seed_name]
            elif overlap == best_overlap and overlap > 0:
                similar_to.append(seed_name)

        score = min(1.0, (best_overlap / 6.0) + max(0, (radius_miles - dist) / max(radius_miles, 1)) * 0.2)
        if best_overlap == 0 and has_any_seed_tags:
            continue

        reasons = [
            f"Tag overlap: {best_overlap}",
            f"Scene: {s.get('scene', 'unknown')}",
        ]
        if not has_any_seed_tags:
            reasons.append("Fallback mode: no known tags for seed artists yet")

        out.append(
            {
                "artist": s["artist"],
                "date": s["date"],
                "venue": s["venue"],
                "venue_url": s["venue_url"],
                "ticket_url": s["ticket_url"],
                "distance_miles": round(dist, 1),
                "similar_to": similar_to,
                "match_score": round(score, 3),
                "reasons": reasons,
            }
        )

    out.sort(key=lambda r: r["match_score"], reverse=True)
    return out
