"""WORK AREA 2 — association rules. Suggested owner: Hugo.

INPUT: ProcessedData from processing.py, or its four exported CSVs via the CLI.
OUTPUT: RuleResults(itemsets, rules) -> results/<run>/rules/ -> shared report.
This branch and clustering are independent; rules are NOT clustering input.

You can start now with tiny hand-written pair tables while processing is built.
Use mlxtend's Apriori; the assignment is representation, interpretation, and
evaluation, unless your course explicitly requires implementing Apriori itself.
"""
import pandas as pd
import numpy as np

from .config import Config
from .contracts import ProcessedData, RuleResults, PAIR_COLUMNS, FEATURE_COLUMNS, RULE_COLUMNS
from mlxtend.frequent_patterns import apriori, association_rules  

ITEMS = ["REPEATED_PROXIMITY", "MANY_PROXIMITY_BINS", "SMS_CONTACT", "CALL_CONTACT"]


def transactions(pairs: pd.DataFrame, cfg: Config) -> pd.DataFrame:
  
    items = pd.DataFrame(index=pairs.index)
    
    items["REPEATED_PROXIMITY"] = pairs["proximity_days"] >= cfg.recurrence_days
    items["MANY_PROXIMITY_BINS"] = pairs["proximity_bins"] >= cfg.many_proximity_bins
    items["SMS_CONTACT"] = pairs["sms_count"] > 0
    items["CALL_CONTACT"] = pairs["completed_calls"] > 0
    
    return items[ITEMS]
  
  
  


def score_rule(items: pd.DataFrame, antecedent: set[str], consequent: set[str]) -> dict:
    """TODO 2: compute n_pairs, antecedent_count, consequent_count, support_count,
    support, confidence, and lift. Return those names as dictionary keys.

    A multi-item side is satisfied only when ALL its items are present.
    Use NaN when confidence/lift has an undefined denominator; do not turn it into 0.
    Work through the small example in tests/test_exercises.py before using real data.
    Explain each denominator: which population does the number describe?
    """
    
    has_antecedent = items[list(antecedent)].all(axis=1)
    has_consequent = items[list(consequent)].all(axis=1)
    has_both = has_antecedent & has_consequent
    n_pairs = len(items)
    antecedent_count = int(has_antecedent.sum())
    consequent_count = int(has_consequent.sum())
    support_count = int(has_both.sum())
    support = support_count/ n_pairs if n_pairs else np.nan
    confidence = support_count / antecedent_count if antecedent_count else np.nan
    lift = confidence / (consequent_count / n_pairs) if n_pairs and consequent_count else np.nan

    return {"n_pairs": n_pairs, "antecedent_count": antecedent_count, "consequent_count": consequent_count, 
            "support_count": support_count, "support": support, "confidence": confidence, "lift": lift}
            
    
def _aligned(population: pd.DataFrame, period_pairs: pd.DataFrame) -> pd.DataFrame:
      """Left-join one period's counts onto the fixed pair population."""
      merged = population.merge(period_pairs, on=PAIR_COLUMNS, how="left")
      merged[FEATURE_COLUMNS] = merged[FEATURE_COLUMNS].fillna(0).astype(int)
      return merged

def _name(item_set) -> str:
    """frozenset -> 'A & B', in the fixed ITEMS order."""
    return " & ".join(sorted(item_set, key=ITEMS.index))


def _empty_results() -> RuleResults:
    """Both tables with their headers but no rows: nothing qualified."""
    return RuleResults(
        itemsets=pd.DataFrame(columns=["items", "support", "support_count"]),
        rules=pd.DataFrame(columns=RULE_COLUMNS),
    )


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
    
    
    discovery_items = transactions(_aligned(data.pair_population, data.discovery_pairs), cfg)
    evaluation_items = transactions(_aligned(data.pair_population, data.evaluation_pairs), cfg)
  
    eligible = set(data.coverage.loc[data.coverage.evaluation_eligible, "user"])
    both_covered = data.pair_population.user_a.isin(eligible) & data.pair_population.user_b.isin(eligible)
    covered_items = evaluation_items[both_covered]
    
    n_pairs = len(discovery_items)
    if n_pairs == 0:
        return _empty_results()

    min_support = cfg.min_rule_count / n_pairs
    frequent = apriori(discovery_items, min_support=min_support,
                       use_colnames=True, max_len=cfg.max_itemset_size)

    if frequent.empty:
        return _empty_results()
    
    itemsets_table = pd.DataFrame({
      "items": frequent.itemsets.apply(_name),
      "support": frequent.support,
      "support_count": (frequent.support * n_pairs).round().astype(int),
    })
    
    rules = association_rules(frequent, metric="confidence", min_threshold=cfg.min_confidence)
    rules = rules[rules.lift > cfg.min_lift]

    populations = [("discovery", discovery_items),
                   ("evaluation", evaluation_items),
                   ("evaluation_covered", covered_items)]

    rows = []
    for rule in rules.itertuples():
        row = {"antecedent": _name(rule.antecedents), "consequent": _name(rule.consequents)}
        for prefix, table in populations:
            for key, value in score_rule(table, set(rule.antecedents), set(rule.consequents)).items():
                row[f"{prefix}_{key}"] = value
        rows.append(row)

    rules_table = pd.DataFrame(rows, columns=RULE_COLUMNS)
    return RuleResults(itemsets=itemsets_table, rules=rules_table)



