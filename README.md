# Karn — MTG Intelligence System

A local Magic: The Gathering intelligence backend. Exposes a unified MCP server (`karn`) combining a semantic card database, the official Comprehensive Rules, and a REST API — all in one self-contained binary.

Named after Karn, the silver golem — an artifact of vast knowledge and timeless understanding of the Multiverse.

---

## What's inside

- **16 MCP tools** — semantic card search, graph traversal, combo lookup, rules lookup, health/update management
- **Card vector DB** — ~27,000 Commander-legal cards embedded with `all-MiniLM-L6-v2`, enriched with Scryfall tags, EDHREC rank/salt, and Commander Spellbook combos
- **NetworkX graph** — 4-level DAG (color → archetype → cluster → card) plus combo, similarity, and tag edges
- **MTG Comprehensive Rules** — fully parsed, BM25 + semantic search, glossary, cross-references
- **HTTP REST API** — on port 7371, same data as MCP, SSE streaming for updates

---

## Quick start

### Option A — download pre-built databases (recommended)

```bash
pip install -e .
python scripts/install_data.py          # downloads cards + rules DBs from GitHub Releases
karn                                    # starts the MCP server
```

### Option B — build from source

```bash
pip install -e .
python scripts/build_rules.py --force-download   # ~1 min
python scripts/build_db.py                       # ~30 min, resumable
karn
```

### Add to Claude Code

Global (`~/.claude/settings.json`) or project (`.claude/settings.json`):

```json
{
  "mcpServers": {
    "karn": {
      "command": "karn",
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Or point at the installed binary directly:

```json
{
  "mcpServers": {
    "karn": {
      "command": "C:/Users/<user>/karnData/arsenal/karn.exe"
    }
  }
}
```

---

## MCP Tools (16 total)

### Card tools

| Tool | Description |
|---|---|
| `search_cards(query, top_k, color_identity, clusters, max_cmc, format_legal)` | Semantic card search via ChromaDB |
| `traverse_graph(node_path, top_k)` | Graph traversal — e.g. `"color:B/archetype:Aristocrats/cluster:Dies"` |
| `get_combos(card_name)` | Known combos involving a card (Commander Spellbook + curated) |
| `get_similar(card_name, top_k)` | Cards that play similarly based on embedding distance |
| `get_card(name)` | Full card details by exact name |
| `get_card_prints(oracle_id)` | All printings with image URLs, set info, and prices |
| `search_cards_in_set(set_code, query, top_k)` | Cards from a specific set, optionally filtered by query |

### Rules tools

| Tool | Description |
|---|---|
| `get_rule(rule_id)` | Exact rule text by ID — e.g. `"702.19"`, `"101.1a"` |
| `search_rules(query, top_k)` | Semantic search (falls back to BM25 keyword search) |
| `get_section(name)` | Section overview by number or keyword — e.g. `"combat"`, `"stack"` |
| `get_glossary(term)` | Official MTG glossary definition |
| `get_related_rules(rule_id)` | Rules that cross-reference a given rule |
| `get_rules_primer()` | Compact ~1,500-token primer (turn structure, zones, stack, Commander, gotchas) |

### Management tools

| Tool | Description |
|---|---|
| `get_health()` | Server status, version, DB versions, card count, uptime |
| `check_updates()` | Check GitHub for available DB updates |
| `update_component(component)` | Download and install `"cards"` or `"rules"` with progress notifications |

---

## HTTP API

The server also exposes a REST API on `http://localhost:7371`:

| Endpoint | Description |
|---|---|
| `GET /health` | Full health status (same as `get_health`) |
| `GET /version` | Binary and DB versions |
| `GET /updates` | Check GitHub for updates |
| `GET /update/{component}` | Download and install component, streams SSE progress |
| `GET /search?q=...` | Card search (`colors`, `clusters`, `max_cmc`, `card_format`, `top_k`) |
| `GET /card/{name}` | Card details by name |
| `GET /similar/{name}` | Similar cards |
| `GET /combos/{name}` | Combos for a card |
| `GET /traverse/{node_path}` | Graph traversal |
| `GET /prints/{oracle_id}` | All printings with images |
| `GET /set/{set_code}?q=...` | Cards from a set |

Start the API standalone:

```bash
karn-api                    # port 7371
karn-api --port 8080        # custom port
```

---

## Building from source

### Rules index (~1 min)

```bash
python scripts/build_rules.py --force-download
# Flags: --force-reindex  --no-wiki  --no-embed  --force-reembed
```

