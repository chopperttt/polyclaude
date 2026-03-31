"""
Strategy 4 — Logical Mismatches ("Nested Subset Arbitrage")

Identifies pairs of markets where a *specific* market is priced higher than
its *general* parent market — a mathematical impossibility.

If P(OpenAI goes public in 2026) > P(any AI company goes public in 2026),
that is a free arbitrage: the child event cannot occur without the parent
event also occurring.

Algorithm:
1. Group markets by category to limit comparison space.
2. Identify "parent" markets via broad-quantifier signals ("any", "some", …).
3. For each parent, find candidate children with strong keyword overlap.
4. Flag pairs where child.yes_price > parent.yes_price.
"""
from __future__ import annotations

import re
import string
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Set, Tuple

from .models import Finding, Market

# ---------------------------------------------------------------------------
# Stopwords for keyword extraction
# ---------------------------------------------------------------------------
_STOPWORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "do", "does", "did", "have", "has", "had", "to", "of", "in", "on",
    "at", "by", "for", "with", "about", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "and", "but", "or", "nor",
    "so", "yet", "both", "either", "neither", "not", "no", "than", "too",
    "very", "just", "if", "that", "this", "these", "those", "it", "its",
    "he", "she", "they", "we", "i", "you", "who", "which", "what", "when",
    "where", "why", "how", "all", "any", "some", "each", "every", "few",
    "more", "most", "other", "such", "up", "use", "go", "get", "make",
    "take", "come", "see", "know", "think", "say", "tell", "ask", "give",
    "there", "from", "into", "also", "only", "same", "new", "first", "last",
    "own", "two", "three", "than", "while", "within", "without", "still",
    "between", "during", "despite", "since", "until", "unless", "although",
    "though", "whether", "because", "however", "therefore", "thus",
    "least", "ever", "never", "always", "often", "current", "currently",
    "official", "officially", "become", "becomes", "became",
    "pass", "passes", "passed", "win", "wins", "won", "lose", "loses", "lost",
}

# Broad-quantifier patterns that signal a "parent" market
_PARENT_SIGNALS = re.compile(
    r"\bany\s+\w|"
    r"\bat\s+least\s+one\b|"
    r"\bsome\s+\w|"
    r"\ba\s+(?:new\s+|major\s+)?(?:company|firm|country|nation|party|candidate|team|player)\b|"
    r"\bsomeone\b|"
    r"\banyone\b|"
    r"\bany\s+(?:country|nation|state|company|firm|team|player|candidate|party|person|individual|AI|tech)\b",
    re.IGNORECASE,
)

# Phrases that signal a specific/child market
_SPECIFIC_SIGNALS = re.compile(
    r"OpenAI|Google|Microsoft|Apple|Amazon|Meta|Tesla|SpaceX|Anthropic|xAI|"
    r"Trump|Biden|Harris|DeSantis|Obama|Clinton|Bush|"
    r"China|Russia|Ukraine|Israel|Iran|North Korea|"
    r"Fed|Federal Reserve|Powell|Yellen|"
    r"NATO|EU|UN|WHO|IMF|"
    r"Bitcoin|Ethereum|Solana|Dogecoin|"
    r"S&P\s*500|Nasdaq|Dow\s*Jones",
    re.IGNORECASE,
)


def _tokenize(text: str) -> Set[str]:
    """Extract meaningful lowercase tokens from a question string."""
    text = text.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    tokens = text.lower().split()
    return {t for t in tokens if t not in _STOPWORDS and len(t) >= 3}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _is_parent_candidate(market: Market) -> bool:
    return bool(_PARENT_SIGNALS.search(market.question))


def _is_specific_candidate(market: Market) -> bool:
    return bool(_SPECIFIC_SIGNALS.search(market.question))


def _find_pairs_in_group(
    group: List[Market],
    overlap_threshold: float,
    min_volume: float,
) -> List[Tuple[Market, Market, float]]:
    """
    Within a category group, find (parent, child, overlap_score) triples
    where the child is a specific instance of the parent.
    """
    pairs: List[Tuple[Market, Market, float]] = []
    tokens: Dict[str, Set[str]] = {m.id: _tokenize(m.question) for m in group}

    parents = [m for m in group if _is_parent_candidate(m) and m.volume >= min_volume]
    children = [m for m in group if _is_specific_candidate(m) and m.volume >= min_volume]

    # If no explicit parent/child signals, fall back to comparing all pairs
    if not parents or not children:
        candidates = [m for m in group if m.volume >= min_volume]
        for a, b in combinations(candidates, 2):
            overlap = _jaccard(tokens[a.id], tokens[b.id])
            if overlap >= overlap_threshold:
                # Longer question → more specific → child
                parent, child = (a, b) if len(a.question) <= len(b.question) else (b, a)
                pairs.append((parent, child, overlap))
        return pairs

    for parent in parents:
        for child in children:
            if parent.id == child.id:
                continue
            overlap = _jaccard(tokens[parent.id], tokens[child.id])
            if overlap >= overlap_threshold:
                pairs.append((parent, child, overlap))

    return pairs


def scan(
    markets: List[Market],
    overlap_threshold: float = 0.50,
    min_volume: float = 1_000.0,
    min_price_gap: float = 0.02,
) -> List[Finding]:
    """
    Run Strategy 4 on a list of markets.

    Args:
        markets: All fetched markets.
        overlap_threshold: Minimum Jaccard keyword overlap to consider a pair (default 0.50).
        min_volume: Minimum market volume (USD) to include in analysis (default $1,000).
        min_price_gap: Minimum price gap (child - parent) to flag (default 0.02 = 2¢).

    Returns:
        List of Finding objects, sorted by price_gap descending.
    """
    groups: Dict[str, List[Market]] = defaultdict(list)
    for m in markets:
        key = (m.category or "uncategorized").lower().strip()
        groups[key].append(m)

    findings: List[Finding] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for category, group in groups.items():
        if len(group) < 2:
            continue

        pairs = _find_pairs_in_group(group, overlap_threshold, min_volume)

        for parent, child, overlap in pairs:
            pair_key = (min(parent.id, child.id), max(parent.id, child.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            price_gap = child.yes_price - parent.yes_price
            if price_gap < min_price_gap:
                continue

            severity = min(price_gap * 2.0, 1.0)
            reason = (
                f"Child market '{child.question}' (YES={child.yes_price:.0%}) is priced "
                f"ABOVE parent market '{parent.question}' (YES={parent.yes_price:.0%}). "
                f"Gap: +{price_gap:.2%}. "
                f"Keyword overlap: {overlap:.0%}. "
                f"A specific event cannot be more likely than its general class."
            )

            findings.append(Finding(
                strategy=4,
                label="Nested Subset",
                market_a=parent,
                market_b=child,
                reason=reason,
                severity=round(severity, 4),
                price_gap=round(price_gap, 4),
            ))

    findings.sort(key=lambda f: f.price_gap, reverse=True)
    return findings
