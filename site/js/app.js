import { GROUPS, findBlindspots, storiesInWindow, summarize, topTags } from "./coverage.js";
import { GROUP_LABEL, METHOD, TEXT } from "./i18n.js";
import { blindspotList, storyCard, storyRow, storyView, tagLabel } from "./render.js";
import { esc, formatDateTime, safeUrl } from "./util.js";

const WINDOWS = [1, 7, 30];
const $ = (sel) => document.querySelector(sel);

const state = {
  lang: initialLang(),
  days: 1,
  tag: null,
  news: null,
  sources: null,
  shown: [],        // stories in the current window + tag filter
  openStory: null,  // id of the story in the dialog
  storyGroup: null, // active tab in the dialog on phones
};

// Whether the open dialog was reached by clicking inside the app. If so,
// closing it can just go back in history; a deep link has nothing to go back to.
let openedInApp = false;

function initialLang() {
  const fromUrl = new URLSearchParams(location.search).get("lang");
  if (fromUrl === "tr" || fromUrl === "en") return fromUrl;
  try {
    const stored = localStorage.getItem("lang");
    if (stored === "tr" || stored === "en") return stored;
  } catch {}
  return "tr";
}

const t = () => TEXT[state.lang];
const windowLabel = (days) => t()[`time${days}`];

// GitHub Pages URL -> repo URL, so the footer and issue links work in any fork.
function repoUrl() {
  const m = location.hostname.match(/^([\w-]+)\.github\.io$/);
  if (!m) return "";
  const repo = location.pathname.split("/").filter(Boolean)[0];
  return `https://github.com/${m[1]}/${repo || `${m[1]}.github.io`}`;
}

/* ---------- rendering ---------- */

function renderStatic() {
  document.documentElement.lang = state.lang;
  for (const el of document.querySelectorAll("[data-t]")) el.textContent = t()[el.dataset.t];
  for (const btn of document.querySelectorAll("[data-lang]")) {
    btn.setAttribute("aria-pressed", String(btn.dataset.lang === state.lang));
  }
  $("#theme-toggle").setAttribute("aria-label", t().themeToggle);
  $("#theme-toggle").title = t().themeToggle;
  $("#story-close").setAttribute("aria-label", t().close);
  $("#agenda-title").textContent = t().agenda;
  $("#blind-title").textContent = t().blindspots;
  $("#blind-pop").innerHTML = t().blindspotsBody;
  $("#about-pop").innerHTML = t().aboutBody.replace("{n}", sourceCount());
  $(".section-tabs [data-section=agenda]").textContent = t().agenda;
  $(".section-tabs [data-section=blindspots]").textContent = t().blindspots;
  for (const el of document.querySelectorAll(".window-label")) el.textContent = windowLabel(state.days);
}

function sourceCount() {
  return state.sources ? state.sources.sources.filter((s) => s.active !== false).length : "";
}

function renderMeta() {
  const updated = state.news ? formatDateTime(state.news.data_updated || state.news.generated_at, state.lang) : "";
  const parts = [];
  if (updated) parts.push(`${esc(t().updated)}: ${esc(updated)}`);
  if (t().betaNote) parts.push(`<i>${esc(t().betaNote)}</i>`);
  $("#meta").innerHTML = parts.join(" · ");
}

function renderFilters(tags) {
  $("#time-filter").setAttribute("aria-label", t().timeframe);
  $("#time-filter").innerHTML = WINDOWS.map(
    (d) => `<button type="button" class="pill" data-days="${d}" aria-pressed="${d === state.days}">${esc(windowLabel(d))}</button>`
  ).join("");

  $("#tag-filter").setAttribute("aria-label", t().topics);
  const options = [[null, t().allStories], ...tags.map((tag) => [tag, tagLabel(tag, state.lang)])];
  $("#tag-filter").innerHTML = options.map(
    ([tag, label]) => `<button type="button" class="pill" data-tag="${esc(tag ?? "")}" aria-pressed="${tag === state.tag}">${esc(label)}</button>`
  ).join("");
}

function renderAgenda() {
  const lang = state.lang;
  const stories = state.shown;
  if (!stories.length) {
    const hint = state.days < 7 ? `<button type="button" class="pill" data-days="7">${esc(t().tryWeek)}</button>` : "";
    $("#agenda-body").innerHTML = `<div class="empty"><p>${esc(t().emptyWindow)}</p>${hint}</div>`;
    return;
  }
  $("#agenda-body").innerHTML = `
    <div class="cards">${stories.slice(0, 3).map((s) => storyCard(s, lang)).join("")}</div>
    <div class="rows">${stories.slice(3).map((s) => storyRow(s, lang)).join("")}</div>`;
}

