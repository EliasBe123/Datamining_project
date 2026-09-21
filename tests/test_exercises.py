"""Starter checks for your work. Skipped means NOT YET IMPLEMENTED, not passed.

Add more tests as you implement. These examples intentionally use tiny inputs
so you can calculate expected results without consulting the completed code.
"""
import numpy as np
import pandas as pd
import pytest

from cns_groups import clustering, processing, rules
from cns_groups.config import Config
from cns_groups.contracts import FEATURE_COLUMNS, PAIR_COLUMNS, ProcessedData


def exercise(function, *args):
    try:
        return function(*args)
    except NotImplementedError as error:
        pytest.skip(f"Unfinished student exercise: {error}")


def pair_table(rows):
    table = pd.DataFrame(rows)
    for column in FEATURE_COLUMNS:
        if column not in table:
            table[column] = 0
    return table.fillna(0).astype(int)


def test_processing_period_boundary():
    cfg = Config()
    raw = pd.DataFrame([[cfg.period_seconds - 1, 0, 1, -70],
                        [cfg.period_seconds, 0, 1, -70]],
                       columns=["# timestamp", "user_a", "user_b", "rssi"])
    actual = exercise(processing.clean_records, raw, "bt", cfg)
    assert actual.period.tolist() == [0, 1]


def test_processing_sentinel_is_observation_not_student():
    bt = pd.DataFrame([[0, 0, -1, 0, 0, 0, 0]],
                      columns=["timestamp", "user_a", "user_b", "rssi", "bin", "day", "period"])
    actual = exercise(processing.observation_coverage, bt, Config()).set_index("user")
    assert list(actual.index) == [0]
    assert actual.loc[0, "discovery_bins"] == 1
    assert actual.loc[0, "evaluation_bins"] == 0


def test_processing_reciprocal_scans_count_once():
    bt = pd.DataFrame([[0, 0, 1, -85, 0, 0, 0], [0, 1, 0, -70, 0, 0, 0],
                       [300, 0, 1, -70, 1, 0, 0]],
                      columns=["timestamp", "user_a", "user_b", "rssi", "bin", "day", "period"])
    calls = pd.DataFrame(columns=["timestamp", "user_a", "user_b", "duration", "bin", "day", "period"])
    sms = pd.DataFrame(columns=["timestamp", "user_a", "user_b", "bin", "day", "period"])
    actual = exercise(processing.aggregate_pairs, bt, calls, sms, 0, Config())
    assert len(actual) == 1
    assert actual.iloc[0].proximity_bins == 2
    assert actual.iloc[0].proximity_days == 1


def test_rules_long_encounter_is_not_repeated_days():
    pairs = pair_table([dict(user_a=0, user_b=1, proximity_days=1, proximity_bins=40)])
    actual = exercise(rules.transactions, pairs, Config())
    assert actual.iloc[0].MANY_PROXIMITY_BINS
    assert not actual.iloc[0].REPEATED_PROXIMITY


def test_rule_metrics_by_hand():
    # Of four pairs, two have A, three have B, and two have both.
    items = pd.DataFrame({"A": [True, True, False, False], "B": [True, True, True, False]})
    actual = exercise(rules.score_rule, items, {"A"}, {"B"})
    assert actual["support_count"] == 2
    assert actual["support"] == 0.5
    assert actual["confidence"] == 1
    assert actual["lift"] == pytest.approx(4 / 3)


def test_similarity_uses_relationships_not_id_differences():
    pairs = pair_table([dict(user_a=10, user_b=99, proximity_days=7)])
    actual = exercise(clustering.similarity_matrix, pairs, [99, 10, 42], "bluetooth", Config())
    np.testing.assert_allclose(actual, [[1, 0.5, 0], [0.5, 1, 0], [0, 0, 1]])


def test_clustering_keeps_an_isolated_student_separate():
    pairs = pair_table([dict(user_a=a, user_b=b, proximity_days=14) for a, b in [(0, 1), (0, 2), (1, 2)]])
    actual = exercise(clustering.cluster_students, pairs, [0, 1, 2, 3], "bluetooth", Config())
    assert actual.loc[actual.user.isin([0, 1, 2]), "cluster"].nunique() == 1
    assert actual.loc[actual.user.eq(3), "kind"].iloc[0] == "singleton"


def test_persistence_and_retention_are_different():
    early = pair_table([dict(user_a=0, user_b=1, proximity_days=3),
                        dict(user_a=0, user_b=2, proximity_days=3)])
    later = pair_table([dict(user_a=0, user_b=1, proximity_days=3),
                        dict(user_a=1, user_b=2, proximity_days=3)])
    coverage = pd.DataFrame({"user": [0, 1, 2], "discovery_bins": [4032]*3, "evaluation_bins": [4032]*3,
                             "discovery_coverage": [1.0]*3, "evaluation_coverage": [1.0]*3,
                             "discovery_eligible": [True]*3, "evaluation_eligible": [True]*3})
    data = ProcessedData(early, later, coverage, early[PAIR_COLUMNS])
    members = pd.DataFrame({"variant": ["bluetooth"]*3, "user": [0, 1, 2], "cluster": [0]*3,
                            "cluster_size": [3]*3, "kind": ["group"]*3})
    actual = exercise(clustering.evaluate_groups, members, data, Config(permutations=5))
    assert actual.iloc[0].later_internal_connectivity == pytest.approx(2 / 3)
    assert actual.iloc[0].connection_retention == 0.5
