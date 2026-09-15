const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("buyer_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Vendor {
  id: string;
  legal_name: string;
  trade_name: string | null;
  city: string | null;
  state: string | null;
  verification_tier: string;
  claim_state: string;
  response_rate: number | null;
  median_response_hours: number | null;
}

export interface PriceLine {
  source: "vendor" | "derived" | "insufficient_data";
  label?: string;
  price_low?: number;
  price_high?: number | null;
  currency?: string;
  incoterm?: string;
  qty_min?: number;
  qty_max?: number | null;
  disclosure?: string;
}

export interface ListingSummary {
  id: string;
  title: string;
  vendor: { id: string; legal_name: string; verification_tier: string; city: string | null };
  hts10: string | null;
  taxonomy_path: string | null;
  price: PriceLine[];
}

export interface ListingDetail {
  id: string;
  title: string;
  description: string;
  specs: Record<string, unknown>;
  hts10: string | null;
  taxonomy_path: string | null;
  moq: number | null;
  lead_time_days: number | null;
  certifications: string[];
  images: string[];
  vendor: Vendor;
  price: PriceLine[];
}

export interface LandedCostComponent {
  label: string;
  amount: number;
  note: string;
  sourced: boolean;
}

export interface LandedCostResponse {
  hts10: string;
  origin: string;
  destination: string;
  unit_price: number;
  components: LandedCostComponent[];
  landed_total: number;
  markup_pct: number;
  partial: boolean;
  computed_at: string;
  disclaimer: string;
}

export const api = {
  searchListings: (q: string) =>
    request<ListingSummary[]>(`/listings/search?q=${encodeURIComponent(q)}`),
  getListing: (id: string) => request<ListingDetail>(`/listings/${id}`),
  landedCost: (payload: { hts10: string; destination: string; unit_price: number }) =>
    request<LandedCostResponse>(`/landed-cost`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  register: (payload: {
    company_name: string;
    contact_name: string;
    email: string;
    password: string;
    country?: string;
  }) => request<{ access_token: string }>(`/auth/register`, { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string }>(`/auth/login`, { method: "POST", body: JSON.stringify(payload) }),
  createEnquiry: (payload: { vendor_id: string; listing_id?: string; qty?: number; destination?: string; specification?: string }) =>
    request<{ id: string; status: string }>(`/enquiries`, { method: "POST", body: JSON.stringify(payload) }),
  releaseContact: (enquiryId: string) =>
    request<{ contact_name: string | null; contact_email: string | null; contact_phone: string | null }>(
      `/enquiries/${enquiryId}/release-contact`,
      { method: "POST" }
    ),
  myEnquiries: () => request<{ id: string; vendor_id: string; status: string; created_at: string }[]>(`/enquiries/mine`),
  createVendor: (payload: { legal_name: string; city?: string; state?: string; iec?: string; gstin?: string }) =>
    request<Vendor>(`/vendors`, { method: "POST", body: JSON.stringify(payload) }),
  createListing: (payload: {
    vendor_id: string;
    title: string;
    description: string;
    specs?: Record<string, unknown>;
    moq?: number;
  }) => request<{ listing_id: string; hts10: string | null; state: string }>(`/listings`, {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  addPriceTier: (
    listingId: string,
    payload: { qty_min: number; qty_max?: number; price_low: number; price_high?: number; incoterm?: string; disclosure?: string }
  ) => request(`/listings/${listingId}/price-tiers`, { method: "POST", body: JSON.stringify(payload) }),
  publishListing: (listingId: string) => request(`/listings/${listingId}/publish`, { method: "POST" }),
  moderationQueue: () =>
    request<{ id: string; listing_id: string; listing_title: string; reason: string }[]>(`/moderation/queue`),
  pendingClaims: () =>
    request<{ id: string; vendor_id: string; claimant_email: string }[]>(`/moderation/claims`),
  approveClaim: (claimId: string) => request(`/vendors/claims/${claimId}/approve`, { method: "POST" }),
};
