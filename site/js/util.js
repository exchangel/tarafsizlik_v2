const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escape anything that comes from the data before it goes into innerHTML. */
export const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);

/** Only plain http(s) links get through; no javascript: and friends. */
export const safeUrl = (url) => (/^https?:\/\/[^\s"'<>]+$/i.test(url || "") ? url : "");

const LOCALE = { tr: "tr-TR", en: "en-GB" };

export function percent(value, lang) {
  const n = Math.round(value);
  return lang === "tr" ? `%${n}` : `${n}%`;
}

export function timeAgo(iso, lang, now = Date.now()) {
  const minutes = Math.round((Date.parse(iso) - now) / 60000);
  const rtf = new Intl.RelativeTimeFormat(LOCALE[lang], { numeric: "auto", style: "short" });
  if (Math.abs(minutes) < 60) return rtf.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return rtf.format(hours, "hour");
  return rtf.format(Math.round(hours / 24), "day");
}

export function formatDateTime(iso, lang) {
  if (!iso) return "";
  return new Intl.DateTimeFormat(LOCALE[lang], {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  }).format(new Date(iso));
}
