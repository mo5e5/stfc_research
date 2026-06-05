import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ARMADA_TYPE_MAP = {
    "Austausch-Bank": ("eclipse", "exchange"),
}

DIFFICULTY_MAP = {
    "Ungewöhnliche": "green",
    "Seltene": "blue",
    "Epische": "purple",
}

DIFFICULTY_KEYWORDS = ["green", "blue", "purple"]

DEFAULT_DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DEFAULT_DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"

# Section 3 enemy fleet column mapping (DE column → (JSON field, type))
# type: "int" | "float" | "str"
ENEMY_FLEET_COLUMNS: dict[str, tuple[str, str]] = {
    "Angreifen": ("attack", "int"),
    "Schaden pro Runde": ("damage_per_round", "int"),
    "Kritische Trefferchance": ("crit_chance", "float"),
    "Kritischer Schaden": ("crit_damage", "float"),
    "Verteidigung": ("defense", "int"),
    "Panzerung": ("armour", "int"),
    "Schildablenkung": ("shield_deflection", "int"),
    "Ausweichen": ("dodge", "int"),
    "Rüstungsdurchdringung": ("armour_pierce", "int"),
    "Schilddurchdringung": ("shield_pierce", "int"),
    "Genauigkeit": ("accuracy", "int"),
    "Schiffsabilität": ("ship_ability", "str"),
}


def split_sections(lines: list[str]) -> list[list[str]]:
    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                sections.append(current)
                current = []
        else:
            current.append(line)
    if current:
        sections.append(current)
    return sections


def parse_tsv(lines: list[str]) -> list[dict]:
    return list(csv.DictReader(lines, delimiter="\t"))


def safe_int(value: Any, field_name: str = "unknown") -> int | None:
    """Parse an integer from a CSV cell. Returns None on failure and logs a warning."""
    if value is None or str(value).strip() in ("", "--"):
        return None
    try:
        cleaned = str(value).strip().replace(".", "").replace(",", "")
        return int(cleaned)
    except (ValueError, TypeError):
        logger.warning("safe_int: cannot parse '%s' as int for field '%s'", value, field_name)
        return None


def safe_float(value: Any, field_name: str = "unknown") -> float | None:
    """Parse a float from a CSV cell. Returns None on failure and logs a warning."""
    if value is None or str(value).strip() in ("", "--"):
        return None
    try:
        cleaned = str(value).strip().replace(",", ".")  # European decimal comma → dot
        return float(cleaned)
    except (ValueError, TypeError):
        logger.warning("safe_float: cannot parse '%s' as float for field '%s'", value, field_name)
        return None


def parse_section1(lines: list[str]) -> dict:
    rows = parse_tsv(lines)
    if len(rows) < 2:
        raise ValueError(
            f"Section 1 has {len(rows)} data row(s), expected at least 2 (player + enemy)"
        )

    player, enemy = rows[0], rows[1]

    hull_max = safe_int(player.get("Hüllen-TP"), "hull_max") or 0
    hull_remaining = safe_int(player.get("Verbleibende Hüllen-TP"), "hull_remaining") or 0
    hull_pct = round(hull_remaining / hull_max * 100, 1) if hull_max > 0 else 0.0

    officers = [
        player[key].strip()
        for key in ("Offizier Eins", "Offizier Zwei", "Offizier Drei")
        if player.get(key, "").strip() not in ("", "--")
    ]

    armada_key = enemy.get("Spielername", "").strip()
    faction, armada_type = ARMADA_TYPE_MAP.get(armada_key, ("unknown", "unknown"))

    hull_hp = safe_int(enemy.get("Hüllen-TP"), "hull_hp")
    shield_hp = safe_int(enemy.get("Schild-TP"), "shield_hp")

    result = "win" if player.get("Ergebnis", "").strip().upper() == "SIEG" else "loss"

    _has_any_hp = hull_hp is not None or shield_hp is not None

    return {
        "faction": faction,
        "type": armada_type,
        "level": safe_int(enemy.get("Spielerlevel"), "level"),
        "strength": safe_int(enemy.get("Schiffsstärke"), "strength"),
        "hull_hp": hull_hp,
        "shield_hp": shield_hp,
        "total_hp": (hull_hp or 0) + (shield_hp or 0) if _has_any_hp else None,
        "result": result,
        "player_hull_remaining_pct": hull_pct,
        "player_ship": player.get("Schiffsname", "").strip(),
        "player_ship_level": safe_int(player.get("Schiffslevel"), "player_ship_level"),
        "player_ship_strength": safe_int(player.get("Schiffsstärke"), "player_ship_strength"),
        "player_officers": officers,
        "location": player.get("Standort", "").strip(),
        "timestamp": player.get("Zeitstempel", "").strip(),
    }


