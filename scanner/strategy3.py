"""
Strategy 3 — Semantic Loopholes ("Rules Edge")

Identifies markets where the YES price is high (market sentiment says it will
happen) but the resolution rules contain high-barrier technical requirements
that the crowd appears to be ignoring.

Examples of high-barrier rules:
  - Specific bill/resolution numbers that must pass (S.J.Res.104, H.R.1234)
  - Formal procedural requirements (roll call vote, cloture)
  - Official government data sources cited as sole arbiter (OPM, BLS)
  - "Signed/enacted into law" language
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .models import BarrierMatch, Finding, Market

# ---------------------------------------------------------------------------
# Barrier pattern definitions: (category, compiled_regex, score)
# ---------------------------------------------------------------------------
_RAW_PATTERNS: List[Tuple[str, str, int]] = [
    # Specific legislative instruments
    (
        "specific bill/resolution number",
        r"S\s*\.\s*J\s*\.\s*Res\s*\.?\s*\d+|"
        r"H\s*\.\s*J\s*\.\s*Res\s*\.?\s*\d+|"
        r"H\s*\.\s*R\s*\.?\s*\d+|"
        r"S\s*\.\s*Con\s*\.\s*Res\s*\.?\s*\d+|"
        r"(?<![A-Z])S\s*\.\s*\d{3,5}\b",
        40,
    ),
    # Official US government data sources
    (
        "official government data source",
        r"\bOPM\b|"
        r"Bureau of Labor Statistics|"
        r"\bBLS\b|"
        r"Federal Register|"
        r"opm\.gov|"
        r"bls\.gov|"
        r"federalregister\.gov|"
        r"whitehouse\.gov|"
        r"congress\.gov|"
        r"\bBureau of Economic Analysis\b|"
        r"\bBEA\b(?!\w)",
        35,
    ),
    # Formal procedural vote requirements
    (
        "formal procedural vote required",
        r"roll\s+call\s+vote|"
        r"recorded\s+vote|"
        r"\bcloture\b|"
        r"yeas?\s+and\s+nays?|"
        r"yea[s]?\s*/\s*nay[s]?|"
        r"floor\s+vote|"
        r"must\s+pass\s+(?:a\s+)?(?:formal\s+)?vote",
        30,
    ),
    # Signed/enacted into law
    (
        "must be signed/enacted into law",
        r"signed\s+into\s+law|"
        r"enacted\s+into\s+law|"
        r"\bpromulgated\b|"
        r"becomes?\s+law|"
        r"presidential\s+signature",
        30,
    ),
    # Sole-source official data citations
    (
        "sole official source cited",
        r"as\s+reported\s+by\s+(?:the\s+)?(?:official|government|federal)|"
        r"as\s+published\s+by\s+(?:the\s+)?(?:official|government|federal)|"
        r"according\s+to\s+(?:the\s+)?official\s+(?:government\s+)?(?:data|source|report|website)|"
        r"per\s+(?:the\s+)?official\s+(?:government\s+)?(?:data|source)|"
        r"official\s+(?:government\s+)?(?:data|website|report)\s+(?:will\s+)?(?:be\s+)?used",
        20,
    ),
    # Adjournment / failure-to-vote clauses
    (
        "resolves NO on adjournment/no-vote",
        r"if\s+(?:the\s+)?(?:Senate|Congress|House)\s+adjourns?|"
        r"without\s+a\s+(?:formal\s+)?vote|"
        r"fails?\s+to\s+(?:hold\s+a\s+)?vote|"
        r"no\s+vote\s+(?:is\s+)?(?:held|taken|occurs?)|"
        r"resolves?\s+(?:NO|No)\s+if\s+(?:no|a)\s+vote",
        25,
    ),
    # Explicit government certification / official declaration
    (
        "requires official government certification",
        r"officially\s+(?:declared|certified|announced|designated)\s+by|"
        r"declared\s+(?:a\s+)?(?:national\s+)?emergency\s+by\s+(?:the\s+)?(?:President|federal)|"
        r"official\s+(?:declaration|certification|designation)|"
        r"Executive\s+Order\s+(?:is\s+)?(?:signed|issued)",
        25,
    ),
]

_COMPILED_PATTERNS: List[Tuple[str, re.Pattern, int]] = [
    (cat, re.compile(pattern, re.IGNORECASE), score)
    for cat, pattern, score in _RAW_PATTERNS
]


def _compute_barrier(description: str) -> Tuple[int, List[BarrierMatch]]:
    """
    Scan description text for high-barrier patterns.

    Returns:
        (barrier_score capped at 100, list of matched BarrierMatch objects)
    """
    matches: List[BarrierMatch] = []
    total_score = 0
    seen_categories: set = set()

    for category, pattern, score in _COMPILED_PATTERNS:
        found = pattern.search(description)
        if found and category not in seen_categories:
            matches.append(BarrierMatch(
                category=category,
                pattern=found.group(0).strip(),
                score=score,
            ))
            total_score += score
            seen_categories.add(category)

    return min(total_score, 100), matches


def scan(
    markets: List[Market],
    min_price: float = 0.40,
    barrier_threshold: int = 50,
) -> List[Finding]:
    """
    Run Strategy 3 on a list of markets.

    Args:
        markets: All fetched markets.
        min_price: Minimum YES price to consider (default 0.40).
        barrier_threshold: Minimum barrier score to flag (default 50).

    Returns:
        List of Finding objects, sorted by severity descending.
    """
    findings: List[Finding] = []

    for market in markets:
        if market.yes_price < min_price:
            continue

        text = market.description or ""
        if not text:
            continue

        score, matches = _compute_barrier(text)
        if score < barrier_threshold:
            continue

        # Severity: normalised combination of price (conviction) and barrier score
        severity = round((market.yes_price * 0.6 + (score / 100) * 0.4), 4)

        categories = ", ".join(m.category for m in matches)
        reason = (
            f"YES price {market.yes_price:.0%} but resolution requires: {categories}. "
            f"Barrier score: {score}/100."
        )

        findings.append(Finding(
            strategy=3,
            label="Rules Edge",
            market_a=market,
            market_b=None,
            reason=reason,
            severity=severity,
            matches=matches,
        ))

    findings.sort(key=lambda f: f.severity, reverse=True)
    return findings
