"""analyze.py — Fit scaling formulas from parsed battle report data.

Reads data/processed/dataset.json, fits exponential models
(strength = a × b^level) per faction+type+difficulty, and writes
results/constants.json.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import curve_fit

logger = logging.getLogger(__name__)

DEFAULT_DATASET = Path(__file__).parent.parent / "data" / "processed" / "dataset.json"
DEFAULT_CONSTANTS = Path(__file__).parent.parent / "results" / "constants.json"


def exponential(level: float, a: float, b: float) -> float:
    """Exponential model: strength = a * b^level."""
    return a * (b ** level)


def fit_group(records: list[dict]) -> dict[str, Any]:
    """Fit exponential model for a group of records (same faction+type+difficulty).

    Returns dict with fitted parameters or None if fitting fails.
    """
    levels = np.array([r["level"] for r in records], dtype=float)
    strengths = np.array([r["strength"] for r in records], dtype=float)

    if len(records) < 3:
        return {
            "status": "insufficient_data",
            "data_points": len(records),
            "a": None,
            "b": None,
            "r_squared": None,
        }

    # Initial guess: a = strength at level 1, b = 1.25
    # Use the first data point's strength as initial a estimate
    p0 = (strengths[0] / (1.25 ** levels[0]), 1.25)

    try:
        popt, pcov = curve_fit(exponential, levels, strengths, p0=p0, maxfev=5000)
        a_fit, b_fit = popt

        # R-squared
        residuals = strengths - exponential(levels, *popt)
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((strengths - np.mean(strengths)) ** 2)
        r_sq = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Standard errors (from covariance diagonal)
        perr = np.sqrt(np.diag(pcov))

        return {
            "status": "ok",
            "data_points": len(records),
            "min_level": int(np.min(levels)),
            "max_level": int(np.max(levels)),
            "a": round(a_fit, 4),
            "b": round(b_fit, 6),
            "a_stderr": round(perr[0], 4),
            "b_stderr": round(perr[1], 6),
            "r_squared": round(r_sq, 6),
        }
    except (RuntimeError, ValueError) as exc:
        logger.warning("Curve fit failed for group: %s", exc)
        return {
            "status": "fit_failed",
            "data_points": len(records),
            "a": None,
            "b": None,
            "r_squared": None,
        }


def load_dataset(path: Path) -> list[dict]:
    """Load and validate dataset.json (supports both old flat format and new _meta format)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    raise ValueError(f"Unexpected dataset.json format: expected list or {{records: [...]}}")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    dataset_path = DEFAULT_DATASET
    constants_path = DEFAULT_CONSTANTS

    if not dataset_path.exists():
        logger.error("Dataset not found: %s — run parse_report.py first.", dataset_path)
        sys.exit(1)

    records = load_dataset(dataset_path)
    logger.info("Loaded %d records from %s", len(records), dataset_path)

    if not records:
        logger.warning("Dataset is empty — no constants to fit.")
        return

    # Group records by (faction, type, difficulty)
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for rec in records:
        key = (rec.get("faction", "unknown"), rec.get("type", "unknown"), rec.get("difficulty", "unknown"))
        groups.setdefault(key, []).append(rec)

    constants: dict[str, Any] = {}
    all_keys = sorted(groups.keys())

    for faction, armada_type, difficulty in all_keys:
        group_recs = groups[(faction, armada_type, difficulty)]
        group_key = f"{faction}/{armada_type}/{difficulty}"
        result = fit_group(group_recs)

        logger.info(
            "  %-40s %s (n=%d, R²=%s)",
            group_key,
            result["status"],
            result["data_points"],
            result.get("r_squared", "—"),
        )

        # Build nested dict structure
        constants.setdefault(faction, {})
        constants[faction].setdefault(armada_type, {})
        constants[faction][armada_type][difficulty] = result

    # Wrap with metadata
    output = {
        "_meta": {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": str(dataset_path),
            "record_count": len(records),
            "group_count": len(all_keys),
        },
        "constants": constants,
    }

    constants_path.parent.mkdir(parents=True, exist_ok=True)
    constants_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("\n%d groups fitted → %s", len(all_keys), constants_path)


if __name__ == "__main__":
    main()
