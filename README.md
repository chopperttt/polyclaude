# polyclaude — Polymarket Logical & Semantic Scanner

Scans live [Polymarket](https://polymarket.com) markets for two types of mispriced opportunities:

- **Strategy 3 — Semantic Loopholes ("Rules Edge")**: Markets priced high where the resolution rules contain high-barrier technicalities the crowd is ignoring.
- **Strategy 4 — Logical Mismatches ("Nested Subset Arbitrage")**: A specific market is priced *above* its general parent market — a mathematical impossibility.

---

## How It Works

### Strategy 3 — Semantic Loopholes

The market *vibe* (price) is high, but the fine print makes resolution much harder than it looks. The scanner detects patterns like:

| Pattern | Example |
|---|---|
| Specific bill/resolution number | Market only resolves YES if *S.J.Res.104* passes |
| Formal procedural vote required | Requires a *roll call vote*, not just a voice vote |
| Must be signed into law | A bill passing committee ≠ becoming law |
| Official government data source | Resolves based solely on *BLS* or *OPM* data |
| Resolves NO on adjournment | If Congress adjourns without voting → NO |
| Official government certification | Requires a formal presidential declaration |

**Example:** "Will the Senate pass the War Powers resolution?" at $0.80, but the rules say it only resolves YES if *S.J.Res.104* receives a formal roll call vote. If the Senate adjourns without one → NO.

### Strategy 4 — Logical Mismatches

Finds parent/child market pairs where the specific child is priced above the general parent — which is impossible.

```
Parent:  "Will any AI company go public in 2026?"   → $0.15
Child:   "Will OpenAI go public in 2026?"           → $0.22
Gap:     +$0.07  ← free arbitrage
```

OpenAI going public *implies* some AI company goes public. If you believe OpenAI IPO has 22% chance, the "any AI company" market must be at least 22%.

---

## Installation

```bash
git clone https://github.com/chopperttt/polyclaude.git
cd polyclaude
pip install -r requirements.txt
```

No API keys required — Polymarket's public API is used for read access.

---

## Usage

```bash
python main.py [OPTIONS]
```

### Run both strategies (default)

```bash
python main.py
```

Fetches 500 active markets and runs both strategies with default thresholds.

### Strategy 3 only — Semantic Loopholes

```bash
python main.py --strategies 3
```

High conviction only (YES price > 60%):
```bash
python main.py --strategies 3 --min-price 0.60
```

Lower the barrier threshold to catch more markets:
```bash
python main.py --strategies 3 --barrier 35
```

### Strategy 4 only — Logical Mismatches

```bash
python main.py --strategies 4
```

### Filter by category

```bash
python main.py --strategies 3 4 --category politics --limit 200
```

Common categories: `politics`, `science`, `crypto`, `sports`, `economics`

### JSON output (for piping / downstream processing)

```bash
python main.py --output json
python main.py --output json > findings.json
```

---

## All Options

```
usage: main.py [-h] [--strategies {3,4} ...] [--limit N] [--category CAT]
               [--min-price PRICE] [--barrier SCORE]
               [--overlap RATIO] [--min-volume USD] [--min-gap GAP]
               [--output {text,json}]

Strategy 3 — Semantic Loopholes:
  --min-price PRICE   Minimum YES price to scan (default: 0.40)
  --barrier SCORE     Minimum barrier score 0–100 to flag (default: 50)

Strategy 4 — Logical Mismatches:
  --overlap RATIO     Minimum keyword overlap 0–1 to pair markets (default: 0.50)
  --min-volume USD    Minimum market volume in USD (default: 1000)
  --min-gap GAP       Minimum price gap to flag (default: 0.02)

General:
  --strategies        Which strategies to run: 3, 4, or both (default: 3 4)
  --limit N           Max markets to fetch (default: 500)
  --category CAT      Filter to a Polymarket category
  --output            Output format: text or json (default: text)
```

---

## Example Output

### Strategy 3
```
============================================================
  STRATEGY 3: SEMANTIC LOOPHOLES  (2 findings)
============================================================
  [HIGH] Will the Senate pass the War Powers resolution by March 6?
         YES Price : 80% ($0.8000)  |  Volume: $45,230
         URL       : https://polymarket.com/event/...
         Barrier   : specific bill/resolution number — matched: "S.J.Res.104" (+40 pts)
         Barrier   : formal procedural vote required — matched: "roll call vote" (+30 pts)
         Reason    : YES price 80% but resolution requires: specific bill/resolution
                     number, formal procedural vote required. Barrier score: 70/100.
```

### Strategy 4
```
============================================================
  STRATEGY 4: LOGICAL MISMATCHES  (1 finding)
============================================================
  [MED]  Specific priced ABOVE General
         Parent : "Will any AI company go public in 2026?"
                  YES = 15% ($0.1500)  |  Volume: $12,000
         Child  : "Will OpenAI go public in 2026?"
                  YES = 22% ($0.2200)  |  Volume: $38,500
         Gap    : +7.00%  (child overpriced by this margin)
```

---

## Project Structure

```
polyclaude/
├── main.py               # CLI entry point
├── requirements.txt
└── scanner/
    ├── api.py            # Polymarket Gamma API client + pagination
    ├── models.py         # Market, Finding, BarrierMatch dataclasses
    ├── strategy3.py      # Regex barrier-pattern scoring engine
    ├── strategy4.py      # Jaccard keyword overlap + parent/child pairing
    └── reporter.py       # ANSI terminal + JSON output
```

---

## Dependencies

- `requests` — HTTP calls to Polymarket API
- `python-dotenv` — optional `.env` support for future API key config

To optionally enable Claude AI-enhanced analysis, uncomment `anthropic` in `requirements.txt` and set `ANTHROPIC_API_KEY` in a `.env` file.
