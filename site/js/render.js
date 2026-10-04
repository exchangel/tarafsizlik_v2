// Functions that turn data into HTML strings. Everything from the data goes through esc().

import { GROUPS } from "./coverage.js";
import { GROUP_LABEL, GROUP_SHORT, TAGS_EN, TEXT } from "./i18n.js";
import { esc, percent, safeUrl, timeAgo } from "./util.js";

export function coverageBar(story, lang) {
  const label = GROUPS.map((g) => `${GROUP_SHORT[lang][g]} ${percent(story.percents[g], lang)}`).join(", ");
  const segments = GROUPS.map(
    (g) => `<span class="seg ${g}" style="width:${story.percents[g].toFixed(2)}%" title="${esc(
      `${GROUP_SHORT[lang][g]}: ${percent(story.percents[g], lang)}`
    )}"></span>`
  ).join("");
  return `<div class="bar" role="img" aria-label="${esc(label)}">${segments}</div>`;
}

function image(url, className) {
  const src = safeUrl(url) || "img/placeholder.svg";
  return `<div class="${className}"><img src="${esc(src)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer"></div>`;
}

function meta(story, lang) {
  return `<span class="story-meta">${esc(TEXT[lang].sources(story.total))} · ${esc(timeAgo(new Date(story.latest).toISOString(), lang))}</span>`;
}

export const tagLabel = (tag, lang) => (lang === "en" && TAGS_EN[tag]) || tag;

const href = (story) => `#/s/${encodeURIComponent(story.id)}`;

export function storyCard(story, lang) {
  return `<a class="card" href="${href(story)}">
    ${image(story.image, "card-img")}
    <div class="card-body">
      <h3>${esc(story.title[lang])}</h3>
      ${coverageBar(story, lang)}
      ${meta(story, lang)}
    </div>
  </a>`;
}

export function storyRow(story, lang) {
  return `<a class="row" href="${href(story)}">
    <div class="row-body">
      <h3>${esc(story.title[lang])}</h3>
      ${coverageBar(story, lang)}
      ${meta(story, lang)}
    </div>
    ${image(story.image, "row-img")}
  </a>`;
}

function blindspotItem({ story, share }, group, lang, withImage) {
  const label = group === "opposition" ? TEXT[lang].oppCoverage : TEXT[lang].progovCoverage;
  return `<a class="blind-item" href="${href(story)}">
    ${withImage ? image(story.image, "blind-img") : ""}
    <h4>${esc(story.title[lang])}</h4>
    ${coverageBar(story, lang)}
    <span class="blind-share ${group}">${esc(percent(share, lang))} ${esc(label)}</span>
  </a>`;
}

export function blindspotList(items, group, lang) {
  const t = TEXT[lang];
  const heading = group === "opposition" ? t.missedByOpposition : t.missedByProgov;
  const emptyText = group === "opposition" ? t.noOppMiss : t.noProgovMiss;

  let body;
  if (!items.length) {
    body = `<p class="empty small">${esc(emptyText)}</p>`;
  } else {
    body = items.slice(0, 2).map((item, i) => blindspotItem(item, group, lang, i === 0)).join("");
    const rest = items.slice(2);
    if (rest.length) {
      body += `<details class="more">
        <summary>${esc(t.moreBlindspots)} (+${rest.length})</summary>
        ${rest.map((item) => blindspotItem(item, group, lang, false)).join("")}
      </details>`;
    }
  }
  return `<section class="blind-group"><h3 class="blind-title ${group}">${esc(heading)}</h3>${body}</section>`;
}

function articleItem(a, lang) {
  const link = safeUrl(a.l);
  const inner = `<span class="src">${esc(a.s)}</span>
    <span class="hl">${esc(a.t)}</span>
    <time datetime="${esc(a.d)}">${esc(timeAgo(a.d, lang))}</time>`;
  return link
    ? `<li><a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${inner}</a></li>`
    : `<li><div>${inner}</div></li>`;
}

/** The story dialog: summary, coverage and the three columns of headlines. */
export function storyView(story, windowLabel, activeGroup, lang) {
  const t = TEXT[lang];
  const byGroup = Object.fromEntries(GROUPS.map((g) => [g, []]));
  for (const a of [...story.articles].sort((x, y) => Date.parse(y.d) - Date.parse(x.d))) {
    byGroup[a.g]?.push(a);
  }

  const legend = GROUPS.map(
    (g) => `<li class="${g}"><span class="dot"></span>${esc(GROUP_LABEL[lang][g])}
      <b>${esc(percent(story.percents[g], lang))}</b>
      <small>${esc(t.sources(story.counts[g]))}</small></li>`
  ).join("");

  const tabs = GROUPS.map(
    (g) => `<button type="button" role="tab" class="${g}" data-group="${g}"
      aria-selected="${g === activeGroup}">${esc(GROUP_SHORT[lang][g])} <small>${byGroup[g].length}</small></button>`
  ).join("");

  const columns = GROUPS.map(
    (g) => `<section class="col ${g}${g === activeGroup ? " active" : ""}" data-group="${g}">
      <h4><span class="dot"></span>${esc(GROUP_LABEL[lang][g])} <small>${esc(t.articles(byGroup[g].length))}</small></h4>
      ${byGroup[g].length
        ? `<ul>${byGroup[g].map((a) => articleItem(a, lang)).join("")}</ul>`
        : `<p class="empty small">${esc(t.noArticles)}</p>`}
    </section>`
  ).join("");

  const tags = story.tags.length ? `<span class="tags">${story.tags.map((tag) => esc(tagLabel(tag, lang))).join(" ")}</span>` : "";

  return `
    <h2 id="story-title">${esc(story.title[lang])}</h2>
    <p class="story-meta">${esc(windowLabel)} · ${esc(t.sources(story.total))} · ${esc(t.articles(story.articles.length))} ${tags}</p>
    ${story.summary[lang] ? `<div class="summary"><b>${esc(t.neutralSummary)}:</b> ${esc(story.summary[lang])}</div>` : ""}
    <ul class="legend">${legend}</ul>
    ${coverageBar(story, lang)}
    <h3 class="headlines-title">${esc(t.headlines)}</h3>
    <div class="group-tabs" role="tablist">${tabs}</div>
    <div class="columns">${columns}</div>`;
}
