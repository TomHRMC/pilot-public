/**
 * tenant-site-host.test — C-B16 parseSitesHost unit tests
 *
 * Location: apps/web/src/lib/__tests__/tenant-site-host.test.ts
 *
 * Full host-matrix coverage: prod domain, localhost dev, apex rejection,
 * reserved-slug rejection, port handling, multi-level subdomain rejection,
 * invalid slug rejection.
 */

import { describe, it, expect } from "vitest";
import { parseSitesHost, RESERVED_HOST_LABELS } from "../tenant-site-host";

describe("parseSitesHost", () => {
  // ── Prod domain matching ──────────────────────────────────────────────
  describe("prod domain (p4tsites.com)", () => {
    const domain = "p4tsites.com";

    it("extracts slug from a valid subdomain", () => {
      expect(parseSitesHost("lang-electric.p4tsites.com", domain)).toEqual({
        slug: "lang-electric",
      });
    });

    it("extracts slug with numbers", () => {
      expect(parseSitesHost("electric123.p4tsites.com", domain)).toEqual({
        slug: "electric123",
      });
    });

    it("extracts slug with hyphens", () => {
      expect(parseSitesHost("a-b-c.p4tsites.com", domain)).toEqual({
        slug: "a-b-c",
      });
    });

    it("rejects apex domain", () => {
      expect(parseSitesHost("p4tsites.com", domain)).toBeNull();
    });

    it("rejects www subdomain", () => {
      expect(parseSitesHost("www.p4tsites.com", domain)).toBeNull();
    });

    it("rejects multi-level subdomain", () => {
      expect(parseSitesHost("foo.bar.p4tsites.com", domain)).toBeNull();
    });

    it("rejects non-matching domain", () => {
      expect(parseSitesHost("lang-electric.example.com", domain)).toBeNull();
    });

    it("rejects pilotfortrades.com", () => {
      expect(parseSitesHost("pilotfortrades.com", domain)).toBeNull();
    });
  });

  // ── Dev localhost matching ────────────────────────────────────────────
  describe("dev localhost", () => {
    const domain = "localhost";

    it("extracts slug from {slug}.localhost", () => {
      expect(parseSitesHost("lang-electric.localhost", domain)).toEqual({
        slug: "lang-electric",
      });
    });

    it("strips port from {slug}.localhost:3000", () => {
      expect(parseSitesHost("lang-electric.localhost:3000", domain)).toEqual({
        slug: "lang-electric",
      });
    });

    it("rejects bare localhost (apex)", () => {
      expect(parseSitesHost("localhost", domain)).toBeNull();
    });

    it("rejects localhost:3000 (apex with port)", () => {
      expect(parseSitesHost("localhost:3000", domain)).toBeNull();
    });

    it("rejects www.localhost", () => {
      expect(parseSitesHost("www.localhost", domain)).toBeNull();
    });

    it("rejects non-localhost host", () => {
      expect(parseSitesHost("lang-electric.p4tsites.com", domain)).toBeNull();
    });
  });

  // ── Reserved slug rejection ───────────────────────────────────────────
  describe("reserved slugs", () => {
    const domain = "p4tsites.com";
    const reserved = [
      "www",
      "api",
      "app",
      "mail",
      "admin",
      "pilot",
      "staging",
      "dev",
      "test",
      "billing",
      "login",
      "signup",
    ];

    it.each(reserved)("rejects reserved slug: %s", (slug) => {
      expect(parseSitesHost(`${slug}.p4tsites.com`, domain)).toBeNull();
    });

    it("RESERVED_HOST_LABELS includes expected entries", () => {
      expect(RESERVED_HOST_LABELS.has("www")).toBe(true);
      expect(RESERVED_HOST_LABELS.has("api")).toBe(true);
      expect(RESERVED_HOST_LABELS.has("admin")).toBe(true);
      expect(RESERVED_HOST_LABELS.has("pilot")).toBe(true);
    });
  });

  // ── Invalid slug rejection ────────────────────────────────────────────
  describe("invalid slug formats", () => {
    const domain = "p4tsites.com";

    it("rejects slug starting with hyphen", () => {
      expect(parseSitesHost("-electric.p4tsites.com", domain)).toBeNull();
    });

    it("rejects slug ending with hyphen", () => {
      expect(parseSitesHost("electric-.p4tsites.com", domain)).toBeNull();
    });

    it("rejects slug with uppercase", () => {
      expect(parseSitesHost("LangElectric.p4tsites.com", domain)).toBeNull();
    });

    it("rejects slug with special chars", () => {
      expect(parseSitesHost("lang_electric.p4tsites.com", domain)).toBeNull();
    });

    it("accepts single-char slug (group is optional in the regex)", () => {
      // regex: ^[a-z0-9]([a-z0-9-]{1,61}[a-z0-9])?$  → group optional → 1 char OK
      expect(parseSitesHost("a.p4tsites.com", domain)).toEqual({
        slug: "a",
      });
    });

    it("rejects two-char slug (group requires min 2 chars, leaving 1 unmatched)", () => {
      expect(parseSitesHost("ab.p4tsites.com", domain)).toBeNull();
    });

    it("accepts three-char slug", () => {
      expect(parseSitesHost("abc.p4tsites.com", domain)).toEqual({
        slug: "abc",
      });
    });
  });

  // ── Edge cases ────────────────────────────────────────────────────────
  describe("edge cases", () => {
    it("returns null for empty hostname", () => {
      expect(parseSitesHost("", "p4tsites.com")).toBeNull();
    });

    it("returns null for empty domain", () => {
      expect(parseSitesHost("lang-electric.p4tsites.com", "")).toBeNull();
    });

    it("handles domain with port in config", () => {
      // If someone configures NEXT_PUBLIC_TENANT_SITES_DOMAIN=localhost:3000
      expect(
        parseSitesHost("lang-electric.localhost:3000", "localhost:3000"),
      ).toEqual({
        slug: "lang-electric",
      });
    });
  });
});
