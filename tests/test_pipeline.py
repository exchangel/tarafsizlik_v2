import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from pipeline import build_site, cluster_news, fetch_news
from pipeline.common import parse_date, slugify, unique_slug, is_http_url, is_irrelevant

NOW = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)


def article(link, story=None, published="2026-10-04T18:00:00Z", source="Sözcü", group="opposition"):
    a = {"source": source, "group": group, "published": published, "title": f"Başlık {link}",
         "link": f"https://example.com/{link}", "image": ""}
    if story:
        a["story"] = story
    return a


# ---------- common ----------

@pytest.mark.parametrize("raw, expected", [
    ("Sun, 04 Oct 2026 14:56:01 +0300", "2026-10-04T11:56:01"),
    ("2026-10-04T14:56:01+03:00", "2026-10-04T11:56:01"),
    ("2026-10-04 14:56:01", "2026-10-04T14:56:01"),  # naive means UTC
    ("2026-10-04T11:56:01Z", "2026-10-04T11:56:01"),
])
def test_parse_date_formats(raw, expected):
    assert parse_date(raw).strftime("%Y-%m-%dT%H:%M:%S") == expected


def test_parse_date_garbage():
    assert parse_date("Hatalı Tarih") is None
    assert parse_date("") is None


def test_slugify_turkish():
    assert slugify("Ioanna Kuçuradi'nin Vefatı") == "ioanna-kucuradi-nin-vefati"
    assert slugify("İŞÇİ ÖĞÜN ÇAĞ") == "isci-ogun-cag"
    assert slugify("!!!") == "story"


def test_unique_slug_adds_suffix():
    taken = {"belediye-operasyonlari": 1, "belediye-operasyonlari-2": 1}
    assert unique_slug("Belediye Operasyonları", taken) == "belediye-operasyonlari-3"


def test_url_check_blocks_scripts():
    assert is_http_url("https://www.sabah.com.tr/a?b=1")
    assert not is_http_url("javascript:alert(1)")
    assert not is_http_url('https://x.com/"><script>')


def test_irrelevant_spellings():
    assert is_irrelevant("Ilgisiz")
    assert is_irrelevant("İlgisiz")
    assert not is_irrelevant("Merkez Bankası Faiz Kararı")


# ---------- fetch ----------

def test_find_image_order():
    entry = {"media_content": [{"url": "https://img/a.jpg"}], "summary": '<img src="https://img/b.jpg">'}
    assert fetch_news.find_image(entry) == "https://img/a.jpg"
    assert fetch_news.find_image({"summary": '<p><img alt="x" src="https://img/b.jpg"/></p>'}) == "https://img/b.jpg"
    enclosure = {"links": [{"rel": "enclosure", "type": "image/jpeg", "href": "https://img/c.jpg"}]}
    assert fetch_news.find_image(enclosure) == "https://img/c.jpg"
    assert fetch_news.find_image({}) == ""


def test_parse_entry_normalizes_date():
    entry = {"title": " Başlık ", "link": "https://a.com/1", "published": "Sun, 04 Oct 2026 14:56:01 +0300"}
    out = fetch_news.parse_entry(entry, {"name": "Sabah", "group": "progov"})
    assert out["published"] == "2026-10-04T11:56:01Z"
    assert out["title"] == "Başlık"


def test_parse_entry_skips_bad_links():
    entry = {"title": "x", "link": "javascript:void(0)"}
    assert fetch_news.parse_entry(entry, {"name": "Sabah", "group": "progov"}) is None


# ---------- cluster ----------

def test_parse_response_strips_fences():
    text = '```json\n[{"konu_basligi": "A", "haber_idleri": [0]}]\n```'
    assert cluster_news.parse_response(text) == [{"konu_basligi": "A", "haber_idleri": [0]}]


def test_parse_response_rejects_non_list():
    with pytest.raises(ValueError):
        cluster_news.parse_response('{"a": 1}')


def test_is_basket():
    same_event = [f"Adana'da deprem {i}" for i in range(8)]
    mixed = ["Netanyahu hamlesi", "Yemen ordusu duyurdu", "Fransa liseliler eylem",
             "İran petrol bakanı", "Gazze sınır kapısı", "Türk dünyası mesajı"]
    assert not cluster_news.is_basket(same_event)
    assert cluster_news.is_basket(mixed)
    assert not cluster_news.is_basket(mixed[:3])  # too few to judge


def test_merge_reuses_story_and_skips_irrelevant():
    store = {
        "stories": {"faiz-karari": {"title_tr": "Faiz Kararı", "title_en": "Rate decision",
                                    "summary_tr": "", "summary_en": "", "tags": []}},
        "articles": [article("old", story="faiz-karari")],
    }
    pending = [article("n0"), article("n1"), article("n2")]
    groups = [
        {"konu_basligi": "Faiz Kararı", "grup_ozeti": "Özet", "etiketler": ["#EkonomiVePiyasalar", "#Uydurma"],
         "haber_idleri": [0, 99, "1"]},
        {"konu_basligi": "Ilgisiz", "haber_idleri": [2]},
    ]
    new, matched = cluster_news.merge(store, pending, groups, NOW)

    assert matched == 1  # 99 is out of range, "1" isn't an int
    assert set(new["stories"]) == {"faiz-karari"}
    assert new["stories"]["faiz-karari"]["tags"] == ["#EkonomiVePiyasalar"]
    # Missing English falls back to Turkish
    assert new["stories"]["faiz-karari"]["summary_en"] == "Özet"
    assert {a["link"] for a in new["articles"]} == {"https://example.com/old", "https://example.com/n0"}
    # Unassigned links are remembered so they're not re-sent
    assert set(new["skipped"]) == {"https://example.com/n1", "https://example.com/n2"}


