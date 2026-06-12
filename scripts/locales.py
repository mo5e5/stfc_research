"""
Locale-specific mappings for STFC battle report parsing.

Supports multiple languages: DE (Deutsch), EN (English).
Each locale contains mappings for armada types, difficulty levels, section headers, and result strings.
"""

LOCALES = {
    "de": {
        # Armada type mapping: ship name → (faction, type)
        "armada": {
            "Austausch-Bank": ("eclipse", "exchange"),
        },
        # Difficulty mapping: reward name → difficulty code
        "difficulty": {
            "Ungewöhnliche": "green",
            "Seltene": "blue",
            "Epische": "purple",
        },
        # Section 1 column headers → internal field name mapping
        "section1": {
            "Spielername": "player_name",
            "Spielerlevel": "player_level",
            "Ergebnis": "result",
            "Schiffsname": "player_ship",
            "Schiffslevel": "player_ship_level",
            "Schiffsstärke": "player_ship_strength",
            "Offizier Eins": "officer_1",
            "Offizier Zwei": "officer_2",
            "Offizier Drei": "officer_3",
            "Hüllen-TP": "hull_hp_max",
            "Verbleibende Hüllen-TP": "hull_hp_remaining",
            "Schild-TP": "shield_hp_max",
            "Verbleibende Schild-TP": "shield_hp_remaining",
            "Standort": "location",
            "Zeitstempel": "timestamp",
        },
        # Section 3 column headers for enemy fleet → (json_field, type)
        "enemy_fleet": {
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
        },
        # Battle result strings → normalized result code
        "result": {
            "SIEG": "win",
            "NIEDERLAGE": "loss",
        },
    },
    "en": {
        # Armada type mapping: ship name → (faction, type)
        "armada": {
            "Exchange Bank": ("eclipse", "exchange"),
        },
        # Difficulty mapping: reward name → difficulty code
        "difficulty": {
            "Uncommon": "green",
            "Rare": "blue",
            "Epic": "purple",
        },
        # Section 1 column headers → internal field name mapping
        "section1": {
            "Player Name": "player_name",
            "Player Level": "player_level",
            "Result": "result",
            "Ship Name": "player_ship",
            "Ship Level": "player_ship_level",
            "Ship Strength": "player_ship_strength",
            "Officer One": "officer_1",
            "Officer Two": "officer_2",
            "Officer Three": "officer_3",
            "Hull HP": "hull_hp_max",
            "Remaining Hull HP": "hull_hp_remaining",
            "Shield HP": "shield_hp_max",
            "Remaining Shield HP": "shield_hp_remaining",
            "Location": "location",
            "Timestamp": "timestamp",
        },
        # Section 3 column headers for enemy fleet → (json_field, type)
        "enemy_fleet": {
            "Attack": ("attack", "int"),
            "Damage Per Round": ("damage_per_round", "int"),
            "Critical Chance": ("crit_chance", "float"),
            "Critical Damage": ("crit_damage", "float"),
            "Defense": ("defense", "int"),
            "Armour": ("armour", "int"),
            "Shield Deflection": ("shield_deflection", "int"),
            "Dodge": ("dodge", "int"),
            "Armour Pierce": ("armour_pierce", "int"),
            "Shield Pierce": ("shield_pierce", "int"),
            "Accuracy": ("accuracy", "int"),
            "Ship Ability": ("ship_ability", "str"),
        },
        # Battle result strings → normalized result code
        "result": {
            "WIN": "win",
            "LOSS": "loss",
        },
    },
}
