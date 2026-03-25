"use client";

import { useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export default function Home() {
  const [city, setCity] = useState("Denver");
  const [latitude, setLatitude] = useState("39.7392");
  const [longitude, setLongitude] = useState("-104.9903");
  const [radius, setRadius] = useState("20");
  const [anchorArtist, setAnchorArtist] = useState("");
  const [artistsText, setArtistsText] = useState(
    "Tame Impala|indie electronic,dream pop,psych\nMJ Lenderman|alt-country,americana,indie rock"
  );
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const parsedArtists = useMemo(() => {
    return artistsText
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [name, tags] = line.split("|");
        return {
          name: (name || "").trim(),
          vibe_tags: (tags || "")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        };
      })
      .filter((a) => a.name);
  }, [artistsText]);

  async function runSearch() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/shows/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city,
          latitude: Number(latitude),
          longitude: Number(longitude),
          radius_miles: Number(radius),
          favorite_artists: parsedArtists,
          anchor_artist: anchorArtist || null,
        }),
      });
      const data = await res.json();
      setResults(data.results || []);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Local Show Finder</h1>
      <p>Vibe-first local show discovery from your favorite artists.</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, maxWidth: 900 }}>
        <label>City<input value={city} onChange={(e) => setCity(e.target.value)} /></label>
        <label>Radius (miles)<input value={radius} onChange={(e) => setRadius(e.target.value)} /></label>
        <label>Latitude<input value={latitude} onChange={(e) => setLatitude(e.target.value)} /></label>
        <label>Longitude<input value={longitude} onChange={(e) => setLongitude(e.target.value)} /></label>
      </div>

      <div style={{ marginTop: 12 }}>
        <label>Optional anchor artist<input value={anchorArtist} onChange={(e) => setAnchorArtist(e.target.value)} /></label>
      </div>

      <div style={{ marginTop: 12 }}>
        <label>Favorite artists (one per line: <code>Artist|tag1,tag2</code>)</label>
        <textarea rows={8} style={{ width: "100%" }} value={artistsText} onChange={(e) => setArtistsText(e.target.value)} />
      </div>

      <button onClick={runSearch} disabled={loading}>{loading ? "Searching..." : "Find Shows"}</button>

      <hr />
      <h2>Matches</h2>
      {results.length === 0 && <p>No matches yet.</p>}
      {results.map((r) => (
        <article key={`${r.artist}-${r.date}`} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 12, marginBottom: 10 }}>
          <h3>{r.artist}</h3>
          <p>{r.date} • {r.venue} • {r.distance_miles} mi</p>
          <p>Similar to: <strong>{r.similar_to.join(", ") || "-"}</strong></p>
          <p>Score: {r.match_score}</p>
          <p>Why: {r.reasons.join(" • ")}</p>
          <p><a href={r.ticket_url} target="_blank">Tickets</a> • <a href={r.venue_url} target="_blank">Venue</a></p>
        </article>
      ))}
    </main>
  );
}
