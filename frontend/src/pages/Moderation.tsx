import { useEffect, useState } from "react";
import { api } from "../api/client";

export function ModerationPage() {
  const [queue, setQueue] = useState<{ id: string; listing_id: string; listing_title: string; reason: string }[]>([]);
  const [claims, setClaims] = useState<{ id: string; vendor_id: string; claimant_email: string }[]>([]);

  async function refresh() {
    setQueue(await api.moderationQueue());
    setClaims(await api.pendingClaims());
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div>
      <h1>Operations console</h1>

      <h3>Listing moderation queue</h3>
      {queue.length === 0 && <p style={{ color: "#a0aec0" }}>Nothing pending.</p>}
      <ul>
        {queue.map((q) => (
          <li key={q.id}>
            {q.listing_title} — {q.reason}{" "}
            <button
              onClick={async () => {
                await api.publishListing(q.listing_id);
                refresh();
              }}
            >
              Approve &amp; publish
            </button>
          </li>
        ))}
      </ul>

      <h3>Vendor claim requests</h3>
      {claims.length === 0 && <p style={{ color: "#a0aec0" }}>Nothing pending.</p>}
      <ul>
        {claims.map((c) => (
          <li key={c.id}>
            Vendor {c.vendor_id} claimed by {c.claimant_email}{" "}
            <button
              onClick={async () => {
                await api.approveClaim(c.id);
                refresh();
              }}
            >
              Approve claim
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
