"""WORK AREA 1 — data processing. Suggested owner: Elias (swap roles freely).

INPUT: original files in data/raw/, plus Config.
OUTPUT: ProcessedData containing four tables; pipeline.py exports them to
        results/<run>/processed/ for BOTH rules.py and clustering.py.

Start with a few rows using pandas.read_csv(..., nrows=20). Do not begin by
running every analysis. See HANDOFFS.md for the exact shared column names.
You may add private helper functions inside this file as you work.
"""
from pathlib import Path

import pandas as pd

from .config import Config
from .contracts import ProcessedData


def clean_records(frame: pd.DataFrame, kind: str, cfg: Config) -> pd.DataFrame:
    """TODO 1: return cleaned events with canonical COLUMN names and time columns.

    Inputs:
      kind = 'bt', 'calls', or 'sms'. Raw headers differ between files.
      Bluetooth: '# timestamp', user_a, user_b, rssi.
      Calls: timestamp, caller, callee, duration. SMS: timestamp, sender, recipient.
    Output:
      timestamp, user_a, user_b, plus rssi/duration if present, and bin/day/period.
      Keep call/SMS direction here. period is 0 (discovery) or 1 (evaluation).

    Work to do:
    - Standardise headers; validate numeric fields and integer IDs.
    - Reject invalid/self-interaction rows and times outside the two periods.
    - Keep Bluetooth -1/-2 markers for coverage. Do NOT make them students.
    - Keep missed calls (-1 duration), but distinguish them from completed calls.
    - Derive time-bin, day, and period from relative seconds, with no overlap.
    - Record/explain how many rows each cleaning rule excludes.

    Check by hand: timestamp == cfg.period_seconds belongs to period 1.
    A single malformed value should not silently change the remaining rows.
    """
    raise NotImplementedError("Processing task 1: clean_records")


def observation_coverage(bt: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """TODO 2: return COVERAGE_COLUMNS, one row per student across both periods.

    Input is cleaned Bluetooth BEFORE RSSI filtering/removing sentinel rows.
    A scan (even empty) or detection by another student is observation evidence.
    Count each student/bin once even if that student meets several people.
    Divide observed bins by all possible bins in each period; derive eligibility
    with cfg.coverage_threshold. Include zero coverage for an absent period.

    Check: observed with no peers is different from having no observation.
    Student identifiers are nominal labels, not quantities to compare numerically.
    """
    raise NotImplementedError("Processing task 2: observation_coverage")


def aggregate_pairs(bt: pd.DataFrame, calls: pd.DataFrame, sms: pd.DataFrame,
                    period: int, cfg: Config) -> pd.DataFrame:
    """TODO 3: cleaned event tables -> PAIR_COLUMNS + FEATURE_COLUMNS.

    - Select ONLY the requested period, then construct unordered pairs (a < b).
    - Remove Bluetooth sentinel rows from interactions; retain strongest RSSI
      per pair/bin and apply cfg.rssi_threshold.
    - Count proximity bins AND distinct proximity days separately.
    - Count SMS events/days, positive-duration calls/days, and all call attempts.
    - Join channel aggregates, filling absent recorded counts with zero.
    - Preserve distinct same-second messages; they may be real separate events.

    Example: 40 proximity bins on one day -> bins=40, days=1, not 40 days.
    Alice seeing Bob and Bob seeing Alice in one bin must count only once.
    """
    raise NotImplementedError("Processing task 3: aggregate_pairs")


def run(raw: Path, cfg: Config) -> ProcessedData:
    """TODO 4: connect your helpers and return the four shared tables.

    Read the three CSVs (bt_symmetric.csv, calls.csv, sms.csv) with pandas.
    Call clean_records, observation_coverage, and aggregate_pairs for periods 0/1.
    Build pair_population from ANY cleaned discovery-period pair interaction,
    including weak Bluetooth and missed calls. Exclude sentinel IDs and duplicates.
    Do not filter this rule population using later observations.

    Return ProcessedData(discovery_pairs=..., evaluation_pairs=...,
                         coverage=..., pair_population=...).
    The CLI handles saving these tables. No need to implement file handoffs here.
    First acceptance check: python -m pytest tests/test_exercises.py -q
    """
    raise NotImplementedError("Processing task 4: run")
