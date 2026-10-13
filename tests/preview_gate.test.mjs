// node --test tests/preview_gate.test.mjs — the Pages middleware that keeps preview builds behind
// the CN Webify preview gate (functions/_middleware.js).
import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { onRequest } from "../functions/_middleware.js";

globalThis.crypto ??= webcrypto;
const SECRET = "g".repeat(64);
const served = new Response("static");
const run = (origin, headers = {}, env = {}) =>
  onRequest({ request: new Request(`${origin}/open-procurement/`, { headers }), env, next: async () => served });

test("a preview host without the secret is refused even with a header", async () => {
  const response = await run("https://dev.open-procurement-x1y.pages.dev", { "x-cnw-preview-gate": "anything" });
  assert.equal(response.status, 403);
  assert.equal(response.headers.get("x-robots-tag"), "noindex, nofollow");
});

test("with the secret, a missing or wrong header is refused", async () => {
  for (const headers of [{}, { "x-cnw-preview-gate": "wrong" }, { "x-cnw-preview-gate": SECRET.slice(1) }]) {
    const response = await run("https://dev.open-procurement-x1y.pages.dev", headers, { PREVIEW_GATE_SECRET: SECRET });
    assert.equal(response.status, 403);
  }
});

test("with the secret, the gate's header is served", async () => {
  assert.equal(await run("https://dev.open-procurement-x1y.pages.dev", { "x-cnw-preview-gate": SECRET }, { PREVIEW_GATE_SECRET: SECRET }), served);
});

test("the production pages.dev host is served without a secret", async () => {
  assert.equal(await run("https://open-procurement-x1y.pages.dev"), served);
});
