import json
import time
from pathlib import Path

import chromadb
import numpy as np
from chromadb.utils import embedding_functions

from arsenal.cards.config import (
    ALL_FORMATS,
    CHROMA_COLLECTION,
    CHROMA_UPSERT_CHUNK,
    CHROMA_DIR,
    EMBED_BATCH_SIZE,
    EMBEDDINGS_NPY_PATH,
    PROGRESS_JSON_PATH,
    SENTENCE_TRANSFORMER_MODEL,
)


def get_collection_for_query(chroma_dir: Path = CHROMA_DIR) -> chromadb.Collection:
    """Open the existing collection without an embedding function — caller provides embeddings."""
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_collection(name=CHROMA_COLLECTION)


def get_or_create_collection(chroma_dir: Path = CHROMA_DIR) -> chromadb.Collection:
    """Create or open the collection with an EF — used only during build_db.py."""
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=SENTENCE_TRANSFORMER_MODEL,
    )
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def _make_embedding_text(card: dict) -> str:
    return f"{card['name']}. {card['type_line']}. {card.get('oracle_text', '') or ''}"


def _card_to_metadata(card: dict, clusters: list[str]) -> dict:
    color_identity = card.get("color_identity") or []
    keywords = card.get("keywords") or []
    legalities = card.get("legalities") or {}
    type_line = card.get("type_line", "") or ""

    return {
        "name": card["name"],
        "type_line": type_line,
        "mana_cost": card.get("mana_cost", "") or "",
        "cmc": float(card.get("cmc", 0) or 0),
        "color_identity": ",".join(color_identity),
        "color_bucket": card.get("color_bucket", "C"),
        "rarity": card.get("rarity", "common"),
        "clusters": ",".join(clusters),
        "keywords": ",".join(keywords),
        "oracle_text": (card.get("oracle_text", "") or "")[:1000],
        "is_creature": "Creature" in type_line,
        "is_instant_sorcery": bool({"Instant", "Sorcery"} & set(type_line.split())),
        **{f"legal_{fmt}": legalities.get(fmt) == "legal" for fmt in ALL_FORMATS},
    }


def _load_progress() -> dict:
    if PROGRESS_JSON_PATH.exists():
        with open(PROGRESS_JSON_PATH) as f:
            return json.load(f)
    return {"last_completed_chunk": -1, "total_chunks": 0, "total_cards": 0}


def _save_progress(data: dict) -> None:
    PROGRESS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_JSON_PATH, "w") as f:
        json.dump(data, f)


def build_embeddings(
    cards: list[dict],
    card_clusters: dict[str, list[str]],
    force_reembed: bool = False,
) -> np.ndarray:
    """
    Encode all cards into ChromaDB and return the full embeddings matrix
    (shape: [len(cards), embedding_dim]) as a numpy array.

    Also saves the matrix to EMBEDDINGS_NPY_PATH so build_similarity_edges
    can reuse it without re-encoding.
    """
    from sentence_transformers import SentenceTransformer

    collection = get_or_create_collection()

    chunks = [
        cards[i : i + CHROMA_UPSERT_CHUNK]
        for i in range(0, len(cards), CHROMA_UPSERT_CHUNK)
    ]
    total_chunks = len(chunks)

    progress = _load_progress()
    if force_reembed:
        progress = {"last_completed_chunk": -1, "total_chunks": total_chunks, "total_cards": len(cards)}
    else:
        progress["total_chunks"] = total_chunks
        progress["total_cards"] = len(cards)

    last_done = progress.get("last_completed_chunk", progress.get("last_completed_batch", -1))
    if last_done >= 0:
        print(f"  Resuming from chunk {last_done + 1}/{total_chunks}")

    print(f"  Loading sentence-transformer model ({SENTENCE_TRANSFORMER_MODEL})...")
    model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

    all_embeddings: list[np.ndarray] = []
    start = time.time()

    for chunk_idx, chunk in enumerate(chunks):
        if chunk_idx <= last_done:
            # Load from saved file for skipped chunks so all_embeddings stays complete
            # (only matters when resuming a partially completed build)
            continue

        chunk_start = chunk_idx * CHROMA_UPSERT_CHUNK
        chunk_end   = min(chunk_start + CHROMA_UPSERT_CHUNK, len(cards))
        print(f"  Encoding chunk {chunk_idx + 1}/{total_chunks} "
              f"({chunk_start + 1:,}–{chunk_end:,} of {len(cards):,} cards)...")

        texts      = [_make_embedding_text(c) for c in chunk]
        embeddings = model.encode(
            texts,
            batch_size=EMBED_BATCH_SIZE,
            show_progress_bar=True,
            convert_to_numpy=True,
        )

        ids       = [c["id"] for c in chunk]
        metadatas = [_card_to_metadata(c, card_clusters.get(c["id"], [])) for c in chunk]

        # Pass numpy array directly — ChromaDB accepts ndarray, avoids .tolist() overhead
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        all_embeddings.append(embeddings)

        progress["last_completed_chunk"] = chunk_idx
        _save_progress(progress)

        elapsed = time.time() - start
        done    = chunk_idx + 1
        eta     = (elapsed / done) * (total_chunks - done) if done else 0
        print(f"  Chunk {done}/{total_chunks} done — elapsed {elapsed:.0f}s, ETA {eta:.0f}s")

    print(f"\n  Embedding complete in {time.time() - start:.1f}s")
    print(f"  ChromaDB collection has {collection.count():,} documents")

    if all_embeddings:
        full_matrix = np.vstack(all_embeddings)
        EMBEDDINGS_NPY_PATH.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(EMBEDDINGS_NPY_PATH), full_matrix)
        print(f"  Embeddings saved → {EMBEDDINGS_NPY_PATH} ({full_matrix.shape})")
        return full_matrix

    # Resuming a fully-completed build: load from disk
    if EMBEDDINGS_NPY_PATH.exists():
        print(f"  All chunks already done — loading embeddings from {EMBEDDINGS_NPY_PATH}")
        return np.load(str(EMBEDDINGS_NPY_PATH))

    # Fallback: return empty array (similarity step will skip gracefully)
    return np.empty((0,), dtype=np.float32)
