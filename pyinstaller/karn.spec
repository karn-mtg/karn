# pyinstaller/karn.spec
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / "arsenal" / "server.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "arsenal" / "rules" / "chunks"), "arsenal/rules/chunks"),
        (str(ROOT / "arsenal" / "rules" / "data" / "rules.json"), "arsenal/rules/data"),
        (str(ROOT / "arsenal" / "rules" / "data" / "glossary.json"), "arsenal/rules/data"),
        (str(ROOT / "arsenal" / "rules" / "data" / "keyword_index.json"), "arsenal/rules/data"),
        (str(ROOT / "arsenal" / "rules" / "data" / "rules_summary.md"), "arsenal/rules/data"),
        (str(ROOT / "arsenal" / "rules" / "data" / "glossary_extra.md"), "arsenal/rules/data"),
        (str(ROOT / "arsenal" / "cards" / "combos.json"), "arsenal/cards"),
        (str(ROOT / "arsenal" / "cards" / "data"), "arsenal/cards/data"),
        (str(ROOT / "version.txt"), "."),
    ],
    hiddenimports=[
        "mcp",
        "mcp.server.fastmcp",
        "sentence_transformers",
        "sentence_transformers.models",
        "chromadb",
        "chromadb.db.impl.sqlite",
        "networkx",
        "networkx.algorithms",
        "fastapi",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.protocols.http.h11_impl",
    ],
    excludes=[
        "torch.distributed",
        "torchvision",
        "torchaudio",
        "IPython",
        "jupyter",
        "matplotlib",
        "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="karn",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
