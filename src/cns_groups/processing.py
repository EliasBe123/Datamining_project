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
    
    counts = counts.reindex(columns=[0, 1], fill_value=0)
    counts.columns = ["discovery_bins", "evaluation_bins"]

    possible_bins = cfg.period_seconds // cfg.bin_seconds

    counts["discovery_coverage"] = (
        counts["discovery_bins"] / possible_bins
    )

    counts["evaluation_coverage"] = (
        counts["evaluation_bins"] / possible_bins
    )

    counts["discovery_eligible"] = (
      counts["discovery_coverage"] >= cfg.coverage_threshold
    )

    counts["evaluation_eligible"] = (
        counts["evaluation_coverage"] >= cfg.coverage_threshold
    )
    return counts.reset_index()[
        [
            "user",
            "discovery_bins",
            "evaluation_bins",
            "discovery_coverage",
            "discovery_eligible",
            "evaluation_coverage",
            "evaluation_eligible",
        ]
    ]

#Private function to order pairs and remove sentinel rows
def _unordered_pairs(frame):
    result = frame.loc[frame["user_b"] >= 0].copy()

    endpoints = result[PAIR].to_numpy()
    result["user_a"] = endpoints.min(axis=1)
    result["user_b"] = endpoints.max(axis=1)

    return result

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

    
    #Select only the requested period
    bt_period = bt.loc[bt["period"].eq(period)].copy()
    calls_period = calls.loc[calls["period"].eq(period)].copy()
    sms_period = sms.loc[sms["period"].eq(period)].copy()
    bt_period = _unordered_pairs(bt_period)

    bt_period = (
      bt_period
      .groupby(PAIR + ["bin"], as_index=False)
      .agg(
          rssi=("rssi", "max"),
          day=("day", "first"),
      )
    )
    #Keep only rows with RSSI above the threshold
    bt_period = bt_period.loc[
      bt_period["rssi"].ge(cfg.rssi_threshold)
    ]
    #Aggregate proximity bins and days per pair
    proximity = bt_period.groupby(PAIR).agg(
      proximity_bins=("bin", "size"),
      proximity_days=("day", "nunique"),
    )

    #Aggregate SMS counts and days per pair
    sms_period = _unordered_pairs(sms_period)
    sms_summary = sms_period.groupby(PAIR).agg(
      sms_count=("timestamp", "size"),
      sms_days=("day", "nunique"),
    )

    #Aggregate completed calls and days per pair
    calls_period = _unordered_pairs(calls_period)
    call_attempts = (
      calls_period
      .groupby(PAIR)
      .size()
      .rename("call_attempts")
      .to_frame()
    )
    #Aggregate completed calls and days per pair
    completed = calls_period.loc[
      calls_period["duration"].gt(0)
    ]
    completed_summary = completed.groupby(PAIR).agg(
        completed_calls=("timestamp", "size"),
        call_days=("day", "nunique"),
    )

    #Combine all aggregates into a single DataFrame, filling missing values with zero
    combined = pd.concat(
      [
          proximity,
          sms_summary,
          completed_summary,
          call_attempts,
      ],
      axis=1,
      join="outer",
    )
    combined = combined.fillna(0).astype("int64")
    result = combined.reset_index()
    return result[PAIR + FEATURES].sort_values(PAIR).reset_index(drop=True)



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
    #Read the three CSVs (bt_symmetric.csv, calls.csv, sms.csv) with pandas
    bt_sym = pd.read_csv(raw / "bt_symmetric.csv")
    calls = pd.read_csv(raw / "calls.csv")
    sms = pd.read_csv(raw / "sms.csv")

    #clean the csvs using clean_records
    clean_bt = clean_records(bt_sym, "bt", cfg)
    clean_calls = clean_records(calls, "calls", cfg)
    clean_sms = clean_records(sms, "sms", cfg)

    #Compute observation coverage for each student across both periods
    coverage = observation_coverage(clean_bt, cfg)

    discovery_pairs = aggregate_pairs(
        clean_bt, clean_calls, clean_sms, 0, cfg
    )

    evaluation_pairs = aggregate_pairs(
        clean_bt, clean_calls, clean_sms, 1, cfg
    )

    # Build pair_population from ANY cleaned discovery-period pair interaction,
    # including weak Bluetooth and missed calls. Exclude sentinel IDs and duplicates.
    pair_tables = []

    for events in [clean_bt, clean_calls, clean_sms]:
        discovery_events = events.loc[events["period"].eq(0)]

        unordered = _unordered_pairs(discovery_events)

        pair_tables.append(unordered[PAIR])

    pair_population = (
        pd.concat(pair_tables, ignore_index=True)
        .drop_duplicates(PAIR)
        .sort_values(PAIR)
        .reset_index(drop=True)
    )


    return ProcessedData(
      discovery_pairs=discovery_pairs,
      evaluation_pairs=evaluation_pairs,
      coverage=coverage,
      pair_population=pair_population,
    )
