import { useState } from "react";
import { api } from "../api/client";

/** Table 19 'Indian vendor' onboarding + listing-editor + price-tier-editor
 * screens, collapsed into one flow for the MVP. */
export function VendorOnboardingPage() {
  const [vendorId, setVendorId] = useState<string | null>(null);
  const [vendor, setVendor] = useState({ legal_name: "", city: "", state: "", iec: "", gstin: "" });
  const [listingId, setListingId] = useState<string | null>(null);
  const [listing, setListing] = useState({ title: "", description: "", moq: 500 });
  const [priceTier, setPriceTier] = useState({ qty_min: 500, price_low: 1, price_high: 1.2, incoterm: "FOB" });
  const [log, setLog] = useState<string[]>([]);

  const push = (m: string) => setLog((l) => [...l, m]);

  async function createVendor() {
    const v = await api.createVendor(vendor);
    setVendorId(v.id);
    push(`Vendor profile created — unclaimed, verification tier: ${v.verification_tier}.`);
  }

  async function createListing() {
    if (!vendorId) return;
    const l = await api.createListing({ vendor_id: vendorId, ...listing });
    setListingId(l.listing_id);
    push(`Listing created — auto-classified HTS ${l.hts10 ?? "unclassified"}, state: ${l.state} (awaiting moderation).`);
  }

  async function addPriceTier() {
    if (!listingId) return;
    await api.addPriceTier(listingId, priceTier);
    push("Price tier added.");
  }

  async function publish() {
    if (!listingId) return;
    await api.publishListing(listingId);
    push("Listing published (operator moderation step, simulated here without a review UI).");
  }

  return (
    <div style={{ maxWidth: 520, display: "grid", gap: 24 }}>
      <h1>Vendor onboarding &amp; listing editor</h1>

      <section>
        <h3>1. Company profile</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <input placeholder="Legal name" onChange={(e) => setVendor({ ...vendor, legal_name: e.target.value })} />
          <input placeholder="City" onChange={(e) => setVendor({ ...vendor, city: e.target.value })} />
          <input placeholder="State" onChange={(e) => setVendor({ ...vendor, state: e.target.value })} />
          <input placeholder="IEC" onChange={(e) => setVendor({ ...vendor, iec: e.target.value })} />
          <input placeholder="GSTIN" onChange={(e) => setVendor({ ...vendor, gstin: e.target.value })} />
          <button onClick={createVendor} disabled={!vendor.legal_name}>
            Create profile
          </button>
        </div>
      </section>

      <section style={{ opacity: vendorId ? 1 : 0.5 }}>
        <h3>2. Add a listing</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <input placeholder="Title" onChange={(e) => setListing({ ...listing, title: e.target.value })} />
          <textarea placeholder="Description" rows={3} onChange={(e) => setListing({ ...listing, description: e.target.value })} />
          <input placeholder="MOQ" type="number" value={listing.moq} onChange={(e) => setListing({ ...listing, moq: Number(e.target.value) })} />
          <button onClick={createListing} disabled={!vendorId || !listing.title}>
            Create listing
          </button>
        </div>
      </section>

      <section style={{ opacity: listingId ? 1 : 0.5 }}>
        <h3>3. Price tier</h3>
        <div style={{ display: "grid", gap: 8 }}>
          <input type="number" placeholder="Min qty" value={priceTier.qty_min} onChange={(e) => setPriceTier({ ...priceTier, qty_min: Number(e.target.value) })} />
          <input type="number" placeholder="Low price" value={priceTier.price_low} onChange={(e) => setPriceTier({ ...priceTier, price_low: Number(e.target.value) })} />
          <input type="number" placeholder="High price" value={priceTier.price_high} onChange={(e) => setPriceTier({ ...priceTier, price_high: Number(e.target.value) })} />
          <button onClick={addPriceTier} disabled={!listingId}>
            Add price tier
          </button>
          <button onClick={publish} disabled={!listingId}>
            Publish (moderation approval)
          </button>
        </div>
      </section>

      <section>
        <h3>Activity</h3>
        <ul>
          {log.map((l, i) => (
            <li key={i} style={{ fontSize: 13, color: "#718096" }}>
              {l}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
