# Group 42 — build the analysis yourselves

**Question:** Can students' repeated encounters, calls, and text messages reveal groups that continue interacting in later weeks?

This is now the **learning repo**. The finished implementation, original tests, raw data, generated report, results, and original checklist were preserved in [../data_mining_complete](../data_mining_complete). The analysis functions here deliberately raise `NotImplementedError` until your group implements them. No old results are left here to confuse with your own work.

## Divide the work

| Suggested owner (swap freely) | Main file | Receives | Produces |
|---|---|---|---|
| Elias | [processing.py](src/cns_groups/processing.py) | Raw Bluetooth/call/SMS CSVs | Discovery/evaluation pair tables, coverage, fixed pair population |
| Hugo | [rules.py](src/cns_groups/rules.py) | Processing's four tables | Frequent itemsets and association rules with later scores |
| Viktor | [clustering.py](src/cns_groups/clustering.py) | The same four tables | Student memberships and later group evaluation |
| All three | [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) | Both branches' results | Explanation, evidence, figures, conclusions |

Clustering/evaluation is the larger work area; plan a shared review of its evaluation calculations. The owner suggestions are only a starting point.

Read [HANDOFFS.md](HANDOFFS.md) together before splitting up. It defines the shared inputs, outputs, and first milestones. Each work file contains function signatures and numbered TODOs explaining what to implement and how to check it. Association rules and clustering are independent branches after processing; you do not need to finish Apriori before starting clustering.

## What is already provided

- `config.toml` and `config.py`: settings, loading, and validation.
- `contracts.py`: named table containers, shared column names, basic structural checks, CSV saving/loading.
- `pipeline.py`: CLI that connects your stages and exports their returned tables.
- `scripts/download_data.py`: verified source downloads. Raw data is already present on this machine.
- `tests/test_scaffold.py`: checks for the provided handoff infrastructure.
- `tests/test_exercises.py`: small examples to check your implementations as you build them.

Everything inside the three analysis work files is yours to implement. Import any needed libraries and add helper functions as you go. The supplied CLI does not do the scientific work for you or generate a finished report automatically.

## Start working

From this folder, use the existing environment on this machine:

```sh
source .venv/bin/activate
python -m cns_groups.pipeline --help
python -m pytest -q
```

For another group member's fresh checkout:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e '.[test]'
python scripts/download_data.py
```

The downloader uses [Copenhagen Networks Study, version 1](https://doi.org/10.6084/m9.figshare.7267433.v1). The [dataset paper](https://doi.org/10.1038/s41597-019-0325-x) explains the observation records. If this Mac's Python cannot find CA certificates, `SSL_CERT_FILE=/etc/ssl/cert.pem python scripts/download_data.py` uses its system certificate bundle; do not disable HTTPS verification.

Run your stages when you have implemented them:

```sh
python -m cns_groups.pipeline --stage processing --output results/run_01
python -m cns_groups.pipeline --stage rules --output results/run_01
python -m cns_groups.pipeline --stage clustering --output results/run_01
```

Or run all three with `--stage all`. Unimplemented stages exit with an explicit learning-task message and do not create fake results. A successful rule/clustering stage may be rerun against the same processing tables. Use a NEW output directory when changing processing or configuration so downstream results cannot silently refer to stale inputs. CLI paths are relative to your working directory.

The exercise tests **skip while their functions raise `NotImplementedError`**. A skipped test means unfinished work, not a correct implementation. After you replace a stub, its assertions run normally. These are starter checks, not complete proof: add cases as you discover failure modes. The completed reference's original 18-test suite is preserved separately.

## How to use support

Start with a tiny example, write down the expected result, implement one function, and run its test. You can ask: “Explain this TODO,” “Give us a hint,” or “Review our implementation without replacing it.” Use “Coach me” when you want one step at a time.

Try your own implementation before opening the corresponding file in the completed copy. The completed code is a reference, not the only valid solution. Its saved results are a sanity check under the same assumptions; matching every cluster ID is not necessary.

The preserved reference still has methodological limitations and partly completed checklist items; “complete” means the working implementation from this session, not a guarantee of a finished course submission. Track your own work in [PROJECT_CHECKLIST.md](PROJECT_CHECKLIST.md).

Data and results are ignored by Git. Teammates must download the data or explicitly share one processing run's four CSVs together with its `config.json`. Commit source and agreed interfaces through your normal group workflow; no commit or push was made during this scaffold setup.
