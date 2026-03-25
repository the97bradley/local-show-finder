import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from urllib.request import urlopen

from app.services.events import scrape_venue_events
from app.services.venues import discover_venues

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_shows.json"
PROFILES_PATH = Path(__file__).resolve().parents[1] / "data" / "artist_profiles.json"
ITUNES_CACHE: Dict[str, List[str]] = {}


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


def _genre_to_tags(genre: str) -> List[str]:
    g = genre.lower().strip()
    if not g:
        return []

    seed = {
        "pop": ["pop", "melodic", "hooky", "mainstream"],
        "alternative": ["alternative", "indie", "guitar", "moody"],
        "indie": ["indie", "alt", "melodic", "scene"],
        "rock": ["rock", "live band", "guitar", "energetic"],
        "electronic": ["electronic", "synth", "dance", "late-night"],
        "dance": ["dance", "electronic", "club", "late-night"],
        "house": ["house", "club", "electronic", "groove"],
        "hip-hop": ["hip-hop", "rhythmic", "bass-heavy", "urban"],
        "rap": ["rap", "hip-hop", "rhythmic", "urban"],
        "country": ["country", "americana", "storytelling", "roots"],
        "folk": ["folk", "acoustic", "storytelling", "intimate"],
        "jazz": ["jazz", "improv", "instrumental", "live"],
        "r&b": ["r&b", "soulful", "groove", "melodic"],
        "soul": ["soul", "warm", "groove", "vocals"],
        "metal": ["metal", "heavy", "aggressive", "loud"],
        "punk": ["punk", "raw", "fast", "diy"],
    }

    for key, tags in seed.items():
        if key in g:
            return tags

    return [g, "live", "band", "scene"]


def _fetch_itunes_tags(name: str) -> List[str]:
    key = name.lower().strip()
    if key in ITUNES_CACHE:
        return ITUNES_CACHE[key]

    try:
        url = f"https://itunes.apple.com/search?term={quote_plus(name)}&entity=musicArtist&limit=1"
        with urlopen(url, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        results = payload.get("results", [])
        if results:
            genre = str(results[0].get("primaryGenreName", "")).strip()
            tags = _genre_to_tags(genre)
            ITUNES_CACHE[key] = tags
            return tags
    except Exception:
        pass

    ITUNES_CACHE[key] = []
    return []


def _seed_tags_for_artist(name: str, explicit_tags: List[str], profiles: Dict[str, List[str]]) -> set[str]:
    if explicit_tags:
        return set(t.lower() for t in explicit_tags)

    profile_tags = profiles.get(name.lower(), [])
    if profile_tags:
        return set(t.lower() for t in profile_tags)

    return set(t.lower() for t in _fetch_itunes_tags(name))


def _load_live_shows(latitude: float, longitude: float, radius_miles: float) -> List[Dict[str, Any]]:
    venues = discover_venues(latitude, longitude, radius_miles)

    rows: List[Dict[str, Any]] = []
    for venue in venues:
        events = scrape_venue_events(venue, horizon_days=90)
        for e in events:
            rows.append(
                {
                    "artist": e.artist,
                    "date": e.date,
                    "venue": e.venue,
                    "venue_url": e.venue_url,
                    "ticket_url": e.ticket_url,
                    "latitude": e.latitude,
                    "longitude": e.longitude,
                    "vibe_tags": e.vibe_tags,
                    "scene": e.scene,
                }
            )

    return rows


def find_matches(
    latitude: float,
    longitude: float,
    radius_miles: float,
    favorite_artists: List[Dict[str, Any]],
    anchor_artist: Optional[str] = None,
) -> List[Dict[str, Any]]:
    shows = _load_live_shows(latitude, longitude, radius_miles)
    if not shows:
        shows = _load_shows()  # fallback for local dev when scraping yields nothing

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

        artist_lc = str(s.get("artist", "")).lower()
        exact_seed_name = next((seed for seed in seed_tags.keys() if seed.lower() in artist_lc), None)
        if exact_seed_name:
            similar_to = [exact_seed_name]
            best_overlap = max(best_overlap, 6)

        score = min(1.0, (best_overlap / 6.0) + max(0, (radius_miles - dist) / max(radius_miles, 1)) * 0.2)
        if exact_seed_name:
            score = 1.0

        if best_overlap == 0 and has_any_seed_tags:
            continue

        reasons = [
            f"Tag overlap: {best_overlap}",
            f"Scene: {s.get('scene', 'unknown')}",
            f"Source venue: {s.get('venue', 'unknown')}",
        ]
        if exact_seed_name:
            reasons.insert(0, "Exact artist name match in scraped venue calendar")
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

    deduped: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    for row in out:
        key = (row["artist"].lower(), row["date"], row["venue"].lower())
        if key not in deduped or row["match_score"] > deduped[key]["match_score"]:
            deduped[key] = row

    final = list(deduped.values())
    final.sort(key=lambda r: r["match_score"], reverse=True)
    return final