### Card database (~30 min, requires ~700 MB disk)

```bash
python scripts/build_db.py
```

Runs an 11-step pipeline: downloads Scryfall bulk data → classifies cards into mechanic clusters → fetches Commander Spellbook combos → embeds into ChromaDB → enriches with Scryfall Tagger tags → EDHREC rank/salt → computes similarity edges → builds `prints.db`. Fully resumable.

```
Flags:
  --force-download      Re-download Scryfall data even if fresh
  --force-reembed       Re-embed all cards even if already done
  --no-spellbook        Skip Commander Spellbook fetch
  --no-tagger           Skip Scryfall Tagger (saves ~90 min)
  --no-edhrec           Skip EDHREC enrichment
  --no-similarity-edges Skip similarity edge computation
  --no-prints           Skip prints.db build
```

### Tag propagation (optional, after build)

```bash
python scripts/propagate_tags.py --dry-run    # preview
python scripts/propagate_tags.py              # apply
```

Uses similarity edges to vote tags and clusters onto cards that tagger missed.

### Build standalone executable

```bash
python scripts/build_executables.py
# Output: dist/karn.exe (Windows) or dist/karn (Linux/macOS)
```

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `KARN_DATA_DIR` | `~/karnData/arsenal/db` | Where ChromaDB, graph.json, and prints.db live |
| `KARN_GITHUB_REPO` | `karn-mtg/karn` | GitHub repo for release checks and downloads |
| `PYTHONIOENCODING` | — | Set to `utf-8` on Windows to prevent BOM issues on MCP pipe |

Copy `.env.example` to `.env` for local overrides.

---

## Architecture

```
karn/
├── arsenal/
│   ├── server.py            — MCP server (16 tools over stdio)
│   ├── api.py               — HTTP REST API on port 7371
│   ├── version.py           — Version resolution (package → exe → bundle)
│   ├── cards/
│   │   ├── _db.py           — Thread-safe DB singletons
│   │   ├── query.py         — CardDB: search, graph traversal, combos
│   │   ├── config.py        — Paths, cluster patterns, archetype definitions
│   │   ├── classifier.py    — Mechanic cluster classifier (regex)
│   │   ├── embedder.py      — ChromaDB upsert + embeddings.npy cache
│   │   ├── graph_builder.py — NetworkX DAG construction
│   │   ├── enrichers/       — Spellbook, Scryfall Tagger, EDHREC (async httpx)
│   │   ├── combos.json      — Curated combo seeds
│   │   └── data/            — Reference markdown (synergies, archetypes, keywords)
│   └── rules/
│       ├── parser.py        — Comprehensive Rules parser
│       ├── search.py        — BM25 keyword search
│       ├── vectordb.py      — Semantic rules search
│       ├── chunks/          — Pre-built section markdown (committed)
│       └── data/            — Parsed artifacts (rules.json, glossary.json, …)
├── scripts/
│   ├── build_db.py          — 11-step card DB pipeline
│   ├── build_rules.py       — Rules index + vector DB
│   ├── propagate_tags.py    — Similarity-vote tag propagation
│   ├── enrich_db.py         — Standalone enrichment re-runner
│   ├── install_data.py      — Download DBs from GitHub Releases
│   ├── build_executables.py — PyInstaller → dist/karn[.exe]
│   └── install_local.py     — Deploy binary to ~/karnData/arsenal/
├── tests/
│   ├── smoke/               — Import and tool-count checks (no DB required)
│   └── unit/                — Card classifier, rules parser, BM25 search
├── pyinstaller/karn.spec    — PyInstaller single-binary spec
└── pyproject.toml
```

---

## Python facade

```python
from karn_db import query, traverse, get_combos, get_similar

query("sacrifice outlet that generates mana", top_k=5)
traverse("color:B/archetype:Aristocrats/cluster:Dies")
get_combos("Blood Artist")
get_similar("Phyrexian Altar", top_k=10)
```

---

## Releases

Three independent release tracks, each triggered by a Git tag:

| Tag prefix | What it does |
|---|---|
| `server-v*` | Builds Windows/Linux/macOS binaries via PyInstaller |
| `cards-db-v*` | Builds and packages the full card vector DB (~700 MB) |
| `rules-db-v*` | Packages the rules artifacts (auto-bumped monthly by CI) |

---

## Requirements

- Python 3.11+
- `pip install -e .`
- Sentence-transformers model `all-MiniLM-L6-v2` (downloaded automatically on first build)
