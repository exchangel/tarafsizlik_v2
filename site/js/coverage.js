// Coverage math. No DOM in here so it can be tested with plain node.

export const GROUPS = ["opposition", "independent", "progov"];

// With only 1-2 outlets a story is always 0% / 100% somewhere, which would
// produce fake blindspots.
export const BLINDSPOT_MIN_SOURCES = 3;
export const BLINDSPOT_MAX_SHARE = 10;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Unique outlets per group. Five articles from one outlet still count once. */
export function sourceCounts(articles) {
  const sets = Object.fromEntries(GROUPS.map((g) => [g, new Set()]));
  for (const a of articles) sets[a.g]?.add(a.s);
  return Object.fromEntries(GROUPS.map((g) => [g, sets[g].size]));
}

/**
 * Groups have different numbers of outlets (e.g. 14 vs 10), so raw counts
 * would favour the bigger group. We take each group's share of its own outlets
 * first and then scale those shares to 100.
 */
export function coveragePercents(counts, groupSizes) {
  const ratios = GROUPS.map((g) => (groupSizes[g] ? Math.min(counts[g] / groupSizes[g], 1) : 0));
  const total = ratios.reduce((sum, r) => sum + r, 0);
  return Object.fromEntries(GROUPS.map((g, i) => [g, total > 0 ? (ratios[i] / total) * 100 : 0]));
}

/** A story plus the numbers the UI needs, computed for a given set of its articles. */
export function summarize(story, articles, groupSizes) {
  const counts = sourceCounts(articles);
  return {
    ...story,
    articles,
    counts,
    total: counts.opposition + counts.independent + counts.progov,
    percents: coveragePercents(counts, groupSizes),
    latest: Math.max(...articles.map((a) => Date.parse(a.d))),
  };
}

/**
 * Stories with at least one article in the last `days`, most covered first.
 * Catch-all groups ("basket") go to the end: their outlet count is inflated
 * by mixing unrelated events, so they'd always top the list otherwise.
 */
export function storiesInWindow(stories, days, groupSizes, now = Date.now()) {
  const cutoff = now - days * DAY_MS;
  const result = [];
  for (const story of stories) {
    const articles = story.articles.filter((a) => Date.parse(a.d) >= cutoff);
    if (articles.length) result.push(summarize(story, articles, groupSizes));
  }
  return result.sort(
    (a, b) => Boolean(a.basket) - Boolean(b.basket) || b.total - a.total || b.latest - a.latest
  );
}

/**
 * Stories one side barely covers. Shares are truncated to whole numbers
 * before comparing, same as the original Streamlit version.
 */
export function findBlindspots(stories) {
  const missedByOpposition = [];
  const missedByProgov = [];
  for (const story of stories) {
    if (story.basket || story.total < BLINDSPOT_MIN_SOURCES) continue;
    const opp = Math.trunc(story.percents.opposition);
    const ind = Math.trunc(story.percents.independent);
    const gov = Math.trunc(story.percents.progov);
    if (opp <= BLINDSPOT_MAX_SHARE && gov + ind > 20) {
      missedByOpposition.push({ story, share: opp });
    } else if (gov <= BLINDSPOT_MAX_SHARE && opp + ind > 20) {
      missedByProgov.push({ story, share: gov });
    }
  }
  return { missedByOpposition, missedByProgov };
}

/** Most used tags, weighted by how many outlets covered each story. */
export function topTags(stories, limit = 8) {
  const weight = new Map();
  for (const s of stories) {
    for (const tag of s.tags) weight.set(tag, (weight.get(tag) || 0) + s.total);
  }
  return [...weight.entries()].sort((a, b) => b[1] - a[1]).slice(0, limit).map(([tag]) => tag);
}
