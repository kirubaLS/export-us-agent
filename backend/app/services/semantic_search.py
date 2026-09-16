"""Section 9.3 — 'find me something like this' discovery, without the
Phase 2 dependency on a hosted embeddings API or Typesense.

This is a pure-Python TF-IDF + cosine-similarity ranker over the live
catalogue. At Phase 1 scale (a few thousand listings, per §4.3's own
estimate of "a few thousand distinct classifications") this comfortably
outperforms ILIKE keyword matching — it ranks by relevance instead of
returning results in an arbitrary order — with zero external dependency
that can fail at deploy time (no API key, no binary wheel, no separate
service to run).

It is explicitly a bridge, not the final architecture: the contract
(`rank(query, corpus) -> ordered ids with scores`) is exactly what a real
embeddings-based ranker would implement, so swapping this out for
Phase 2 (`text-embedding-3-*` + pgvector, or a hosted reranker) means
replacing this module's internals, not any caller.
"""

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _document_text(listing) -> str:
    parts = [listing.title, listing.description, listing.taxonomy_path or ""]
    specs = listing.specs or {}
    parts.extend(str(v) for v in specs.values())
    parts.extend(listing.certifications or [])
    return " ".join(parts)


def rank(query: str, listings: list) -> list[tuple[str, float]]:
    """Returns [(listing_id, score), ...] sorted by descending relevance.
    A listing with score 0 (no overlapping terms) is dropped rather than
    padded in — callers fall back to recency ordering for the rest."""
    query_terms = _tokenize(query)
    if not query_terms or not listings:
        return []

    doc_tokens: dict[str, list[str]] = {l.id: _tokenize(_document_text(l)) for l in listings}
    doc_count = len(doc_tokens)

    df = Counter()
    for tokens in doc_tokens.values():
        df.update(set(tokens))

    def idf(term: str) -> float:
        # +1 smoothing so a term present in every document isn't zeroed out
        return math.log((doc_count + 1) / (df.get(term, 0) + 1)) + 1

    query_tf = Counter(query_terms)
    query_vec = {term: freq * idf(term) for term, freq in query_tf.items()}
    query_norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0

    scored: list[tuple[str, float]] = []
    for listing_id, tokens in doc_tokens.items():
        if not tokens:
            continue
        tf = Counter(tokens)
        doc_vec = {term: freq * idf(term) for term, freq in tf.items()}
        doc_norm = math.sqrt(sum(v * v for v in doc_vec.values())) or 1.0

        dot = sum(weight * doc_vec.get(term, 0.0) for term, weight in query_vec.items())
        score = dot / (query_norm * doc_norm)
        if score > 0:
            scored.append((listing_id, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
