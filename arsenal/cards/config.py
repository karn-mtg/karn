import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

BASE_DIR = Path(os.environ.get("KARN_DATA_DIR") or Path.home() / "karnData" / "arsenal" / "db").expanduser()
CHROMA_DIR = BASE_DIR / "chroma_db"
GRAPH_JSON_PATH = BASE_DIR / "graph.json"
PROGRESS_JSON_PATH  = BASE_DIR / "progress.json"
EMBEDDINGS_NPY_PATH = BASE_DIR / "embeddings.npy"
SCRYFALL_BULK_JSON = BASE_DIR / "scryfall_oracle.json"

SCRYFALL_BULK_API = "https://api.scryfall.com/bulk-data"
SCRYFALL_DEFAULT_CARDS_JSON = BASE_DIR / "scryfall_default_cards.json"
PRINTS_DB_PATH = BASE_DIR / "prints.db"

SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"

ALL_FORMATS = [
    "standard", "pioneer", "modern", "legacy", "vintage",
    "pauper", "commander", "brawl", "historic", "timeless",
    "alchemy", "explorer", "oathbreaker", "paupercommander",
    "duel", "oldschool", "premodern", "predh",
]
EMBED_BATCH_SIZE = 512       # sentence-transformers internal encode batch size
CHROMA_UPSERT_CHUNK = 5000  # cards per ChromaDB upsert call (fewer calls = less HNSW overhead)
CHROMA_COLLECTION = "mtg_cards"

MECHANIC_CLUSTERS: dict[str, list[str]] = {
    "ETB": [
        r"when(?:ever)?\s+\S+\s+enters",
        r"when(?:ever)?\s+.+\s+enters the battlefield",
    ],
    "Dies": [
        r"when(?:ever)?\s+.+\s+dies",
        r"when(?:ever)?\s+.+\s+is put into a graveyard from the battlefield",
    ],
    "Sacrifice": [
        r"sacrifice [^.:]+:",
        r"sacrifice a ",
        r"sacrifice another",
    ],
    "Blink": [
        r"exile [^\.]+ then return",
        r"exile [^\.]+ return it",
        r"exile [^\.]+ at the beginning",
    ],
    "Tokens": [
        r"create [^\.]+ token",
        r"put [^\.]+ token",
    ],
    "Ramp": [
        r"search your library for [^\.]+ land",
        r"add [^\.]+ mana",
        r"untap [^\.]+ land",
        r"adds? one mana",
    ],
    "Flying": [r"\bflying\b"],
    "Proliferate": [r"\bproliferate\b"],
    "Infect": [r"\binfect\b"],
    "Undying": [r"\bundying\b"],
    "Persist": [r"\bpersist\b"],
    "Graveyard": [
        r"from your graveyard",
        r"from a graveyard",
        r"\bdredge\b",
        r"\bflashback\b",
        r"\bescape\b",
        r"\breanimator\b",
        r"return [^\.]+ from your graveyard",
    ],
    "Counters": [
        r"\+1/\+1 counter",
        r"-1/-1 counter",
        r"put .+ counter",
    ],
    "Draw": [r"draw [^\.]+ card"],
    "Lifegain": [
        r"you gain [^\.]+ life",
        r"\blifelink\b",
        r"gain [^\.]+ life",
    ],
    "Mill": [
        r"\bmill\b",
        r"put the top [^\.]+ of [^\.]+ library into [^\.]+ graveyard",
    ],
    "Haste": [r"\bhaste\b"],
    "Trample": [r"\btrample\b"],
    "Deathtouch": [r"\bdeathtouch\b"],
    "Tribal": [],  # handled by subtype detection in classifier.py
}

ARCHETYPES: dict[str, list[str]] = {
    "Aggro": ["ETB", "Flying", "Tribal", "Haste", "Trample"],
    "Aristocrats": ["Dies", "Sacrifice", "Lifegain", "Tokens"],
    "Control": ["Draw", "Mill"],
    "Combo": ["Undying", "Persist", "Blink", "Infect", "Graveyard"],
    "Ramp": ["Ramp", "Counters"],
    "Tokens": ["Tokens", "Lifegain"],
    "Reanimator": ["Graveyard"],
    "Infect": ["Infect"],
    "Proliferate": ["Proliferate", "Counters"],
    "Spellslinger": ["Draw"],
    "Voltron": ["Counters", "Trample", "Haste", "Flying"],
}

TRIBE_SUBTYPES = {
    "Goblin", "Elf", "Zombie", "Vampire", "Dragon", "Merfolk", "Sliver",
    "Human", "Angel", "Demon", "Wizard", "Soldier", "Knight", "Rogue",
    "Warrior", "Cleric", "Shaman", "Druid", "Beast", "Cat", "Bird",
    "Snake", "Spider", "Elemental", "Spirit", "Horror", "Faerie",
    "Dwarf", "Giant", "Treefolk", "Dinosaur", "Pirate", "Rat",
}

COLOR_NAMES = {
    "W": "White",
    "U": "Blue",
    "B": "Black",
    "R": "Red",
    "G": "Green",
    "C": "Colorless",
    "M": "Multicolor",
}

TAGGER_TAG_TO_CLUSTER: dict[str, str] = {
    "mana rock":        "Ramp",
    "mana dork":        "Ramp",
    "sacrifice outlet": "Sacrifice",
    "card draw":        "Draw",
    "recursion":        "Graveyard",
    "reanimation":      "Graveyard",
    "flicker":          "Blink",
    "blink":            "Blink",
    "mill":             "Mill",
    "lifegain":         "Lifegain",
}
