"""WORK AREA 3 — clustering and persistence."""

import numpy as np
import pandas as pd
import igraph as ig
import leidenalg as la
import matplotlib.pyplot as plt

from .config import Config
from .contracts import ClusteringResults, ProcessedData

MEMBERSHIP_COLUMNS = [
    "user_id",
    "cluster",
    "cluster_size",
]

EDGE_THRESHOLD = 0.4

def similarity_matrix(
    pairs: pd.DataFrame,
    users: list,
    cfg: Config,
) -> pd.DataFrame:


    if cfg.period_days <= 0:
        raise ValueError("period_days must be positive")

    users = list(users)

    if len(users) != len(set(users)):
        raise ValueError("Duplicate user IDs supplied")
    weights = cfg.combined_weights

    if not np.isclose(sum(weights), 1.0):
        raise ValueError(
            "weights not summing to 1"
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

        bluetooth = pd.to_numeric(relevant["proximity_days"], errors="raise")/ cfg.period_days

        calls = pd.to_numeric(relevant["call_days"], errors="raise")/ cfg.period_days
        

        sms = pd.to_numeric(relevant["sms_days"], errors="raise")/ cfg.period_days
        

        w_bluetooth, w_calls, w_sms = weights

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
    
    return matrix

def build_graph(
    matrix: pd.DataFrame,
    edge_threshold: float = EDGE_THRESHOLD,
) -> ig.Graph:
    values = matrix.to_numpy(dtype=float)
    users = list(matrix.index)

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



# community detection
# -----------------------------------

def calculate_modularity(
    matrix: pd.DataFrame,
    cfg: Config,
) -> tuple[pd.DataFrame, float, ig.Graph]:
    graph = build_graph(matrix)

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

    # Store the memberships before filtering.
    graph.vs["cluster"] = membership

    members = pd.DataFrame({
        "user_id": graph.vs["user_id"],
        "cluster": membership,
    })

    members["cluster_size"] = (
        members.groupby("cluster")["user_id"].transform("size")
    )

    # Remove singleton communities.
    community_sizes = pd.Series(membership).value_counts()

    keep_vertices = [
        i
        for i, cluster in enumerate(membership)
        if community_sizes[cluster] > 1
    ]

    graph = graph.induced_subgraph(keep_vertices)

    members = members.loc[members["cluster_size"] > 1].copy()
    
    # Recalculate sizes since we removed singletons
    if not members.empty:
        members["cluster_size"] = (
            members.groupby("cluster")["user_id"].transform("size")
        )

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

    return members[MEMBERSHIP_COLUMNS], modularity, graph


# graph visualisation
# --------------------------------

def show_igraph(
    graph: ig.Graph,
    type: str,
    modularity: float,
):
    clusters = graph.vs["cluster"]

    # map every Leiden community ID to exactly one color.
    unique_clusters = sorted(set(clusters))
    number_of_clusters = len(unique_clusters)

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

    # draw edges first.
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

    # every vertex in the same community receives the same color.
    ax.scatter(
        positions[:, 0],
        positions[:, 1],
        c=node_colors,
        s=35,
        edgecolors="black",
        linewidths=0.25,
        zorder=2,
    )

    # label vertices with user IDs.
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
        f"{type} "
        f"Similarity Graph "
        f"({graph.vcount()} students, {graph.ecount()} edges, "
        f"{number_of_clusters} communities) "
        f"\nedge threshold: {EDGE_THRESHOLD}, "
        f"Modularity: {modularity}"
    )

    ax.axis("off")
    fig.tight_layout()

# evaluation and plotting
# -----------------------------------------------------


