"""Copy built executable to ~/karnData/arsenal/ for local karnforge dev."""
import shutil
import subprocess
import sys
import time
from pathlib import Path

NAMES_TO_KILL = ["karn-cards", "karn-rules", "karn"]
KARNFORGE_TITLE = "Karn Forge"


def _kill_processes() -> None:
    for name in NAMES_TO_KILL:
        subprocess.run(
            ["powershell", "-Command", f"Stop-Process -Name {name} -Force -ErrorAction SilentlyContinue"],
            check=False, capture_output=True,
        )
    subprocess.run(
        ["powershell", "-Command",
         f"Get-Process electron -ErrorAction SilentlyContinue "
         f"| Where-Object {{ $_.MainWindowTitle -eq '{KARNFORGE_TITLE}' }} "
         f"| Stop-Process -Force"],
        check=False, capture_output=True,
    )


def _copy_with_retry(src: Path, dst: Path, retries: int = 3, delay: float = 1.0) -> None:
    for attempt in range(retries):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError as e:
            if attempt < retries - 1:
                print(f"  Locked: {dst.name} — retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Could not copy {src.name}: {e}") from e


def main() -> None:
    src = Path("dist")
    dst_root = Path.home() / "karnData" / "arsenal"

    print("Stopping running karn processes...")
    _kill_processes()
    time.sleep(1.0)

    dst_root.mkdir(parents=True, exist_ok=True)

    # Single binary: karn or karn.exe
    ext = ".exe" if sys.platform == "win32" else ""
    exe_name = f"karn{ext}"
    exe_path = src / exe_name

    for f in [exe_path, Path("version.txt")]:
        if not f.exists():
            print(f"  Skipping {f.name} (not found)")
            continue
        print(f"  Copying {f.name}...")
        _copy_with_retry(f, dst_root / f.name)

    print(f"Installed to {dst_root}")


if __name__ == "__main__":
    main()
