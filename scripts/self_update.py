"""
Download and install a new server binary, then restart in place.

Unix:    atomic os.replace + os.execv restart (seamless, no race window)
Windows: rename-old / move-new / spawn-detached (exe lock workaround)

Only works when running as a compiled PyInstaller binary (sys.frozen == True).
Returns an error immediately in dev mode.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

GITHUB_REPO = os.environ.get("KARN_GITHUB_REPO", "karn-mtg/karn")
GITHUB_API = "https://api.github.com"
_TAG_PREFIX = "server-v"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _platform_suffix() -> str:
    if sys.platform == "win32":
        return "win"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def _arsenal_dir() -> Path:
    return Path(sys.executable).parent


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_newer(remote: str, local: Optional[str]) -> bool:
    if local is None:
        return True
    try:
        return tuple(int(x) for x in remote.split(".")) > tuple(int(x) for x in local.split("."))
    except ValueError:
        return remote != local


def check_server_version() -> dict:
    """Return {local, latest, has_update} for the server binary."""
    from arsenal.version import get_version
    local = get_version()
    if local == "unknown":
        local = None
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/releases",
            params={"per_page": 50},
            headers=_github_headers(),
        )
        resp.raise_for_status()
    release = next(
        (r for r in resp.json() if r.get("tag_name", "").startswith(_TAG_PREFIX)),
        None,
    )
    latest = release["tag_name"].removeprefix(_TAG_PREFIX) if release else None
    return {
        "local": local,
        "latest": latest,
        "has_update": _is_newer(latest, local) if latest else False,
    }


def _extract_binary(zip_path: Path, dest_dir: Path) -> Path:
    exe_name = "karn.exe" if sys.platform == "win32" else "karn"
    with zipfile.ZipFile(zip_path) as zf:
        safe = [m for m in zf.namelist() if not m.startswith("/") and ".." not in m]
        zf.extractall(dest_dir, members=[zf.getinfo(n) for n in safe])
    binary = dest_dir / exe_name
    if not binary.exists():
        available = [m for m in safe]
        raise FileNotFoundError(f"'{exe_name}' not found in zip. Contents: {available}")
    return binary


def _replace_and_restart(staged: Path) -> None:
    """Replace the running binary with staged and restart. Never returns on success."""
    current = Path(sys.executable)
    if sys.platform == "win32":
        old = current.with_suffix(".exe.old")
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
        current.rename(old)
        shutil.copy2(staged, current)
        try:
            staged.unlink()
        except OSError:
            pass
        import subprocess
        subprocess.Popen(
            [str(current)] + sys.argv[1:],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        sys.exit(0)
    else:
        staged.chmod(0o755)
        os.replace(str(staged), str(current))
        os.execv(str(current), [str(current)] + sys.argv[1:])


def _fetch_release(client: httpx.Client, version: Optional[str]) -> dict | None:
    if version:
        resp = client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/releases/tags/{_TAG_PREFIX}{version}",
            headers=_github_headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    resp = client.get(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/releases",
        params={"per_page": 50},
        headers=_github_headers(),
    )
    resp.raise_for_status()
    return next(
        (r for r in resp.json() if r.get("tag_name", "").startswith(_TAG_PREFIX)),
        None,
    )


async def _fetch_release_async(client: httpx.AsyncClient, version: Optional[str]) -> dict | None:
    if version:
        resp = await client.get(
            f"{GITHUB_API}/repos/{GITHUB_REPO}/releases/tags/{_TAG_PREFIX}{version}",
            headers=_github_headers(),
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    resp = await client.get(
        f"{GITHUB_API}/repos/{GITHUB_REPO}/releases",
        params={"per_page": 50},
        headers=_github_headers(),
    )
    resp.raise_for_status()
    return next(
        (r for r in resp.json() if r.get("tag_name", "").startswith(_TAG_PREFIX)),
        None,
    )


def _resolve_asset(release: dict, remote_version: str) -> tuple[str, int]:
    asset_name = f"karn-arsenal-v{remote_version}-{_platform_suffix()}.zip"
    asset = next((a for a in release.get("assets", []) if a["name"] == asset_name), None)
    if not asset:
        available = [a["name"] for a in release.get("assets", [])]
        raise ValueError(f"Asset {asset_name!r} not found. Available: {available}")
    return asset["browser_download_url"], asset["size"]


def self_update_server(
    *,
    force: bool = False,
    version: Optional[str] = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Download the latest server binary, replace this executable, and restart.
    Never returns on success. Returns a dict only on failure or when already up to date.
    """
    if not _is_frozen():
        return {"installed": False, "version": None, "error": "Cannot self-update: not running as a compiled binary."}

    try:
        from arsenal.version import get_version
        local_version: Optional[str] = get_version()
        if local_version == "unknown":
            local_version = None

        with httpx.Client(timeout=30) as client:
            release = _fetch_release(client, version)

        if release is None:
            msg = f"Release server-v{version} not found" if version else "No server release found on GitHub"
            return {"installed": False, "version": None, "error": msg}

        remote_version = release["tag_name"].removeprefix(_TAG_PREFIX)

        if not force and not _is_newer(remote_version, local_version):
            return {"installed": False, "version": local_version, "error": None}

        url, size = _resolve_asset(release, remote_version)

        new_name = "karn.new.exe" if sys.platform == "win32" else "karn.new"
        staged = _arsenal_dir() / new_name

        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / f"karn-arsenal-v{remote_version}-{_platform_suffix()}.zip"
            downloaded = 0
            with httpx.stream("GET", url, follow_redirects=True, timeout=600) as resp:
                resp.raise_for_status()
                with open(archive, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if on_progress is not None:
                            try:
                                on_progress(downloaded, size)
                            except Exception:
                                pass
            extracted = _extract_binary(archive, Path(tmp) / "x")
            shutil.copy2(extracted, staged)

        (_arsenal_dir() / "version.txt").write_text(remote_version, encoding="utf-8")
        _replace_and_restart(staged)

        # Unreachable — satisfies type checker
        return {"installed": True, "version": remote_version, "error": None}

    except Exception as exc:
        return {"installed": False, "version": None, "error": str(exc)}


async def self_update_server_async(
    *,
    force: bool = False,
    version: Optional[str] = None,
    on_progress: Callable[[int, int], Awaitable[None]] | None = None,
) -> dict:
    """
    Async version. Downloads and stages the new binary, then schedules restart via
    call_later(0.5s) so the caller can flush its response before the process exits.
    Returns {"installed": True, "restarting": True} on success.
    """
    if not _is_frozen():
        return {"installed": False, "version": None, "error": "Cannot self-update: not running as a compiled binary."}

    try:
        from arsenal.version import get_version
        local_version: Optional[str] = get_version()
        if local_version == "unknown":
            local_version = None

        async with httpx.AsyncClient(timeout=30) as client:
            release = await _fetch_release_async(client, version)

        if release is None:
            msg = f"Release server-v{version} not found" if version else "No server release found on GitHub"
            return {"installed": False, "version": None, "error": msg}

        remote_version = release["tag_name"].removeprefix(_TAG_PREFIX)

        if not force and not _is_newer(remote_version, local_version):
            return {"installed": False, "version": local_version, "error": None}

        url, size = _resolve_asset(release, remote_version)

        new_name = "karn.new.exe" if sys.platform == "win32" else "karn.new"
        staged = _arsenal_dir() / new_name

        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / f"karn-arsenal-v{remote_version}-{_platform_suffix()}.zip"
            downloaded = 0
            async with httpx.AsyncClient(timeout=600, follow_redirects=True) as dl:
                async with dl.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with open(archive, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if on_progress is not None:
                                try:
                                    await on_progress(downloaded, size)
                                except Exception:
                                    pass
            extracted = await asyncio.to_thread(_extract_binary, archive, Path(tmp) / "x")
            await asyncio.to_thread(shutil.copy2, extracted, staged)

        await asyncio.to_thread(
            lambda: (_arsenal_dir() / "version.txt").write_text(remote_version, encoding="utf-8")
        )

        # Give the caller 0.5 s to flush its response, then restart
        loop = asyncio.get_event_loop()
        loop.call_later(0.5, lambda: _replace_and_restart(staged))
        return {"installed": True, "version": remote_version, "error": None, "restarting": True}

    except Exception as exc:
        return {"installed": False, "version": None, "error": str(exc)}
