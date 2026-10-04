"""Group pending articles into stories with Gemini and merge them into the store.

Reads data/pending.json, asks the model which headlines describe the same event,
then writes the result into data/articles.json (30-day rolling window).

    GEMINI_API_KEY=... python -m pipeline.cluster_news
"""
import json
import os
import re
import sys
import time
from datetime import timedelta

from pipeline.common import (
    ARTICLES_FILE, PENDING_FILE, RETENTION_DAYS, TAGS, iso, is_irrelevant,
    load_json, now_utc, parse_date, save_json, unique_slug,
)

# Tried in order until one answers.
MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
]

# How far back we look for story titles the model should reuse.
REUSE_WINDOW_DAYS = 3
MAX_REUSE_TITLES = 60

# The prompt stays in Turkish: the headlines are Turkish and the model groups
# them noticeably better this way.
PROMPT = """
Sen tarafsiz ve profesyonel bir medya analistisin. Asagida Turkiye gundemine ait haber basliklari JSON formatinda verilmistir.

GOREVLERIN:
1. AYNI siyasi, ekonomik, hukuki veya toplumsal olayi/gelismeyi anlatan haberleri tek bir grupta birlestir.
2. Magazin, kedi-kopek, basit trafik kazalari, hava durumu gibi ulusal gundemle ilgisi olmayan 3. sayfa haberlerini SADECE "Ilgisiz" adli tek bir grupta topla. Bunlara etiket atama.
3. Her gecerli grup icin nesnel, tarafsiz ve profesyonel bir 'konu_basligi' belirle (Ornek: 'Merkez Bankasi Politika Faizi Karari', 'Anayasa Mahkemesi Karari').
   Grup asagidaki MEVCUT BASLIKLAR'dan biriyle AYNI olayi anlatiyorsa o basligi harfi harfine AYNEN kullan; yeni olaysa yeni baslik yaz.
   'Dis Politika Gelismeleri' veya 'Meclis Gundemi' gibi farkli olaylari toplayan genel/sepet basliklar KULLANMA; her grup tek bir somut olay olmali.
   MEVCUT BASLIKLAR: {existing}
4. Her grup icin bu olayin tam olarak ne oldugunu anlatan nesnel, tarafsiz ve tek cumlelik kisa bir 'grup_ozeti' yaz.
5. 'konu_basligi' ve 'grup_ozeti' alanlarinin Ingilizce cevirisini 'konu_basligi_en' ve 'grup_ozeti_en' alanlarina yaz.
6. Her grup icin SADECE asagidaki listeden en uygun 1, 2 veya 3 etiketi sec. Bu liste disindan ASLA baska etiket kullanma:
{tags}

CIKTI FORMATI:
SADECE asagidaki JSON formatinda cikti ver. Ekstra aciklama metni yazma:
[
  {{
    "konu_basligi": "Konu Adi",
    "konu_basligi_en": "Topic Name",
    "grup_ozeti": "Olayin tarafsiz ve 1 cumlelik ozeti.",
    "grup_ozeti_en": "One-sentence neutral summary of the event.",
    "etiketler": ["#etiket1", "#etiket2"],
    "haber_idleri": [0, 5, 12]
  }}
]

Haber Listesi:
{headlines}
"""


def _words(text):
    return {w for w in re.findall(r"\w+", str(text).lower()) if len(w) > 3}


def is_basket(headlines):
    """True if a story looks like a catch-all bucket rather than one event.

    In a real story most headline pairs share at least one meaningful word.
    Buckets like "Uluslararası Diplomasi" mix unrelated events, so the share
    drops sharply. We don't feed those titles back to the model, otherwise
    they'd grow with every run.
    """
    sets = [_words(h) for h in headlines]
    if len(sets) < 6:
        return False
    pairs = [(a, b) for i, a in enumerate(sets) for b in sets[i + 1:]]
    shared = sum(1 for a, b in pairs if a & b) / len(pairs)
    return shared < 0.2


def reusable_titles(store, now):
    """Recent story titles, most covered first, without buckets."""
    cutoff = now - timedelta(days=REUSE_WINDOW_DAYS)
    by_story = {}
    for a in store["articles"]:
        published = parse_date(a["published"])
        if published and published >= cutoff:
            by_story.setdefault(a["story"], []).append(a["title"])
    ranked = sorted(by_story.items(), key=lambda kv: len(kv[1]), reverse=True)
    titles = []
    for story_id, headlines in ranked:
        story = store["stories"].get(story_id)
        if story and not is_basket(headlines):
            titles.append(story["title_tr"])
    return titles[:MAX_REUSE_TITLES]


