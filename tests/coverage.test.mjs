// node --test tests/
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  coveragePercents, findBlindspots, sourceCounts, storiesInWindow, summarize, topTags,
} from "../site/js/coverage.js";

const SIZES = { opposition: 10, independent: 10, progov: 14 };
const NOW = Date.parse("2026-10-04T20:00:00Z");
const a = (s, g, d = "2026-10-04T18:00:00Z") => ({ s, g, t: "x", l: "https://x", d });

test("same outlet counts once", () => {
  const counts = sourceCounts([a("Sözcü", "opposition"), a("Sözcü", "opposition"), a("NTV", "independent"), a("Sabah", "progov")]);
  assert.deepEqual(counts, { opposition: 1, independent: 1, progov: 1 });
});

test("percents are normalized by group size", () => {
  // 5/10 opposition vs 7/14 pro-gov: equal shares despite different raw counts
  const p = coveragePercents({ opposition: 5, independent: 0, progov: 7 }, SIZES);
  assert.equal(p.opposition, 50);
  assert.equal(p.progov, 50);
  assert.equal(p.independent, 0);
});

test("no coverage gives zeros, not NaN", () => {
  const p = coveragePercents({ opposition: 0, independent: 0, progov: 0 }, SIZES);
  assert.deepEqual(p, { opposition: 0, independent: 0, progov: 0 });
});

test("window filters articles and sorts by outlets", () => {
  const stories = [
    { id: "old", tags: [], articles: [a("A", "opposition", "2026-09-30T00:00:00Z")] },
    { id: "small", tags: [], articles: [a("A", "opposition")] },
    { id: "big", tags: [], articles: [a("A", "opposition"), a("B", "progov")] },
  ];
  assert.deepEqual(storiesInWindow(stories, 1, SIZES, NOW).map((s) => s.id), ["big", "small"]);
  assert.equal(storiesInWindow(stories, 7, SIZES, NOW).length, 3);
});

test("blindspots need 3 outlets and a share of 10% or less", () => {
  const make = (id, arts) => summarize({ id, tags: [] }, arts, SIZES);
  const missedByOpp = make("gov-only", [a("S1", "progov"), a("S2", "progov"), a("N1", "independent")]);
  const missedByGov = make("opp-only", [a("O1", "opposition"), a("O2", "opposition"), a("O3", "opposition")]);
  const tooSmall = make("two", [a("S1", "progov"), a("S2", "progov")]);
  const balanced = make("balanced", [a("O1", "opposition"), a("S1", "progov"), a("N1", "independent")]);

  const { missedByOpposition, missedByProgov } = findBlindspots([missedByOpp, missedByGov, tooSmall, balanced]);
  assert.deepEqual(missedByOpposition.map((x) => x.story.id), ["gov-only"]);
  assert.deepEqual(missedByProgov.map((x) => x.story.id), ["opp-only"]);
  assert.equal(missedByOpposition[0].share, 0);
});

test("top tags weighted by outlets", () => {
  const stories = [
    { tags: ["#Eğitim"], total: 2 },
    { tags: ["#Sağlık", "#Eğitim"], total: 5 },
    { tags: ["#DepremVeAfet"], total: 6 },
  ];
  assert.deepEqual(topTags(stories, 2), ["#Eğitim", "#DepremVeAfet"]);
});

test("catch-all groups go last and never count as blindspots", () => {
  const arts = [a("S1", "progov"), a("S2", "progov"), a("S3", "progov"), a("N1", "independent")];
  const stories = [
    { id: "basket", basket: true, tags: [], articles: arts },
    { id: "real", tags: [], articles: [a("O1", "opposition")] },
  ];
  const ranked = storiesInWindow(stories, 1, SIZES, NOW);
  assert.deepEqual(ranked.map((s) => s.id), ["real", "basket"]);
  assert.equal(findBlindspots(ranked).missedByOpposition.length, 0);
});
