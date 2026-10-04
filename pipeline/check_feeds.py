"""Check that every feed is reachable from GitHub's runners and still fresh.

Also tries a few candidate outlets, so adding a new source starts from a
working URL. The report ends up in the Actions run summary.

    python -m pipeline.check_feeds
"""
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import feedparser
import requests

from pipeline.common import active_sources

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
}

# A feed with no new item for this long gets flagged.
STALE_HOURS = 48

# Candidate outlets: homepage plus guessed feed URLs, first one that works wins.
# The homepage is scanned for <link rel="alternate" type="application/rss+xml">.
CANDIDATES = {
    "T24": ["https://t24.com.tr", "https://t24.com.tr/rss/haber/gundem", "https://t24.com.tr/rss/haber/son-dakika"],
    "Gazete Oksijen": ["https://gazeteoksijen.com", "https://gazeteoksijen.com/rss.xml", "https://gazeteoksijen.com/feed"],
    "ANKA Haber Ajansı": ["https://ankahaber.net", "https://ankahaber.net/rss.xml", "https://ankahaber.net/feed"],
    "Nefes": ["https://www.nefes.com.tr", "https://www.nefes.com.tr/rss.xml", "https://www.nefes.com.tr/feed"],
    "Türkiye Gazetesi": ["https://www.turkiyegazetesi.com.tr/rss/son-dakika-haberleri"],
    "Haber7": ["https://i12.haber7.net/sondakika/newsstand/latest.xml"],
    "Takvim": ["https://www.takvim.com.tr/rss/anasayfa"],
    "TGRT Haber": ["https://www.tgrthaber.com/rss/manset"],
}


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return r.status_code, r.content
    except requests.RequestException as e:
        return type(e).__name__, b""


def find_feed_link(page, base):
    """Look for an RSS/Atom link on an HTML page."""
    text = page.decode("utf-8", errors="ignore")
    for tag in re.findall(r"<link\b[^>]*>", text, re.I):
        if re.search(r"application/(rss|atom)\+xml", tag, re.I):
            href = re.search(r"href\s*=\s*[\"']([^\"']+)", tag, re.I)
            if href:
                return urljoin(base, href.group(1))
    # No <link>, try the first thing that looks like a feed URL.
    href = re.search(r"href\s*=\s*[\"']([^\"']*(?:/rss|/feed|\.rss|rss\.xml)[^\"']*)", text, re.I)
    return urljoin(base, href.group(1)) if href else None


def check(url, follow=True):
    status, body = fetch(url)
    if status != 200:
        return {"url": url, "status": f"HTTP {status}" if isinstance(status, int) else f"connection error ({status})"}

    feed = feedparser.parse(body)
    if not feed.entries:
        if follow and b"<html" in body[:2000].lower():
            found = find_feed_link(body, url)
            if found and found != url:
                return check(found, follow=False)
            return {"url": url, "status": "HTML, no feed"}
        return {"url": url, "status": "empty feed"}

    now = datetime.now(timezone.utc)
    dates = [datetime(*t[:6], tzinfo=timezone.utc)
             for e in feed.entries if (t := e.get("published_parsed") or e.get("updated_parsed"))]
    newest = max(dates) if dates else None
    with_image = sum(1 for e in feed.entries if e.get("media_content") or e.get("enclosures"))
    return {
        "url": url,
        "status": "OK",
        "items": len(feed.entries),
        "last_24h": sum(1 for d in dates if (now - d).total_seconds() < 86400),
        "hours_since_last": round((now - newest).total_seconds() / 3600, 1) if newest else None,
        "images": f"{with_image}/{len(feed.entries)}",
    }


def row(name, group, r):
    return (f"| {name} | {group} | {r['status']} | {r.get('items', '')} | {r.get('last_24h', '')} | "
            f"{r.get('hours_since_last', '')} | {r.get('images', '')} | {r['url']} |")


def main():
    header = ("| Source | Group | Status | Items | Last 24h | Hours since last | With image | URL |\n"
              "|---|---|---|---|---|---|---|---|")
    lines = ["## Current sources", header]
    broken = 0
    for source in active_sources():
        r = check(source["url"])
        name = source["name"]
        if r["status"] != "OK" or (r.get("hours_since_last") or 0) > STALE_HOURS:
            broken += 1
            name = f"**{name}** ⚠️"
        lines.append(row(name, source["group"], r))
        time.sleep(0.5)

    lines += ["", "## Candidates", header]
    for name, urls in CANDIDATES.items():
        for url in urls:
            r = check(url)
            if r["status"] == "OK":
                break
        lines.append(row(name, "candidate", r))
        time.sleep(0.5)

    report = "\n".join([
        f"# Feed check ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)",
        f"Sources with problems: **{broken}**",
        "",
        *lines,
    ])
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(report + "\n")


if __name__ == "__main__":
    main()
