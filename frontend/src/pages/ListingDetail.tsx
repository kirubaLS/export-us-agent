import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type ListingDetail, type LandedCostResponse } from "../api/client";
import { VerificationBadge } from "../components/VerificationBadge";
import { PriceDisplay } from "../components/PriceDisplay";
import { EnquiryPanel } from "../components/EnquiryPanel";

export function ListingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [landed, setLanded] = useState<LandedCostResponse | null>(null);
  const [destination, setDestination] = useState("US-CA");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getListing(id).then(setListing).catch((e) => setError(e.message));
  }, [id]);

  async function computeLanded() {
    if (!listing || !listing.hts10) return;
    const vendorTier = listing.price.find((p) => p.source === "vendor" || p.source === "derived");
    const unitPrice = vendorTier?.price_low ?? 1;
    const result = await api.landedCost({ hts10: listing.hts10, destination, unit_price: unitPrice });
    setLanded(result);
  }

  if (error) return <p style={{ color: "crimson" }}>{error}</p>;
  if (!listing) return <p>Loading…</p>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24 }}>
      <div>
        <h1>{listing.title}</h1>
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <VerificationBadge tier={listing.vendor.verification_tier} />
          <span style={{ color: "#718096" }}>
            {listing.vendor.legal_name} · {listing.vendor.city}, {listing.vendor.state}
          </span>
        </div>
        <p>{listing.description}</p>
        {listing.hts10 && <p style={{ color: "#718096" }}>HTS classification: {listing.hts10}</p>}
        {listing.moq && <p style={{ color: "#718096" }}>MOQ: {listing.moq} units · Lead time: {listing.lead_time_days ?? "—"} days</p>}

        <h3>Price</h3>
        <PriceDisplay price={listing.price} />

        <h3 style={{ marginTop: 24 }}>Landed cost estimate</h3>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="Destination, e.g. US-CA" />
          <button onClick={computeLanded} disabled={!listing.hts10}>
            Calculate
          </button>
        </div>
        {landed && (
          <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 12 }}>
            <div>Vendor price: {landed.unit_price} / unit</div>
            {landed.components.map((c, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                <span>
                  {c.label} {!c.sourced && <em style={{ color: "#a0aec0" }}>(est.)</em>}
                </span>
                <span>{c.amount}</span>
              </div>
            ))}
            <hr />
            <strong>
              Landed: {landed.landed_total} (+{landed.markup_pct}%)
            </strong>
            {landed.partial && <p style={{ color: "#b7791f" }}>Duty rate not available for this classification — treat as incomplete.</p>}
            <p style={{ fontSize: 11, color: "#a0aec0" }}>{landed.disclaimer}</p>
          </div>
        )}
      </div>

      <EnquiryPanel vendorId={listing.vendor.id} listingId={listing.id} />
    </div>
  );
}
