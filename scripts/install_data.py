#!/usr/bin/env python3
"""
Download pre-built Arsenal databases from GitHub Releases.

Components:
  cards  — card vector DB (ChromaDB + prints.db + graph.json)
  rules  — rules data (rules.json, glossary.json, keyword_index.json, chunks/)

Usage:
    python install_data.py [--component cards|rules|all] [--force] [--version 1.2.0]

Can also be imported:
    from scripts.install_data import check_db_versions, install_component
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

GITHUB_REPO = os.environ.get("KARN_GITHUB_REPO", "karn-mtg/karn")
DB_DIR = Path(
    os.environ.get("KARN_DATA_DIR") or Path.home() / "karnData" / "arsenal" / "db"
).expanduser()

GITHUB_API = "https://api.github.com"

_COMPONENT_CONFIG: dict[str, dict] = {
    "cards": {
        "tag_prefix": "cards-db-v",
        "asset_template": "karn-cards-db-v{version}.tar.gz",
        "version_file": "cards-db-version.txt",
        "label": "Cards DB",
    },
    "rules": {
        "tag_prefix": "rules-db-v",
        "asset_template": "karn-rules-db-v{version}.tar.gz",
        "version_file": "rules-db-version.txt",
        "label": "Rules DB",
    },
    "agent": {
        "tag_prefix": "agent-v",
        "asset_template": "karn-agent-v{version}.tar.gz",
        "version_file": "agent-version.txt",
        "label": "Agent",
    },
}


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_latest_by_prefix(prefix: str) -> Optional[dict]:
    """Return the most recent release whose tag_name starts with prefix, or None."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/releases",
            params={"per_page": 50},
            headers=_github_headers(),
        )
        if resp.status_code == 404:
            print(f"ERROR: Repo '{GITHUB_REPO}' not found. Set KARN_GITHUB_REPO env var.")
            sys.exit(1)
        resp.raise_for_status()

    for release in resp.json():
        if release.get("tag_name", "").startswith(prefix):
            return release
    return None


