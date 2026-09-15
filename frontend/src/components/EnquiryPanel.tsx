import { useState } from "react";
import { api } from "../api/client";

/** Section 5 disclosure model as a UI flow: a buyer must be logged in and
 * must submit a real enquiry before any contact detail is requested, and
 * even then the vendor may not have consented yet (claim_state check on
 * the backend), in which case the release call 409s. */
export function EnquiryPanel({ vendorId, listingId }: { vendorId: string; listingId: string }) {
  const [qty, setQty] = useState<number | undefined>();
  const [destination, setDestination] = useState("");
  const [specification, setSpecification] = useState("");
  const [enquiryId, setEnquiryId] = useState<string | null>(null);
  const [contact, setContact] = useState<{ contact_name: string | null; contact_email: string | null; contact_phone: string | null } | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const loggedIn = !!localStorage.getItem("buyer_token");

  async function submitEnquiry() {
    setStatus(null);
    try {
      const enquiry = await api.createEnquiry({ vendor_id: vendorId, listing_id: listingId, qty, destination, specification });
      setEnquiryId(enquiry.id);
      setStatus("Enquiry sent. Requesting contact details…");
      const released = await api.releaseContact(enquiry.id);
      setContact(released);
      setStatus(null);
    } catch (err) {
      setStatus((err as Error).message);
    }
  }

  if (!loggedIn) {
    return (
      <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 16 }}>
        <h3>Contact this vendor</h3>
        <p style={{ color: "#718096" }}>
          Register a free buyer account to send an enquiry. Contact details are released only after you submit
          a real request for quote (Section 5) — never shown publicly.
        </p>
        <a href="/register">Register as a buyer →</a>
      </div>
    );
  }

  return (
    <div style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 16 }}>
      <h3>Request a quote</h3>
      {!contact ? (
        <>
          <input placeholder="Quantity" type="number" onChange={(e) => setQty(Number(e.target.value))} style={{ width: "100%", marginBottom: 8, padding: 6 }} />
          <input placeholder="Destination (e.g. US-CA)" value={destination} onChange={(e) => setDestination(e.target.value)} style={{ width: "100%", marginBottom: 8, padding: 6 }} />
          <textarea placeholder="Specification / requirements" value={specification} onChange={(e) => setSpecification(e.target.value)} style={{ width: "100%", marginBottom: 8, padding: 6 }} rows={4} />
          <button onClick={submitEnquiry} style={{ width: "100%" }}>
            Send enquiry
          </button>
          {status && <p style={{ color: "#b7791f", fontSize: 13 }}>{status}</p>}
        </>
      ) : (
        <div>
          <p style={{ color: "#2f855a" }}>Enquiry #{enquiryId} sent — contact released:</p>
          <div>{contact.contact_name}</div>
          <div>{contact.contact_email}</div>
          <div>{contact.contact_phone}</div>
        </div>
      )}
    </div>
  );
}
