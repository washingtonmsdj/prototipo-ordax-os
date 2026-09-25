import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = await readFile(resolve(ROOT, "system/surface/ui/memory-review-controls.mjs"), "utf8");

for (const marker of [
  'MEMORY_REVIEW_CONTROLS_SCHEMA = "ordax.memory-review-controls/1"',
  'data-memory-review',
  'dataset.memoryReviewSearch',
  'dataset.memoryReviewOwner',
  'dataset.memoryReviewSave',
  'dataset.memoryReviewRemove',
  'dataset.memoryReviewPage',
  'article.dataset.sensitivity = item.sensitivity',
  '${item.kind} · ${item.scope} · ${item.sensitivity} · ${item.provenance}',
  'viewModel.setQuery(target.value)',
  'viewModel.selectOwner({',
  'viewModel.previousPage()',
  'viewModel.nextPage()',
  'viewModel.update(id, { content: textarea.value })',
  'viewModel.remove(id)',
  'viewModel.subscribe(render)',
  'unsubscribe()',
]) {
  assert.equal(source.includes(marker), true, `missing memory-review control marker: ${marker}`);
}

assert.equal(source.includes("localStorage"), false);
assert.equal(source.includes("fetch("), false);
assert.equal(source.includes("OpenAI"), false);
assert.equal(source.includes("llama"), false);
assert.equal(source.includes("window.confirm"), false);
assert.equal(source.includes("CSS.escape"), false);

console.log("MEMORY_REVIEW_CONTROLS=PASS");
