/**
 * FeedbackFormModal — FE-B16
 *
 * Location: apps/web/src/features/help/components/FeedbackFormModal.tsx
 *
 * Modal overlay feedback form — escalation entry point from help chat.
 * Uses plain React controlled state (no react-hook-form — incompatible with React 19).
 *
 * RULE 5: POSTs to /api/v1/feedback, not email client directly.
 */

"use client";

import React, { useState } from "react";
import { useSubmitFeedback } from "../hooks/useSubmitFeedback";
import type { FeedbackCategory } from "../types";

export interface FeedbackFormModalProps {
  fromHelpChatSessionId?: string;
  prefilledBody?: string;
  onClose: () => void;
}

const CATEGORY_OPTIONS: Array<{ value: FeedbackCategory; label: string }> = [
  { value: "bug", label: "Bug report" },
  { value: "feature_request", label: "Feature request" },
  { value: "question", label: "Question" },
  { value: "general", label: "General feedback" },
];

function validate(body: string): string | null {
  if (!body.trim()) return "Please describe your feedback";
  if (body.length > 5000) return "Maximum 5000 characters";
  return null;
}

export function FeedbackFormModal({
  fromHelpChatSessionId,
  prefilledBody = "",
  onClose,
}: FeedbackFormModalProps) {
  const submitFeedback = useSubmitFeedback();
  const [category, setCategory] = useState<FeedbackCategory>(
    fromHelpChatSessionId ? "question" : "general",
  );
  const [body, setBody] = useState(prefilledBody);
  const [fieldError, setFieldError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate(body);
    if (err) {
      setFieldError(err);
      return;
    }
    setFieldError(null);
    submitFeedback.mutate({
      category,
      body,
      from_help_chat_session_id: fromHelpChatSessionId,
    });
  };

  // Success state
  if (submitFeedback.isSuccess) {
    return (
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-neutral-900/20"
        data-testid="feedback-modal"
      >
        <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full mx-4">
          <div
            className="bg-margin-50 border border-margin-200 text-margin-700 rounded-lg p-4 text-sm text-center"
            data-testid="feedback-success-banner"
          >
            <p className="font-medium">Thanks for your feedback!</p>
            <p className="mt-1 text-margin-600">
              {submitFeedback.data?.confirmation_message}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="mt-4 w-full px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-neutral-900/20"
      data-testid="feedback-modal"
    >
      <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-neutral-800">
            Send feedback
          </h3>
          <button
            type="button"
            aria-label="Close feedback form"
            onClick={onClose}
            className="p-1 text-neutral-400 hover:text-neutral-600 rounded transition-colors"
            data-testid="feedback-modal-close"
          >
            &#10005;
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate data-testid="feedback-form">
          {/* Hidden session ID when escalating */}
          <input
            type="hidden"
            name="from_help_chat_session_id"
            value={fromHelpChatSessionId ?? ""}
            data-testid="feedback-session-id-input"
          />

          {/* Category */}
          <fieldset className="mb-4">
            <legend className="text-xs font-medium text-neutral-700 mb-2">
              Category
            </legend>
            <div className="space-y-1.5">
              {CATEGORY_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className="flex items-center gap-2 cursor-pointer"
                  data-testid={`feedback-category-${opt.value}`}
                >
                  <input
                    type="radio"
                    name="category"
                    value={opt.value}
                    checked={category === opt.value}
                    onChange={() => setCategory(opt.value)}
                    disabled={
                      !!fromHelpChatSessionId && opt.value !== "question"
                    }
                    className="text-brand-600 focus:ring-brand-300 border-neutral-300"
                  />
                  <span className="text-sm text-neutral-700">{opt.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {/* Body */}
          <div className="mb-4">
            <label
              htmlFor="feedback-modal-body"
              className="block text-xs font-medium text-neutral-700 mb-1"
            >
              Your feedback
            </label>
            <textarea
              id="feedback-modal-body"
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Describe your feedback..."
              data-testid="feedback-body-input"
              className="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-300 resize-none"
            />
            <div className="flex justify-between mt-1">
              {fieldError ? (
                <p className="text-xs text-alert-600">{fieldError}</p>
              ) : (
                <span />
              )}
              <p className="text-xs text-neutral-400">{body.length}/5000</p>
            </div>
          </div>

          {submitFeedback.isError && (
            <div className="mb-3 text-xs text-alert-600 bg-alert-50 border border-alert-200 rounded-lg px-3 py-2">
              {(submitFeedback.error as Error)?.message ??
                "Submission failed. Please try again."}
            </div>
          )}

          <button
            type="submit"
            disabled={submitFeedback.isPending}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg transition-colors"
            data-testid="feedback-submit-btn"
          >
            {submitFeedback.isPending ? "Sending\u2026" : "Send feedback"}
          </button>
        </form>
      </div>
    </div>
  );
}
