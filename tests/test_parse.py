import pytest

from scripts.parse_report import (
    difficulty_from_filename,
    parse_report,
    parse_section1,
    parse_section2,
    parse_section3,
    parse_section4,
    safe_float,
    safe_int,
    split_sections,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SECTION1_LINES = [
    (
        "Spielername\tSpielerlevel\tErgebnis\tSchiffsname\tSchiffslevel\tSchiffsstärke"
        "\tOffizier Eins\tOffizier Zwei\tOffizier Drei"
        "\tHüllen-TP\tVerbleibende Hüllen-TP\tSchild-TP\tVerbleibende Schild-TP\tStandort\tZeitstempel"
    ),
    (
        "m0535\t55\tSIEG\tSTELLA\t25\t2008084"
        "\tJames T. Kirk\tSpock\tKhan Noonien Singh"
        "\t5000000\t4530000\t3000000\t0\tKarppinen\t2026-05-03T19:23:31"
    ),
    (
        "Austausch-Bank\t35\t\tAustausch-Bank\t35\t45292360"
        "\t--\t--\t--"
        "\t51249215\t0\t34785341\t0\t\t"
    ),
]

SECTION2_GREEN = ["Belohnungsname\tAnzahl", "Ungewöhnliche Schrottteile\t5"]
SECTION2_BLUE = ["Belohnungsname\tAnzahl", "Seltene Ausrüstung\t3"]
SECTION2_PURPLE = ["Belohnungsname\tAnzahl", "Epische Teile\t1"]

SECTION3_LINES = [
    "Flotte\tAngreifen\tSchaden pro Runde\tKritische Trefferchance\tKritischer Schaden",
    "Spielerflotte 1\t1000000\t50000\t10\t200",
    "Feindliche Flotte 1\t570510\t28000\t5\t150",
]

SECTION3_LINES_FULL = [
    "Flotte\tAngreifen\tSchaden pro Runde\tKritische Trefferchance\tKritischer Schaden"
    "\tVerteidigung\tPanzerung\tSchildablenkung\tAusweichen"
    "\tRüstungsdurchdringung\tSchilddurchdringung\tGenauigkeit\tSchiffsabilität",
    "Spielerflotte 1\t1000000\t50000\t10\t200\t500000\t8000000\t300000\t25000\t15000\t10000\t40000\t--",
    "Feindliche Flotte 1\t570510\t28000\t5\t150\t420000\t6500000\t250000\t18000\t12000\t8000\t35000\tInterdimensional Threat III",
]

SECTION4_LINES = [
    "Runde\tEreignis\tAngreifer\tZiel\tSchaden",
    "1\tAngriff\tSTELLA\tAustausch-Bank\t100000",
    "7\tAngriff\tAustausch-Bank\tSTELLA\t50000",
    "12\tAngriff\tSTELLA\tAustausch-Bank\t200000",
]

SAMPLE_CSV = "\n".join([
    *SECTION1_LINES,
    "",
    *SECTION2_GREEN,
    "",
    *SECTION3_LINES_FULL,
    "",
    *SECTION4_LINES,
])


# ── split_sections ─────────────────────────────────────────────────────────────

def test_split_sections_returns_four():
    assert len(split_sections(SAMPLE_CSV.splitlines())) == 4


def test_split_sections_ignores_trailing_blanks():
    lines = SAMPLE_CSV.splitlines() + ["", ""]
    assert len(split_sections(lines)) == 4


def test_split_sections_multiple_blank_lines_between():
    lines = [*SECTION1_LINES, "", "", *SECTION2_GREEN, "", *SECTION3_LINES, "", *SECTION4_LINES]
    assert len(split_sections(lines)) == 4


# ── parse_section1 ─────────────────────────────────────────────────────────────

def test_section1_faction_and_type():
    data = parse_section1(SECTION1_LINES)
    assert data["faction"] == "eclipse"
    assert data["type"] == "exchange"


def test_section1_unknown_armada():
    lines = [SECTION1_LINES[0], SECTION1_LINES[1], SECTION1_LINES[2].replace("Austausch-Bank", "Unbekannt")]
    data = parse_section1(lines)
    assert data["faction"] == "unknown"
    assert data["type"] == "unknown"


def test_section1_level_and_strength():
    data = parse_section1(SECTION1_LINES)
    assert data["level"] == 35
    assert data["strength"] == 45292360


def test_section1_hp():
    data = parse_section1(SECTION1_LINES)
    assert data["hull_hp"] == 51249215
    assert data["shield_hp"] == 34785341
    assert data["total_hp"] == 51249215 + 34785341


def test_section1_result_win():
    assert parse_section1(SECTION1_LINES)["result"] == "win"


def test_section1_result_loss():
    lines = [
        SECTION1_LINES[0],
        SECTION1_LINES[1].replace("SIEG", "NIEDERLAGE"),
        SECTION1_LINES[2],
    ]
    assert parse_section1(lines)["result"] == "loss"


def test_section1_player_hull_remaining_pct():
    data = parse_section1(SECTION1_LINES)
    assert data["player_hull_remaining_pct"] == pytest.approx(90.6, abs=0.1)


def test_section1_player_hull_pct_zero_when_max_zero():
    lines = [
        SECTION1_LINES[0],
        SECTION1_LINES[1].replace("5000000\t4530000", "0\t0"),
        SECTION1_LINES[2],
    ]
    assert parse_section1(lines)["player_hull_remaining_pct"] == 0.0


def test_section1_player_ship():
    data = parse_section1(SECTION1_LINES)
    assert data["player_ship"] == "STELLA"
    assert data["player_ship_level"] == 25
    assert data["player_ship_strength"] == 2008084


def test_section1_officers():
    data = parse_section1(SECTION1_LINES)
    assert data["player_officers"] == ["James T. Kirk", "Spock", "Khan Noonien Singh"]


def test_section1_officers_excludes_dashes():
    lines = [
        SECTION1_LINES[0],
        SECTION1_LINES[1].replace("James T. Kirk\tSpock\tKhan Noonien Singh", "--\t--\t--"),
        SECTION1_LINES[2],
    ]
    assert parse_section1(lines)["player_officers"] == []


def test_section1_location_and_timestamp():
    data = parse_section1(SECTION1_LINES)
    assert data["location"] == "Karppinen"
    assert data["timestamp"] == "2026-05-03T19:23:31"


# ── parse_section2 ─────────────────────────────────────────────────────────────

def test_section2_green():
    assert parse_section2(SECTION2_GREEN) == "green"


def test_section2_blue():
    assert parse_section2(SECTION2_BLUE) == "blue"


def test_section2_purple():
    assert parse_section2(SECTION2_PURPLE) == "purple"


def test_section2_unknown():
    lines = ["Belohnungsname\tAnzahl", "Gewöhnliche Belohnung\t1"]
    assert parse_section2(lines) == "unknown"


# ── safe_int / safe_float / difficulty_from_filename ─────────────────────────

def test_safe_int_parses_integer():
    assert safe_int("12345", "test") == 12345


def test_safe_int_handles_thousands_separators():
    assert safe_int("1.500", "test") == 1500


def test_safe_int_returns_none_for_invalid():
    assert safe_int("abc", "test") is None


def test_safe_int_returns_none_for_none():
    assert safe_int(None, "test") is None


def test_safe_int_returns_none_for_dash():
    assert safe_int("--", "test") is None


def test_safe_float_parses_float():
    assert safe_float("5.5", "test") == 5.5


def test_safe_float_handles_european_comma():
    assert safe_float("5,5", "test") == 5.5


def test_safe_float_returns_none_for_invalid():
    assert safe_float("abc", "test") is None


def test_difficulty_from_filename_green():
    assert difficulty_from_filename("stella_vs_35_green.csv") == "green"


def test_difficulty_from_filename_blue():
    assert difficulty_from_filename("borg_42_blue.csv") == "blue"


def test_difficulty_from_filename_purple():
    assert difficulty_from_filename("eclipse_40_purple.csv") == "purple"


def test_difficulty_from_filename_unknown():
    assert difficulty_from_filename("report_unknown.csv") == "unknown"


def test_difficulty_from_filename_case_insensitive():
    assert difficulty_from_filename("eclipse_35_GREEN.csv") == "green"


# ── parse_section3 ─────────────────────────────────────────────────────────────

def test_section3_attack():
    assert parse_section3(SECTION3_LINES)["attack"] == 570510


def test_section3_only_header_returns_none():
    result = parse_section3(["Flotte\tAngreifen"])
    assert result["attack"] is None


def test_section3_all_fields_with_full_fixture():
    result = parse_section3(SECTION3_LINES_FULL)
    assert result["attack"] == 570510
    assert result["damage_per_round"] == 28000
    assert result["crit_chance"] == 5.0
    assert result["crit_damage"] == 150.0
    assert result["defense"] == 420000
    assert result["armour"] == 6500000
    assert result["shield_deflection"] == 250000
    assert result["dodge"] == 18000
    assert result["armour_pierce"] == 12000
    assert result["shield_pierce"] == 8000
    assert result["accuracy"] == 35000
    assert result["ship_ability"] == "Interdimensional Threat III"


def test_section3_missing_columns_return_none():
    """With minimal SECTION3_LINES, columns not in the header should be None."""
    result = parse_section3(SECTION3_LINES)
    assert result["attack"] == 570510
    assert result["defense"] is None
    assert result["armour"] is None
    assert result["ship_ability"] is None


# ── parse_section4 ─────────────────────────────────────────────────────────────

def test_section4_max_round():
    assert parse_section4(SECTION4_LINES) == 12


def test_section4_only_header_returns_zero():
    assert parse_section4(["Runde\tEreignis"]) == 0


# ── parse_report (integration) ─────────────────────────────────────────────────

def test_parse_report_full(tmp_path):
    csv_file = tmp_path / "stella vs 35 green.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    record = parse_report(csv_file)

    assert record["faction"] == "eclipse"
    assert record["type"] == "exchange"
    assert record["difficulty"] == "green"
    assert record["level"] == 35
    assert record["strength"] == 45292360
    assert record["hull_hp"] == 51249215
    assert record["shield_hp"] == 34785341
    assert record["total_hp"] == 86034556
    assert record["result"] == "win"
    assert record["player_hull_remaining_pct"] == pytest.approx(90.6, abs=0.1)
    assert record["player_ship"] == "STELLA"
    assert record["player_ship_level"] == 25
    assert record["player_ship_strength"] == 2008084
    assert record["player_officers"] == ["James T. Kirk", "Spock", "Khan Noonien Singh"]
    assert record["attack"] == 570510
    assert record["damage_per_round"] == 28000
    assert record["crit_chance"] == 5.0
    assert record["crit_damage"] == 150.0
    assert record["defense"] == 420000
    assert record["armour"] == 6500000
    assert record["shield_deflection"] == 250000
    assert record["dodge"] == 18000
    assert record["armour_pierce"] == 12000
    assert record["shield_pierce"] == 8000
    assert record["accuracy"] == 35000
    assert record["ship_ability"] == "Interdimensional Threat III"
    assert record["rounds"] == 12
    assert record["location"] == "Karppinen"
    assert record["timestamp"] == "2026-05-03T19:23:31"
    assert record["source_file"] == "stella vs 35 green.csv"


def test_parse_report_too_few_sections(tmp_path):
    csv_file = tmp_path / "broken.csv"
    csv_file.write_text("nur eine Sektion\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Fewer than 4 sections"):
        parse_report(csv_file)
