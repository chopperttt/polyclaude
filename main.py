#!/usr/bin/env python3
"""
polyclaude — Polymarket Logical & Semantic Scanner
===================================================

Scans live Polymarket markets for two types of inefficiency:

  Strategy 3 — Semantic Loopholes ("Rules Edge")
      Markets priced high where resolution rules contain high-barrier
      technicalities the crowd appears to be ignoring (specific bill numbers,
      mandatory roll-call votes, sole-source official data requirements, etc.)

  Strategy 4 — Logical Mismatches ("Nested Subset Arbitrage")
      A specific market (e.g. "Will OpenAI go public in 2026?") is priced
      ABOVE its general parent market ("Will any AI company go public in 2026?"),
      which is a mathematical impossibility.

Usage examples:
  python main.py                                # both strategies, 500 markets
  python main.py --strategies 3 --min-price 0.60
  python main.py --strategies 4 --output json
  python main.py --strategies 3 4 --category politics --limit 200
"""
from __future__ import annotations

import argparse
import sys

from scanner import api, reporter, strategy3, strategy4
from scanner.models import Finding


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="polyclaude",
        description="Scan Polymarket for Semantic Loopholes (S3) and Logical Mismatches (S4).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument(
        "--strategies",
        nargs="+",
        type=int,
        choices=[3, 4],
        default=[3, 4],
        metavar="{3,4}",
        help="Which strategies to run (default: 3 4)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=500,
        metavar="N",
        help="Max number of markets to fetch (default: 500)",
    )
    p.add_argument(
        "--category",
        type=str,
        default=None,
        metavar="CAT",
        help="Filter to a specific Polymarket category (e.g. politics, science)",
    )

    # Strategy 3 options
    s3 = p.add_argument_group("Strategy 3 — Semantic Loopholes")
    s3.add_argument(
        "--min-price",
        type=float,
        default=0.40,
        metavar="PRICE",
        help="Minimum YES price (0–1) for S3 analysis (default: 0.40)",
    )
    s3.add_argument(
        "--barrier",
        type=int,
        default=50,
        metavar="SCORE",
        help="Minimum barrier score (0–100) to flag a market (default: 50)",
    )

    # Strategy 4 options
    s4 = p.add_argument_group("Strategy 4 — Logical Mismatches")
    s4.add_argument(
        "--overlap",
        type=float,
        default=0.50,
        metavar="RATIO",
        help="Minimum Jaccard keyword overlap (0–1) for pairing (default: 0.50)",
    )
    s4.add_argument(
        "--min-volume",
        type=float,
        default=1_000.0,
        metavar="USD",
        help="Minimum market volume (USD) to include in S4 analysis (default: 1000)",
    )
    s4.add_argument(
        "--min-gap",
        type=float,
        default=0.02,
        metavar="GAP",
        help="Minimum price gap (child - parent) to flag (default: 0.02)",
    )

    # Output
    p.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default) or json",
    )

    return p.parse_args()


def main() -> int:
    args = parse_args()

    print(f"[polyclaude] Fetching up to {args.limit} markets from Polymarket…")
    markets = api.fetch_markets(
        limit=args.limit,
        category=args.category,
        active_only=True,
    )
    print(f"[polyclaude] Fetched {len(markets)} markets.")

    if not markets:
        print("[polyclaude] No markets returned. Check your connection or filters.")
        return 1

    findings: list[Finding] = []

    if 3 in args.strategies:
        print(
            f"[polyclaude] Running Strategy 3 (min_price={args.min_price}, "
            f"barrier_threshold={args.barrier})…"
        )
        s3_findings = strategy3.scan(
            markets,
            min_price=args.min_price,
            barrier_threshold=args.barrier,
        )
        print(f"[polyclaude] Strategy 3: {len(s3_findings)} finding(s).")
        findings.extend(s3_findings)

    if 4 in args.strategies:
        print(
            f"[polyclaude] Running Strategy 4 (overlap={args.overlap}, "
            f"min_volume={args.min_volume}, min_gap={args.min_gap})…"
        )
        s4_findings = strategy4.scan(
            markets,
            overlap_threshold=args.overlap,
            min_volume=args.min_volume,
            min_price_gap=args.min_gap,
        )
        print(f"[polyclaude] Strategy 4: {len(s4_findings)} finding(s).")
        findings.extend(s4_findings)

    print()

    if args.output == "json":
        reporter.render_json(findings)
    else:
        reporter.render_text(findings)

    return 0


if __name__ == "__main__":
    sys.exit(main())
