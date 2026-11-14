/**
 * getApiProblem unit tests — TEST-UPLIFT-1B STEP 1
 *
 * Location: packages/shared-api/src/problem.test.ts
 *
 * Covers all three FastAPI error-body shapes + network error + non-axios throw
 * + garbage input (never throws from the parser).
 */

import { describe, it, expect } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";
import { getApiProblem, parseProblemBody, type ApiProblem } from "./problem";

// Helper: build a realistic AxiosError with a response body
function makeAxiosError(
  status: number,
  data: unknown,
  hasResponse = true,
): AxiosError {
  const err = new AxiosError(
    "Request failed",
    hasResponse ? undefined : "ERR_NETWORK",
    {
      headers: new AxiosHeaders(),
      url: "http://localhost:8000/api/v1/test",
      method: "get",
    },
    undefined,
    hasResponse
      ? {
          data,
          status,
          statusText: "",
          headers: {},
          config: { headers: new AxiosHeaders() },
        }
      : undefined,
  );
  return err;
}

describe("getApiProblem", () => {
  // ── Shape A — RFC 7807 dict ──────────────────────────────────────────────

  it("parses RFC 7807 dict in data.detail (send-invoice 404 shape from 1A)", () => {
    const err = makeAxiosError(404, {
      detail: {
        type: "https://errors.pilotfortrades.com/not-found",
        title: "Invoice not found",
        status: 404,
        detail: "Invoice does not exist in this tenant.",
      },
    });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(404);
    expect(problem.type).toBe("https://errors.pilotfortrades.com/not-found");
    expect(problem.title).toBe("Invoice not found");
    expect(problem.detail).toBe("Invoice does not exist in this tenant.");
    expect(problem.code).toBeUndefined();
  });

  it("parses RFC 7807 dict with top-level code extension (confirm-payment 401)", () => {
    const err = makeAxiosError(401, {
      detail: {
        type: "https://errors.pilotfortrades.com/invalid-link",
        title: "Invalid link",
        status: 401,
        detail: "The link is invalid or has been tampered with.",
      },
      code: "invalid_token",
    });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(401);
    expect(problem.type).toBe("https://errors.pilotfortrades.com/invalid-link");
    expect(problem.title).toBe("Invalid link");
    expect(problem.detail).toBe(
      "The link is invalid or has been tampered with.",
    );
    expect(problem.code).toBe("invalid_token");
  });

  // ── Shape B — legacy plain string ────────────────────────────────────────

  it("parses legacy plain-string data.detail", () => {
    const err = makeAxiosError(422, {
      detail: "Amount must be greater than $0.",
    });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(422);
    expect(problem.detail).toBe("Amount must be greater than $0.");
    expect(problem.type).toBeUndefined();
    expect(problem.title).toBeUndefined();
  });

  it("parses legacy string with code extension (MFA shape)", () => {
    const err = makeAxiosError(400, {
      detail: "The MFA code has expired.",
      code: "mfa_code_expired",
    });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(400);
    expect(problem.detail).toBe("The MFA code has expired.");
    expect(problem.code).toBe("mfa_code_expired");
  });

  // ── Shape C — FastAPI validation array ───────────────────────────────────

  it("joins FastAPI validation-array detail messages", () => {
    const err = makeAxiosError(422, {
      detail: [
        {
          type: "value_error",
          loc: ["body", "amount_cents"],
          msg: "amount_cents must be a positive integer",
          input: -100,
        },
        {
          type: "missing",
          loc: ["body", "paid_via"],
          msg: "Field required",
          input: null,
        },
      ],
    });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(422);
    expect(problem.detail).toBe(
      "amount_cents must be a positive integer; Field required",
    );
  });

  it("handles empty validation array gracefully", () => {
    const err = makeAxiosError(422, { detail: [] });
    const problem = getApiProblem(err);
    expect(problem.status).toBe(422);
    expect(problem.detail).toBeUndefined();
  });

  // ── Shape D — network error (no response) ────────────────────────────────

  it("returns status 0 + generic detail for network error (no response)", () => {
    const err = makeAxiosError(0, undefined, false);
    const problem = getApiProblem(err);
    expect(problem.status).toBe(0);
    expect(problem.detail).toContain("Network error");
    expect(problem.type).toBeUndefined();
  });

  // ── Shape E — non-axios throw ────────────────────────────────────────────

  it("returns status 0 + String(error) for non-axios throw", () => {
    const problem = getApiProblem(new Error("Something broke"));
    expect(problem.status).toBe(0);
    expect(problem.detail).toBe("Error: Something broke");
  });

  it("returns status 0 + String for string throw", () => {
    const problem = getApiProblem("plain string error");
    expect(problem.status).toBe(0);
    expect(problem.detail).toBe("plain string error");
  });

  // ── Garbage input — never throws ─────────────────────────────────────────

  it("never throws on null body", () => {
    const err = makeAxiosError(500, null);
    expect(() => getApiProblem(err)).not.toThrow();
    const problem = getApiProblem(err);
    expect(problem.status).toBe(500);
    expect(problem.detail).toBeUndefined();
  });

  it("never throws on undefined body", () => {
    const err = makeAxiosError(500, undefined);
    expect(() => getApiProblem(err)).not.toThrow();
    const problem = getApiProblem(err);
    expect(problem.status).toBe(500);
  });

  it("never throws on { detail: null }", () => {
    const err = makeAxiosError(500, { detail: null });
    expect(() => getApiProblem(err)).not.toThrow();
    const problem = getApiProblem(err);
    expect(problem.status).toBe(500);
    expect(problem.detail).toBeUndefined();
  });

  it("never throws on bare string body (not wrapped in detail)", () => {
    const err = makeAxiosError(500, "Internal Server Error");
    expect(() => getApiProblem(err)).not.toThrow();
    const problem = getApiProblem(err);
    expect(problem.status).toBe(500);
    expect(problem.detail).toBe("Internal Server Error");
  });

  it("never throws on completely unknown input shape", () => {
    expect(() => getApiProblem({ weird: true })).not.toThrow();
    expect(() => getApiProblem(42)).not.toThrow();
    expect(() => getApiProblem(null)).not.toThrow();
    expect(() => getApiProblem(undefined)).not.toThrow();
  });
});

describe("parseProblemBody", () => {
  it("parses RFC 7807 dict directly (for fetch-based public pages)", () => {
    const problem = parseProblemBody(404, {
      detail: {
        type: "https://errors.pilotfortrades.com/not-found",
        title: "Not Found",
        status: 404,
        detail: "Resource not found.",
      },
    });
    expect(problem.status).toBe(404);
    expect(problem.title).toBe("Not Found");
    expect(problem.detail).toBe("Resource not found.");
  });

  it("parses legacy string directly", () => {
    const problem = parseProblemBody(422, { detail: "Invalid input." });
    expect(problem.status).toBe(422);
    expect(problem.detail).toBe("Invalid input.");
  });

  it("returns undefined detail for null data", () => {
    const problem = parseProblemBody(500, null);
    expect(problem.status).toBe(500);
    expect(problem.detail).toBeUndefined();
  });

  it("handles bare string data", () => {
    const problem = parseProblemBody(500, "Server error");
    expect(problem.status).toBe(500);
    expect(problem.detail).toBe("Server error");
  });

  it("satisfies ApiProblem interface", () => {
    const problem: ApiProblem = parseProblemBody(404, {
      detail: { status: 404, detail: "Not found" },
    });
    expect(problem.status).toBe(404);
  });
});
