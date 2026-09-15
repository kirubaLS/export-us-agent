"""Section 9.1 — Stage A of the Export-to-Entry Agent, reused unchanged.

Stub keyword classifier standing in for the real LLM-with-web-search
classification stage. Contract is preserved: return a code, a confidence,
and a reasoning trail; anything below the confidence threshold is routed
to the moderation queue rather than published silently (Section 9.5).
"""

MODERATION_CONFIDENCE_THRESHOLD = 0.75

_KEYWORD_RULES: list[tuple[list[str], str, str]] = [
    (["ceramic", "mug", "tableware", "kitchenware"], "6912.00.4810", "Ceramic tableware/kitchenware, non-porcelain, matches HTS 6912."),
    (["cotton", "t-shirt", "shirt", "apparel", "garment"], "6203.42.4011", "Cotton apparel matches HTS Chapter 62 knit/woven men's garments heading."),
    (["furniture", "wooden", "chair", "table", "seat"], "9403.60.8081", "Wooden furniture matches HTS Chapter 94 furniture heading."),
]


def classify(title: str, description: str, materials: str | None = None) -> dict:
    haystack = f"{title} {description} {materials or ''}".lower()

    for keywords, hts10, reasoning in _KEYWORD_RULES:
        hits = [k for k in keywords if k in haystack]
        if hits:
            confidence = min(0.6 + 0.1 * len(hits), 0.95)
            return {
                "hts10": hts10,
                "confidence": confidence,
                "reasoning": f"{reasoning} Matched terms: {', '.join(hits)}.",
                "requires_moderation": confidence < MODERATION_CONFIDENCE_THRESHOLD,
            }

    return {
        "hts10": None,
        "confidence": 0.0,
        "reasoning": "No confident match against the fixture rule set — route to manual classification.",
        "requires_moderation": True,
    }
