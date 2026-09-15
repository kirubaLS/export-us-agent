import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

export function RegisterPage() {
  const [form, setForm] = useState({ company_name: "", contact_name: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const { access_token } = await api.register(form);
      localStorage.setItem("buyer_token", access_token);
      navigate("/");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={submit} style={{ maxWidth: 360, display: "grid", gap: 8 }}>
      <h1>Register as a buyer</h1>
      <input placeholder="Company name" required onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
      <input placeholder="Your name" required onChange={(e) => setForm({ ...form, contact_name: e.target.value })} />
      <input placeholder="Business email" type="email" required onChange={(e) => setForm({ ...form, email: e.target.value })} />
      <input placeholder="Password" type="password" required onChange={(e) => setForm({ ...form, password: e.target.value })} />
      <button type="submit">Create account</button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </form>
  );
}
