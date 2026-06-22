from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
import networkx as nx
from sentence_transformers import SentenceTransformer

from arsenal.cards.config import CHROMA_DIR, GRAPH_JSON_PATH, SENTENCE_TRANSFORMER_MODEL
from arsenal.cards.embedder import get_collection_for_query
from arsenal.cards.graph_builder import load_graph


@dataclass
class CardResult:
    id: str
    name: str
    type_line: str
    mana_cost: str
    cmc: float
    color_identity: list[str]
    oracle_text: str
    clusters: list[str]
    rarity: str
    score: float | None = None
    edhrec_rank: int | None = None
    salt_score: float | None = None
    scryfall_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type_line": self.type_line,
            "mana_cost": self.mana_cost,
            "cmc": self.cmc,
            "color_identity": self.color_identity,
            "oracle_text": self.oracle_text,
            "clusters": self.clusters,
            "rarity": self.rarity,
            "score": self.score,
            "edhrec_rank": self.edhrec_rank,
            "salt_score": self.salt_score,
            "scryfall_tags": self.scryfall_tags,
        }


@dataclass
class ComboResult:
    cards: list[str]
    combo_type: str
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "cards": self.cards,
            "combo_type": self.combo_type,
            "description": self.description,
        }


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _metadata_to_card_result(
    card_id: str,
    meta: dict,
    score: float | None = None,
) -> CardResult:
    edhrec_rank_raw = meta.get("edhrec_rank")
    salt_score_raw = meta.get("salt_score")
    return CardResult(
        id=card_id,
        name=meta.get("name", ""),
        type_line=meta.get("type_line", ""),
        mana_cost=meta.get("mana_cost", ""),
        cmc=float(meta.get("cmc", 0)),
        color_identity=_parse_csv(meta.get("color_identity")),
        oracle_text=meta.get("oracle_text", ""),
        clusters=_parse_csv(meta.get("clusters")),
        rarity=meta.get("rarity", "common"),
        score=score,
        edhrec_rank=int(edhrec_rank_raw) if edhrec_rank_raw is not None else None,
        salt_score=float(salt_score_raw) if salt_score_raw is not None else None,
        scryfall_tags=_parse_csv(meta.get("scryfall_tags")),
    )


