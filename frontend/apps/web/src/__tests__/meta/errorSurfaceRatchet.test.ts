/**
 * Error-Surface Ratchet Meta-Test — TEST-UPLIFT-1B STEP 2
 *
 * Location: apps/web/src/__tests__/meta/errorSurfaceRatchet.test.ts
 *
 * Scans every hook file under apps/web/src/features (any hooks subfolder) that
 * contains an `apiClient.` call. Each such hook must show error-handling
 * evidence — either in the hook file itself OR in a sibling component file
 * within the same feature folder. Hooks without evidence must be listed in
 * the checked-in baseline (error_surface_baseline.json).
 *
 * Ratchet semantics (design §G Q7):
 *   - test_no_new_error_surface_gaps: FAILS when a hook has apiClient calls,
 *     no evidence, and is NOT in the baseline (new gap → must wire error UX).
 *   - test_baseline_entries_still_gaps: FAILS when a baseline entry now HAS
 *     evidence (prune reminder — remove it from the baseline).
 *
 * The baseline only shrinks during burn-down. After STEP 3 closes the §C.1
 * surfaces, those entries are removed from the baseline.
 */

import { describe, it, expect } from "vitest";
import * as fs from "node:fs";
import * as path from "node:path";

// ─── Configuration ────────────────────────────────────────────────────────────

const FEATURES_DIR = path.resolve(__dirname, "../../features");
const BASELINE_PATH = path.resolve(__dirname, "error_surface_baseline.json");

/** Regex detecting error-handling evidence in a file's source. */
const ERROR_EVIDENCE =
  /getApiProblem|isError|onError|errorCode|errorDetail|ErrorState|NotificationBanner|\.error\b|catch\s*[\({]/;

/** Regex detecting apiClient calls (not just imports). */
const APICLIENT_CALL = /apiClient\.(get|post|put|patch|delete)\s*\(/;

// ─── Filesystem scan helpers ──────────────────────────────────────────────────

/** Recursively collect hook files in any hooks subfolder under features. */
function findHookFiles(dir: string): string[] {
  const results: string[] = [];
  if (!fs.existsSync(dir)) return results;

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Skip __tests__ and node_modules
      if (entry.name === "__tests__" || entry.name === "node_modules") continue;
      results.push(...findHookFiles(fullPath));
    } else if (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx")) {
      // Only files inside a "hooks" directory
      if (
        dir.includes(`${path.sep}hooks${path.sep}`) ||
        dir.endsWith(`${path.sep}hooks`)
      ) {
        // Exclude test files
        if (entry.name.includes(".test.") || entry.name.includes(".spec."))
          continue;
        results.push(fullPath);
      }
    }
  }
  return results;
}

/** Read a file's contents safely (returns empty string on error). */
function readFileSafe(filePath: string): string {
  try {
    return fs.readFileSync(filePath, "utf-8");
  } catch {
    return "";
  }
}

/** Check if a file contains apiClient calls. */
function hasApiClientCall(filePath: string): boolean {
  return APICLIENT_CALL.test(readFileSafe(filePath));
}

/** Check if a file contains error-handling evidence. */
function hasErrorEvidence(filePath: string): boolean {
  return ERROR_EVIDENCE.test(readFileSafe(filePath));
}

/**
 * Sibling rule: a hook file is "covered" if it has evidence OR a sibling
 * component file in the same feature folder (or a parent component importing
 * the hook) has evidence. We scan all .ts/.tsx files in the same feature
 * folder tree (the top-level feature domain directory) for evidence.
 */
function hasSiblingEvidence(hookFilePath: string): boolean {
  // Walk up to the feature domain root: features/<domain>/
  // The hook is at features/<domain>/hooks/<file>.ts
  const hooksDir = path.dirname(hookFilePath);
  const featureDir = path.dirname(hooksDir); // features/<domain>

  // Scan all non-test .ts/.tsx files in the feature directory tree
  function scanDir(dir: string): boolean {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === "__tests__" || entry.name === "node_modules")
          continue;
        if (scanDir(fullPath)) return true;
      } else if (
        (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx")) &&
        !entry.name.includes(".test.") &&
        !entry.name.includes(".spec.")
      ) {
        if (hasErrorEvidence(fullPath)) return true;
      }
    }
    return false;
  }

  return scanDir(featureDir);
}

/** Convert an absolute path to a repo-relative features/ path. */
function toRelativePath(absPath: string): string {
  return path.relative(FEATURES_DIR, absPath).replace(/\\/g, "/");
}

// ─── Scan: build the gap list ─────────────────────────────────────────────────

interface ScanResult {
  allHooks: string[]; // all hook files with apiClient calls
  covered: string[]; // hooks with evidence (self or sibling)
  gaps: string[]; // hooks without evidence
}

function scanErrorSurfaces(): ScanResult {
  const hookFiles = findHookFiles(FEATURES_DIR);
  const allHooks: string[] = [];
  const covered: string[] = [];
  const gaps: string[] = [];

  for (const hookFile of hookFiles) {
    if (!hasApiClientCall(hookFile)) continue;
    const relPath = toRelativePath(hookFile);
    allHooks.push(relPath);

    const selfEvidence = hasErrorEvidence(hookFile);
    const siblingEvidence = hasSiblingEvidence(hookFile);

    if (selfEvidence || siblingEvidence) {
      covered.push(relPath);
    } else {
      gaps.push(relPath);
    }
  }

  return { allHooks, covered, gaps };
}

// ─── Baseline loading ─────────────────────────────────────────────────────────

function loadBaseline(): Record<string, string> {
  try {
    const raw = fs.readFileSync(BASELINE_PATH, "utf-8");
    return JSON.parse(raw) as Record<string, string>;
  } catch {
    return {};
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Error-Surface Ratchet (TEST-UPLIFT-1B)", () => {
  const scan = scanErrorSurfaces();
  const baseline = loadBaseline();

  it("test_no_new_error_surface_gaps — every apiClient hook has evidence or is baselined", () => {
    const newGaps = scan.gaps.filter((g) => !(g in baseline));
    if (newGaps.length > 0) {
      // Print helpful diagnostics
      console.error(
        "NEW error-surface gaps (not in baseline):\n" +
          newGaps.map((g) => `  - ${g}`).join("\n"),
      );
    }
    expect(newGaps).toEqual([]);
  });

  it("test_baseline_entries_still_gaps — no baseline entry now has evidence (prune reminder)", () => {
    const staleEntries = Object.keys(baseline).filter((entry) => {
      // An entry is stale if it's no longer a gap (now has evidence)
      return !scan.gaps.includes(entry);
    });
    if (staleEntries.length > 0) {
      console.error(
        "STALE baseline entries (now have evidence — prune them):\n" +
          staleEntries.map((e) => `  - ${e}`).join("\n"),
      );
    }
    expect(staleEntries).toEqual([]);
  });

  it("scan summary — documents the current state", () => {
    // This test always passes — it's a diagnostic assertion
    console.log(
      `Error-surface scan: ${scan.allHooks.length} apiClient hooks, ` +
        `${scan.covered.length} covered, ${scan.gaps.length} gaps, ` +
        `${Object.keys(baseline).length} baselined.`,
    );
    expect(scan.allHooks.length).toBeGreaterThan(0);
  });
});
