# local-show-finder

Vibe-first local show discovery app.

## What this initial build includes

- **Python FastAPI backend** (`backend/`)
  - `POST /api/v1/shows/recommend`
  - Filters shows by radius from a location
  - Matches local shows to your seed artists using vibe-tag overlap + distance
- **JS frontend (Next.js)** (`frontend/`)
  - Enter city + coordinates + radius
  - Paste seed artists (tags optional)
  - Optional anchor artist mode
  - See matched shows with “similar to” explanations

## Run locally (quickest)

```bash
docker compose up
```

Then open:
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## API request shape

`POST /api/v1/shows/recommend`

```json
{
  "city": "Denver",
  "latitude": 39.7392,
  "longitude": -104.9903,
  "radius_miles": 20,
  "favorite_artists": [
    {"name": "Tame Impala", "vibe_tags": ["indie electronic", "dream pop", "psych"]}
  ],
  "anchor_artist": "Tame Impala"
}
```

## Next implementation steps

1. Spotify + Apple import (OAuth + saved artists)
2. Real event ingestion (Songkick/Eventbrite/venue crawlers)
3. Audio embedding service for true vibe matching
4. Postgres + pgvector + persistent user accounts
