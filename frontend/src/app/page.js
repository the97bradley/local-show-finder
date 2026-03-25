"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export default function Home() {
  const [city, setCity] = useState("Denver");
  const [address, setAddress] = useState("Denver, CO");
  const [latitude, setLatitude] = useState("39.7392");
  const [longitude, setLongitude] = useState("-104.9903");
  const [radius, setRadius] = useState("20");
  const [anchorArtist, setAnchorArtist] = useState("");
  const [artistsText, setArtistsText] = useState(
    "Tame Impala\nMJ Lenderman\nKhruangbin",
  );
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const circleRef = useRef(null);
  const mapNodeRef = useRef(null);

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

  useEffect(() => {
    let mounted = true;
    if (mapRef.current || !mapNodeRef.current) return;

    (async () => {
      const L = (await import("leaflet")).default;
      if (!mounted || mapRef.current || !mapNodeRef.current) return;

      const lat = Number(latitude);
      const lon = Number(longitude);
      const radMeters = Number(radius) * 1609.34;

      const map = L.map(mapNodeRef.current).setView([lat, lon], 11);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);

      const marker = L.marker([lat, lon], { draggable: true }).addTo(map);
      const circle = L.circle([lat, lon], {
        radius: radMeters,
        color: "#6d7cff",
        fillColor: "#6d7cff",
        fillOpacity: 0.18,
        weight: 2,
      }).addTo(map);

      marker.on("dragend", () => {
        const ll = marker.getLatLng();
        setLatitude(ll.lat.toFixed(6));
        setLongitude(ll.lng.toFixed(6));
        circle.setLatLng(ll);
      });

      map.on("click", (e) => {
        marker.setLatLng(e.latlng);
        circle.setLatLng(e.latlng);
        setLatitude(e.latlng.lat.toFixed(6));
        setLongitude(e.latlng.lng.toFixed(6));
      });

      map.on("contextmenu", (e) => {
        const center = marker.getLatLng();
        const meters = center.distanceTo(e.latlng);
        const miles = Math.max(1, meters / 1609.34);
        setRadius(miles.toFixed(1));
        circle.setRadius(miles * 1609.34);
      });

      mapRef.current = map;
      markerRef.current = marker;
      circleRef.current = circle;
    })();

    return () => {
      mounted = false;
      if (mapRef.current) mapRef.current.remove();
      mapRef.current = null;
      markerRef.current = null;
      circleRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!markerRef.current || !circleRef.current || !mapRef.current) return;
    const lat = Number(latitude);
    const lon = Number(longitude);
    const ll = { lat, lng: lon };
    markerRef.current.setLatLng(ll);
    circleRef.current.setLatLng(ll);
    circleRef.current.setRadius(Number(radius) * 1609.34);
    mapRef.current.panTo(ll);
  }, [latitude, longitude, radius]);

  async function geocodeAddress() {
    const q = address.trim();
    if (!q) return;
    const r = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(q)}&limit=1`,
    );
    const data = await r.json();
    if (!data?.length) return;
    setLatitude(Number(data[0].lat).toFixed(6));
    setLongitude(Number(data[0].lon).toFixed(6));
  }

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
          Enter an address, set your radius on the map, then find vibe-matched
          local shows.
        </p>
      </header>

      <section className="panel">
        <div className="grid">
          <label className="label">
            City
            <input className="input" value={city} onChange={(e) => setCity(e.target.value)} />
          </label>
          <label className="label">
            Address
            <div className="row">
              <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} />
              <button className="btn" type="button" onClick={geocodeAddress}>Locate</button>
            </div>
          </label>
        </div>

        <div className="mapWrap" style={{ marginTop: 12 }}>
          <div ref={mapNodeRef} className="map" />
        </div>
        <p className="meta" style={{ marginTop: 8 }}>
          Tip: drag marker to move center. Right-click map edge to resize circle.
          Current radius: {radius} mi.
        </p>

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
            Favorite artists (one per line, tags optional: <code>Artist</code> or <code>Artist|tag1,tag2</code>)
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
            <a href={r.ticket_url} target="_blank">Tickets</a> • <a href={r.venue_url} target="_blank">Venue</a>
          </p>
        </article>
      ))}
    </main>
  );
}
