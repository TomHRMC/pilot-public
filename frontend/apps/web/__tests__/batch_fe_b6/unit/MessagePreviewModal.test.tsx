/**
 * Unit tests — MessagePreviewModal (Web)
 *
 * Location: apps/web/__tests__/batch_fe_b6/unit/MessagePreviewModal.test.tsx
 * Tests: rendering, accessibility, interactions, channel variants, voice mode
 * Target: 25 unit tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";

// Mock VoiceConfirmTurn to avoid AccessibilityInfo.announceForAccessibility
// in the web jsdom test environment — it's only available in RN native runtime
vi.mock("@pilot/ui/voice-confirm-turn", () => ({
  VoiceConfirmTurn: ({ testID }: { testID?: string }) =>
    React.createElement(
      "div",
      { "data-testid": testID ?? "voice-confirm-turn" },
      "Voice Confirm",
    ),
  useVoiceConfirmation: () => ({
    pendingConfirmation: null,
    setPendingConfirmation: vi.fn(),
    confirm: vi.fn(),
    cancel: vi.fn(),
    isConfirming: false,
  }),
}));

import { MessagePreviewModal } from "@pilot/ui";
import type {
  CommunicationPreviewResponse,
  FreeFormPreviewData,
} from "@pilot/ui";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const SMS_PREVIEW: CommunicationPreviewResponse = {
  rendered_subject: null,
  rendered_body: "Hi! I'm on my way, ETA about 20 minutes.",
  recipient_name: "Johnson Family",
  recipient_address: "+15555551234",
  actual_channel: "sms",
  editable_variables: [
    {
      name: "eta_minutes",
      value: 20,
      label: "ETA (minutes)",
      type: "time_minutes",
    },
  ],
};

const EMAIL_PREVIEW: CommunicationPreviewResponse = {
  rendered_subject: "Update from your technician",
  rendered_body: "Hi! The job is complete.",
  recipient_name: "Sarah Johnson",
  recipient_address: "sarah@example.com",
  actual_channel: "email",
  editable_variables: [],
};

const FREE_FORM_PREVIEW: FreeFormPreviewData = {
  rendered_subject: null,
  rendered_body: "I'm on my way!",
  recipient_name: "Bob Smith",
  recipient_address: "+15555559999",
  actual_channel: "sms",
  editable_variables: [],
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("MessagePreviewModal — rendering", () => {
  it("1. renders null when isOpen is false", () => {
    const { container } = render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("2. renders null when previewData is null", () => {
    const { container } = render(
      <MessagePreviewModal
        previewData={null}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("3. renders rendered_body text", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText(SMS_PREVIEW.rendered_body)).toBeInTheDocument();
  });

  it("4. renders SMS channel pill with accessible label", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Channel: sms")).toBeInTheDocument();
  });

  it("5. renders email channel pill with accessible label", () => {
    render(
      <MessagePreviewModal
        previewData={EMAIL_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Channel: email")).toBeInTheDocument();
  });

  it("6. renders subject line for email channel", () => {
    render(
      <MessagePreviewModal
        previewData={EMAIL_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(
      screen.getByText(EMAIL_PREVIEW.rendered_subject!),
    ).toBeInTheDocument();
  });

  it("7. does not render subject section for SMS channel", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByText("Subject")).not.toBeInTheDocument();
  });

  it("8. renders 'Send to [name]' in confirm button", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("preview-send-btn")).toHaveTextContent(
      "Send to Johnson Family",
    );
  });

  it("9. renders editable variable chip for each editable_variables entry", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Edit ETA (minutes): 20")).toBeInTheDocument();
  });

  it("10. no editable chips when editable_variables is empty", () => {
    render(
      <MessagePreviewModal
        previewData={EMAIL_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: /Edit ETA/i }),
    ).not.toBeInTheDocument();
  });

  it("11. renders recipient name and address", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Johnson Family")).toBeInTheDocument();
    expect(screen.getByText("+15555551234")).toBeInTheDocument();
  });
});

describe("MessagePreviewModal — button interactions", () => {
  it("12. calls onConfirm when Send button is clicked", () => {
    const onConfirm = vi.fn();
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("preview-send-btn"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("13. calls onCancel when Cancel button is clicked", () => {
    const onCancel = vi.fn();
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId("preview-cancel-btn"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("14. renders Edit button when onEdit is provided", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        onEdit={vi.fn()}
      />,
    );
    expect(screen.getByTestId("preview-edit-btn")).toBeInTheDocument();
  });

  it("15. calls onEdit when Edit button is clicked", () => {
    const onEdit = vi.fn();
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        onEdit={onEdit}
      />,
    );
    fireEvent.click(screen.getByTestId("preview-edit-btn"));
    expect(onEdit).toHaveBeenCalledOnce();
  });

  it("16. all buttons disabled when isSending is true", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        onEdit={vi.fn()}
        isSending={true}
      />,
    );
    expect(screen.getByTestId("preview-send-btn")).toBeDisabled();
    expect(screen.getByTestId("preview-cancel-btn")).toBeDisabled();
    expect(screen.getByTestId("preview-edit-btn")).toBeDisabled();
  });

  it("17. Send button shows 'Sending…' text when isSending is true", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        isSending={true}
      />,
    );
    expect(screen.getByTestId("preview-send-btn")).toHaveTextContent(
      "Sending…",
    );
  });

  it("18. Edit button not rendered when onEdit is not provided", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("preview-edit-btn")).not.toBeInTheDocument();
  });
});

describe("MessagePreviewModal — SMS segment count", () => {
  it("19. renders segment count for SMS channel", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        smsSegmentCount={1}
      />,
    );
    expect(screen.getByText("1 SMS segment")).toBeInTheDocument();
  });

  it("20. renders plural segments for count > 1", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        smsSegmentCount={3}
      />,
    );
    expect(screen.getByText("3 SMS segments")).toBeInTheDocument();
  });

  it("21. does not render segment count for email channel", () => {
    render(
      <MessagePreviewModal
        previewData={EMAIL_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        smsSegmentCount={1}
      />,
    );
    expect(screen.queryByText(/SMS segment/)).not.toBeInTheDocument();
  });
});

describe("MessagePreviewModal — voice mode", () => {
  it("22. voiceMode renders VoiceConfirmTurn, not button row", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
        voiceMode={true}
      />,
    );
    expect(screen.getByTestId("voice-confirm-in-preview")).toBeInTheDocument();
    expect(screen.queryByTestId("preview-send-btn")).not.toBeInTheDocument();
  });
});

describe("MessagePreviewModal — free-form (FE-B10 compat)", () => {
  it("23. renders free-form message body", () => {
    render(
      <MessagePreviewModal
        previewData={FREE_FORM_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("I'm on my way!")).toBeInTheDocument();
  });

  it("24. renders recipient name from free-form preview", () => {
    render(
      <MessagePreviewModal
        previewData={FREE_FORM_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("Bob Smith")).toBeInTheDocument();
  });
});

describe("MessagePreviewModal — accessibility", () => {
  it("25. modal has role='dialog' and aria-modal='true'", () => {
    render(
      <MessagePreviewModal
        previewData={SMS_PREVIEW}
        isOpen={true}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });
});