def parse_section2(lines: list[str]) -> str:
    for row in parse_tsv(lines):
        name = row.get("Belohnungsname", "")
        for keyword, difficulty in DIFFICULTY_MAP.items():
            if keyword in name:
                return difficulty
    return "unknown"


def difficulty_from_filename(filename: str) -> str:
    stem = filename.lower()
    for keyword in DIFFICULTY_KEYWORDS:
        if keyword in stem:
            return keyword
    return "unknown"


def parse_section3(lines: list[str]) -> dict:
    rows = parse_tsv(lines)
    if len(rows) < 2:
        logger.warning("Section 3 has fewer than 2 data rows — returning null fields")
        return {json_field: None for json_field, _ in ENEMY_FLEET_COLUMNS.values()}

    enemy = rows[1]
    result = {}
    for de_col, (json_field, col_type) in ENEMY_FLEET_COLUMNS.items():
        raw = enemy.get(de_col)
        if raw is None or str(raw).strip() in ("", "--"):
            result[json_field] = None
        elif col_type == "str":
            result[json_field] = str(raw).strip()
        elif col_type == "float":
            result[json_field] = safe_float(raw, json_field)
        else:
            result[json_field] = safe_int(raw, json_field)
    return result


def parse_section4(lines: list[str]) -> int:
    max_round = 0
    for row in parse_tsv(lines):
        try:
            max_round = max(max_round, int(str(row.get("Runde", 0)).strip()))
        except (ValueError, TypeError):
            logger.debug("parse_section4: skipping unparseable round value '%s'", row.get("Runde"))
    return max_round


def parse_report(filepath: Path) -> dict:
    text = None
    for enc in ("utf-8", "cp1252"):
        try:
            text = filepath.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError(f"Could not decode {filepath.name}")

    sections = split_sections(text.splitlines())
    if len(sections) < 4:
        raise ValueError(f"{filepath.name}: Fewer than 4 sections found")

    data = parse_section1(sections[0])
    difficulty = parse_section2(sections[1])
    if difficulty == "unknown":
        difficulty = difficulty_from_filename(filepath.name)
    data["difficulty"] = difficulty
    data.update(parse_section3(sections[2]))
    data["rounds"] = parse_section4(sections[3])
    data["source_file"] = filepath.name
    return data


def main():
    parser = argparse.ArgumentParser(description="Parse STFC battle report CSVs")
    parser.add_argument("--data-raw", type=str, default=str(DEFAULT_DATA_RAW),
                        help=f"Raw CSV directory (default: {DEFAULT_DATA_RAW})")
    parser.add_argument("--data-processed", type=str, default=str(DEFAULT_DATA_PROCESSED),
                        help=f"Output directory (default: {DEFAULT_DATA_PROCESSED})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress info logging")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else (
        logging.WARNING if args.quiet else logging.INFO
    )
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    data_raw = Path(args.data_raw)
    data_processed = Path(args.data_processed)
    data_processed.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(data_raw.glob("*.csv")) + sorted(data_raw.glob("*.CSV"))
    if not csv_files:
        logger.info("No CSVs found in %s.", data_raw)
        return

    records: list[dict] = []
    errors = 0
    for path in csv_files:
        try:
            records.append(parse_report(path))
            logger.info("  OK  %s", path.name)
        except ValueError as exc:
            errors += 1
            logger.warning("  ERR %s: %s", path.name, exc)
        except Exception as exc:
            errors += 1
            logger.exception("  UNEXPECTED ERROR %s: %s", path.name, exc)

    out = data_processed / "dataset.json"
    output = {
        "_meta": {
            "schema_version": "1.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_count": len(records) + errors,
            "parse_errors": errors,
            "success_count": len(records),
        },
        "records": records,
    }
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("%d records written → %s (%d errors)", len(records), out, errors)


if __name__ == "__main__":
    main()
