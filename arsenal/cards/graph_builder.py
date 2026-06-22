import json
from pathlib import Path

import networkx as nx

from arsenal.cards.config import ARCHETYPES, COLOR_NAMES, GRAPH_JSON_PATH

ROOT_ID = "root"


def build_graph(
    cards: list[dict],
    card_clusters: dict[str, list[str]],
    combos: list[dict],
) -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node(ROOT_ID, type="root", label="MTG Cards")

    # L1: color nodes
    for code, name in COLOR_NAMES.items():
        nid = f"color:{code}"
        G.add_node(nid, type="color", code=code, label=name)
        G.add_edge(ROOT_ID, nid)

    # L2: archetype nodes + edges from each color
    for archetype in ARCHETYPES:
        nid = f"archetype:{archetype}"
        G.add_node(nid, type="archetype", label=archetype)
        for code in COLOR_NAMES:
            G.add_edge(f"color:{code}", nid)

    # L3: cluster nodes + edges from each archetype that uses them
    archetype_clusters: dict[str, set[str]] = {
        arch: set(clusters) for arch, clusters in ARCHETYPES.items()
    }
    all_clusters: set[str] = set()
    for clusters in archetype_clusters.values():
        all_clusters.update(clusters)

    for cluster in all_clusters:
        nid = f"cluster:{cluster}"
        G.add_node(nid, type="cluster", label=cluster)
        for arch, clusters in archetype_clusters.items():
            if cluster in clusters:
                G.add_edge(f"archetype:{arch}", nid)

    # L4: card nodes
    for card in cards:
        card_id = card["id"]
        nid = f"card:{card_id}"
        clusters = card_clusters.get(card_id, [])
        color_bucket = card.get("color_bucket", "C")

        G.add_node(
            nid,
            type="card",
            label=card["name"],
            **{k: v for k, v in card.items() if k not in ("legalities",)},
            clusters=clusters,
        )

        # edge from color node
        G.add_edge(f"color:{color_bucket}", nid)

        # edges from cluster nodes (and transitively their archetypes)
        for cluster in clusters:
            cluster_nid = f"cluster:{cluster}"
            if G.has_node(cluster_nid):
                G.add_edge(cluster_nid, nid)

    # Combo edges
    card_name_to_ids: dict[str, str] = {
        G.nodes[n]["name"]: n
        for n in G.nodes
        if G.nodes[n].get("type") == "card"
    }
    for i, combo in enumerate(combos):
        combo_id = f"combo:{i}"
        combo_card_nodes = []
        for card_name in combo.get("cards", []):
            node_id = card_name_to_ids.get(card_name)
            if node_id:
                combo_card_nodes.append(node_id)

        # add bidirectional combo edges between all cards in the combo
        for j, src in enumerate(combo_card_nodes):
            for dst in combo_card_nodes:
                if src != dst:
                    G.add_edge(
                        src,
                        dst,
                        edge_type="combo",
                        combo_id=combo_id,
                        combo_type=combo.get("type", "combo"),
                    )

    return G


def add_similarity_edges(
    G: nx.DiGraph,
    similarities: list[tuple[str, str, float]],
) -> None:
    """Add card→card similarity edges. similarities is list of (card_id_a, card_id_b, score)."""
    for card_id_a, card_id_b, score in similarities:
        src = f"card:{card_id_a}"
        dst = f"card:{card_id_b}"
        if G.has_node(src) and G.has_node(dst) and src != dst:
            G.add_edge(src, dst, edge_type="similar_to", score=score)


def save_graph(G: nx.DiGraph, path: Path = GRAPH_JSON_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(G, edges="edges")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, default=_json_default)
    print(f"  Graph saved: {G.number_of_nodes():,} nodes, {G.number_of_edges():,} edges → {path}")


def load_graph(path: Path = GRAPH_JSON_PATH) -> nx.DiGraph:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, directed=True, edges="edges")


def _json_default(obj):
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
