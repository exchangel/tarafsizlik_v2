# Tarafsızlık Türkiye

Same news, three different presses. This site collects headlines from 36 Turkish news outlets, groups the ones about the same event, and shows how much each side of the media covered it: opposition, mainstream/independent, or pro-government.

**Live:** https://exchangel.github.io/tarafsizlik_v2/

<!-- screenshot: docs/screenshot.png -->

## Why

In Turkey the main media divide isn't left vs. right, it's how close an outlet is to the government. The same day can look very different depending on which papers you read. The site makes that visible:

- **Coverage bars** show which side reported on a story.
- **Blindspots** list stories that one side barely touched.
- **Side-by-side headlines** put the opposition, independent and pro-government headlines for one event next to each other.

Every story has its own link (`/s/<story-id>/`) with a proper preview when shared on WhatsApp, Telegram or X.

## How it works

```
RSS feeds ──> fetch_news.py ──> data/pending.json
                                      │
                                      v
                     cluster_news.py (Gemini) ──> data/articles.json   (committed, 30-day window)
                                                        │
                                                        v
                                   build_site.py ──> _site/  ──> GitHub Pages
                                                   ├── data/news.json
                                                   └── s/<id>/index.html (share pages)
```

1. **Fetch** (`pipeline/fetch_news.py`): reads every active feed from `data/sources.json`, skips links it has already seen, pulls out an image and normalizes dates to UTC.
2. **Cluster** (`pipeline/cluster_news.py`): sends only the headlines to Gemini and asks which ones describe the same event. Titles from the last three days are passed back to the model so a story keeps the same name, and with it the same URL, across runs. The prompt insists on one concrete event per group and spells out what counts as off-topic (gossip, routine sports) and what never does (violence against women, workplace deaths, disasters). Catch-all groups that slip through anyway ("foreign policy developments") are detected by checking how many headline pairs share a word stem; they're not offered for reuse, sit at the bottom of the list and never count as blindspots.
3. **Build** (`pipeline/build_site.py`): turns the store into a compact `news.json` and writes one small HTML page per story with Open Graph tags that redirects into the app.
4. **Frontend** (`site/`): plain HTML, CSS and JavaScript modules. No framework, no build step. Time windows, filters and blindspots are computed in the browser.

GitHub Actions runs steps 1 to 3 three times a day (`update.yml`) and deploys to Pages (`deploy.yml`). A weekly job (`check-feeds.yml`) checks that every feed is still reachable and fresh.

The only state is `data/articles.json` in the repo, so there's no server or database.

## How coverage is calculated

The groups don't have the same number of outlets (14 pro-government, 11 independent, 11 opposition right now). Counting articles would favour the biggest group, so for each story:

1. count **unique outlets** per group (five articles from one outlet count once),
2. divide by the group's size: the share of that group's outlets that covered it,
3. scale the three shares to 100%.

A story is a **blindspot** for a side if at least 3 outlets covered it, that side's share is 10% or less and the other two together are above 20%. This only reflects what shows up in RSS feeds. A blindspot doesn't prove an outlet ignored the story.

The logic lives in [`site/js/coverage.js`](site/js/coverage.js) and is tested in [`tests/coverage.test.mjs`](tests/coverage.test.mjs).

## Source classification

[`data/sources.json`](data/sources.json) lists each outlet with its group, a short reason and links to the evidence (Reuters Institute Digital News Report, Media Bias/Fact Check, Media Ownership Monitor, Wikipedia). Outlets without solid sources are marked "under review". Changing an outlet's group there also re-groups its older articles on the next build.

If you think a classification is wrong, open an issue with a source.

## Running it locally

Needs Python 3.10+.

```bash
pip install -r requirements.txt pytest

# build the site from the committed data and serve it
python -m pipeline.build_site
python -m http.server -d _site 8000
# -> http://localhost:8000
```

To run the full pipeline you need a [Gemini API key](https://aistudio.google.com/apikey):

```bash
python -m pipeline.fetch_news
GEMINI_API_KEY=... python -m pipeline.cluster_news
```

Tests:

```bash
python -m pytest
node --test tests/*.test.mjs   # Node 18+
```

## Running your own copy

1. Fork the repo.
2. *Settings → Secrets and variables → Actions*: add `GEMINI_API_KEY`.
3. *Settings → Pages*: set the source to **GitHub Actions**.
4. Run the *Update news* workflow once by hand, or wait for the schedule.

## Project layout

```
pipeline/       Python: fetch, cluster, build, feed check
data/           sources.json (classification), articles.json (30-day store)
site/           index.html, css/, js/, img/
tests/          pytest + node:test
.github/        the three workflows
```

## Limitations

- Only what outlets put in their RSS feeds is counted. Some publish everything, some only a selection.
- Grouping and the neutral summaries come from an LLM and are sometimes wrong. Occasionally two different events land in one group, or one event is split in two.
- Story summaries have English versions, but article headlines stay in Turkish.
- Images are loaded straight from the news sites; a few block that and show a placeholder.

## History

This started as a Streamlit app ([exchangel/tarafsizlik2026](https://github.com/exchangel/tarafsizlik2026)). It worked, but it went to sleep, re-ran on every visit and had no links to individual stories, which made it hard to share. This version is static and cheap to host, and sharing a story link is the main way people find it.

The first data in this repo was imported from the old project with `pipeline/migrate_legacy.py`.

## License

MIT. News headlines and images belong to their publishers.
