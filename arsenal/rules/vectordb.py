# arsenal/rules/vectordb.py
from __future__ import annotations

import chromadb
from sentence_transformers import SentenceTransformer

from arsenal.cards.config import SENTENCE_TRANSFORMER_MODEL

_RULES_COLLECTION = "mtg_rules"
_GLOSSARY_COLLECTION = "mtg_glossary"
_BATCH_SIZE = 500


def build_rules_vectordb(
    rules: dict,
    glossary: dict,
    db_path: str,
    force: bool = False,
) -> None:
    """Embed all parsed rules and glossary terms into ChromaDB collections."""
    client = chromadb.PersistentClient(path=db_path)
    _build_rules_collection(client, rules, force)
    _build_glossary_collection(client, glossary, force)


def _build_rules_collection(
    client: chromadb.ClientAPI,
    rules: dict,
    force: bool,
) -> None:
    col = client.get_or_create_collection(
        _RULES_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    if not force and col.count() == len(rules):
        print(f"  Rules vector DB already current ({col.count()} rules). Use --force-reembed to rebuild.")
        return

    model = _get_model()
    ids, texts, metadatas = [], [], []

    for rule_id, rule in rules.items():
        text_parts = [f"{rule_id}. {rule['text']}"]
        text_parts.extend(rule.get("examples", []))
        ids.append(rule_id)
        texts.append(" ".join(text_parts))
        metadatas.append({
            "rule_id": rule_id,
            "section": int(rule_id.split(".")[0]) if rule_id[0].isdigit() else 0,
            "parent": rule.get("parent", "") or "",
        })

    print(f"  Embedding {len(ids)} rules...")
    _upsert_in_batches(col, model, ids, texts, metadatas)
    print(f"  Rules vector DB: {col.count()} rules embedded.")


def _build_glossary_collection(
    client: chromadb.ClientAPI,
    glossary: dict,
    force: bool,
) -> None:
    col = client.get_or_create_collection(
        _GLOSSARY_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    if not force and col.count() == len(glossary):
        print(f"  Glossary vector DB already current ({col.count()} terms).")
        return

    model = _get_model()
    ids = list(glossary.keys())
    texts = [f"{term}: {definition}" for term, definition in glossary.items()]
    metadatas = [{"term": term} for term in glossary]

    print(f"  Embedding {len(ids)} glossary terms...")
    _upsert_in_batches(col, model, ids, texts, metadatas)
    print(f"  Glossary vector DB: {col.count()} terms embedded.")


def _upsert_in_batches(
    col: chromadb.Collection,
    model: SentenceTransformer,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
) -> None:
    for i in range(0, len(ids), _BATCH_SIZE):
        batch_ids = ids[i : i + _BATCH_SIZE]
        batch_texts = texts[i : i + _BATCH_SIZE]
        batch_meta = metadatas[i : i + _BATCH_SIZE]
        embeddings = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)
        col.upsert(
            ids=batch_ids,
            embeddings=embeddings.tolist(),
            documents=batch_texts,
            metadatas=batch_meta,
        )
        print(f"    Upserted {min(i + _BATCH_SIZE, len(ids))}/{len(ids)}", end="\r")
    print()


_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, device="cpu")
    return _model


def semantic_search_rules(query: str, top_k: int = 5, db_path: str = "") -> list[dict]:
    """Search rules using semantic vector similarity."""
    if not db_path:
        from arsenal.cards.config import BASE_DIR
        db_path = str(BASE_DIR)

    client = chromadb.PersistentClient(path=db_path)
    col = client.get_collection(_RULES_COLLECTION)

    model = _get_model()
    query_embedding = model.encode([query], convert_to_numpy=True)[0]

    results = col.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=min(top_k, 20),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "id": meta["rule_id"],
            "text": doc,
            "section": meta.get("section", 0),
            "score": round(1.0 - dist, 4),
        })
    return output
