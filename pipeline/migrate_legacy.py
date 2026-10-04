"""One-off import from the old Streamlit repo (exchangel/tarafsizlik2026).

Converts kaynaklar.json and analizli_haber_veriseti.csv into data/sources.json
and data/articles.json so the new site doesn't start empty.

    python -m pipeline.migrate_legacy path/to/tarafsizlik2026
"""
import csv
import json
import sys
from pathlib import Path

from pipeline.common import (
    ARTICLES_FILE, SOURCES_FILE, TAGS, iso, is_http_url, is_irrelevant,
    now_utc, parse_date, save_json, unique_slug,
)

OLD_GROUPS = {
    "Muhalif / Eleştirel": "opposition",
    "Merkez / Bağımsız": "independent",
    "Muhafazakar / İktidar Çizgisi": "progov",
}
OLD_STATUS = {"kaynakli": "sourced", "degerlendirme": "review", "tartismali": "disputed"}


def convert_evidence(items):
    return [{"name": d["ad"], "url": d["url"]} for d in items or []]


def convert_sources(old):
    return {
        "updated": old.get("guncelleme", ""),
        "sources": [
            {
                "name": k["ad"],
                "url": k["url"],
                "group": OLD_GROUPS[k["grup"]],
                "active": k.get("aktif", True),
                "reason": k.get("gerekce", ""),
                "evidence": convert_evidence(k.get("dayanak")),
                "status": OLD_STATUS.get(k.get("durum"), "review"),
            }
            for k in old["kaynaklar"]
        ],
        "removed": [
            {"name": k["ad"], "reason": k.get("neden", ""), "evidence": convert_evidence(k.get("dayanak"))}
            for k in old.get("cikarilanlar", [])
        ],
    }


def convert_articles(rows, group_of):
    stories, id_by_title, by_link = {}, {}, {}
    for row in rows:
        title = (row.get("Grup_Basligi") or "").strip()
        published = parse_date(row.get("Tarih"))
        link = (row.get("Link") or "").strip()
        if is_irrelevant(title) or not published or not is_http_url(link):
            continue
        story_id = id_by_title.get(title)
        if story_id is None:
            story_id = unique_slug(title, stories)
            id_by_title[title] = story_id
            summary = (row.get("Grup_Ozeti") or "").strip()
            tags = [t.strip() for t in (row.get("Etiketler") or "").split(",")]
            # Old data has no English versions; the UI falls back to Turkish.
            stories[story_id] = {
                "title_tr": title, "title_en": title,
                "summary_tr": summary, "summary_en": summary,
                "tags": [t for t in tags if t in TAGS][:3],
            }
        image = (row.get("Gorsel_URL") or "").strip()
        by_link[link] = {
            "source": row["Kaynak"],
            "group": group_of.get(row["Kaynak"]) or OLD_GROUPS.get(row.get("Gorus_Acisi"), "independent"),
            "published": iso(published),
            "title": (row.get("Baslik") or "").strip(),
            "link": link,
            "image": image if is_http_url(image) else "",
            "story": story_id,
        }
    articles = sorted(by_link.values(), key=lambda a: a["published"], reverse=True)
    return {"updated": iso(now_utc()), "stories": stories, "articles": articles, "skipped": {}}


def main(legacy_dir):
    legacy = Path(legacy_dir)
    with open(legacy / "kaynaklar.json", encoding="utf-8") as f:
        sources = convert_sources(json.load(f))
    group_of = {s["name"]: s["group"] for s in sources["sources"]}

    with open(legacy / "analizli_haber_veriseti.csv", encoding="utf-8-sig", newline="") as f:
        store = convert_articles(csv.DictReader(f), group_of)

    save_json(SOURCES_FILE, sources)
    save_json(ARTICLES_FILE, store)
    print(f"{len(sources['sources'])} sources, {len(store['articles'])} articles, "
          f"{len(store['stories'])} stories imported.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
