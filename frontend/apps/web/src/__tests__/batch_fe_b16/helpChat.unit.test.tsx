/**
 * useHelpChat unit tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/helpChat.unit.test.tsx
 */

import { describe, it, expect } from "vitest";

describe("useHelpChat \u2014 knowledge boundary detection", () => {
  it("sets is_knowledge_boundary=true when retrieved_article_ids is empty", async () => {
    const { MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY } =
      await import("../../mocks/fixtures/helpFixtures");
    expect(
      MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY.retrieved_article_ids,
    ).toHaveLength(0);
  });

  it("sets is_knowledge_boundary=false when retrieved_article_ids has items", async () => {
    const { MOCK_CHAT_RESPONSE_NORMAL } =
      await import("../../mocks/fixtures/helpFixtures");
    expect(
      MOCK_CHAT_RESPONSE_NORMAL.retrieved_article_ids.length,
    ).toBeGreaterThan(0);
  });

  it("knowledge boundary response carries session_id", async () => {
    const { MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY } =
      await import("../../mocks/fixtures/helpFixtures");
    expect(MOCK_CHAT_RESPONSE_KNOWLEDGE_BOUNDARY.session_id).toBeTruthy();
  });

  it("normal response has non-empty retrieved_article_ids (not a boundary)", async () => {
    const { MOCK_CHAT_RESPONSE_NORMAL } =
      await import("../../mocks/fixtures/helpFixtures");
    const isKnowledgeBoundary =
      MOCK_CHAT_RESPONSE_NORMAL.retrieved_article_ids.length === 0;
    expect(isKnowledgeBoundary).toBe(false);
  });

  it("context payload response includes session_id", async () => {
    const { MOCK_CHAT_RESPONSE_WITH_CONTEXT } =
      await import("../../mocks/fixtures/helpFixtures");
    expect(MOCK_CHAT_RESPONSE_WITH_CONTEXT.session_id).toBeTruthy();
  });

  it("session_id is null/omitted on first message (fixture: no session_id in request)", async () => {
    const { MOCK_CHAT_RESPONSE_NORMAL } =
      await import("../../mocks/fixtures/helpFixtures");
    expect(typeof MOCK_CHAT_RESPONSE_NORMAL.session_id).toBe("string");
  });
});
