import csv
import json
from pathlib import Path

ARMADA_TYPE_MAP = {
    "Austausch-Bank": ("eclipse", "exchange"),
}

DIFFICULTY_MAP = {
    "Ungewöhnliche": "green",
    "Seltene": "blue",
    "Epische": "purple",
}

DATA_RAW = Path(__file__).parent.parent / "data" / "raw"
DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"


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


def safe_int(value) -> int:
    try:
        return int(str(value).strip().replace(".", "").replace(",", ""))
    except (ValueError, TypeError):
        return 0


def parse_section1(lines: list[str]) -> dict:
    rows = parse_tsv(lines)
    player, enemy = rows[0], rows[1]

    hull_max = safe_int(player.get("Hüllen-TP", 0))
    hull_remaining = safe_int(player.get("Verbleibende Hüllen-TP", 0))
    hull_pct = round(hull_remaining / hull_max * 100, 1) if hull_max > 0 else 0.0

    officers = [
        player[key].strip()
        for key in ("Offizier Eins", "Offizier Zwei", "Offizier Drei")
        if player.get(key, "").strip() not in ("", "--")
    ]

    armada_key = enemy.get("Spielername", "").strip()
    faction, armada_type = ARMADA_TYPE_MAP.get(armada_key, ("unknown", "unknown"))

    hull_hp = safe_int(enemy.get("Hüllen-TP", 0))
    shield_hp = safe_int(enemy.get("Schild-TP", 0))

    result = "win" if player.get("Ergebnis", "").strip().upper() == "SIEG" else "loss"

    return {
        "faction": faction,
        "type": armada_type,
        "level": safe_int(enemy.get("Spielerlevel", 0)),
        "strength": safe_int(enemy.get("Schiffsstärke", 0)),
        "hull_hp": hull_hp,
        "shield_hp": shield_hp,
        "total_hp": hull_hp + shield_hp,
        "result": result,
        "player_hull_remaining_pct": hull_pct,
        "player_ship": player.get("Schiffsname", "").strip(),
        "player_ship_level": safe_int(player.get("Schiffslevel", 0)),
        "player_ship_strength": safe_int(player.get("Schiffsstärke", 0)),
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


def parse_section3(lines: list[str]) -> dict:
    rows = parse_tsv(lines)
    if len(rows) < 2:
        return {"attack": 0}
    enemy = rows[1]
    return {"attack": safe_int(enemy.get("Angreifen", 0))}


def parse_section4(lines: list[str]) -> int:
    max_round = 0
    for row in parse_tsv(lines):
        try:
            max_round = max(max_round, int(str(row.get("Runde", 0)).strip()))
        except (ValueError, TypeError):
            pass
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
    data["difficulty"] = parse_section2(sections[1])
    data.update(parse_section3(sections[2]))
    data["rounds"] = parse_section4(sections[3])
    data["source_file"] = filepath.name
    return data


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(DATA_RAW.glob("*.csv"))
    if not csv_files:
        print(f"No CSVs found in {DATA_RAW}.")
        return

    records = []
    for path in csv_files:
        try:
            records.append(parse_report(path))
            print(f"  OK  {path.name}")
        except Exception as exc:
            print(f"  ERR {path.name}: {exc}")

    out = DATA_PROCESSED / "dataset.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(records)} records written → {out}")


if __name__ == "__main__":
    main()
