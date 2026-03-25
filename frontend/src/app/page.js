"use client";

import { useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export default function Home() {
  const [city, setCity] = useState("Denver");
  const [latitude, setLatitude] = useState("39.7392");
  const [longitude, setLongitude] = useState("-104.9903");
  const [radius, setRadius] = useState("20");
  const [anchorArtist, setAnchorArtist] = useState("");
  const [artistsText, setArtistsText] = useState(
    "Tame Impala|indie electronic,dream pop,psych\nMJ Lenderman|alt-country,americana,indie rock",
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
    <main className="container">
      <header className="header">
        <h1 className="title">Local Show Finder</h1>
        <p className="subtitle">
          Find upcoming local shows that match your taste by <strong>vibe</strong>,
          not just popularity.
        </p>
      </header>

      <section className="panel">
        <div className="grid">
          <label className="label">
            City
            <input className="input" value={city} onChange={(e) => setCity(e.target.value)} />
          </label>
          <label className="label">
            Radius (miles)
            <input className="input" value={radius} onChange={(e) => setRadius(e.target.value)} />
          </label>
          <label className="label">
            Latitude
            <input className="input" value={latitude} onChange={(e) => setLatitude(e.target.value)} />
          </label>
          <label className="label">
            Longitude
            <input className="input" value={longitude} onChange={(e) => setLongitude(e.target.value)} />
          </label>
        </div>

        <div style={{ marginTop: 10 }}>
          <label className="label">
            Optional anchor artist
            <input
              className="input"
              value={anchorArtist}
              onChange={(e) => setAnchorArtist(e.target.value)}
              placeholder="e.g. Tame Impala"
            />
          </label>
        </div>

        <div style={{ marginTop: 10 }}>
          <label className="label">
            Favorite artists (one per line: <code>Artist|tag1,tag2</code>)
            <textarea
              className="textarea"
              rows={8}
              value={artistsText}
              onChange={(e) => setArtistsText(e.target.value)}
            />
          </label>
        </div>

        <div className="row" style={{ marginTop: 10 }}>
          <button className="btn" onClick={runSearch} disabled={loading}>
            {loading ? "Finding vibe matches..." : "Find Shows"}
          </button>
          <span className="meta">API: {API_BASE}</span>
        </div>
      </section>

      <h2 className="section-title">Matches</h2>
      {results.length === 0 && <p className="meta">No matches yet.</p>}

      {results.map((r) => (
        <article key={`${r.artist}-${r.date}`} className="card">
          <h3>{r.artist}</h3>
          <p className="meta">
            {r.date} • {r.venue} • {r.distance_miles} mi
          </p>
          <p>
            Similar to: <strong>{r.similar_to.join(", ") || "-"}</strong>
          </p>
          <span className="score">Match score {r.match_score}</span>
          <p className="meta" style={{ marginTop: 8 }}>
            Why: {r.reasons.join(" • ")}
          </p>
          <p className="links">
            <a href={r.ticket_url} target="_blank">
              Tickets
            </a>{" "}
            •{" "}
            <a href={r.venue_url} target="_blank">
              Venue
            </a>
          </p>
        </article>
      ))}
    </main>
  );
}