function renderBlindspots() {
  const { missedByOpposition, missedByProgov } = findBlindspots(state.shown);
  $("#blind-body").innerHTML =
    blindspotList(missedByOpposition, "opposition", state.lang) +
    blindspotList(missedByProgov, "progov", state.lang);
}

function renderMethod() {
  const data = state.sources;
  if (!data) return;
  const lang = state.lang;
  const evidence = (items) =>
    items.length
      ? `<ul class="evidence">${items
          .filter((d) => safeUrl(d.url))
          .map((d) => `<li><a href="${esc(d.url)}" target="_blank" rel="noopener noreferrer">${esc(d.name)}</a></li>`)
          .join("")}</ul>`
      : "";

  const groups = ["progov", "independent", "opposition"].map((g) => {
    const members = data.sources.filter((s) => s.group === g && s.active !== false);
    const cards = members.map(
      (s) => `<li class="source-card">
        <div class="source-head"><b>${esc(s.name)}</b><span class="badge ${esc(s.status)}">${esc(t().status[s.status] || s.status)}</span></div>
        <p>${esc(s.reason)}</p>
        ${evidence(s.evidence || [])}
      </li>`
    ).join("");
    return `<h3 class="group-title ${g}">${esc(GROUP_LABEL[lang][g])} (${members.length})</h3><ul class="source-list">${cards}</ul>`;
  }).join("");

  const removed = data.removed?.length
    ? `<h3 class="group-title">${esc(t().removed)}</h3><ul class="source-list">${data.removed.map(
        (s) => `<li class="source-card"><div class="source-head"><b>${esc(s.name)}</b></div><p>${esc(s.reason)}</p>${evidence(s.evidence || [])}</li>`
      ).join("")}</ul>`
    : "";

  $("#method-body").innerHTML = METHOD[lang](esc(data.updated), repoUrl()) + groups + removed;
}

function renderFooter() {
  const repo = repoUrl();
  $("#footer").innerHTML = `
    <p>${esc(t().footer.replace("{n}", sourceCount()))}</p>
    <p><i>${esc(t().disclaimer)}</i></p>
    <p><b>Tarafsızlık Türkiye</b> © 2026${repo ? ` · <a href="${esc(repo)}" target="_blank" rel="noopener">${esc(t().sourceCode)}</a>` : ""}</p>`;
}

function render() {
  renderStatic();
  renderMeta();
  renderFooter();
  if (!state.news) return;

  const sizes = state.news.group_sizes;
  const inWindow = storiesInWindow(state.news.stories, state.days, sizes);
  const tags = topTags(inWindow);
  if (state.tag && !tags.includes(state.tag)) state.tag = null;
  state.shown = state.tag ? inWindow.filter((s) => s.tags.includes(state.tag)) : inWindow;

  renderFilters(tags);
  renderAgenda();
  renderBlindspots();
  renderMethod();
  if (state.openStory) renderStory();
}

/* ---------- story dialog ---------- */

// Prefer the story as it looks in the current window, so the numbers match the
// card that was tapped. Shared links to older stories fall back to all 30 days.
function storyForView(id) {
  const inView = state.shown.find((s) => s.id === id);
  if (inView) return { story: inView, label: windowLabel(state.days) };
  const raw = state.news.stories.find((s) => s.id === id);
  if (raw) return { story: summarize(raw, raw.articles, state.news.group_sizes), label: t().allTime };
  return null;
}

function renderStory() {
  const found = storyForView(state.openStory);
  const body = $("#story-body");
  $("#story-share").hidden = !found;
  if (!found) {
    body.innerHTML = `<p class="empty">${esc(t().storyGone)}</p>`;
    return;
  }
  const { story, label } = found;
  if (!state.storyGroup) {
    // Start the phone tabs on the side with the most articles.
    const count = (g) => story.articles.filter((a) => a.g === g).length;
    state.storyGroup = GROUPS.reduce((best, g) => (count(g) > count(best) ? g : best), GROUPS[0]);
  }
  body.innerHTML = storyView(story, label, state.storyGroup, state.lang);
  document.title = `${story.title[state.lang]} · Tarafsızlık Türkiye`;
}

function openStory(id) {
  const dialog = $("#story");
  state.openStory = id;
  state.storyGroup = null;
  if (state.news) renderStory();
  if (!dialog.open) {
    dialog.showModal();
    document.documentElement.classList.add("modal-open");
  }
  $("#story-body").scrollTop = 0;
}

function hideStory() {
  const dialog = $("#story");
  state.openStory = null;
  if (dialog.open) dialog.close();
  document.documentElement.classList.remove("modal-open");
  document.title = "Tarafsızlık Türkiye";
}

