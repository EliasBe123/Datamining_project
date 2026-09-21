"""Shared handoff formats and CSV plumbing. Provided infrastructure, not an assignment.

Agree as a team before changing a column name here. See HANDOFFS.md for meanings.
The dataclasses are simply named containers for pandas tables.
"""
from dataclasses import dataclass, fields
from pathlib import Path

import pandas as pd

PAIR_COLUMNS = ["user_a", "user_b"]
FEATURE_COLUMNS = ["proximity_bins", "proximity_days", "sms_count", "sms_days",
                   "completed_calls", "call_days", "call_attempts"]
COVERAGE_COLUMNS = ["user", "discovery_bins", "evaluation_bins", "discovery_coverage",
                    "discovery_eligible", "evaluation_coverage", "evaluation_eligible"]
METRICS = ["n_pairs", "antecedent_count", "consequent_count", "support_count", "support", "confidence", "lift"]
RULE_COLUMNS = ["antecedent", "consequent"] + [f"{period}_{metric}" for period in
                ("discovery", "evaluation", "evaluation_covered") for metric in METRICS]
MEMBERSHIP_COLUMNS = ["variant", "user", "cluster", "cluster_size", "kind"]
GROUP_COLUMNS = ["variant", "cluster", "original_members", "evaluated_members", "excluded_members",
                 "possible_pairs", "evaluated_pairs", "excluded_pairs", "later_recurring_pairs",
                 "initial_recurring_pairs", "retained_pairs", "later_internal_connectivity",
                 "connection_retention", "later_communication", "null_mean", "null_low", "null_high",
                 "permutation_p"]


@dataclass
class ProcessedData:
    discovery_pairs: pd.DataFrame
    evaluation_pairs: pd.DataFrame
    coverage: pd.DataFrame
    pair_population: pd.DataFrame


@dataclass
class RuleResults:
    itemsets: pd.DataFrame
    rules: pd.DataFrame


@dataclass
class ClusteringResults:
    memberships: pd.DataFrame
    group_evaluation: pd.DataFrame


SCHEMAS = {
    ProcessedData: {"discovery_pairs": PAIR_COLUMNS + FEATURE_COLUMNS,
                    "evaluation_pairs": PAIR_COLUMNS + FEATURE_COLUMNS,
                    "coverage": COVERAGE_COLUMNS, "pair_population": PAIR_COLUMNS},
    RuleResults: {"itemsets": ["items", "support", "support_count"], "rules": RULE_COLUMNS},
    ClusteringResults: {"memberships": MEMBERSHIP_COLUMNS, "group_evaluation": GROUP_COLUMNS},
}


def validate_tables(bundle):
    """Check structural handoffs. Students still need to verify the scientific calculations."""
    for name, expected in SCHEMAS[type(bundle)].items():
        table = getattr(bundle, name)
        if not isinstance(table, pd.DataFrame):
            raise ValueError(f"{name} must be a pandas DataFrame")
        missing = set(expected) - set(table.columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")
    if isinstance(bundle, ProcessedData):
        for name in ("discovery_pairs", "evaluation_pairs", "pair_population"):
            table = getattr(bundle, name)
            if table[PAIR_COLUMNS].isna().any().any() or table.duplicated(PAIR_COLUMNS).any():
                raise ValueError(f"{name} must have one non-null row per unordered pair")
            if not (table.user_a.ge(0) & table.user_a.lt(table.user_b)).all():
                raise ValueError(f"{name} requires 0 <= user_a < user_b")
        for name in ("discovery_pairs", "evaluation_pairs"):
            values = getattr(bundle, name)[FEATURE_COLUMNS]
            if values.isna().any().any() or not ((values >= 0) & (values % 1 == 0)).all().all():
                raise ValueError(f"{name} features must be nonnegative integer counts")
        coverage = bundle.coverage
        if coverage.user.isna().any() or coverage.user.duplicated().any():
            raise ValueError("coverage requires one row per student")
        for period in ("discovery", "evaluation"):
            if not coverage[f"{period}_coverage"].between(0, 1).all():
                raise ValueError("Coverage must be in [0, 1]")
            if not pd.api.types.is_bool_dtype(coverage[f"{period}_eligible"]):
                raise ValueError("Eligibility columns must be Boolean")


def save_tables(bundle, directory: Path):
    validate_tables(bundle)
    directory.mkdir(parents=True, exist_ok=True)
    for field in fields(bundle):
        getattr(bundle, field.name).to_csv(directory / f"{field.name}.csv", index=False)


def load_processed(directory: Path):
    tables = {}
    for field in fields(ProcessedData):
        path = directory / f"{field.name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. Finish and run the processing stage first.")
        tables[field.name] = pd.read_csv(path)
    # Parse explicitly: astype(bool) on the string 'False' would incorrectly yield True.
    for period in ("discovery", "evaluation"):
        col = f"{period}_eligible"
        values = tables["coverage"][col]
        if not pd.api.types.is_bool_dtype(values):
            converted = values.map({"True": True, "False": False})
            if converted.isna().any():
                raise ValueError(f"Invalid Boolean values in {col}")
            tables["coverage"][col] = converted.astype(bool)
    result = ProcessedData(**tables)
    validate_tables(result)
    return result
