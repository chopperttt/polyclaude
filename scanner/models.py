from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Market:
    id: str
    question: str
    description: str
    category: str
    yes_price: float        # 0.0 – 1.0
    volume: float
    url: str
    slug: str = ""
    outcomes: List[str] = field(default_factory=list)


@dataclass
class BarrierMatch:
    category: str
    pattern: str
    score: int


@dataclass
class Finding:
    strategy: int                           # 3 or 4
    label: str                              # "Rules Edge" or "Nested Subset"
    market_a: Market
    market_b: Optional[Market]              # None for Strategy 3; child market for Strategy 4
    reason: str
    severity: float                         # 0.0–1.0
    matches: List[BarrierMatch] = field(default_factory=list)  # Strategy 3 matched patterns
    price_gap: float = 0.0                  # Strategy 4: child_price - parent_price

    def to_dict(self) -> dict:
        d: dict = {
            "strategy": self.strategy,
            "label": self.label,
            "reason": self.reason,
            "severity": round(self.severity, 4),
            "market_a": {
                "id": self.market_a.id,
                "question": self.market_a.question,
                "yes_price": self.market_a.yes_price,
                "volume": self.market_a.volume,
                "url": self.market_a.url,
            },
        }
        if self.market_b is not None:
            d["market_b"] = {
                "id": self.market_b.id,
                "question": self.market_b.question,
                "yes_price": self.market_b.yes_price,
                "volume": self.market_b.volume,
                "url": self.market_b.url,
            }
            d["price_gap"] = round(self.price_gap, 4)
        if self.matches:
            d["barrier_matches"] = [
                {"category": m.category, "pattern": m.pattern, "score": m.score}
                for m in self.matches
            ]
        return d
