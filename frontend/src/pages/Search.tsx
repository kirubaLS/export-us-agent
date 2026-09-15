import { useState } from "react";
import { Link } from "react-router-dom";
import { api, type ListingSummary } from "../api/client";
import { VerificationBadge } from "../components/VerificationBadge";
import { PriceDisplay } from "../components/PriceDisplay";

export function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ListingSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResults(await api.searchListings(q));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Find verified Indian export suppliers</h1>
      <p style={{ color: "#718096" }}>
        Search by product, material, or HS classification. Public listings only — every price shown includes
        a public band or a derived estimate; contact details are released after you submit an enquiry.
      </p>
      <form onSubmit={runSearch} style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. ceramic mug, cotton t-shirt"
          style={{ flex: 1, padding: 8 }}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <div style={{ display: "grid", gap: 12 }}>
        {results.map((r) => (
          <Link
            key={r.id}
            to={`/listings/${r.id}`}
            style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 12, textDecoration: "none", color: "inherit" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{r.title}</strong>
              <VerificationBadge tier={r.vendor.verification_tier} />
            </div>
            <div style={{ color: "#718096", fontSize: 13 }}>
              {r.vendor.legal_name} · {r.vendor.city || "India"} {r.hts10 && `· HTS ${r.hts10}`}
            </div>
            <PriceDisplay price={r.price} />
          </Link>
        ))}
        {!loading && results.length === 0 && <p style={{ color: "#a0aec0" }}>No results yet — try a search above.</p>}
      </div>
    </div>
  );
}
