# Work areas and data handoffs

This document is the agreement between your three work areas. Change it together if you change a field, definition, or return type.

```text
data/raw/*.csv
       |
       v
processing.run(raw_directory, cfg) -> ProcessedData
       |
       +----> rules.run(data, cfg) -> RuleResults --------+
       |                                               |
       +----> clustering.run(data, cfg)                  v
                 -> ClusteringResults -----------> report/figures
```

The pipeline supplies `cfg` and saves returned tables. Each function returns data; it should not silently read a different period or substitute finished reference results.

## 1. Processing handoff

Input files: `bt_symmetric.csv`, `calls.csv`, and `sms.csv`. The three files have different headers; inspect them before coding. Timestamps are relative seconds. IDs are nominal labels even when stored as integers. Bluetooth negative identifiers are observation markers, not students.

`processing.run()` returns `ProcessedData` with four pandas DataFrames:

| Table / exported CSV | Columns | Row meaning |
|---|---|---|
| `discovery_pairs` | `user_a`, `user_b`, `proximity_bins`, `proximity_days`, `sms_count`, `sms_days`, `completed_calls`, `call_days`, `call_attempts` | One unordered interacting pair in discovery |
| `evaluation_pairs` | Same columns | One unordered interacting pair in evaluation |
| `coverage` | `user`, `discovery_bins`, `evaluation_bins`, `discovery_coverage`, `discovery_eligible`, `evaluation_coverage`, `evaluation_eligible` | One student with observation evidence in either period |
| `pair_population` | `user_a`, `user_b` | One pair with any valid recorded discovery interaction, including weak Bluetooth or missed calls |

Rules for these tables:

- Unique unordered pair keys: `0 <= user_a < user_b`. No sentinel IDs or self-pairs.
- Pair features are nonnegative integer counts. If one channel is absent, its recorded count is zero. Zero does not establish that no real-world interaction happened.
- Distinct-day counts and bin/event counts are different measures. Calls with duration > 0 count as completed; all calls contribute to attempts.
- An absent pair does not need an explicit all-zero row in each feature table. The rule branch left-joins these tables onto the fixed `pair_population`.
- Coverage fractions are in [0, 1], and eligibility flags are Boolean. Count a student/bin at most once. Keep both periods' coverage, including zero for a missing period.
- With the default configuration, discovery is `[0, 14 days)` and evaluation `[14, 28 days)`. Exactly day 14 goes into evaluation.
- Coverage uses valid observation evidence before RSSI filtering; sentinel rows can demonstrate coverage without contact.

The CLI writes these to `results/<run>/processed/*.csv`, with settings in `results/<run>/config.json`. Share all five files if teammates exchange a processing run manually.

**First milestone:** load and inspect 20 rows from each file. Then clean a tiny synthetic example, check time boundaries and reciprocal scans, and only afterwards process the full dataset. Record exclusion counts and their reasons for the report.

## 2. Association-rule handoff

Input: the four processing tables. No cluster memberships are needed.

Construct one transaction per `pair_population` row, separately for each period. Preserve the population and pair order; keep empty baskets. Items:

| Item | Default condition |
|---|---|
| `REPEATED_PROXIMITY` | `proximity_days >= 3` |
| `MANY_PROXIMITY_BINS` | `proximity_bins >= 12` |
| `SMS_CONTACT` | `sms_count > 0` |
| `CALL_CONTACT` | `completed_calls > 0` |

`rules.run()` returns `RuleResults`:

- `itemsets`: `items`, `support`, `support_count`.
- `rules`: `antecedent`, `consequent`, then `n_pairs`, `antecedent_count`, `consequent_count`, `support_count`, `support`, `confidence`, and `lift`, each prefixed with `discovery_`, `evaluation_`, or `evaluation_covered_`.

Example column names: `discovery_confidence`, `evaluation_support_count`, `evaluation_covered_lift`. The complete list is `contracts.RULE_COLUMNS`. Export item names in a stable order joined by ` & `, not Python set strings. Undefined metrics remain NaN; empty results still have column headers.

