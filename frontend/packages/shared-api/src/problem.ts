/**
 * getApiProblem — shared RFC 7807 / FastAPI error normalizer
 *
 * Location: packages/shared-api/src/problem.ts
 *
 * TEST-UPLIFT-1B STEP 1: One shared helper for the three FastAPI error-body
 * shapes that production emits. Every feature already imports @pilot/shared-api;
 * per-feature parsers diverge today. This normalizer is RN-safe (no window/DOM).
 *
 * Shapes handled:
 *   A — RFC 7807 dict:  data.detail is { type, title, status, detail, ... }
 *   B — legacy string:  data.detail is a plain string (1A fixed 2 of these)
 *   C — validation:     data.detail is an array of { loc, msg, type } → joined msgs
 *   D — network error:  no response (CORS / offline) → status 0, generic detail
 *   E — non-axios throw: status 0, String(error) — never throws from the parser
 *
 * The `code` extension field is read from the top-level response body (e.g.
 * { detail: "...", code: "mfa_code_expired" }) — the MFA and some billing
 * endpoints use this pattern. It is NOT inside the RFC 7807 dict.
 */

import { isAxiosError } from "./client";

export interface ApiProblem {
  /** HTTP status; 0 = network error / no response */
  status: number;
  /** RFC 7807 type URI when present */
  type?: string;
  /** Short summary — banner heading */
  title?: string;
  /** Human sentence — banner/body copy. ALWAYS populated when the server sent one. */
  detail?: string;
  /** Machine code extension field when present (e.g. "mfa_code_expired") */
  code?: string;
}

const NETWORK_ERROR_DETAIL =
  "Network error — check your connection and try again.";

/**
 * Normalize a parsed response body (the `data` object from an Axios error or a
 * `fetch().json()` result) into an ApiProblem. This is the shared core used by
 * both `getApiProblem` (Axios) and `parseProblemBody` (fetch — public pages).
 *
 * Exposed so the public token pages (which use raw `fetch` per Rule 35
 * exception) can normalize consistently without constructing a fake AxiosError.
 */
export function parseProblemBody(status: number, data: unknown): ApiProblem {
  // No body / null body
  if (data == null || typeof data !== "object") {
    // data could be a plain string (some legacy endpoints return a bare string)
    if (typeof data === "string" && data.length > 0) {
      return { status, detail: data };
    }
    return { status, detail: undefined };
  }

  const body = data as Record<string, unknown>;
  const rawDetail = body["detail"];
  const code =
    typeof body["code"] === "string" ? (body["code"] as string) : undefined;

  // Shape A — RFC 7807 dict: detail is an object with type/title/status/detail
  if (
    rawDetail != null &&
    typeof rawDetail === "object" &&
    !Array.isArray(rawDetail)
  ) {
    const prob = rawDetail as Record<string, unknown>;
    return {
      status:
        typeof prob["status"] === "number"
          ? (prob["status"] as number)
          : status,
      type:
        typeof prob["type"] === "string" ? (prob["type"] as string) : undefined,
      title:
        typeof prob["title"] === "string"
          ? (prob["title"] as string)
          : undefined,
      detail:
        typeof prob["detail"] === "string"
          ? (prob["detail"] as string)
          : undefined,
      code,
    };
  }

  // Shape B — legacy: detail is a plain string
  if (typeof rawDetail === "string") {
    return { status, detail: rawDetail, code };
  }

  // Shape C — FastAPI validation: detail is an array of { loc, msg, type }
  if (Array.isArray(rawDetail)) {
    const msgs = rawDetail
      .map((item) => {
        if (item != null && typeof item === "object" && "msg" in item) {
          const msg = (item as Record<string, unknown>)["msg"];
          return typeof msg === "string" ? msg : undefined;
        }
        return undefined;
      })
      .filter((m): m is string => typeof m === "string");
    if (msgs.length > 0) {
      return { status, detail: msgs.join("; "), code };
    }
  }

  // Fallback: no recognizable detail — use a generic message keyed to status
  return { status, detail: undefined, code };
}

/**
 * Normalize any thrown value from an `apiClient` call into an ApiProblem.
 *
 * Handles AxiosError (all three body shapes), network errors (no response),
 * and non-axios throws. **Never throws** — safe to call in catch blocks and
 * render paths.
 *
 * @example
 *   try {
 *     await apiClient.post("/api/v1/invoices/123/send");
 *   } catch (err) {
 *     const problem = getApiProblem(err);
 *     setBanner({ severity: "fault", message: problem.detail ?? "Send failed." });
 *   }
 */
export function getApiProblem(error: unknown): ApiProblem {
  // Non-axios throw (programmer error, unexpected rejection)
  if (!isAxiosError(error)) {
    return { status: 0, detail: String(error) };
  }

  const axiosErr = error as import("axios").AxiosError;
  const status = axiosErr.response?.status ?? 0;

  // Network error / no response (CORS, offline, DNS failure)
  if (!axiosErr.response) {
    return { status: 0, detail: NETWORK_ERROR_DETAIL };
  }

  return parseProblemBody(status, axiosErr.response.data);
}
