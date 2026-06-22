# Contributing to Karn

## Development setup

```bash
git clone https://github.com/karn-mtg/karn
cd karn
pip install -e ".[dev]"
```

The dev extras add `pytest`, `pytest-asyncio`, `pytest-cov`, and `ruff`.

You do **not** need to build the card database to run tests or work on most of the codebase. The smoke and unit tests run without any DB.

---

## Running tests

```bash
# Fast — no DB required (~1 second)
python -m pytest tests/smoke/ tests/unit/ -v

# With coverage
python -m pytest tests/smoke/ tests/unit/ --cov=arsenal --cov-report=term-missing
```

### Test layout

| Directory | What it tests | Needs DB? |
|---|---|---|
| `tests/smoke/` | Server imports, tool count, package imports | No |
| `tests/unit/` | Card classifier, rules parser, BM25 search | No |

If you add a new MCP tool, update `tests/smoke/test_smoke.py`:
- Bump the count in `test_exactly_N_tools`
- Add the tool name to the `expected` set in `test_all_expected_tools_present`

---

## Linting

```bash
ruff check .
ruff check . --fix   # auto-fix safe issues
```

CI runs ruff on every push. Line length is 120, `E501` is ignored.

---

## Project structure at a glance

The codebase has three distinct layers:

**Build pipeline** (`scripts/`) — one-time scripts that produce the DB artifacts. Run locally or in CI, never imported by the server.

**Server** (`arsenal/server.py`, `arsenal/api.py`) — the runtime. Reads the artifacts built by the pipeline and serves them over MCP stdio and HTTP. Should start in under 2 seconds; the DB warms up in a background thread.

**Library** (`arsenal/cards/`, `arsenal/rules/`) — the domain logic. `CardDB` owns ChromaDB queries and graph traversal. Rules parsing and search live in `arsenal/rules/`.

---

## Adding a new MCP tool

1. Open `arsenal/server.py` and add a `@mcp.tool()` function in the appropriate section (cards, rules, or management).
2. Update `tests/smoke/test_smoke.py` — bump the count and add the tool name to `expected`.
3. If the tool also makes sense as an HTTP endpoint, add a matching `@app.get(...)` route in `arsenal/api.py`.

```python
@mcp.tool()
def my_new_tool(param: str) -> dict:
    """One-line description that becomes the tool's docstring in MCP."""
    db = _get_db()
    ...
```

Tools that need streaming progress should be `async` and accept a `ctx: Context` parameter:

```python
@mcp.tool()
async def my_async_tool(param: str, ctx: Context) -> dict:
    await ctx.report_progress(current, total)
    ...
```

---

## Adding or changing enrichers

Enrichers live in `arsenal/cards/enrichers/`. Each one:
- Fetches external data with `httpx.AsyncClient` + `asyncio.Semaphore(10)` for concurrency
- Writes results to ChromaDB metadata and/or the NetworkX graph
- Caches results to a JSON file in `KARN_DATA_DIR` so re-runs are fast

The main pipeline in `scripts/build_db.py` calls each enricher as a numbered step. Add a new enricher there with a corresponding `--no-X` / `--force-X` flag pair.

---

## Release process

Releases are tag-triggered. There is no manual publish step.

### Binary release

```bash
git tag server-v1.2.0
git push origin server-v1.2.0
```

GitHub Actions (`release-server.yml`) builds `karn.exe` (Windows), `karn` (Linux), `karn` (macOS) via PyInstaller and uploads them to a GitHub Release. The version string is stamped into the binary from the tag before the build runs.

### Card database release

```bash
git tag cards-db-v1.2.0
git push origin cards-db-v1.2.0
```

CI (`release-cards-db.yml`) runs the full `build_db.py` pipeline (up to 60 min) and uploads `karn-cards-db-v1.2.0.tar.gz`.

### Rules database release

Rules are released automatically. A monthly cron job (`update-rules.yml`) rebuilds the rules artifacts, commits any changes, bumps the `rules-db-v*` tag, and pushes it — which triggers `release-rules-db.yml` to package and upload the release.

You can also trigger it manually from the GitHub Actions tab.

### When to cut each release

| Changed | Release needed |
|---|---|
| `arsenal/` code or `scripts/` | `server-v*` |
| Card embeddings, graph, enricher data | `cards-db-v*` |
| Rules JSON, glossary, chunks | `rules-db-v*` (usually automatic) |

---

## Environment variables

| Variable | Default | When you need it |
|---|---|---|
| `KARN_DATA_DIR` | `~/karnData/arsenal/db` | To store DB artifacts somewhere other than home |
| `KARN_GITHUB_REPO` | `karn-mtg/karn` | Only if you fork and want updates from your fork |
| `PYTHONIOENCODING` | — | Set to `utf-8` on Windows when running the MCP server |
| `GITHUB_TOKEN` | — | Optional, raises GitHub API rate limits for `install_data.py` |

Copy `.env.example` to `.env` for local development.

---

## Pull request guidelines

- Keep PRs focused — one logical change per PR.
- Tests must pass (`pytest tests/smoke/ tests/unit/`).
- If you add a dependency, add it to `pyproject.toml` and explain why in the PR description.
- Don't commit built artifacts (`chroma_db/`, `graph.json`, `prints.db`, `dist/`, `*.npy`).
- Rules data files (`arsenal/rules/data/`, `arsenal/rules/chunks/`) are committed and managed by the update cron — don't edit them manually unless you're fixing a parser bug.
