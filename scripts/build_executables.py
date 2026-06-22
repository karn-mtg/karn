import subprocess
import sys


def main() -> None:
    spec = "pyinstaller/karn.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", spec],
        check=True,
    )
    exe = "dist\\karn.exe" if sys.platform == "win32" else "dist/karn"
    print(f"Built: {exe}")


if __name__ == "__main__":
    main()