def compare_communities_jaccard(members_a, members_b, threshold = 0.1):
    communities_a = {
        cluster: set(group["user_id"]) for cluster, group in members_a.groupby("cluster")
    }

    communities_b = {
        cluster: set(group["user_id"]) for cluster, group in members_b.groupby("cluster")
    }

    results = []
    total_similarity = 0.0
    total_pairings = 0

    for cluster_a, users_a in communities_a.items():
        for cluster_b, users_b in communities_b.items():
            intersection = users_a & users_b

            if not intersection:
                continue

            union = users_a | users_b
            similarity = len(intersection) / len(union)
            total_similarity += similarity
            total_pairings+=1
            
            if similarity < threshold:
                continue

            results.append({
                "cluster_a": cluster_a,
                "cluster_b": cluster_b,
                "shared_users": len(intersection),
                "size_a": len(users_a),
                "size_b": len(users_b),
                "jaccard": similarity,
                "shared_user_ids": sorted(intersection),
            })

    return (
        pd.DataFrame(results)
        .sort_values("jaccard", ascending=False)
        .reset_index(drop=True),
        total_similarity/total_pairings
    )

def plot_jaccard_comparison(
    members_a: pd.DataFrame,
    members_b: pd.DataFrame,
    comparison: pd.DataFrame,
    average_similarity: int,
) -> None:
    """Plot matching communities using a heatmap."""

    # communities_a = (members_a["cluster"].unique().tolist())
    # communities_b = (members_b["cluster"].unique().tolist())
    communities_a = sorted(members_a["cluster"].unique().tolist())
    communities_b = sorted(members_b["cluster"].unique().tolist())

    # Create a matrix initialized to zero, so unmatched pairs are 0
    similarity_matrix = pd.DataFrame(
        0.0,
        index=communities_a,
        columns=communities_b,
    )

    if not comparison.empty:
        for row in comparison.itertuples(index=False):
            similarity_matrix.loc[
                row.cluster_a, row.cluster_b
            ] = row.jaccard

    # matplotlib shit
    #-------------------------------
    fig_width = max(10, len(communities_b) * 0.35)
    fig_height = max(7, len(communities_a) * 0.30)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    image = ax.imshow(
        similarity_matrix.to_numpy(),
        cmap="viridis",
        vmin=0,
        vmax=1,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(communities_b)))
    ax.set_xticklabels(communities_b, rotation=90, fontsize=7)

    ax.set_yticks(range(len(communities_a)))
    ax.set_yticklabels(communities_a, fontsize=7)

    ax.set_xlabel("Evaluation community")
    ax.set_ylabel("Discovery community")
    ax.set_title("Community Jaccard similarity "
                 f"\nAverage similarity: {average_similarity}")

    fig.colorbar(image, ax=ax, label="Jaccard similarity")
    fig.tight_layout()

def run(
    data: ProcessedData,
    cfg: Config,
) -> ClusteringResults:

    discovery = data.discovery_pairs
    evaluation = data.evaluation_pairs
    population = data.pair_population

    users = sorted(
        set(population["user_a"])
        | set(population["user_b"])
    )

    evaluation_all_memberships = []
    
    discovery_all_memberships = []

    
    discovery_matrix = similarity_matrix(
        discovery,
        users,
        cfg,
    )
    
    evaluation_matrix = similarity_matrix(
        evaluation,
        users,
        cfg,
    )

    discovery_members, discovery_modularity, discovery_graph = calculate_modularity(
        discovery_matrix,
        cfg,
    )
    
    evaluation_members, evaluation_modularity, evaluation_graph = calculate_modularity(
        evaluation_matrix,
        cfg,
    )

    discovery_all_memberships.append(discovery_members)
    evaluation_all_memberships.append(evaluation_members)
    
    comparison, average_similarity = compare_communities_jaccard(discovery_members, evaluation_members)
    print(f"\nJaccard comparison: ")
    print(comparison.to_string(index=False))

    plot_jaccard_comparison(
        discovery_members,
        evaluation_members,
        comparison,
        average_similarity,
    )

    discovery_memberships = pd.concat(
        discovery_all_memberships,
        ignore_index=True,
    )
    
    show_igraph(discovery_graph, "discovery", discovery_modularity)
    show_igraph(evaluation_graph, "evaluation", evaluation_modularity)

    plt.show()

    return ClusteringResults(
        memberships=discovery_memberships,
        group_evaluation=False,
    )
