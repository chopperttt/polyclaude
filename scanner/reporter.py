"""
Output formatting for scanner findings.

Supports two modes:
  - text  (default): human-readable terminal output with ANSI colours
  - json:             machine-readable JSON array
"""
from __future__ import annotations

import json
import sys
from typing import List

from .models import Finding

# ---------------------------------------------------------------------------
# ANSI colour helpers (auto-disabled when stdout is not a tty)
# ---------------------------------------------------------------------------
_USE_COLOUR = sys.stdout.isatty()

_RESET  = "\033[0m"  if _USE_COLOUR else ""
_BOLD   = "\033[1m"  if _USE_COLOUR else ""
_RED    = "\033[91m" if _USE_COLOUR else ""
_YELLOW = "\033[93m" if _USE_COLOUR else ""
_CYAN   = "\033[96m" if _USE_COLOUR else ""
_GREEN  = "\033[92m" if _USE_COLOUR else ""
_DIM    = "\033[2m"  if _USE_COLOUR else ""


def _severity_tag(severity: float) -> str:
    if severity >= 0.70:
        return f"{_RED}[HIGH]{_RESET}"
    elif severity >= 0.45:
        return f"{_YELLOW}[MED]{_RESET} "
    else:
        return f"{_DIM}[LOW]{_RESET} "


def _fmt_price(price: float) -> str:
    return f"{price:.0%} (${price:.4f})"


def _wrap(text: str, width: int = 90, indent: str = "       ") -> str:
    """Naive word-wrap for terminal output."""
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = indent + word
        else:
            current = (current + " " + word).lstrip()
    if current:
        lines.append(current)
    return ("\n" + indent).join(lines)


def _render_s3(findings: List[Finding]) -> str:
    if not findings:
        return f"{_DIM}  No Strategy 3 findings.{_RESET}\n"

    lines: List[str] = []
    for f in findings:
        tag = _severity_tag(f.severity)
        lines.append(f"  {tag} {_BOLD}{f.market_a.question}{_RESET}")
        lines.append(
            f"         YES Price : {_CYAN}{_fmt_price(f.market_a.yes_price)}{_RESET}"
            f"  |  Volume: ${f.market_a.volume:,.0f}"
        )
        if f.market_a.url:
            lines.append(f"         URL       : {_DIM}{f.market_a.url}{_RESET}")
        for m in f.matches:
            lines.append(
                f"         Barrier   : {_YELLOW}{m.category}{_RESET}"
                f" — matched: \"{_DIM}{m.pattern}{_RESET}\""
                f" (+{m.score} pts)"
            )
        lines.append(f"         Reason    : {_wrap(f.reason, indent=' ' * 19)}")
        lines.append("")

    return "\n".join(lines)


def _render_s4(findings: List[Finding]) -> str:
    if not findings:
        return f"{_DIM}  No Strategy 4 findings.{_RESET}\n"

    lines: List[str] = []
    for f in findings:
        parent = f.market_a
        child  = f.market_b
        tag = _severity_tag(f.severity)
        lines.append(f"  {tag} {_RED}Specific priced ABOVE General{_RESET}")
        lines.append(f"         {_GREEN}Parent{_RESET} : \"{parent.question}\"")
        lines.append(
            f"                  YES = {_CYAN}{_fmt_price(parent.yes_price)}{_RESET}"
            f"  |  Volume: ${parent.volume:,.0f}"
        )
        if child:
            lines.append(f"         {_RED}Child{_RESET}  : \"{child.question}\"")
            lines.append(
                f"                  YES = {_RED}{_fmt_price(child.yes_price)}{_RESET}"
                f"  |  Volume: ${child.volume:,.0f}"
            )
        lines.append(
            f"         Gap    : {_BOLD}{_RED}+{f.price_gap:.2%}{_RESET}"
            f"  (child overpriced by this margin)"
        )
        lines.append(f"         Reason : {_wrap(f.reason, indent=' ' * 19)}")
        if parent.url:
            lines.append(f"         Parent URL : {_DIM}{parent.url}{_RESET}")
        if child and child.url:
            lines.append(f"         Child URL  : {_DIM}{child.url}{_RESET}")
        lines.append("")

    return "\n".join(lines)


def render_text(findings: List[Finding]) -> None:
    """Print all findings to stdout in human-readable terminal format."""
    s3 = [f for f in findings if f.strategy == 3]
    s4 = [f for f in findings if f.strategy == 4]

    print()
    print(
        f"{_BOLD}{'='*60}{_RESET}\n"
        f"{_BOLD}  STRATEGY 3: SEMANTIC LOOPHOLES  "
        f"({len(s3)} finding{'s' if len(s3) != 1 else ''}){_RESET}\n"
        f"{_BOLD}{'='*60}{_RESET}"
    )
    print(_render_s3(s3))

    print(
        f"{_BOLD}{'='*60}{_RESET}\n"
        f"{_BOLD}  STRATEGY 4: LOGICAL MISMATCHES  "
        f"({len(s4)} finding{'s' if len(s4) != 1 else ''}){_RESET}\n"
        f"{_BOLD}{'='*60}{_RESET}"
    )
    print(_render_s4(s4))

    print(f"{_BOLD}Total findings: {len(findings)}{_RESET}  (S3: {len(s3)}, S4: {len(s4)})\n")


def render_json(findings: List[Finding]) -> None:
    """Print all findings to stdout as a JSON object."""
    output = {
        "total": len(findings),
        "strategy_3_count": sum(1 for f in findings if f.strategy == 3),
        "strategy_4_count": sum(1 for f in findings if f.strategy == 4),
        "findings": [f.to_dict() for f in findings],
    }
    print(json.dumps(output, indent=2))
