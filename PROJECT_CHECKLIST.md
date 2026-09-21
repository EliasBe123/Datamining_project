# Learning-repo project checklist

This checklist belongs to YOUR implementation. The earlier implementation's evidence-based assessment is preserved in [the completed reference](../data_mining_complete/PROJECT_CHECKLIST.md). Its checkmarks do not transfer to these unfinished exercises.

Keep a link to your code, table, test, or report paragraph beside each item when checking it off. Suggested methods and settings are already provided; you still need to implement, verify, and motivate them yourselves.

- [x] The problem is clearly stated at the beginning, in non-technical terms. See [README.md](README.md) and [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md).
- [ ] The problem requires a Data Mining approach. Explain why encounter totals are insufficient.
- [ ] The chosen Data Mining approach is appropriate. Explain the roles of rules, clustering, and later evaluation.
- [ ] The chosen data representation (table, set, graph, …) is appropriate. Explain your agreed handoffs.
- [ ] [For tabular data] Each attribute has been given the correct type (nominal, …). Document IDs, counts, time, RSSI, special codes, and Boolean items.
- [ ] The chosen algorithm is appropriate (motivate the choice w.r.t. the features of the data and problem at hand).
- [ ] The list of applied pre-processing operations has been motivated. Include exclusion counts.
- [ ] An appropriate proximity function (Jaccard, Manhattan, …) has been used, if required by the algorithm. Explain your direct-pair similarity and distance.
- [ ] If relevant, scaling/normalization issues have been addressed. Explain day fractions and channel weights.
- [ ] If relevant, correlation issues have been addressed. Inspect overlapping items and related channels.
- [ ] Dimensionality has been reduced, if necessary. Explain why further reduction is or is not needed.
- [ ] If relevant, appropriate train/test datasets have been generated. Verify chronological boundaries and frozen discovery outputs.
- [ ] If necessary, noise has been reduced. Test duplicate scans, invalid values, RSSI filtering, and coverage handling.
- [ ] If relevant, hyperparameters are tuned properly. Distinguish fixed settings/sensitivity from tuning; avoid selection on later results.
- [ ] The results are supported by sufficient evidence (large leaf sizes, high-support, …). Show actual counts, group sizes, later outcomes, and shuffled comparisons.
- [ ] The results have been interpreted and related to the original problem: was it solved, how can results be used, and what hypotheses remain?
