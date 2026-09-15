import type { PriceLine } from "../api/client";

/** Section 4 / Table 15 rendered as UI policy: never show a blank price. */
export function PriceDisplay({ price }: { price: PriceLine[] }) {
  if (!price.length) return null;

  return (
    <div style={{ marginTop: 4 }}>
      {price.map((line, i) => {
        if (line.source === "insufficient_data") {
          return (
            <div key={i} style={{ color: "#718096", fontStyle: "italic" }}>
              {line.label}
            </div>
          );
        }
        const label =
          line.source === "derived" ? (
            <span style={{ fontSize: 12, color: "#b7791f" }}>{line.label}</span>
          ) : null;
        return (
          <div key={i}>
            <strong>
              {line.price_low}
              {line.price_high && line.price_high !== line.price_low ? `–${line.price_high}` : ""} {line.currency}
            </strong>{" "}
            {line.incoterm && <span>{line.incoterm}</span>}{" "}
            {line.qty_min && <span style={{ color: "#718096" }}>MOQ {line.qty_min}</span>}
            {label}
          </div>
        );
      })}
    </div>
  );
}
