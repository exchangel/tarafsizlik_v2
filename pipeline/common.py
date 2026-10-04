"""Shared paths, constants and small helpers for the pipeline scripts."""
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
BUILD_DIR = ROOT / "_site"

SOURCES_FILE = DATA_DIR / "sources.json"
ARTICLES_FILE = DATA_DIR / "articles.json"
PENDING_FILE = DATA_DIR / "pending.json"

# Order matters: the UI always shows opposition | independent | pro-gov.
GROUPS = ("opposition", "independent", "progov")

# Articles older than this are dropped from the store.
RETENTION_DAYS = 30

# Tags the model is allowed to use. Kept in Turkish because they're shown as-is
# in the TR interface; the frontend has the English names.
TAGS = [
    "#İçPolitika", "#DışPolitika", "#EkonomiVePiyasalar", "#EnflasyonVeGeçim",
    "#AdaletVeYargı", "#AnayasaVeMeclis", "#SeçimVePartiler", "#GüvenlikVeTerör",
    "#SavunmaSanayii", "#GöçVeSığınmacılar", "#Eğitim", "#Sağlık",
    "#KadınVeÇocukHakları", "#İnsanHaklarıVeHukuk", "#MedyaVeİfadeÖzgürlüğü",
    "#YerelYönetimler", "#ÇevreVeİklim", "#DepremVeAfet",
]

# Bucket names for off-topic articles. "İlgisiz".lower() keeps a combining dot,
# hence the second spelling.
IRRELEVANT = {"ilgisiz", "i̇lgisiz", "irrelevant", "grup yok"}


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data, compact=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        if compact:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")


def active_sources():
    data = load_json(SOURCES_FILE, {"sources": []})
    return [s for s in data["sources"] if s.get("active", True)]


def now_utc():
    return datetime.now(timezone.utc)


def parse_date(value):
    """Parse the date formats we see in feeds and old data. Returns aware UTC or None.

    RSS uses RFC 822 ("Sun, 04 Oct 2026 14:56:01 +0300"), Atom and our own
    store use ISO 8601. Naive values are treated as UTC.
    """
    if not value:
        return None
    text = str(value).strip()
    dt = None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(text)
        except (TypeError, ValueError, IndexError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
    "â": "a", "Â": "a", "î": "i", "Î": "i", "û": "u", "Û": "u",
})


def slugify(text, max_len=80):
    s = str(text).translate(_TR_MAP).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rsplit("-", 1)[0]
    return s or "story"


def unique_slug(title, taken):
    """Slug for title that isn't in `taken`; adds -2, -3 ... on collision."""
    base = slugify(title)
    slug, n = base, 2
    while slug in taken:
        slug = f"{base}-{n}"
        n += 1
    return slug


def is_http_url(value):
    return isinstance(value, str) and re.match(r"^https?://[^\s\"'<>]+$", value) is not None


def is_irrelevant(title):
    return not title or str(title).strip().lower() in IRRELEVANT