def test_merge_new_story_gets_unique_id():
    store = {"stories": {"deprem": {"title_tr": "Deprem!", "title_en": "", "summary_tr": "", "summary_en": "",
                                    "tags": []}},
             "articles": [article("a", story="deprem")]}
    groups = [{"konu_basligi": "Deprem", "haber_idleri": [0]}]
    new, _ = cluster_news.merge(store, [article("b")], groups, NOW)
    assert "deprem-2" in new["stories"]


def test_merge_drops_old_articles_and_empty_stories():
    old = (NOW - timedelta(days=31)).strftime("%Y-%m-%dT%H:%M:%SZ")
    store = {"stories": {"eski": {"title_tr": "Eski", "title_en": "", "summary_tr": "", "summary_en": "", "tags": []}},
             "articles": [article("x", story="eski", published=old)],
             "skipped": {"https://example.com/s": old}}
    new, _ = cluster_news.merge(store, [], [], NOW)
    assert new["articles"] == [] and new["stories"] == {} and new["skipped"] == {}


def test_merge_same_link_keeps_latest():
    store = {"stories": {"a": {"title_tr": "A", "title_en": "", "summary_tr": "", "summary_en": "", "tags": []}},
             "articles": [article("same", story="a")]}
    groups = [{"konu_basligi": "B", "haber_idleri": [0]}]
    new, _ = cluster_news.merge(store, [article("same")], groups, NOW)
    assert [a["story"] for a in new["articles"]] == ["b"]
    assert set(new["stories"]) == {"b"}


def test_reusable_titles_skips_baskets_and_old():
    articles = [article(f"d{i}", story="deprem", source=f"S{i}") for i in range(6)]
    for a, t in zip(articles, ["Adana deprem 1", "Adana deprem 2", "Adana deprem 3",
                               "Adana deprem 4", "Adana deprem 5", "Adana deprem 6"]):
        a["title"] = t
    mixed = [article(f"m{i}", story="sepet") for i in range(6)]
    for a, t in zip(mixed, ["Netanyahu hamlesi", "Yemen ordusu", "Fransa liseliler",
                            "İran petrol", "Gazze sınırı", "Türk dünyası"]):
        a["title"] = t
    stale = article("o", story="eski", published="2026-09-20T00:00:00Z")
    store = {"stories": {"deprem": {"title_tr": "Adana Depremi"}, "sepet": {"title_tr": "Diplomasi"},
                         "eski": {"title_tr": "Eski"}},
             "articles": articles + mixed + [stale]}
    assert cluster_news.reusable_titles(store, NOW) == ["Adana Depremi"]


def test_prompt_contains_headlines_and_tags():
    prompt = cluster_news.build_prompt([article("x")], ["Faiz Kararı"])
    assert '"baslik": "Başlık x"' in prompt
    assert "#DepremVeAfet" in prompt and "Faiz Kararı" in prompt


# ---------- build ----------

SOURCES = [
    {"name": "Sözcü", "group": "opposition", "active": True},
    {"name": "Sabah", "group": "progov", "active": True},
    {"name": "NTV", "group": "independent", "active": True},
    {"name": "Old", "group": "progov", "active": False},
]


def test_build_news_shape():
    store = {
        "stories": {"s": {"title_tr": "Başlık", "title_en": "", "summary_tr": "Özet", "summary_en": "", "tags": ["#Eğitim"]}},
        "articles": [article("1", story="s"), {**article("2", story="s", source="NTV", group="progov"), "image": "https://i/x.jpg"}],
    }
    news = build_site.build_news(store, SOURCES)
    assert news["group_sizes"] == {"opposition": 1, "independent": 1, "progov": 1}
    story = news["stories"][0]
    assert story["title"] == {"tr": "Başlık", "en": "Başlık"}
    assert story["image"] == "https://i/x.jpg"
    # Group comes from sources.json, not from what was stored with the article
    assert [a["g"] for a in story["articles"]] == ["opposition", "independent"]
    assert set(story["articles"][0]) == {"s", "g", "t", "l", "d"}


def test_share_page_escapes_and_redirects():
    story = {"id": "a-b", "title": {"tr": 'X "<script>'}, "summary": {"tr": "Özet & más"}, "image": ""}
    page = build_site.share_page(story, "https://u.github.io/repo/")
    assert "<script>\"" not in page and "&lt;script&gt;" in page
    assert 'content="https://u.github.io/repo/s/a-b/"' in page
    assert 'content="https://u.github.io/repo/img/og-default.png"' in page
    assert 'location.replace("../../#/s/a-b")' in page


def test_build_writes_site(tmp_path, monkeypatch):
    site = tmp_path / "site"
    (site / "js").mkdir(parents=True)
    (site / "index.html").write_text("<!doctype html>")
    data = tmp_path / "data"
    data.mkdir()
    (data / "sources.json").write_text(json.dumps({"updated": "", "sources": SOURCES, "removed": []}))
    (data / "articles.json").write_text(json.dumps({
        "stories": {"s": {"title_tr": "T", "summary_tr": "", "tags": []}},
        "articles": [article("1", story="s")],
    }))
    monkeypatch.setattr(build_site, "SITE_DIR", site)
    monkeypatch.setattr(build_site, "BUILD_DIR", tmp_path / "_site")
    monkeypatch.setattr(build_site, "ARTICLES_FILE", data / "articles.json")
    monkeypatch.setattr(build_site, "SOURCES_FILE", data / "sources.json")
    build_site.main()
    out = tmp_path / "_site"
    assert (out / "index.html").exists() and (out / ".nojekyll").exists()
    assert (out / "s" / "s" / "index.html").exists()
    assert json.loads((out / "data" / "news.json").read_text(encoding="utf-8"))["stories"][0]["id"] == "s"
