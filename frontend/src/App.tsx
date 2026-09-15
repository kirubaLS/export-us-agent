import { Link, Route, Routes } from "react-router-dom";
import { SearchPage } from "./pages/Search";
import { ListingDetailPage } from "./pages/ListingDetail";
import { RegisterPage } from "./pages/Register";
import { VendorOnboardingPage } from "./pages/VendorOnboarding";
import { ModerationPage } from "./pages/Moderation";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1024, margin: "0 auto", padding: 24 }}>
      <nav style={{ display: "flex", gap: 16, marginBottom: 24, borderBottom: "1px solid #e2e8f0", paddingBottom: 12 }}>
        <Link to="/">Search</Link>
        <Link to="/vendor-onboarding">Vendor onboarding</Link>
        <Link to="/moderation">Operations</Link>
        <Link to="/register" style={{ marginLeft: "auto" }}>
          Buyer register
        </Link>
      </nav>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/listings/:id" element={<ListingDetailPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/vendor-onboarding" element={<VendorOnboardingPage />} />
        <Route path="/moderation" element={<ModerationPage />} />
      </Routes>
    </div>
  );
}
