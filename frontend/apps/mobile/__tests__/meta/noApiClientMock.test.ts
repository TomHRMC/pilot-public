/**
 * noApiClientMock.test.ts — TEST-UPLIFT-1C STEP 4
 *
 * Location: apps/mobile/__tests__/meta/noApiClientMock.test.ts
 *
 * Anti-regression ratchet: scans all mobile test files for the banned
 * `jest.mock("@pilot/shared-api", ...)` pattern and fails on any hit not
 * in the checked-in baseline (no_api_client_mock_baseline.json).
 *
 * Per react-engineer-rules §9 / inclusions §9: "Never mock apiClient
 * directly — MSW intercepts at the HTTP level and is the only correct
 * approach." This ratchet enforces that rule permanently.
 *
 * The baseline ships as `{}` (empty) — TEST-UPLIFT-1C achieved full closure
 * (all 10 banned-pattern files converted). Any new violation will fail this
 * test. Any baseline entry whose file no longer mocks will also fail (stale
 * entry — prune reminder).
 *
 * Detection: matches lines containing `jest.mock(` followed by a string
 * literal `"@pilot/shared-api"` or `'@pilot/shared-api'`, excluding lines
 * that are comments (starting with `*`, `//`, or `/*`).
 */

import * as fs from "fs";
import * as path from "path";

const MOBILE_ROOT = path.resolve(__dirname, "../..");
const BASELINE_PATH = path.resolve(
  __dirname,
  "no_api_client_mock_baseline.json",
);

// Regex: matches jest.mock("@pilot/shared-api" or jest.mock('@pilot/shared-api'
// but NOT inside comments (lines starting with *, //, or /*)
const BANNED_PATTERN = /jest\.mock\(\s*["']@pilot\/shared-api["']/;

function isCommentLine(line: string): boolean {
  const trimmed = line.trim();
  return (
    trimmed.startsWith("*") ||
    trimmed.startsWith("//") ||
    trimmed.startsWith("/*") ||
    trimmed.startsWith("*/")
  );
}

function findTestFiles(dir: string, results: string[]): void {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Skip node_modules and e2e
      if (entry.name === "node_modules" || entry.name === "e2e") continue;
      findTestFiles(fullPath, results);
    } else if (
      entry.name.endsWith(".test.ts") ||
      entry.name.endsWith(".test.tsx")
    ) {
      results.push(fullPath);
    }
  }
}

function findBannedMocks(): Map<string, number> {
  const testFiles: string[] = [];
  findTestFiles(MOBILE_ROOT, testFiles);

  const hits = new Map<string, number>();
  for (const file of testFiles) {
    const content = fs.readFileSync(file, "utf-8");
    const lines = content.split("\n");
    let count = 0;
    for (const line of lines) {
      if (isCommentLine(line)) continue;
      if (BANNED_PATTERN.test(line)) {
        count++;
      }
    }
    if (count > 0) {
      // Store relative path from mobile root for stable baseline keys
      const relPath = path.relative(MOBILE_ROOT, file);
      hits.set(relPath, count);
    }
  }
  return hits;
}

describe("noApiClientMock ratchet (TEST-UPLIFT-1C)", () => {
  it("no mobile test file mocks @pilot/shared-api directly (MSW at HTTP level only)", () => {
    const baselineRaw = fs.readFileSync(BASELINE_PATH, "utf-8");
    const baseline = JSON.parse(baselineRaw) as Record<string, number>;

    const currentHits = findBannedMocks();

    // 1. Fail on any new violation not in the baseline
    const newViolations: string[] = [];
    for (const [file, count] of currentHits) {
      const baselineCount = baseline[file] ?? 0;
      if (count > baselineCount) {
        newViolations.push(
          `  NEW: ${file} — ${count} hit(s) (baseline: ${baselineCount})`,
        );
      }
    }

    // 2. Fail on stale baseline entries (file no longer mocks)
    const staleEntries: string[] = [];
    for (const [file, baselineCount] of Object.entries(baseline)) {
      const currentCount = currentHits.get(file) ?? 0;
      if (currentCount < baselineCount) {
        staleEntries.push(
          `  STALE: ${file} — baseline says ${baselineCount} but found ${currentCount} (prune the baseline)`,
        );
      }
    }

    const errors = [...newViolations, ...staleEntries];
    if (errors.length > 0) {
      const message = [
        "noApiClientMock ratchet failures:",
        "",
        ...newViolations,
        ...staleEntries,
        "",
        "Rule: Never mock @pilot/shared-api directly — use MSW setupServer",
        "with wildcard */api/v1/... handlers (react-engineer-rules §9, §18).",
        "If a violation is justified, add it to no_api_client_mock_baseline.json",
        "with a reason and track it to BE-TESTS-MAINT.",
      ].join("\n");
      throw new Error(message);
    }

    // Pass: zero new violations, zero stale entries
    expect(newViolations).toHaveLength(0);
    expect(staleEntries).toHaveLength(0);
  });
});
