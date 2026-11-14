/**
 * Contextual anchor integration tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/contextualAnchor.integration.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { HelpAnchor } from "@pilot/ui";
import type { HelpContextPayload } from "@pilot/ui";

const qbPayload: HelpContextPayload = {
  route: "/settings/integrations/quickbooks",
  anchor_id: "qb-auto-expire",
  entity_type: null,
  recent_actions: ["opened_settings", "changed_setting"],
  user_role: "owner",
  tenant_metadata: { size: "small", trade: "electrical" },
};

describe("HelpAnchor contextual integration", () => {
  it("renders ? icon on QB settings surface", () => {
    const onOpen = vi.fn();
    render(
      <div>
        <label>Auto-expire</label>
        <HelpAnchor contextPayload={qbPayload} onOpen={onOpen} />
      </div>,
    );
    expect(
      screen.getByRole("button", { name: "Open contextual help" }),
    ).toBeInTheDocument();
  });

  it("clicking anchor passes correct context_payload to onOpen handler", () => {
    const onOpen = vi.fn();
    render(<HelpAnchor contextPayload={qbPayload} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onOpen).toHaveBeenCalledWith(qbPayload);
    expect(onOpen.mock.calls[0][0]).toMatchObject({
      route: "/settings/integrations/quickbooks",
      anchor_id: "qb-auto-expire",
    });
  });

  it("payload contains only action-type fields (no entity ID / dollar amounts)", () => {
    const onOpen = vi.fn();
    render(<HelpAnchor contextPayload={qbPayload} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button"));
    const payload = onOpen.mock.calls[0][0] as HelpContextPayload;
    expect(payload.entity_type).toBeNull();
    expect(typeof payload.recent_actions[0]).toBe("string");
    expect(payload).not.toHaveProperty("quote_id");
    expect(payload).not.toHaveProperty("amount");
  });
});
