"""Tests for scripts/analyze.py."""

import json

import pytest

from scripts.analyze import exponential, fit_group, load_dataset, R_SQUARED_MIN


def test_exponential_returns_a_when_b_is_1():
    assert exponential(10, 100, 1.0) == 100.0


def test_exponential_doubles_each_level_when_b_is_2():
    assert exponential(1, 1, 2.0) == 2.0
    assert exponential(2, 1, 2.0) == 4.0
    assert exponential(3, 1, 2.0) == 8.0


def test_fit_group_insufficient_data():
    records = [{"level": 35, "strength": 45_000_000}]
    result = fit_group(records)
    assert result["status"] == "insufficient_data"
    assert result["a"] is None


def test_fit_group_exact_perfect_data():
    records = [
        {"level": 1, "strength": 1000},
        {"level": 2, "strength": 1250},
        {"level": 3, "strength": 1562.5},
        {"level": 4, "strength": 1953.125},
        {"level": 5, "strength": 2441.40625},
    ]
    result = fit_group(records)
    assert result["status"] == "ok"
    assert result["data_points"] == 5
    assert result["a"] == pytest.approx(800, rel=0.1)
    assert result["b"] == pytest.approx(1.25, rel=0.05)
    assert result["r_squared"] > 0.99


def test_fit_group_noisy_data():
    records = [
        {"level": 35, "strength": 45_292_360},
        {"level": 37, "strength": 72_453_312},
        {"level": 40, "strength": 137_386_288},
    ]
    result = fit_group(records)
    assert result["status"] == "ok"
    assert result["data_points"] == 3
    assert result["a"] is not None
    assert result["b"] is not None
    assert 1.1 < result["b"] < 1.5


def test_load_dataset_old_format(tmp_path):
    data = [{"level": 35, "strength": 45_000_000}]
    f = tmp_path / "dataset.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    assert load_dataset(f) == data


def test_load_dataset_new_format(tmp_path):
    data = {"_meta": {"schema_version": "1.1"}, "records": [{"level": 35, "strength": 45_000_000}]}
    f = tmp_path / "dataset.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    assert load_dataset(f) == data["records"]


def test_load_dataset_invalid_format(tmp_path):
    f = tmp_path / "dataset.json"
    f.write_text('"just a string"', encoding="utf-8")
    with pytest.raises(ValueError, match="Unexpected dataset.json format"):
        load_dataset(f)


def test_fit_group_clean_exponential_data():
    """Test fit_group with 3 perfectly exponential points → status='ok', R²≈1."""
    records = [
        {"level": 1, "strength": 10},
        {"level": 2, "strength": 20},
        {"level": 3, "strength": 40},
    ]
    result = fit_group(records)
    assert result["status"] == "ok"
    assert result["data_points"] == 3
    assert result["r_squared"] > 0.99


def test_fit_group_poor_fit_data():
    """Test fit_group with poorly fitting data → status='low_confidence', R²<R_SQUARED_MIN."""
    records = [
        {"level": 1, "strength": 10},
        {"level": 2, "strength": 1000},
        {"level": 3, "strength": 12},
    ]
    result = fit_group(records)
    assert result["status"] == "low_confidence"
    assert result["data_points"] == 3
    assert result["r_squared"] < R_SQUARED_MIN


def test_r_squared_min_constant_exists():
    """Test that R_SQUARED_MIN is defined and is a float."""
    assert isinstance(R_SQUARED_MIN, (int, float))
    assert R_SQUARED_MIN > 0
    assert R_SQUARED_MIN <= 1
