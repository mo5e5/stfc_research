import argparse
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.locales import LOCALES

logger = logging.getLogger(__name__)

DIFFICULTY_KEYWORDS = ["green", "blue", "purple"]

DEFAULT_DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DEFAULT_DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"


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


def detect_locale(lines: list[str]) -> str:
    """
    Auto-detect locale by checking which locale's section1 keys appear in the header.
    Returns "de" or "en"; defaults to "de" if ambiguous or no match.
    """
    if not lines:
        return "de"

    header = lines[0].lower()

    de_section1 = LOCALES["de"]["section1"]
    en_section1 = LOCALES["en"]["section1"]

    de_matches = sum(1 for key in de_section1.keys() if key.lower() in header)
    en_matches = sum(1 for key in en_section1.keys() if key.lower() in header)

    if en_matches > de_matches:
        return "en"
    return "de"


def _get_column_key(s1_map: dict, internal_name: str) -> str | None:
    """Get the locale-specific column key for an internal field name."""
    for col_name, field_name in s1_map.items():
        if field_name == internal_name:
            return col_name
    return None


def parse_section1(lines: list[str], locale: str = "de") -> dict:
    rows = parse_tsv(lines)
    if len(rows) < 2:
        raise ValueError(
            f"Section 1 has {len(rows)} data row(s), expected at least 2 (player + enemy)"
        )

    player, enemy = rows[0], rows[1]

    locale_data = LOCALES[locale]
    s1_map = locale_data["section1"]
    armada_map = locale_data["armada"]
    result_map = locale_data["result"]

    # Get column keys for this locale (both in player and enemy rows)
    hull_hp_max_key = _get_column_key(s1_map, "hull_hp_max")
    hull_hp_remaining_key = _get_column_key(s1_map, "hull_hp_remaining")
    officer_1_key = _get_column_key(s1_map, "officer_1")
    officer_2_key = _get_column_key(s1_map, "officer_2")
    officer_3_key = _get_column_key(s1_map, "officer_3")
    player_name_key = _get_column_key(s1_map, "player_name")
    player_level_key = _get_column_key(s1_map, "player_level")
    player_ship_key = _get_column_key(s1_map, "player_ship")
    player_ship_level_key = _get_column_key(s1_map, "player_ship_level")
    player_ship_strength_key = _get_column_key(s1_map, "player_ship_strength")
    location_key = _get_column_key(s1_map, "location")
    timestamp_key = _get_column_key(s1_map, "timestamp")
    shield_hp_max_key = _get_column_key(s1_map, "shield_hp_max")
    result_key = _get_column_key(s1_map, "result")

    hull_max = safe_int(player.get(hull_hp_max_key) if hull_hp_max_key else None, "hull_max") or 0
    hull_remaining = safe_int(player.get(hull_hp_remaining_key) if hull_hp_remaining_key else None, "hull_remaining") or 0
    hull_pct = round(hull_remaining / hull_max * 100, 1) if hull_max > 0 else 0.0

    officers = []
    for key in (officer_1_key, officer_2_key, officer_3_key):
        if key and player.get(key, "").strip() not in ("", "--"):
            officers.append(player.get(key, "").strip())

    armada_key = enemy.get(player_name_key, "").strip() if player_name_key else ""
    faction, armada_type = armada_map.get(armada_key, ("unknown", "unknown"))

    hull_hp = safe_int(enemy.get(hull_hp_max_key) if hull_hp_max_key else None, "hull_hp")
    shield_hp = safe_int(enemy.get(shield_hp_max_key) if shield_hp_max_key else None, "shield_hp")

    # Result comes from the player row
    result_str = player.get(result_key, "").strip().upper() if result_key else ""
    result = result_map.get(result_str, "loss")

    _has_any_hp = hull_hp is not None or shield_hp is not None

    return {
        "faction": faction,
        "type": armada_type,
        "level": safe_int(enemy.get(player_level_key) if player_level_key else None, "level"),
        "strength": safe_int(enemy.get(player_ship_strength_key) if player_ship_strength_key else None, "strength"),
        "hull_hp": hull_hp,
        "shield_hp": shield_hp,
        "total_hp": (hull_hp or 0) + (shield_hp or 0) if _has_any_hp else None,
        "result": result,
        "player_hull_remaining_pct": hull_pct,
        "player_ship": player.get(player_ship_key, "").strip() if player_ship_key else "",
        "player_ship_level": safe_int(player.get(player_ship_level_key) if player_ship_level_key else None, "player_ship_level"),
        "player_ship_strength": safe_int(player.get(player_ship_strength_key) if player_ship_strength_key else None, "player_ship_strength"),
        "player_officers": officers,
        "location": player.get(location_key, "").strip() if location_key else "",
        "timestamp": player.get(timestamp_key, "").strip() if timestamp_key else "",
    }


def parse_section2(lines: list[str], locale: str = "de") -> str:
    locale_data = LOCALES[locale]
    difficulty_map = locale_data["difficulty"]

    for row in parse_tsv(lines):
        name = row.get("Belohnungsname" if locale == "de" else "Reward Name", "")
        for keyword, difficulty in difficulty_map.items():
            if keyword in name:
                return difficulty
    return "unknown"


def difficulty_from_filename(filename: str) -> str:
    stem = filename.lower()
    for keyword in DIFFICULTY_KEYWORDS:
        if keyword in stem:
            return keyword
    return "unknown"


def parse_section3(lines: list[str], locale: str = "de") -> dict:
    rows = parse_tsv(lines)
    if len(rows) < 2:
        logger.warning("Section 3 has fewer than 2 data rows — returning null fields")
        locale_data = LOCALES[locale]
        enemy_fleet_map = locale_data["enemy_fleet"]
        return {json_field: None for json_field, _ in enemy_fleet_map.values()}

    enemy = rows[1]
    locale_data = LOCALES[locale]
    enemy_fleet_map = locale_data["enemy_fleet"]

    result = {}
    for locale_col, (json_field, col_type) in enemy_fleet_map.items():
        raw = enemy.get(locale_col)
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


def parse_report(filepath: Path, lang: str = "auto") -> dict:
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

    # Auto-detect locale if requested
    if lang == "auto":
        locale = detect_locale(sections[0])
    elif lang in ("de", "en"):
        locale = lang
    else:
        locale = "de"

    data = parse_section1(sections[0], locale=locale)
    difficulty = parse_section2(sections[1], locale=locale)
    if difficulty == "unknown":
        difficulty = difficulty_from_filename(filepath.name)
    data["difficulty"] = difficulty
    data.update(parse_section3(sections[2], locale=locale))
    data["rounds"] = parse_section4(sections[3])
    data["source_file"] = filepath.name
    return data


def main():
    parser = argparse.ArgumentParser(description="Parse STFC battle report CSVs")
    parser.add_argument("--data-raw", type=str, default=str(DEFAULT_DATA_RAW),
                        help=f"Raw CSV directory (default: {DEFAULT_DATA_RAW})")
    parser.add_argument("--data-processed", type=str, default=str(DEFAULT_DATA_PROCESSED),
                        help=f"Output directory (default: {DEFAULT_DATA_PROCESSED})")
    parser.add_argument("--lang", type=str, choices=["auto", "de", "en"], default="auto",
                        help="Language/locale for parsing (default: auto-detect)")
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
            records.append(parse_report(path, lang=args.lang))
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
