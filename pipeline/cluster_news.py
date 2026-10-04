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
    ARTICLES_FILE, PENDING_FILE, RETENTION_DAYS, TAGS, is_basket, iso,
    is_irrelevant, load_json, now_utc, parse_date, save_json, unique_slug,
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

# The prompt is in Turkish: the headlines are Turkish and the model groups
# them noticeably better this way.
PROMPT = """
Sen tarafsız ve titiz bir medya analistisin. Aşağıda Türk haber sitelerinden gelen başlıklar JSON listesi olarak verilmiştir.
Görevin, AYNI OLAYI anlatan başlıkları gruplamak. Bu gruplar, farklı yayın gruplarının aynı olayı ne kadar haberleştirdiğini
karşılaştırmak için kullanılacak; bu yüzden gruplama hatasız ve dengeli olmalı.

1) GRUP = TEK BİR SOMUT OLAY
- Bir grup; aynı aktörlerin, aynı yerde, aynı zaman diliminde yaşadığı tek bir gelişmeyi ve onun doğrudan devamını
  (açıklamalar, tepkiler, gözaltı → tutuklama gibi) kapsar.
- Sadece konusu benzer diye farklı olayları BİRLEŞTİRME. Yanlış örnekler: "Dış Politika Gelişmeleri", "Meclis Gündemi",
  "Terörle Mücadele ve Operasyonlar", "Ekonomi Haberleri". Farklı illerdeki farklı operasyonlar, farklı ülkelerle yapılan
  farklı görüşmeler AYRI gruplardır.
- Kontrol: Grubun özetini TEK bir somut olay cümlesiyle yazamıyorsan grubu böl.
- Tek başlıklı grup olabilir; zorla birleştirme.

2) GÜNDEM DIŞI HABERLER → "Ilgisiz"
Aşağıdakileri SADECE "Ilgisiz" adlı tek grupta topla ve etiket verme:
- Magazin, ünlüler, dizi/film, burç, yaşam tarzı, sağlık/diyet önerileri, tarifler, reklam ve ürün haberleri.
- Rutin hava durumu, sıradan trafik kazaları ve kamuoyu boyutu olmayan tekil adli olaylar. Buna tek bir
  yerel kadına/çocuğa şiddet vakası ve tek kişinin öldüğü bir iş kazası da dahildir.
- Spor: aşağıdaki istisnalar dışında TÜM spor haberleri (maç sonuçları, transfer, sakatlık, teknik direktör açıklamaları).
Şunlar ise toplumsal gündemdir, "Ilgisiz" SAYMA:
- Kadına/çocuğa şiddet ve iş cinayetlerinde kamuoyu boyutu olanlar: ülke çapında tepki ve protesto doğuran vakalar,
  mahkeme kararları ve cezalar (ör. iyi hal indirimi tartışması), kamu görevlisi veya kurum ihmali iddiası taşıyanlar,
  aylık/yıllık raporlar ve istatistikler (ör. Kadın Cinayetlerini Durduracağız Platformu, İSİG Meclisi), yasa ve politika değişiklikleri.
- Toplu ölümlü kazalar, maden kazaları, afetler, çevre felaketleri, gazetecilere yönelik gözaltı ve davalar.

3) SPOR İSTİSNASI (#Spor)
Spor haberini SADECE şu durumlarda grupla:
- Milli takımların resmi maçları ve büyük turnuvalar.
- Galatasaray, Fenerbahçe, Beşiktaş ve Trabzonspor'un kendi aralarındaki derbiler.
- Türk kulüplerinin Avrupa kupalarında tur atlama/elenme gibi sonuç belirleyen maçları.
- Sporun yargı, siyaset veya ekonomiyle kesiştiği olaylar (hakem/şike soruşturması, federasyon seçimi, kulüp borç krizi).

4) BAŞLIK: 'konu_basligi'
- Olayı anlatan, 3-8 kelimelik, somut bir başlık: aktör + olay (+ yer). Örnek: "Merkez Bankası Faizi Sabit Tuttu",
  "Adana'da 4,9 Büyüklüğünde Deprem". Kötü örnek: "Depremler", "Ekonomi Gelişmeleri".
- Grup aşağıdaki MEVCUT BAŞLIKLAR'dan biriyle AYNI olayı anlatıyorsa o başlığı harfi harfine AYNEN kullan; değilse yeni başlık yaz.
  Mevcut bir başlık birden fazla olayı kapsıyorsa onu KULLANMA.
  MEVCUT BAŞLIKLAR: {existing}

5) TARAFSIZ DİL
- Başlık ve özette hiçbir yayın grubunun yüklü dilini kullanma (örneğin "hain", "darbeci", "soykırımcı", "rejim", "yandaş",
  "faşist" gibi nitelemeler). Taraflardan birinin iddiasını gerçek gibi yazma; gerekiyorsa "… iddia etti / açıkladı" de.
- Kurum ve kişileri resmi adlarıyla an. Yorum, değerlendirme ve sıfat ekleme.

6) ÖZET VE ÇEVİRİ
- 'grup_ozeti': Olayın ne olduğunu anlatan, tek cümlelik, nesnel bir özet.
- 'konu_basligi_en' ve 'grup_ozeti_en': başlık ve özetin İngilizce çevirisi.

7) ETİKET
Her grup için SADECE aşağıdaki listeden en uygun 1-3 etiketi seç; liste dışında etiket KULLANMA:
{tags}

ÇIKTI: Sadece aşağıdaki biçimde bir JSON listesi döndür, başka metin yazma. Her haber id'si en fazla bir grupta yer alsın.
[
  {{
    "konu_basligi": "Konu Başlığı",
    "konu_basligi_en": "Story Title",
    "grup_ozeti": "Olayın tarafsız, tek cümlelik özeti.",
    "grup_ozeti_en": "One-sentence neutral summary of the event.",
    "etiketler": ["#etiket1", "#etiket2"],
    "haber_idleri": [0, 5, 12]
  }}
]

Haber listesi:
{headlines}
"""


def reusable_titles(store, now):
    """Recent story titles, most covered first, without buckets.

    Bucket titles aren't offered for reuse, otherwise they'd grow with every run.
    """
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
