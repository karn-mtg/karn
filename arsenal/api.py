"""Local HTTP REST API for the card database.

Usage:
    python -m arsenal.api            # default port 7371
    python -m arsenal.api --port 8080
    karn-api                        # via installed entry point

Endpoints:
    GET /health
    GET /search?q=...&top_k=10&colors=B,G&clusters=Dies,ETB&max_cmc=4&format=commander
    GET /card/{name}
    GET /similar/{name}?top_k=10
    GET /combos/{name}
    GET /traverse/{node_path}?top_k=20   (node_path e.g. color:B/archetype:Aristocrats)
    GET /prints/{oracle_id}
    GET /set/{set_code}?q=...&top_k=20
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from typing import Annotated

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from arsenal.cards._db import (
    get_db,
    get_card_count,
    get_prints,
    is_ready,
    parse_card_row,
    parse_prints_row,
    reload_db,
    start_preload_thread,
)
from arsenal.version import get_version, get_db_version

app = FastAPI(title="Karn Card DB", version="1.0.0")
_START_TIME = time.time()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7371", "http://127.0.0.1:7371", "app://.", "file://"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _require_db():
    try:
        return get_db()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ready" if is_ready() else "warming_up",
        "version": get_version(),
        "cards_db_version": get_db_version("cards"),
        "rules_db_version": get_db_version("rules"),
        "agent_version": get_db_version("agent"),
        "card_count": get_card_count(),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@app.get("/version")
def version():
    return {
        "version": get_version(),
        "cards_db_version": get_db_version("cards"),
        "rules_db_version": get_db_version("rules"),
        "agent_version": get_db_version("agent"),
    }


@app.get("/updates")
async def check_for_updates():
    from scripts.install_data import check_db_versions
    from scripts.self_update import check_server_version
    try:
        components = await asyncio.to_thread(check_db_versions)
        server = await asyncio.to_thread(check_server_version)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to check updates: {exc}")
    return {"server": server, **components}


@app.get("/update/{component}")
async def update_component(component: str):
    if component not in ("cards", "rules", "agent", "server"):
        raise HTTPException(status_code=422, detail=f"Unknown component {component!r}. Must be 'cards', 'rules', 'agent', or 'server'.")

    if component == "server":
        from scripts.self_update import self_update_server_async

        async def server_stream():
            queue: asyncio.Queue[str | None] = asyncio.Queue()

            async def on_progress(downloaded: int, total: int) -> None:
                pct = round(downloaded / total * 100, 1) if total > 0 else 0
                await queue.put(
                    f'data: {json.dumps({"type":"progress","downloaded":downloaded,"total":total,"pct":pct})}\n\n'
                )

            async def run_update() -> dict:
                result = await self_update_server_async(on_progress=on_progress)
                await queue.put(None)
                return result

            update_task = asyncio.create_task(run_update())

            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

            result = await update_task

            if result.get("error"):
                yield f'data: {json.dumps({"type":"error","message":result["error"]})}\n\n'
            else:
                yield f'data: {json.dumps({"type":"done","version":result["version"],"installed":result["installed"],"restarting":result.get("restarting",False)})}\n\n'

        return StreamingResponse(
            server_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    from scripts.install_data import install_component_async

    async def event_stream():
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_progress(downloaded: int, total: int) -> None:
            pct = round(downloaded / total * 100, 1) if total > 0 else 0
            await queue.put(
                f'data: {json.dumps({"type":"progress","downloaded":downloaded,"total":total,"pct":pct})}\n\n'
            )

        async def run_install() -> dict:
            result = await install_component_async(component, on_progress=on_progress)
            await queue.put(None)  # sentinel — download finished
            return result

        install_task = asyncio.create_task(run_install())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        result = await install_task

        if result["error"]:
            yield f'data: {json.dumps({"type":"error","message":result["error"]})}\n\n'
        else:
            if result["installed"] and component == "cards":
                reload_db()
            yield f'data: {json.dumps({"type":"done","version":result["version"],"installed":result["installed"]})}\n\n'

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/search")
def search_cards(
    q: Annotated[str, Query(min_length=1)],
    top_k: int = 10,
    colors: str = "",
    clusters: str = "",
    max_cmc: float = 0,
    card_format: str = "",
):
    db = _require_db()
    color_list = [c.strip() for c in colors.split(",") if c.strip()] or None
    cluster_list = [c.strip() for c in clusters.split(",") if c.strip()] or None
    results = db.query(
        q,
        top_k=top_k,
        color_identity=color_list,
        clusters=cluster_list,
        max_cmc=max_cmc if max_cmc > 0 else None,
        format_legal=card_format.strip() or None,
    )
    return [r.to_dict() for r in results]


@app.get("/card/{name}")
def get_card(name: str):
    db = _require_db()
    result = db.get_by_name(name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Card '{name}' not found.")
    return result.to_dict()


@app.get("/similar/{name}")
def get_similar(name: str, top_k: int = 10):
    db = _require_db()
    return [r.to_dict() for r in db.get_similar(name, top_k=top_k)]


@app.get("/combos/{name}")
def get_combos(name: str):
    db = _require_db()
    return [r.to_dict() for r in db.get_combos(name)]


@app.get("/traverse/{node_path:path}")
def traverse(node_path: str, top_k: int = 20):
    db = _require_db()
    return [r.to_dict() for r in db.traverse(node_path, top_k=top_k)]


@app.get("/prints/{oracle_id}")
def get_prints_for_card(oracle_id: str):
    con = get_prints()
    if not con:
        return []
    rows = con.execute(
        "SELECT * FROM card_images WHERE oracle_id = ? ORDER BY released_at ASC",
        (oracle_id,),
    ).fetchall()
    return [parse_prints_row(row) for row in rows]


@app.get("/set/{set_code}")
def search_in_set(set_code: str, q: str = "", top_k: int = 20):
    con = get_prints()
    if not con:
        return []
    safe_set = set_code.strip().lower()
    if q.strip():
        db = _require_db()
        results = db.query(q, top_k=top_k * 3)
        oracle_ids = [r.id for r in results]
        if not oracle_ids:
            return []
        placeholders = ",".join("?" * len(oracle_ids))
        rows = con.execute(
            f"""
            SELECT DISTINCT c.oracle_id, c.name, c.type_line, c.mana_cost, c.cmc,
                            c.color_identity, c.oracle_text, c.legalities, c.full_data
            FROM cards c
            JOIN card_images ci ON ci.oracle_id = c.oracle_id
            WHERE ci.set_code = ? AND c.oracle_id IN ({placeholders})
            LIMIT ?
            """,
            [safe_set, *oracle_ids, top_k],
        ).fetchall()
    else:
        rows = con.execute(
            """
            SELECT DISTINCT c.oracle_id, c.name, c.type_line, c.mana_cost, c.cmc,
                            c.color_identity, c.oracle_text, c.legalities, c.full_data
            FROM cards c
            JOIN card_images ci ON ci.oracle_id = c.oracle_id
            WHERE ci.set_code = ?
            ORDER BY c.name ASC
            LIMIT ?
            """,
            (safe_set, top_k),
        ).fetchall()
    return [parse_card_row(row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Karn Card DB HTTP API")
    parser.add_argument("--port", type=int, default=7371)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    start_preload_thread()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
