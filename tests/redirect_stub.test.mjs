// node --test tests/redirect_stub.test.mjs — the GitHub Pages redirect stub (redirect/).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const read = (name) => readFileSync(new URL(`../redirect/${name}`, import.meta.url), "utf8");
const html = read("index.html");
const base = "https://projects.cristian-nichifor.com/open-procurement/";

const destination = (pathname, search = "", hash = "") => {
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)];
  assert.equal(scripts.length, 1, "expected one redirect script");
  const seen = [];
  vm.runInNewContext(scripts[0][1], { location: { pathname, search, hash, replace: (u) => seen.push(u) } }, { timeout: 1000 });
  assert.equal(seen.length, 1);
  return seen[0];
};

test("404.html is the same page, so unknown paths redirect too", () => {
  assert.equal(read("404.html"), html);
});

test("path, query and hash carry across to the hub", () => {
  assert.equal(destination("/open-procurement/a/b", "?x=1", "#h"), `${base}a/b?x=1#h`);
  assert.equal(destination("/open-procurement/", "", "#v=preturi&minn=5"), `${base}#v=preturi&minn=5`);
  assert.equal(destination("/open-procurement"), base);
  assert.equal(destination("/open-procurement/data/manifest.json"), `${base}data/manifest.json`);
  // Only the project prefix is stripped, not a lookalike.
  assert.equal(destination("/open-procurement-x/y"), `${base}open-procurement-x/y`);
});

test("canonical, no-JavaScript fallback, visible link and noindex agree", () => {
  assert.ok(html.includes(`<link rel="canonical" href="${base}" />`));
  const fallback = html.match(/<noscript\b[^>]*>([\s\S]*?)<\/noscript\s*>/i);
  assert.ok(fallback, "no-JavaScript fallback is required");
  assert.ok(fallback[1].includes(`http-equiv="refresh" content="0; url=${base}"`));
  assert.ok(html.includes(`<a href="${base}">`));
  assert.ok(html.includes('<meta name="robots" content="noindex" />'));
});