function closeStory() {
  if (openedInApp) {
    history.back();
  } else {
    history.replaceState(null, "", location.pathname + location.search);
    hideStory();
  }
}

function route() {
  const m = location.hash.match(/^#\/s\/([^/?#]+)/);
  if (m) openStory(decodeURIComponent(m[1]));
  else hideStory();
}

async function shareStory() {
  const found = storyForView(state.openStory);
  if (!found) return;
  const base = location.href.split("#")[0].split("?")[0].replace(/index\.html$/, "");
  const url = new URL(`s/${encodeURIComponent(found.story.id)}/`, base).href;
  const title = found.story.title[state.lang];
  if (navigator.share) {
    try {
      await navigator.share({ title, url });
      return;
    } catch (e) {
      if (e.name === "AbortError") return;
    }
  }
  try {
    await navigator.clipboard.writeText(url);
    toast(t().copied);
  } catch {
    prompt(t().share, url);
  }
}

let toastTimer;
function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
}

/* ---------- theme ---------- */

const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const currentTheme = () => document.documentElement.dataset.theme || (darkQuery.matches ? "dark" : "light");

function syncThemeColor() {
  const bg = getComputedStyle(document.documentElement).getPropertyValue("--bg").trim();
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) meta.content = bg;
}

function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem("theme", next);
  } catch {}
  syncThemeColor();
}

/* ---------- events ---------- */

function closePopovers(except) {
  for (const box of document.querySelectorAll(".info.open")) {
    if (box === except) continue;
    box.classList.remove("open");
    box.querySelector(".info-toggle").setAttribute("aria-expanded", "false");
  }
}

function bindEvents() {
  document.addEventListener("click", (e) => {
    const target = e.target.closest("button, a");

    // Info popovers: hover on desktop is pure CSS, a tap/click pins them open.
    const toggle = e.target.closest(".info-toggle");
    if (toggle) {
      const box = toggle.closest(".info");
      closePopovers(box);
      const open = box.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
      return;
    }
    if (!e.target.closest(".popover")) closePopovers();

    if (!target) return;
    const { lang, days, tag, section, group } = target.dataset;

    if (lang && lang !== state.lang) {
      state.lang = lang;
      try {
        localStorage.setItem("lang", lang);
      } catch {}
      render();
    } else if (days) {
      state.days = Number(days);
      render();
    } else if (tag !== undefined && target.closest("#tag-filter")) {
      state.tag = tag || null;
      render();
    } else if (section) {
      document.querySelector(".layout").dataset.section = section;
      for (const tab of document.querySelectorAll(".section-tabs [role=tab]")) {
        tab.setAttribute("aria-selected", String(tab.dataset.section === section));
      }
      window.scrollTo({ top: $(".filters").offsetTop + $(".filters").offsetHeight - 8 });
    } else if (group && target.closest(".group-tabs")) {
      state.storyGroup = group;
      for (const el of document.querySelectorAll(".group-tabs [data-group]")) {
        el.setAttribute("aria-selected", String(el.dataset.group === group));
      }
      for (const col of document.querySelectorAll(".columns .col")) {
        col.classList.toggle("active", col.dataset.group === group);
      }
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePopovers();
  });

  // Broken or hotlink-blocked images get the neutral placeholder.
  document.addEventListener("error", (e) => {
    const img = e.target;
    if (img.tagName === "IMG" && !img.src.endsWith("placeholder.svg")) img.src = "img/placeholder.svg";
  }, true);

  window.addEventListener("hashchange", () => {
    openedInApp = true;
    route();
  });

  const dialog = $("#story");
  dialog.addEventListener("cancel", (e) => {
    e.preventDefault();
    closeStory();
  });
  // Click on the backdrop (outside the dialog box) closes it.
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) closeStory();
  });
  $("#story-close").addEventListener("click", closeStory);
  $("#story-share").addEventListener("click", shareStory);
  $("#theme-toggle").addEventListener("click", toggleTheme);
  darkQuery.addEventListener("change", syncThemeColor);
}

/* ---------- start ---------- */

async function loadJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

async function main() {
  bindEvents();
  syncThemeColor();
  render();
  route();
  try {
    [state.news, state.sources] = await Promise.all([loadJson("data/news.json"), loadJson("data/sources.json")]);
  } catch (e) {
    console.error(e);
    $("#agenda-body").innerHTML = `<p class="empty">${esc(t().noData)}</p>`;
    return;
  }
  // Nothing in the last 24h (e.g. the pipeline was down)? Start with the week instead.
  if (!storiesInWindow(state.news.stories, 1, state.news.group_sizes).length) state.days = 7;
  render();
}

main();
