"""Pull the latest headlines from every active RSS feed.

New articles (links we haven't stored yet) go to data/pending.json, where
cluster_news.py picks them up.

    python -m pipeline.fetch_news
"""
import re
from datetime import datetime, timezone

import feedparser

from pipeline.common import (
    ARTICLES_FILE, PENDING_FILE, active_sources, iso, is_http_url, load_json,
    now_utc, parse_date, save_json,
)

# Some outlets block anything that doesn't look like a browser.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# Busy outlets publish far more than this between two runs (8 hours), and
# anything we miss counts as "didn't cover it". Keep it generous.
PER_FEED_LIMIT = 50
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def find_image(entry):
    """media:content first, then an image enclosure, then the first <img> in the summary."""
    for media in entry.get("media_content", []) or []:
        url = media.get("url", "")
        if "image" in media.get("medium", "") or url.lower().split("?")[0].endswith(IMAGE_EXT):
            return url
    for media in entry.get("media_thumbnail", []) or []:
        if media.get("url"):
            return media["url"]
    for link in entry.get("links", []) or []:
        if link.get("rel") == "enclosure" and "image" in link.get("type", ""):
            return link.get("href", "")
    summary = entry.get("summary") or entry.get("description") or ""
    m = re.search(r"<img[^>]+src=[\"']([^\"'>]+)", summary)
    return m.group(1) if m else ""


def entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return parse_date(entry.get("published") or entry.get("updated")) or now_utc()


def parse_entry(entry, source):
    link = (entry.get("link") or "").strip()
    title = (entry.get("title") or "").strip()
    if not title or not is_http_url(link):
        return None
    image = find_image(entry).strip()
    return {
        "source": source["name"],
        "group": source["group"],
        "published": iso(entry_date(entry)),
        "title": title,
        "link": link,
        "image": image if is_http_url(image) else "",
    }


def main():
    store = load_json(ARTICLES_FILE, {"articles": []})
    known = {a["link"] for a in store["articles"]} | set(store.get("skipped", {}))
    sources = active_sources()
    print(f"Fetching {len(sources)} feeds...")

    fresh = []
    for source in sources:
        try:
            feed = feedparser.parse(source["url"], request_headers=HEADERS)
        except Exception as e:  # feedparser rarely raises, but a broken feed shouldn't stop the run
            print(f"[{source['name']}] error: {e}")
            continue
        if not feed.entries:
            print(f"[{source['name']}] empty or unreachable")
            continue

        count = 0
        for entry in feed.entries[:PER_FEED_LIMIT]:
            article = parse_entry(entry, source)
            if article and article["link"] not in known:
                known.add(article["link"])
                fresh.append(article)
                count += 1
        print(f"[{source['name']}] {count} new")

    save_json(PENDING_FILE, fresh)
    print(f"{len(fresh)} new articles written to {PENDING_FILE.name}")


if __name__ == "__main__":
    main()
