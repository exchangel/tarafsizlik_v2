"""Build the static site into _site/.

Copies site/, writes the compact data files the frontend loads, and creates a
small page per story (s/<id>/) carrying Open Graph tags, so links shared on
WhatsApp, Telegram etc. get a proper preview.

    SITE_URL=https://user.github.io/repo/ python -m pipeline.build_site
"""
from html import escape as esc
import os
import shutil
from collections import Counter

from pipeline.common import (
    ARTICLES_FILE, BUILD_DIR, GROUPS, SITE_DIR, SOURCES_FILE, is_basket, iso,
    load_json, now_utc, save_json,
)

SITE_NAME = "Tarafsızlık Türkiye"

SHARE_PAGE = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<meta name="description" content="{summary}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary}">
<meta property="og:image" content="{image}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace({target_js});</script>
</head>
<body><a href="{target}">{title}</a></body>
</html>
"""


def story_image(articles):
    for a in articles:
        if a["image"]:
            return a["image"]
    return ""


def build_news(store, sources):
    """Shape the store into what the frontend needs, with short keys to keep it small."""
    group_sizes = Counter(s["group"] for s in sources if s.get("active", True))
    group_of = {s["name"]: s["group"] for s in sources}

    by_story = {}
    for a in store["articles"]:
        by_story.setdefault(a["story"], []).append(a)

    stories = []
    for story_id, articles in by_story.items():
        meta = store["stories"].get(story_id)
        if not meta:
            continue
        stories.append({
            "id": story_id,
            "title": {"tr": meta["title_tr"], "en": meta.get("title_en") or meta["title_tr"]},
            "summary": {"tr": meta["summary_tr"], "en": meta.get("summary_en") or meta["summary_tr"]},
            "tags": meta.get("tags", []),
            "image": story_image(articles),
            # Catch-all groups the model shouldn't have made; the UI pushes them down.
            "basket": is_basket(a["title"] for a in articles),
            # Classification comes from sources.json, so re-grouping an outlet
            # also moves its older articles.
            "articles": [
                {"s": a["source"], "g": group_of.get(a["source"], a["group"]),
                 "t": a["title"], "l": a["link"], "d": a["published"]}
                for a in articles
            ],
        })

    return {
        "generated_at": iso(now_utc()),
        "data_updated": store.get("updated", ""),
        "group_sizes": {g: group_sizes.get(g, 0) for g in GROUPS},
        "stories": stories,
    }


def share_page(story, site_url):
    story_id = story["id"]
    target = f"../../#/s/{story_id}"
    url = f"{site_url}s/{story_id}/" if site_url else "./"
    image = story["image"] or (f"{site_url}img/og-default.png" if site_url else "../../img/og-default.png")
    return SHARE_PAGE.format(
        site=esc(SITE_NAME),
        title=esc(story["title"]["tr"]),
        summary=esc(story["summary"]["tr"]),
        image=esc(image),
        url=esc(url),
        target=esc(target),
        target_js=f'"{target}"',  # id is a slug, nothing to escape
    )


def main():
    site_url = os.environ.get("SITE_URL", "").strip()
    if site_url and not site_url.endswith("/"):
        site_url += "/"

    store = load_json(ARTICLES_FILE, {"stories": {}, "articles": []})
    sources = load_json(SOURCES_FILE)

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    shutil.copytree(SITE_DIR, BUILD_DIR)

    news = build_news(store, sources["sources"])
    save_json(BUILD_DIR / "data" / "news.json", news, compact=True)
    save_json(BUILD_DIR / "data" / "sources.json", sources, compact=True)

    for story in news["stories"]:
        page = BUILD_DIR / "s" / story["id"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(share_page(story, site_url), encoding="utf-8")

    # Pages would otherwise run Jekyll and skip some files.
    (BUILD_DIR / ".nojekyll").touch()
    print(f"Built {len(news['stories'])} stories into {BUILD_DIR}")


if __name__ == "__main__":
    main()
