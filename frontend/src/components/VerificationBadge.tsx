const LABELS: Record<string, string> = {
  listed: "Listed (unclaimed)",
  claimed: "Claimed",
  verified: "Verified",
  trade_proven: "Trade-proven",
  audited: "Audited",
};

const COLORS: Record<string, string> = {
  listed: "#9aa0a6",
  claimed: "#2b6cb0",
  verified: "#2f855a",
  trade_proven: "#b7791f",
  audited: "#6b46c1",
};

export function VerificationBadge({ tier }: { tier: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        color: "white",
        background: COLORS[tier] || "#9aa0a6",
      }}
    >
      {LABELS[tier] || tier}
    </span>
  );
}