class CardDB:
    def __init__(
        self,
        chroma_dir: str | Path = None,
        graph_path: str | Path = None,
    ):
        chroma_dir = Path(chroma_dir) if chroma_dir else CHROMA_DIR
        graph_path = Path(graph_path) if graph_path else GRAPH_JSON_PATH

        self._model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, local_files_only=True)
        self._collection: chromadb.Collection = get_collection_for_query(chroma_dir)
        self._graph: nx.DiGraph = load_graph(graph_path)
        self._count: int = self._collection.count()

        # build name → node_id index for fast lookup (skip nodes with no name)
        self._name_index: dict[str, str] = {
            self._graph.nodes[n]["name"]: n
            for n in self._graph.nodes
            if self._graph.nodes[n].get("type") == "card"
            and self._graph.nodes[n].get("name")
        }

        # warmup: load HNSW index into memory so the first real query is instant
        warmup_vec = self._model.encode(["warmup"]).tolist()
        try:
            self._collection.query(query_embeddings=warmup_vec, n_results=1, include=["metadatas"])
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(
        self,
        text: str,
        top_k: int = 10,
        color_identity: list[str] | None = None,
        clusters: list[str] | None = None,
        max_cmc: float | None = None,
        card_types: list[str] | None = None,
        format_legal: str | None = None,
    ) -> list[CardResult]:
        where = _build_where(
            color_identity=color_identity,
            clusters=clusters,
            max_cmc=max_cmc,
            card_types=card_types,
            format_legal=format_legal,
        )

        embedding = self._model.encode([text]).tolist()
        kwargs: dict[str, Any] = {
            "query_embeddings": embedding,
            "n_results": min(top_k, self._count),
            "include": ["metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        return [
            _metadata_to_card_result(card_id, meta, score=1.0 - dist)
            for card_id, meta, dist in zip(ids, metadatas, distances)
        ]

    def traverse(
        self,
        node_path: str,
        top_k: int | None = None,
    ) -> list[CardResult]:
        segments = [s.strip() for s in node_path.split("/") if s.strip()]

        if not segments:
            return []

        # Find descendants of each segment and intersect
        candidate_sets: list[set[str]] = []
        for segment in segments:
            if not self._graph.has_node(segment):
                return []
            descendants = nx.descendants(self._graph, segment)
            card_descendants = {n for n in descendants if self._graph.nodes[n].get("type") == "card"}
            candidate_sets.append(card_descendants)

        card_nodes = candidate_sets[0]
        for s in candidate_sets[1:]:
            card_nodes = card_nodes & s

        results: list[CardResult] = []
        for node_id in card_nodes:
            attrs = self._graph.nodes[node_id]
            result = CardResult(
                id=attrs.get("id", node_id.removeprefix("card:")),
                name=attrs.get("name", ""),
                type_line=attrs.get("type_line", ""),
                mana_cost=attrs.get("mana_cost", ""),
                cmc=float(attrs.get("cmc", 0)),
                color_identity=attrs.get("color_identity") or [],
                oracle_text=attrs.get("oracle_text", "") or "",
                clusters=attrs.get("clusters") or [],
                rarity=attrs.get("rarity", "common"),
                score=None,
            )
            results.append(result)

        results.sort(key=lambda r: (r.cmc, r.name))
        return results[:top_k] if top_k else results

    def get_combos(self, card_name: str) -> list[ComboResult]:
        node_id = self._name_index.get(card_name)
        if not node_id:
            return []

        # Find all combo edges from this node
        seen_combo_ids: set[str] = set()
        results: list[ComboResult] = []

        for _, neighbor, edge_data in self._graph.out_edges(node_id, data=True):
            if edge_data.get("edge_type") != "combo":
                continue
            combo_id = edge_data.get("combo_id", "")
            if combo_id in seen_combo_ids:
                continue
            seen_combo_ids.add(combo_id)

            # Collect all cards in this combo (nodes that share the same combo_id edge with this node)
            combo_cards: list[str] = [card_name]
            combo_type = edge_data.get("combo_type", "combo")
            for _, other, other_edge in self._graph.out_edges(node_id, data=True):
                if other_edge.get("combo_id") == combo_id and other != neighbor:
                    other_name = self._graph.nodes[other].get("name", "")
                    if other_name and other_name not in combo_cards:
                        combo_cards.append(other_name)
            neighbor_name = self._graph.nodes[neighbor].get("name", "")
            if neighbor_name and neighbor_name not in combo_cards:
                combo_cards.append(neighbor_name)

            results.append(ComboResult(
                cards=combo_cards,
                combo_type=combo_type,
            ))

        return results

    def get_by_name(self, name: str) -> CardResult | None:
        results = self._collection.get(
            where={"name": {"$eq": name}},
            include=["metadatas"],
        )
        if not results["ids"]:
            return None
        return _metadata_to_card_result(results["ids"][0], results["metadatas"][0])

    def get_similar(self, card_name: str, top_k: int = 10) -> list[CardResult]:
        node_id = self._name_index.get(card_name)
        if not node_id:
            # Fall back to semantic search by name
            return self.query(card_name, top_k=top_k + 1)[1:]

        # Try similarity edges in graph first
        similar_via_graph: list[tuple[str, float]] = []
        for _, neighbor, edge_data in self._graph.out_edges(node_id, data=True):
            if edge_data.get("edge_type") == "similar_to":
                score = float(edge_data.get("score", 0.0))
                similar_via_graph.append((neighbor, score))

        if similar_via_graph:
            similar_via_graph.sort(key=lambda x: x[1], reverse=True)
            results: list[CardResult] = []
            for neighbor_id, score in similar_via_graph[:top_k]:
                attrs = self._graph.nodes[neighbor_id]
                results.append(CardResult(
                    id=attrs.get("id", neighbor_id.removeprefix("card:")),
                    name=attrs.get("name", ""),
                    type_line=attrs.get("type_line", ""),
                    mana_cost=attrs.get("mana_cost", ""),
                    cmc=float(attrs.get("cmc", 0)),
                    color_identity=attrs.get("color_identity") or [],
                    oracle_text=attrs.get("oracle_text", "") or "",
                    clusters=attrs.get("clusters") or [],
                    rarity=attrs.get("rarity", "common"),
                    score=score,
                ))
            return results

        # Fall back to semantic search
        return self.query(card_name, top_k=top_k + 1)[1:]


# ------------------------------------------------------------------
# Where clause builder
# ------------------------------------------------------------------

def _build_where(
    color_identity: list[str] | None,
    clusters: list[str] | None,
    max_cmc: float | None,
    card_types: list[str] | None,
    format_legal: str | None,
) -> dict | None:
    conditions: list[dict] = []

    if color_identity:
        for color in color_identity:
            conditions.append({"color_identity": {"$contains": color}})

    if clusters:
        for cluster in clusters:
            conditions.append({"clusters": {"$contains": cluster}})

    if max_cmc is not None:
        conditions.append({"cmc": {"$lte": max_cmc}})

    if card_types:
        for ct in card_types:
            conditions.append({"type_line": {"$contains": ct}})

    if format_legal:
        conditions.append({f"legal_{format_legal}": {"$eq": True}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
