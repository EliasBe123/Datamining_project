"""Checks for provided infrastructure. These do not certify the student analyses."""
from dataclasses import replace
import json

import pandas as pd
import pytest

from cns_groups.config import Config
from cns_groups.contracts import (COVERAGE_COLUMNS, FEATURE_COLUMNS, PAIR_COLUMNS, ProcessedData,
                                  load_processed, save_tables, validate_tables)
from cns_groups.pipeline import run


@pytest.fixture
def example_data():
    # Small agreed handoff, not a processing algorithm or an expected real result.
    pair = pd.DataFrame([[0, 1, 2, 1, 0, 0, 0, 0, 0]], columns=PAIR_COLUMNS + FEATURE_COLUMNS)
    coverage = pd.DataFrame([[0, 3000, 3000, 3000/4032, True, 3000/4032, True],
                             [1, 3000, 0, 3000/4032, True, 0.0, False]], columns=COVERAGE_COLUMNS)
    return ProcessedData(pair, pair.copy(), coverage, pair[PAIR_COLUMNS].copy())


def test_csv_handoff_roundtrip(tmp_path, example_data):
    save_tables(example_data, tmp_path)
    loaded = load_processed(tmp_path)
    pd.testing.assert_frame_equal(loaded.discovery_pairs, example_data.discovery_pairs)
    pd.testing.assert_frame_equal(loaded.coverage, example_data.coverage)
    assert not loaded.coverage.iloc[1].evaluation_eligible


def test_handoff_rejects_missing_columns_and_duplicate_pairs(example_data):
    with pytest.raises(ValueError, match="missing columns"):
        validate_tables(replace(example_data, discovery_pairs=pd.DataFrame()))
    repeated = pd.concat([example_data.discovery_pairs] * 2)
    with pytest.raises(ValueError, match="one non-null row"):
        validate_tables(replace(example_data, discovery_pairs=repeated))


def test_missing_processing_handoff_is_clear(tmp_path):
    with pytest.raises(FileNotFoundError, match="processing"):
        run("rules", tmp_path / "raw", tmp_path / "output", Config())


def test_pipeline_exports_processing_and_rejects_mixed_config(tmp_path, monkeypatch, example_data):
    # Replace the unfinished analysis only here to test the supplied file plumbing.
    monkeypatch.setattr("cns_groups.processing.run", lambda raw, cfg: example_data)
    target = tmp_path / "run"
    run("processing", tmp_path, target, Config())
    assert (target / "processed/discovery_pairs.csv").exists()
    assert json.loads((target / "config.json").read_text())["period_days"] == 14
    with pytest.raises(ValueError, match="different config"):
        run("rules", tmp_path, target, Config(rssi_threshold=-75))
    with pytest.raises(ValueError, match="already exist"):
        run("processing", tmp_path, target, Config())