def _fetch_by_tag(tag: str) -> Optional[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/releases/tags/{tag}",
            headers=_github_headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def _find_asset(release: dict, asset_name: str) -> tuple[str, int]:
    for asset in release.get("assets", []):
        if asset["name"] == asset_name:
            return asset["browser_download_url"], asset["size"]
    available = [a["name"] for a in release.get("assets", [])]
    print(f"ERROR: Asset '{asset_name}' not found in release {release.get('tag_name', '?')}.")
    print(f"  Available: {available}")
    sys.exit(1)


def _download_with_progress(url: str, dest: Path, total_bytes: int) -> None:
    downloaded = 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total_bytes > 0:
                    pct = downloaded / total_bytes * 100
                    print(
                        f"\r  Downloading... {pct:5.1f}%  ({downloaded // 1024 // 1024} MB)",
                        end="",
                        flush=True,
                    )
    print()


def _extract(archive: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        safe_members = [
            m for m in tf.getmembers()
            if not m.name.startswith("/") and ".." not in m.name
        ]
        tf.extractall(path=dest_dir, members=safe_members)


def _get_local_version(component: str) -> Optional[str]:
    cfg = _COMPONENT_CONFIG[component]
    version_path = DB_DIR / cfg["version_file"]
    try:
        text = version_path.read_text().strip()
        return text or None
    except FileNotFoundError:
        return None


def _set_local_version(component: str, version: str) -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    cfg = _COMPONENT_CONFIG[component]
    (DB_DIR / cfg["version_file"]).write_text(version)


def _is_newer(remote: str, local: Optional[str]) -> bool:
    """Return True if remote version is strictly newer than local."""
    if local is None:
        return True
    try:
        r = tuple(int(x) for x in remote.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except ValueError:
        return remote != local


def install_component(
    component: str,
    *,
    force: bool = False,
    version: Optional[str] = None,
) -> bool:
    """Download and install one component. Returns True if anything was installed/updated."""
    cfg = _COMPONENT_CONFIG[component]
    label = cfg["label"]
    prefix = cfg["tag_prefix"]

    print(f"\n[{label}]")

    if version:
        release = _fetch_by_tag(f"{prefix}{version}")
        if not release:
            print(f"  ERROR: Release '{prefix}{version}' not found.")
            return False
    else:
        release = _fetch_latest_by_prefix(prefix)
        if not release:
            print(f"  No release found with tag prefix '{prefix}'.")
            return False

    tag_name: str = release["tag_name"]
    remote_version = tag_name.removeprefix(prefix)
    local_version = _get_local_version(component)

    if not force and not _is_newer(remote_version, local_version):
        print(f"  Already up to date: v{local_version}")
        return False

    if local_version:
        print(f"  Updating v{local_version} → v{remote_version}")
    else:
        print(f"  Installing v{remote_version}")

    asset_name = cfg["asset_template"].format(version=remote_version)
    url, size = _find_asset(release, asset_name)
    print(f"  Asset: {asset_name} ({size / 1024 / 1024:.1f} MB)")

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / asset_name
        _download_with_progress(url, archive, size)
        print(f"  Extracting to {DB_DIR} ...")
        _extract(archive, DB_DIR)

    _set_local_version(component, remote_version)
    print(f"  {label} v{remote_version} installed.")
    return True


def _find_asset_safe(release: dict, asset_name: str) -> tuple[str, int]:
    """Like _find_asset but raises ValueError instead of sys.exit — safe for async callers."""
    for asset in release.get("assets", []):
        if asset["name"] == asset_name:
            return asset["browser_download_url"], asset["size"]
    available = [a["name"] for a in release.get("assets", [])]
    raise ValueError(f"Asset '{asset_name}' not found in release {release.get('tag_name', '?')}. Available: {available}")


async def _download_async(
    url: str,
    dest: Path,
    total_bytes: int,
    on_progress: Callable[[int, int], Awaitable[None]] | None,
) -> None:
    downloaded = 0
    async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None:
                        try:
                            await on_progress(downloaded, total_bytes)
                        except Exception:
                            pass


async def install_component_async(
    component: str,
    *,
    force: bool = False,
    version: Optional[str] = None,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> dict:
    """
    Async version of install_component.
    Returns {"installed": bool, "version": str | None, "error": str | None}.
    """
    if component not in _COMPONENT_CONFIG:
        return {"installed": False, "version": None, "error": f"Unknown component: {component!r}"}

    cfg = _COMPONENT_CONFIG[component]
    prefix = cfg["tag_prefix"]

    try:
        if version:
            release = await asyncio.to_thread(_fetch_by_tag, f"{prefix}{version}")
            if not release:
                return {"installed": False, "version": None, "error": f"Release '{prefix}{version}' not found"}
        else:
            release = await asyncio.to_thread(_fetch_latest_by_prefix, prefix)
            if not release:
                return {"installed": False, "version": None, "error": f"No release found with tag prefix '{prefix}'"}

        tag_name: str = release["tag_name"]
        remote_version = tag_name.removeprefix(prefix)
        local_version = _get_local_version(component)

        if not force and not _is_newer(remote_version, local_version):
            return {"installed": False, "version": local_version, "error": None}

        asset_name = cfg["asset_template"].format(version=remote_version)
        url, size = _find_asset_safe(release, asset_name)

        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / asset_name
            await _download_async(url, archive, size, on_progress)
            await asyncio.to_thread(_extract, archive, DB_DIR)

        await asyncio.to_thread(_set_local_version, component, remote_version)
        return {"installed": True, "version": remote_version, "error": None}

    except Exception as exc:
        return {"installed": False, "version": None, "error": str(exc)}


def check_db_versions() -> dict[str, dict]:
    """
    Return update status for each component without downloading anything.
    Keys: component name → {local, latest, has_update}.
    """
    result: dict[str, dict] = {}
    for component, cfg in _COMPONENT_CONFIG.items():
        local = _get_local_version(component)
        release = _fetch_latest_by_prefix(cfg["tag_prefix"])
        if release:
            latest = release["tag_name"].removeprefix(cfg["tag_prefix"])
            has_update = _is_newer(latest, local)
        else:
            latest = None
            has_update = False
        result[component] = {"local": local, "latest": latest, "has_update": has_update}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download pre-built Arsenal databases from GitHub Releases"
    )
    parser.add_argument(
        "--component",
        choices=["cards", "rules", "all"],
        default="all",
        help="Which database to install (default: all)",
    )
    parser.add_argument(
        "--version",
        metavar="VER",
        help="Specific semver to install, e.g. 1.2.0 (default: latest)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reinstall even if already up to date",
    )
    args = parser.parse_args()

    components = list(_COMPONENT_CONFIG) if args.component == "all" else [args.component]

    print(f"Arsenal DB installer  ({GITHUB_REPO})")
    any_updated = False
    for comp in components:
        updated = install_component(comp, force=args.force, version=args.version)
        any_updated = any_updated or updated

    if any_updated:
        print("\nDone. Restart the Arsenal server to apply changes.")
    else:
        print("\nAll databases are up to date.")


if __name__ == "__main__":
    main()
