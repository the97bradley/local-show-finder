import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from html import unescape
from typing import List
from urllib.request import Request, urlopen

from app.services.venues import Venue


@dataclass
class LocalEvent:
    artist: str
    date: str
    venue: str
    venue_url: str
    ticket_url: str
    latitude: float
    longitude: float
    vibe_tags: list[str]
    scene: str


MONTH_PATTERN = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_REGEX = re.compile(rf"\b({MONTH_PATTERN})\s+([0-3]?\d)(?:,\s*(20\d\d))?\b", re.IGNORECASE)


def _clean_text(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text


def _guess_vibe_tags(snippet: str) -> list[str]:
    s = snippet.lower()
    tags = []
    if any(w in s for w in ["dj", "house", "techno", "dance"]):
        tags += ["electronic", "late-night", "dance"]
    if any(w in s for w in ["indie", "alt", "shoegaze", "dream"]):
        tags += ["indie", "moody", "guitar"]
    if any(w in s for w in ["country", "americana", "folk"]):
        tags += ["americana", "storytelling", "roots"]
    if any(w in s for w in ["metal", "punk", "hardcore"]):
        tags += ["heavy", "loud", "diy"]
    if not tags:
        tags = ["live", "local", "band"]
    return list(dict.fromkeys(tags))


def scrape_venue_events(venue: Venue, horizon_days: int = 90) -> List[LocalEvent]:
    if not venue.website:
        return []

    url = venue.website.strip()
    if not url.startswith("http"):
        return []

    req = Request(url, headers={"User-Agent": "local-show-finder/0.1"})
    try:
        with urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    text = _clean_text(html)
    now = datetime.utcnow().date()
    end = now + timedelta(days=horizon_days)

    events: List[LocalEvent] = []
    for m in DATE_REGEX.finditer(text):
        month = m.group(1)
        day = m.group(2)
        year = m.group(3) or str(now.year)

        try:
            dt = datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()
        except Exception:
            try:
                dt = datetime.strptime(f"{month} {day} {year}", "%b %d %Y").date()
            except Exception:
                continue

        if dt < now or dt > end:
            continue

        start = max(0, m.start() - 80)
        finish = min(len(text), m.end() + 80)
        snippet = text[start:finish].strip()

        artist = snippet[:70].strip(" -|:") or f"Show at {venue.name}"
        events.append(
            LocalEvent(
                artist=artist,
                date=dt.isoformat(),
                venue=venue.name,
                venue_url=url,
                ticket_url=url,
                latitude=venue.latitude,
                longitude=venue.longitude,
                vibe_tags=_guess_vibe_tags(snippet),
                scene="venue-calendar",
            )
        )

    dedup: dict[tuple[str, str], LocalEvent] = {}
    for e in events:
        key = (e.artist.lower(), e.date)
        if key not in dedup:
            dedup[key] = e
    return list(dedup.values())
