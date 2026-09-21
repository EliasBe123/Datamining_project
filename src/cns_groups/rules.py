"""WORK AREA 2 — association rules. Suggested owner: Hugo.

INPUT: ProcessedData from processing.py, or its four exported CSVs via the CLI.
OUTPUT: RuleResults(itemsets, rules) -> results/<run>/rules/ -> shared report.
This branch and clustering are independent; rules are NOT clustering input.

You can start now with tiny hand-written pair tables while processing is built.
Use mlxtend's Apriori; the assignment is representation, interpretation, and
evaluation, unless your course explicitly requires implementing Apriori itself.
"""
import pandas as pd

from .config import Config
from .contracts import ProcessedData, RuleResults

ITEMS = ["REPEATED_PROXIMITY", "MANY_PROXIMITY_BINS", "SMS_CONTACT", "CALL_CONTACT"]


def transactions(pairs: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """TODO 1: return Boolean columns ITEMS, preserving input row order/index.

    Use proximity_days >= recurrence_days; proximity_bins >= many_proximity_bins;
    sms_count > 0; completed_calls > 0. Do not include IDs as numerical features.
    One row is one student PAIR, not one encounter or student.

    Example counts days=4, bins=18, SMS=5, calls=0 -> True, True, True, False.
    This function assumes pairs have already been aligned to the fixed population.
    """
    raise NotImplementedError("Rules task 1: transactions")


def score_rule(items: pd.DataFrame, antecedent: set[str], consequent: set[str]) -> dict:
    """TODO 2: compute n_pairs, antecedent_count, consequent_count, support_count,
    support, confidence, and lift. Return those names as dictionary keys.

    A multi-item side is satisfied only when ALL its items are present.
    Use NaN when confidence/lift has an undefined denominator; do not turn it into 0.
    Work through the small example in tests/test_exercises.py before using real data.
    Explain each denominator: which population does the number describe?
    """
    raise NotImplementedError("Rules task 2: score_rule")


def run(data: ProcessedData, cfg: Config) -> RuleResults:
    """TODO 3: prepare transactions, mine in discovery, score frozen rules later.

    - Left-join BOTH period tables onto data.pair_population; fill absent counts
      with zero. Keep empty baskets and exactly the same pair order/population.
    - Call transactions for each period. Mine discovery itemsets with Apriori.
    - Convert cfg.min_rule_count to a support fraction; use max_itemset_size.
    - Generate rules meeting min_confidence and lift > min_lift.
    - Use score_rule for each selected rule in discovery, evaluation, and a
      separately labelled evaluation_covered subset (both members later eligible).
    - Export columns from contracts.RULE_COLUMNS; use ' & ' to join item names.
      itemsets uses columns items (joined names), support, support_count.
    - Return empty tables WITH headers if no itemsets/rules qualify.

    Do not mine later rules and replace the discovery rules with more successful ones.
    Do not claim causality or automatically treat very high lift as strong evidence.
    For the report, inspect overlapping Bluetooth items and channel correlations
    using discovery data; identify rules largely explained by item construction.
    """
    raise NotImplementedError("Rules task 3: run")
