import pytest

from scripts.parse_report import (
    parse_report,
    parse_section1,
    parse_section2,
    parse_section3,
    parse_section4,
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
    *SECTION3_LINES,
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


# ── parse_section3 ─────────────────────────────────────────────────────────────

def test_section3_attack():
    assert parse_section3(SECTION3_LINES)["attack"] == 570510


def test_section3_only_header_returns_zero():
    assert parse_section3(["Flotte\tAngreifen"]) == {"attack": 0}


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
    assert record["rounds"] == 12
    assert record["location"] == "Karppinen"
    assert record["timestamp"] == "2026-05-03T19:23:31"
    assert record["source_file"] == "stella vs 35 green.csv"


def test_parse_report_too_few_sections(tmp_path):
    csv_file = tmp_path / "broken.csv"
    csv_file.write_text("nur eine Sektion\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Fewer than 4 sections"):
        parse_report(csv_file)
