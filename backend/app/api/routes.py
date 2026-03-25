from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.matching import find_matches

router = APIRouter()


class ArtistSeed(BaseModel):
    name: str
    vibe_tags: List[str] = Field(default_factory=list)


class FeedRequest(BaseModel):
    city: str
    latitude: float
    longitude: float
    radius_miles: float = 25
    favorite_artists: List[ArtistSeed] = Field(default_factory=list)
    anchor_artist: Optional[str] = None


class ShowMatch(BaseModel):
    artist: str
    date: str
    venue: str
    venue_url: str
    ticket_url: str
    distance_miles: float
    similar_to: List[str]
    match_score: float
    reasons: List[str]


class FeedResponse(BaseModel):
    city: str
    results: List[ShowMatch]


@router.post("/shows/recommend", response_model=FeedResponse)
def recommend_shows(payload: FeedRequest) -> FeedResponse:
    results = find_matches(
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_miles=payload.radius_miles,
        favorite_artists=[a.model_dump() for a in payload.favorite_artists],
        anchor_artist=payload.anchor_artist,
    )
    return FeedResponse(city=payload.city, results=results)
