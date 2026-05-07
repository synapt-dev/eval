import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { precisionAtK, recallAtK, kendallTau } from "../src/scoring/mod.ts";

describe("precisionAtK", () => {
  it("computes correct precision", () => {
    assert.strictEqual(precisionAtK(["a", "b", "c"], ["a", "c"], 3), 2 / 3);
  });

  it("returns 0 for k=0", () => {
    assert.strictEqual(precisionAtK(["a"], ["a"], 0), 0);
  });

  it("returns 0 for empty retrieved", () => {
    assert.strictEqual(precisionAtK([], ["a", "b"], 5), 0);
  });

  it("handles perfect precision", () => {
    assert.strictEqual(precisionAtK(["a", "b"], ["a", "b"], 2), 1.0);
  });

  it("handles zero precision", () => {
    assert.strictEqual(precisionAtK(["x", "y"], ["a", "b"], 2), 0);
  });

  it("truncates to k", () => {
    assert.strictEqual(precisionAtK(["a", "b", "c", "d"], ["a"], 2), 0.5);
  });
});

describe("recallAtK", () => {
  it("computes correct recall", () => {
    assert.strictEqual(recallAtK(["a", "b", "c"], ["a", "c", "d"], 3), 2 / 3);
  });

  it("returns 0 for empty relevant", () => {
    assert.strictEqual(recallAtK(["a"], [], 5), 0);
  });

  it("returns 0 for k=0", () => {
    assert.strictEqual(recallAtK(["a"], ["a"], 0), 0);
  });

  it("handles perfect recall", () => {
    assert.strictEqual(recallAtK(["a", "b"], ["a", "b"], 5), 1.0);
  });

  it("truncates to k", () => {
    assert.strictEqual(recallAtK(["a", "b", "c"], ["a", "c"], 1), 0.5);
  });
});

describe("kendallTau", () => {
  it("returns 1.0 for identical rankings", () => {
    assert.strictEqual(kendallTau(["a", "b", "c"], ["a", "b", "c"]), 1.0);
  });

  it("returns -1.0 for reversed rankings", () => {
    assert.strictEqual(kendallTau(["a", "b", "c"], ["c", "b", "a"]), -1.0);
  });

  it("returns null for fewer than 2 common items", () => {
    assert.strictEqual(kendallTau(["a"], ["a"]), null);
  });

  it("returns null for no common items", () => {
    assert.strictEqual(kendallTau(["a", "b"], ["c", "d"]), null);
  });

  it("handles partial overlap", () => {
    const tau = kendallTau(["a", "b", "c"], ["b", "a", "c"]);
    assert.notStrictEqual(tau, null);
    assert.ok(tau! > -1 && tau! < 1);
  });
});
