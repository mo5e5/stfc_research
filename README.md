# stfc_research

Data analysis for *Star Trek Fleet Command* — analytical foundation for [stfc_calc](https://github.com/mo5e5/stfc_calc).

## Goal

Derive reliable scaling formulas for armada strengths from real in-game battle reports (CSV export) — per faction and difficulty (Green/Blue/Purple). Validated constants are transferred manually into `stfc_calc`.

## Model

```
strength(level) = a × b^level
```

Exponential fit via `scipy.optimize.curve_fit`. Parameters `a` and `b` are determined per faction and difficulty level and stored in `results/constants.json`.

## Structure

```
data/
  raw/           # Original CSVs (unmodified)
  processed/     # dataset.json — normalized data points
scripts/
  parse_report.py   # CSV → dataset.json
  analyze.py        # Fitting → constants.json
results/
  constants.json    # Final constants for stfc_calc
tests/
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python scripts/parse_report.py   # Parse raw data
python scripts/analyze.py        # Fit formulas
pytest                           # Run tests
```

## Interface to stfc_calc

`results/constants.json` → transferred manually into `stfc_calc` once values are validated. No automatic sync.

## Data Status

First data points: Eclipse Exchange Green, Level 35 / 37 / 40 (Solo-STELLA).
Preliminary scaling factor: ~×1.25 per level (low confidence, 3 data points).

## Sources & References

Values are empirical measurements from personal in-game battle reports. No reverse engineering, no unofficial APIs.

## License

Copyright (C) 2026 mo5e5

Licensed under the **GNU General Public License v3.0 or later** — see [LICENSE](LICENSE) for the full text. You may use, modify, and redistribute this software; derivative works must remain under the GPL.

---

<sub>Community tool — not affiliated with Scopely or CBS Studios.</sub>
