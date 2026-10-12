"""WORK AREA 3 — clustering and persistence."""

import numpy as np
import pandas as pd
import igraph as ig
import leidenalg as la
import matplotlib.pyplot as plt

from .config import Config
from .contracts import ClusteringResults, ProcessedData


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

MEMBERSHIP_COLUMNS = [
    "user_id",
    "variant",
    "cluster",
    "cluster_size",
    "kind",
]

GROUP_COLUMNS = [
    "variant",
    "cluster",
    "group_size",
    "possible_pairs",
    "evaluated_pairs",
    "excluded_pairs",
    "initially_recurring_pairs",
    "later_recurring_pairs",
    "retained_pairs",
    "later_communication_pairs",
    "connectivity",
    "retention",
    "later_communication_rate",
    "null_mean",
    "null_low",
    "null_high",
    "permutation_p",
]

EDGE_THRESHOLD = 0.20


# ---------------------------------------------------------------------
# Similarity matrix
# ---------------------------------------------------------------------

def similarity_matrix(
    pairs: pd.DataFrame,
    users: list,
    variant: str,
    cfg: Config,
) -> pd.DataFrame:
    """Construct a symmetric similarity matrix for the selected variant."""

    if variant not in {"bluetooth", "combined"}:
        raise ValueError("variant must be 'bluetooth' or 'combined'")

    if cfg.period_days <= 0:
        raise ValueError("period_days must be positive")

    users = list(users)

    if len(users) != len(set(users)):
        raise ValueError("Duplicate user IDs supplied")

    required = {"user_a", "user_b", "proximity_days"}
    missing = required - set(pairs.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if variant == "combined":
        missing = {"call_days", "sms_days"} - set(pairs.columns)

        if missing:
            raise ValueError(
                f"Missing combined columns: {sorted(missing)}"
            )

        weights = tuple(cfg.combined_weights)

        if (
            len(weights) != 3
            or any(w < 0 for w in weights)
            or not np.isclose(sum(weights), 1.0)
        ):
            raise ValueError(
                "combined_weights must contain three nonnegative "
                "weights summing to 1"
            )

    matrix = pd.DataFrame(
        0.0,
        index=pd.Index(users, name="user_id"),
        columns=pd.Index(users, name="user_id"),
    )

    user_set = set(users)

    relevant = pairs.loc[
        pairs["user_a"].isin(user_set)
        & pairs["user_b"].isin(user_set)
        & (pairs["user_a"] != pairs["user_b"])
    ].copy()

    if not relevant.empty:
        relevant["_low"] = relevant[
            ["user_a", "user_b"]
        ].min(axis=1)

        relevant["_high"] = relevant[
            ["user_a", "user_b"]
        ].max(axis=1)

        if relevant.duplicated(["_low", "_high"]).any():
            raise ValueError(
                "Duplicate unordered user pairs found. "
                "Aggregate the pairs before clustering."
            )

        bluetooth = (
            pd.to_numeric(
                relevant["proximity_days"], errors="raise"
            )
            .fillna(0)
            .clip(0, cfg.period_days)
            / cfg.period_days
        )

        if variant == "bluetooth":
            similarities = bluetooth
        else:
            calls = (
                pd.to_numeric(
                    relevant["call_days"], errors="raise"
                )
                .fillna(0)
                .clip(0, cfg.period_days)
                / cfg.period_days
            )

            sms = (
                pd.to_numeric(
                    relevant["sms_days"], errors="raise"
                )
                .fillna(0)
                .clip(0, cfg.period_days)
                / cfg.period_days
            )

            w_bluetooth, w_calls, w_sms = cfg.combined_weights

            similarities = (
                w_bluetooth * bluetooth
                + w_calls * calls
                + w_sms * sms
            )

        for a, b, value in zip(
            relevant["user_a"],
            relevant["user_b"],
            similarities,
        ):
            value = float(np.clip(value, 0, 1))
            matrix.loc[a, b] = value
            matrix.loc[b, a] = value

    np.fill_diagonal(matrix.values, 1.0)

    values = matrix.to_numpy()

    if not np.isfinite(values).all():
        raise ValueError("Similarity matrix contains invalid values")

    if not np.allclose(values, values.T):
        raise ValueError("Similarity matrix is not symmetric")

    return matrix


# ---------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------

def build_graph(
    matrix: pd.DataFrame,
    edge_threshold: float = EDGE_THRESHOLD,
) -> ig.Graph:
    """Build an undirected weighted graph, retaining isolated vertices."""

    if not 0 <= edge_threshold <= 1:
        raise ValueError("edge_threshold must be in [0, 1]")

    values = matrix.to_numpy(dtype=float)
    users = list(matrix.index)

    if values.shape != (len(users), len(users)):
        raise ValueError("Similarity matrix must be square")

    if not np.isfinite(values).all():
        raise ValueError("Similarity matrix contains non-finite values")

    if not np.allclose(values, values.T):
        raise ValueError("Similarity matrix must be symmetric")

    graph = ig.Graph(n=len(users), directed=False)

    graph.vs["name"] = [str(user) for user in users]
    graph.vs["user_id"] = users

    edges = []
    edge_weights = []

    for i in range(len(users)):
        for j in range(i + 1, len(users)):
            similarity = float(values[i, j])

            if similarity >= edge_threshold and similarity > 0:
                edges.append((i, j))
                edge_weights.append(similarity)

    graph.add_edges(edges)
    graph.es["weight"] = edge_weights

    return graph


# ---------------------------------------------------------------------
# Leiden community detection
# ---------------------------------------------------------------------

def calculate_modularity(
    matrix: pd.DataFrame,
    variant: str,
    cfg: Config,
) -> tuple[pd.DataFrame, float, ig.Graph]:
    """Run Leiden, remove singleton communities, and return the results."""

    graph = build_graph(matrix)

    if graph.vcount() == 0:
        return (
            pd.DataFrame(columns=MEMBERSHIP_COLUMNS),
            float("nan"),
            graph,
        )

    if graph.ecount() == 0:
        # With no edges, every vertex is a singleton.
        membership = list(range(graph.vcount()))
        modularity = float("nan")
    else:
        partition = la.find_partition(
            graph,
            la.ModularityVertexPartition,
            weights="weight",
            n_iterations=-1,
            seed=cfg.seed,
        )

        membership = list(partition.membership)

        modularity = graph.modularity(
            membership,
            weights="weight",
        )

    # Store the original Leiden memberships before filtering.
    graph.vs["cluster"] = membership

    members = pd.DataFrame({
        "user_id": graph.vs["user_id"],
        "variant": variant,
        "cluster": membership,
    })

    members["cluster_size"] = (
        members.groupby("cluster")["user_id"].transform("size")
    )

    members["kind"] = np.select(
        [
            members["cluster_size"] >= cfg.min_group_size,
            members["cluster_size"] == 2,
        ],
        ["group", "pair"],
        default="singleton",
    )

    # Remove singleton communities from both the output and displayed graph.
    community_sizes = pd.Series(membership).value_counts()

    keep_vertices = [
        i
        for i, cluster in enumerate(membership)
        if community_sizes[cluster] > 1
    ]

    graph = graph.induced_subgraph(keep_vertices)

    members = members.loc[members["cluster_size"] > 1].copy()

    # Recalculate sizes and kinds for the retained membership table.
    if not members.empty:
        members["cluster_size"] = (
            members.groupby("cluster")["user_id"].transform("size")
        )

        members["kind"] = np.where(
            members["cluster_size"] >= cfg.min_group_size,
            "group",
            "pair",
        )

    print(f"\n[{variant}]")
    print(f"Vertices after singleton removal: {graph.vcount()}")
    print(f"Edges: {graph.ecount()}")
    print(f"Edge threshold: {EDGE_THRESHOLD}")
    print(f"Communities retained: {members['cluster'].nunique()}")

    print(
        "Community sizes:",
        members["cluster"]
        .value_counts()
        .sort_values(ascending=False)
        .tolist(),
    )

    if np.isfinite(modularity):
        print(f"Modularity before singleton removal: {modularity:.4f}")
    else:
        print("Modularity undefined (no edges)")

    return members[MEMBERSHIP_COLUMNS], modularity, graph


# ---------------------------------------------------------------------
# Graph visualisation
# ---------------------------------------------------------------------

def show_igraph(
    graph: ig.Graph,
    variant: str,
    type: str,
) -> None:
    """Display the graph with consistent community colors using Matplotlib."""

    if graph.vcount() == 0:
        print(f"[{variant}] No non-singleton communities to display.")
        return

    if "cluster" not in graph.vs.attributes():
        raise ValueError("Graph is missing its 'cluster' vertex attribute")

    clusters = graph.vs["cluster"]

    # Map every distinct Leiden community ID to exactly one color.
    unique_clusters = sorted(set(clusters))
    number_of_clusters = len(unique_clusters)

    # tab20 is a qualitative palette designed for distinct categories.
    cmap = plt.get_cmap("tab20", max(number_of_clusters, 1))

    cluster_colors = {
        cluster: cmap(i)
        for i, cluster in enumerate(unique_clusters)
    }

    node_colors = [
        cluster_colors[cluster]
        for cluster in clusters
    ]

    positions = np.asarray(graph.layout("fr", weights="weight").coords)

    fig, ax = plt.subplots(figsize=(14, 10))

    # Draw edges first.
    for edge in graph.es:
        source, target = edge.tuple

        x1, y1 = positions[source]
        x2, y2 = positions[target]

        weight = edge["weight"]

        ax.plot(
            [x1, x2],
            [y1, y2],
            color="gray",
            linewidth=0.3 + 1.5 * weight,
            alpha=0.20 + 0.45 * weight,
            zorder=1,
        )

    # Every vertex in the same community receives the same color.
    ax.scatter(
        positions[:, 0],
        positions[:, 1],
        c=node_colors,
        s=35,
        edgecolors="black",
        linewidths=0.25,
        zorder=2,
    )

    # Label vertices with user IDs.
    for i, user in enumerate(graph.vs["name"]):
        ax.annotate(
            str(user),
            positions[i],
            xytext=(2, 3),
            textcoords="offset points",
            fontsize=5,
            zorder=3,
        )

    ax.set_title(
        f"{type}"
        f"{variant.capitalize()} Similarity Graph "
        f"({graph.vcount()} students, {graph.ecount()} edges, "
        f"{number_of_clusters} communities)"
    )

    ax.axis("off")
    fig.tight_layout()


# ---------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------

def evaluate_groups(
    members: pd.DataFrame,
    data: ProcessedData,
    cfg: Config,
) -> pd.DataFrame:
    """
    Placeholder for later-period persistence evaluation.

    Implement the evaluation before interpreting persistence results.
    """

    return pd.DataFrame(columns=GROUP_COLUMNS)


# ---------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------

def run(
    data: ProcessedData,
    cfg: Config,
) -> ClusteringResults:
    """Cluster both variants, then display both graphs."""

    discovery = data.discovery_pairs
    evaluation = data.evaluation_pairs
    population = data.pair_population

    users = sorted(
        set(population["user_a"])
        | set(population["user_b"])
    )

    evaluation_all_memberships = []
    evaluation_all_evaluations = []
    evaluation_graphs = {}
    
    discovery_all_memberships = []
    discovery_all_evaluations = []
    discovery_graphs = {}

    for variant in ("bluetooth", "combined"):
        discovery_matrix = similarity_matrix(
            discovery,
            users,
            variant,
            cfg,
        )
        
        evaluation_matrix = similarity_matrix(
            evaluation,
            users,
            variant,
            cfg,
        )

        discovery_members, modularity, discovery_graph = calculate_modularity(
            discovery_matrix,
            variant,
            cfg,
        )
        
        evaluation_members, modularity, evaluation_graph = calculate_modularity(
            evaluation_matrix,
            variant,
            cfg,
        )

        discovery_all_memberships.append(discovery_members)
        evaluation_all_memberships.append(evaluation_members)

        discovery_all_evaluations.append(
            evaluate_groups(discovery_members, data, cfg)
        )
        evaluation_all_evaluations.append(
            evaluate_groups(evaluation_members, data, cfg)
        )

        discovery_graphs[variant] = discovery_graph
        evaluation_graphs[variant] = evaluation_graph

    discovery_memberships = pd.concat(
        discovery_all_memberships,
        ignore_index=True,
    )
    
    evaluation_memberships = pd.concat(
        evaluation_all_memberships,
        ignore_index=True,
    )

    evaluation_group_evaluation = pd.concat(
        evaluation_all_evaluations,
        ignore_index=True,
    )
    
    discovery_group_evaluation = pd.concat(
        discovery_all_evaluations,
        ignore_index=True,
    )

    for variant, graph in discovery_graphs.items():
        show_igraph(graph, variant, "discovery")
        
    for variant, graph in evaluation_graphs.items():
        show_igraph(graph, variant, "evaluation")

    plt.show()

    return ClusteringResults(
        memberships=discovery_memberships,
        group_evaluation=discovery_group_evaluation,
    )