Mine only discovery itemsets and rules. Evaluate the same selected rules on the later population, plus a separately labelled subset where BOTH participants have later coverage. Calls/SMS absent from the logs are not proof of no communication through other channels.

The CLI writes `results/<run>/rules/itemsets.csv` and `rules.csv`.

**First milestone:** implement `transactions()` and manually calculate a rule's support/confidence/lift on four rows. Then use Apriori and compare its discovery metrics with your calculations. Assess correlated/overlapping items before interpreting high lift as a new insight.

## 3. Clustering and evaluation handoff

Input: the same four processing tables; clustering primarily uses the two feature tables and coverage.

Select users using discovery coverage only. Build similarity matrices in an explicit user order. Run average-linkage clustering on `1 - similarity`. Keep both `bluetooth` and `combined` variants separate.

`clustering.run()` returns `ClusteringResults`:

- `memberships`: `variant`, `user`, `cluster`, `cluster_size`, `kind`. One row per discovery-eligible student per variant, including small clusters. Cluster IDs have meaning only within their variant/run.
- `group_evaluation`: the columns in `contracts.GROUP_COLUMNS`. One row per originally qualifying group per variant. Include original/evaluated/excluded members and pair counts, later recurring pairs, initially recurring pairs, retained pairs, connectivity, retention, communication, and the shuffled reference metrics.

Metric definitions:

- Later connectivity = later recurring member pairs / evaluated possible member pairs.
- Retention = member pairs recurring in both periods / initially recurring evaluated member pairs.
- Later communication = evaluated pairs with later SMS or completed calls / evaluated possible member pairs.
- A recurring pair meets on at least `recurrence_days` distinct days in the relevant period.
- Denominator zero means undefined, not zero persistence.

Keep original memberships even when a member disappears or a newcomer arrives. Exclude poorly observed members from evaluation without relabelling the original groups, and report the resulting exclusions.

The shuffled comparison randomly reassigns labels within discovery-activity bands while preserving group sizes in the evaluated cohort. Use every later-covered discovery student as the shuffle pool, including original pairs/singletons. Record seed and permutation count. Explain what this comparison controls for and what it cannot establish.

The CLI writes `results/<run>/clustering/memberships.csv` and `group_evaluation.csv`.

**First milestone:** build a three-person matrix and check symmetry/diagonal. Then check a simple clustering result, calculate one group's later metrics by hand, and implement shuffled comparisons last.

## 4. Shared integration and report

Once the primary pipeline works:

1. Add diagnostics and figures: coverage, daily activity, group sizes, matrix heatmap, dendrogram, and observed versus shuffled persistence. Save underlying numerical tables too.
2. Run predefined sensitivity scenarios: RSSI −75/−85 at cutoff 0.8 and cutoffs 0.7/0.9 at RSSI −80. Keep both channel variants in each scenario. These are separate runs, not automatic scaffold features.
3. For each scenario, use a copied TOML configuration and a NEW `--output` directory. The CLI intentionally rejects mixing configurations within one run. Rebuild processing when RSSI changes; for simplicity the scaffold requires a matching processing run even if only a clustering setting changes.
4. Keep evaluation outcomes out of parameter selection. Sensitivity analysis is not tuning, and the reference's later outcomes have already been inspected; disclose any new adaptations as exploratory.
5. Complete `REPORT_TEMPLATE.md` with your own results and update `PROJECT_CHECKLIST.md` with evidence. Do not copy the reference's numerical conclusions without reproducing and understanding them.

## Getting unstuck

Bring one function, a tiny input, your expected output, and the actual output when asking for help. First request a hint or review; consult the preserved implementation if needed.

Reference mapping: your processing/rules files correspond to the same filenames in `../data_mining_complete/src/cns_groups`. Your clustering file combines ideas from the reference's `clustering.py` and `evaluation.py`. Plotting examples are in its `plots.py`. Its `tests/test_analysis.py` contains additional finished examples. The reference has more modules; do not assume its old functions have the same signatures as this scaffold.
