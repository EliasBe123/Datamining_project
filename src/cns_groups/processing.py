"""WORK AREA 1 — data processing. Suggested owner: Elias (swap roles freely).

INPUT: original files in data/raw/, plus Config.
OUTPUT: ProcessedData containing four tables; pipeline.py exports them to
        results/<run>/processed/ for BOTH rules.py and clustering.py.

Start with a few rows using pandas.read_csv(..., nrows=20). Do not begin by
running every analysis. See HANDOFFS.md for the exact shared column names.
You may add private helper functions inside this file as you work.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from .config import Config
from .contracts import ProcessedData
PAIR = ["user_a", "user_b"]
FEATURES = ["proximity_bins", "proximity_days", "sms_count", "sms_days",
            "completed_calls", "call_days", "call_attempts"]
SCHEMAS = {"bt": ["timestamp", *PAIR, "rssi"],
           "calls": ["timestamp", *PAIR, "duration"], "sms": ["timestamp", *PAIR]}

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
    frame = frame.copy()

    frame.columns = (
        frame.columns
        .str.strip()
        .str.lstrip("#")
        .str.strip()
    )

    frame = frame.rename(columns={
        "caller": "user_a",
        "callee": "user_b",
        "sender": "user_a",
        "recipient": "user_b",
    })
    #Validate schema
    if list(frame.columns) != SCHEMAS[kind]:
      raise ValueError(f"Unexpected columns: {list(frame.columns)}")
    for column in SCHEMAS[kind]:
      frame[column] = pd.to_numeric(frame[column], errors="coerce")
    valid = np.isfinite(frame[SCHEMAS[kind]]).all(axis=1)

    for column in SCHEMAS[kind]:
       valid &= frame[column].eq(np.floor(frame[column]))
    
    valid &= frame["user_a"].ne(frame["user_b"])
    frame = frame[valid].copy()
    #remove rows with invalid user_a values
    before = len(frame)

    frame = frame[frame["user_a"].ge(0)].copy()

    excluded = before - len(frame)
    print(f"Excluded {excluded} rows with negative or invalid user_a values.")

    if kind == "calls" or kind == "sms":
        #remove rows with invalid user_b values for calls and sms
        before = len(frame)

        frame = frame[frame["user_b"].ge(0)].copy()

        excluded = before - len(frame)
        print(f"Excluded {excluded} rows with negative or invalid user_b values for calls and sms.")
    
    if kind == "calls":
        #remove rows with invalid duration values for calls
        before = len(frame)

        frame = frame[frame["duration"].ge(-1)].copy()

        excluded = before - len(frame)
        print(f"Excluded {excluded} rows with invalid duration values for calls.")
    
    if kind == "bt":
        #remove rows with invalid user_b values for bluetooth
        before = len(frame)

        frame = frame[frame["user_b"].ge(-2)].copy()

        excluded = before - len(frame)
        print(f"Excluded {excluded} rows with invalid user_b values for bluetooth.")

        #remove rows with invalid bluetooth RSSI values
        before = len(frame)

        frame = frame[frame["rssi"].le(0)].copy()

        excluded = before - len(frame)
        print(f"Excluded {excluded} rows with invalid rssi values.")
    inside_window = (
    frame["timestamp"].ge(0)
    & frame["timestamp"].lt(2 * cfg.period_seconds)
  )

    frame = frame.loc[inside_window].copy()
    frame = frame.astype("int64")

    frame["bin"] = frame["timestamp"] // cfg.bin_seconds
    frame["day"] = frame["timestamp"] // 86400
    frame["period"] = frame["timestamp"] // cfg.period_seconds
    return frame


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
    scanning_students = bt[["user_a", "bin", "period"]].rename(columns={"user_a": "user"})
    detected_students = bt.loc[bt.user_b.ge(0), ["user_b", "bin", "period"]].rename(columns={"user_b": "user"})
    observations = pd.concat(
      [scanning_students, detected_students],
      ignore_index=True,
  )

    observations = observations.drop_duplicates(["user", "bin"])

    counts = (
      observations
      .groupby(["user", "period"])
      .size()
      .unstack(fill_value=0)
  )
    
    
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
    bt_sym = pd.read_csv(raw / "bt_symmetric.csv")
    calls = pd.read_csv(raw / "calls.csv")
    sms = pd.read_csv(raw / "sms.csv")
    clean_bt = clean_records(bt_sym, "bt", cfg)
    clean_calls = clean_records(calls, "calls", cfg)
    clean_sms = clean_records(sms, "sms", cfg)

    raise NotImplementedError("Processing task 4: run")