def build_prompt(pending, existing_titles):
    headlines = [{"id": i, "baslik": a["title"]} for i, a in enumerate(pending)]
    return PROMPT.format(
        existing=json.dumps(existing_titles, ensure_ascii=False),
        tags=json.dumps(TAGS, ensure_ascii=False),
        headlines=json.dumps(headlines, ensure_ascii=False),
    )


def parse_response(text):
    """Model output -> list of groups. Strips ```json fences if the model adds them."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    groups = json.loads(cleaned)
    if not isinstance(groups, list):
        raise ValueError("expected a JSON list")
    return groups


def merge(store, pending, groups, now):
    """Attach pending articles to stories and fold them into the store.

    Returns the new store and the number of articles that got a story.
    """
    stories = dict(store["stories"])
    id_by_title = {s["title_tr"]: sid for sid, s in stories.items()}
    added = []

    for group in groups:
        title = str(group.get("konu_basligi", "")).strip()
        if is_irrelevant(title):
            continue
        story_id = id_by_title.get(title) or unique_slug(title, stories)
        id_by_title[title] = story_id
        summary = str(group.get("grup_ozeti", "")).strip()
        stories[story_id] = {
            "title_tr": title,
            "title_en": str(group.get("konu_basligi_en", "")).strip() or title,
            "summary_tr": summary,
            "summary_en": str(group.get("grup_ozeti_en", "")).strip() or summary,
            "tags": [t for t in group.get("etiketler", []) if t in TAGS][:3],
        }
        for idx in group.get("haber_idleri", []):
            if isinstance(idx, int) and 0 <= idx < len(pending):
                added.append({**pending[idx], "story": story_id})

    # Same link analysed again -> keep the newest version.
    by_link = {a["link"]: a for a in store["articles"]}
    for a in added:
        by_link[a["link"]] = a

    cutoff = now - timedelta(days=RETENTION_DAYS)

    def recent(published):
        return (parse_date(published) or now) >= cutoff

    articles = [a for a in by_link.values() if recent(a["published"])]
    articles.sort(key=lambda a: a["published"], reverse=True)

    # Off-topic links are remembered too, so fetch_news doesn't send them
    # to the model again on every run while they're still in the feed.
    assigned = {a["link"] for a in added}
    skipped = dict(store.get("skipped", {}))
    skipped.update({a["link"]: a["published"] for a in pending if a["link"] not in assigned})
    skipped = {link: p for link, p in skipped.items() if link not in by_link and recent(p)}

    used = {a["story"] for a in articles}
    stories = {sid: s for sid, s in stories.items() if sid in used}
    new_store = {"updated": iso(now), "stories": stories, "articles": articles, "skipped": skipped}
    return new_store, len(added)


def ask_model(prompt):
    from google import genai  # imported here so tests don't need the SDK

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    for model in MODELS:
        try:
            print(f"Trying {model}...")
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            if response.text:
                return response.text
        except Exception as e:
            print(f"{model} failed: {e}")
            time.sleep(2)
    return None


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set")

    store = load_json(ARTICLES_FILE, {"stories": {}, "articles": []})
    pending = load_json(PENDING_FILE, [])
    now = now_utc()

    if not pending:
        print("Nothing new to cluster, only pruning old articles.")
        store, _ = merge(store, [], [], now)
        save_json(ARTICLES_FILE, store)
        return

    print(f"Clustering {len(pending)} headlines...")
    text = ask_model(build_prompt(pending, reusable_titles(store, now)))
    if not text:
        sys.exit("No model answered. Check the API key and quota.")

    try:
        groups = parse_response(text)
    except (json.JSONDecodeError, ValueError) as e:
        print(text)
        sys.exit(f"Could not parse model output: {e}")

    store, matched = merge(store, pending, groups, now)
    save_json(ARTICLES_FILE, store)
    save_json(PENDING_FILE, [])
    print(f"{matched} of {len(pending)} articles assigned. "
          f"Store: {len(store['articles'])} articles in {len(store['stories'])} stories.")


if __name__ == "__main__":
    main()
