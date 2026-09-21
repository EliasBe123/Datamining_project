"""WORK AREA 3 — clustering and persistence. Suggested owner: Viktor.

INPUT: ProcessedData, independently of the association-rule branch.
OUTPUT: ClusteringResults -> results/<run>/clustering/ -> shared report.
This area is larger; ask another member to review evaluation once their stage works.
Start with three students and a hand-calculated matrix, not the entire dataset.
"""
import numpy as np
import pandas as pd

from .config import Config
from .contracts import ClusteringResults, ProcessedData


def similarity_matrix(pairs: pd.DataFrame, users: list[int], variant: str,
                      cfg: Config) -> np.ndarray:
    """TODO 1: produce a symmetric N x N matrix in the EXACT order of users.

    pairs must contain discovery features only. variant is 'bluetooth' or 'combined'.
    Bluetooth similarity: proximity_days / period_days.
    Combined: weighted Bluetooth/call/SMS day fractions, using combined_weights.
    Ignore pairs outside users. Absent recorded edges have similarity 0.
    Set the diagonal to 1; check finite values within [0, 1].

    Important: IDs are labels; do not compute numerical differences between IDs.
    Use day counts consistently so raw SMS volume cannot dominate the other channels.
    """
    raise NotImplementedError("Clustering task 1: similarity_matrix")


def cluster_students(pairs: pd.DataFrame, users: list[int], variant: str,
                     cfg: Config) -> pd.DataFrame:
    """TODO 2: return MEMBERSHIP_COLUMNS, one row per supplied discovery student.

    Use scikit-learn AgglomerativeClustering with average linkage, precomputed
    distance = 1 - similarity, no fixed cluster count, and cfg.distance_cutoff.
    Keep the user-to-matrix-row mapping consistent. Handle zero/one student.
    Include variant, cluster label, size, and kind ('group', 'pair', 'singleton')
    under the default min_group_size=3. Keep small clusters visible in exports.
    Later observations MUST NOT affect these memberships.

    Explain average linkage on a three-student example and why Ward is unsuitable
    for this chosen dissimilarity. The cutoff is not a requirement on every edge.
    """
    raise NotImplementedError("Clustering task 2: cluster_students")


def evaluate_groups(members: pd.DataFrame, data: ProcessedData, cfg: Config) -> pd.DataFrame:
    """TODO 3: evaluate ONE variant's frozen memberships; return GROUP_COLUMNS.

    - Evaluate groups originally having at least min_group_size members.
    - Keep original membership; assess only pairs whose members have sufficient
      later Bluetooth coverage. Report excluded members/pairs, not fake failures.
    - Count each unordered pair once. A recurring tie has >= recurrence_days.
    - Later connectivity: later recurring pairs / evaluated possible pairs.
    - Retention: pairs recurring in BOTH periods / initially recurring evaluated pairs.
    - Later communication: pairs with later SMS OR completed calls / evaluated pairs.
    - Undefined denominator -> NaN. Count original possible pairs before exclusions.

    Then add the shuffled reference (write your own helper functions here):
    - Calculate each evaluated student's discovery proximity-bin activity over ALL
      partners. Divide into quartile strata, keeping equal activity values together.
    - Shuffle labels within strata among ALL later-covered discovery students,
      including students originally in pairs/singletons. Preserve label counts.
    - Recalculate group connectivity cfg.permutations times, with cfg.seed.
    - Export null_mean, 2.5/97.5 percentiles (null_low/high), and permutation_p.
      Use (1 + shuffled scores >= observed) / (1 + permutations) for the latter.
    These ranges are shuffled reference ranges, not confidence intervals for truth.

    Alice/Bob/Charlie remain the original group even if David later joins Alice.
    Work out connectivity vs retention on paper before implementing this function.
    """
    raise NotImplementedError("Clustering task 3: evaluate_groups")


def run(data: ProcessedData, cfg: Config) -> ClusteringResults:
    """TODO 4: select students using discovery coverage, then run BOTH variants.

    Use cluster_students followed by evaluate_groups for each variant.
    Concatenate their results, retaining the variant column to separate labels.
    Return ClusteringResults(memberships=..., group_evaluation=...).

    Next milestones AFTER primary results work:
    - Add group-size, similarity, dendrogram, and persistence figures.
    - Repeat the predefined RSSI/cutoff scenarios (see HANDOFFS.md), changing one
      setting at a time. An RSSI change requires rebuilding processing outputs.
    - Pool pair counts when reporting aggregate connectivity; do not accidentally
      replace that with an unweighted mean of group percentages.
    - Compare group sizes and exclusions before claiming combined channels help.
    """
    raise NotImplementedError("Clustering task 4: run")
