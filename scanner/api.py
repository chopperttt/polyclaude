"""
Polymarket Gamma API client.

Docs: https://docs.polymarket.com/#gamma-markets-api
"""
from __future__ import annotations

import time
from typing import List, Optional

import requests

from .models import Market

_BASE_URL = "https://gamma-api.polymarket.com/markets"
_PAGE_SIZE = 100
_RATE_DELAY = 0.5   # seconds between pages


def _parse_yes_price(market_data: dict) -> float:
    """Extract YES price (0.0–1.0) from a market dict."""
    try:
        prices = market_data.get("outcomePrices", [])
        outcomes = market_data.get("outcomes", [])

        if not prices:
            return 0.0

        # Prices may be JSON-encoded strings e.g. '["0.8","0.2"]'
        if isinstance(prices, str):
            import json
            prices = json.loads(prices)
        if isinstance(outcomes, str):
            import json
            outcomes = json.loads(outcomes)

        # Find the index of the "Yes" outcome
        yes_idx = 0
        for i, o in enumerate(outcomes):
            if str(o).lower() in ("yes", "true", "1"):
                yes_idx = i
                break

        return float(prices[yes_idx])
    except (IndexError, ValueError, TypeError):
        return 0.0


def _parse_market(raw: dict) -> Optional[Market]:
    """Convert a raw API dict to a Market object. Returns None if unusable."""
    question = raw.get("question", "").strip()
    if not question:
        return None

    yes_price = _parse_yes_price(raw)

    slug = raw.get("slug", "")
    url = f"https://polymarket.com/event/{slug}" if slug else ""

    outcomes = raw.get("outcomes", [])
    if isinstance(outcomes, str):
        import json
        try:
            outcomes = json.loads(outcomes)
        except Exception:
            outcomes = []

    return Market(
        id=str(raw.get("id", raw.get("conditionId", ""))),
        question=question,
        description=raw.get("description", "") or "",
        category=raw.get("category", "") or "",
        yes_price=yes_price,
        volume=float(raw.get("volume", 0) or 0),
        url=url,
        slug=slug,
        outcomes=outcomes,
    )


def fetch_markets(
    limit: int = 500,
    category: Optional[str] = None,
    active_only: bool = True,
) -> List[Market]:
    """
    Fetch markets from Polymarket Gamma API with pagination.

    Args:
        limit: Maximum total number of markets to return.
        category: Optional category filter (e.g. "politics", "science").
        active_only: Only return active (non-closed) markets.

    Returns:
        List of Market objects.
    """
    markets: List[Market] = []
    offset = 0

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    while len(markets) < limit:
        page_limit = min(_PAGE_SIZE, limit - len(markets))
        params: dict = {
            "limit": page_limit,
            "offset": offset,
            "active": "true" if active_only else "false",
            "closed": "false",
        }
        if category:
            params["category"] = category

        try:
            resp = session.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[api] Request failed (offset={offset}): {exc}")
            break

        data = resp.json()

        # Gamma API returns a list directly or {"markets": [...]}
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            raw_list = data.get("markets", data.get("data", []))
        else:
            break

        if not raw_list:
            break

        for raw in raw_list:
            market = _parse_market(raw)
            if market is not None:
                markets.append(market)

        if len(raw_list) < page_limit:
            break  # no more pages

        offset += page_limit
        time.sleep(_RATE_DELAY)

    return markets[:limit]
