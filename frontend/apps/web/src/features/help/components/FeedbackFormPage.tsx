/**
 * FeedbackFormPage — FE-B16
 *
 * Location: apps/web/src/features/help/components/FeedbackFormPage.tsx
 *
 * Full-page standalone feedback form — Settings > Help & About > Send feedback.
 * Uses plain React controlled state (no react-hook-form — incompatible with React 19).
 */

"use client";

import React, { useState } from "react";
import { useSubmitFeedback } from "../hooks/useSubmitFeedback";
import type { FeedbackCategory } from "../types";

const CATEGORY_OPTIONS: Array<{
  value: FeedbackCategory;
  label: string;
  description: string;
}> = [
  {
    value: "bug",
    label: "Bug report",
    description: "Something isn\u2019t working correctly",
  },
  {
    value: "feature_request",
    label: "Feature request",
    description: "Suggest a new feature or improvement",
  },
  {
    value: "question",
    label: "Question",
    description: "I need help with something",
  },
  {
    value: "general",
    label: "General feedback",
    description: "Other feedback or thoughts",
  },
];

function validate(body: string): string | null {
  if (!body.trim()) return "Please describe your feedback";
  if (body.length > 5000) return "Maximum 5000 characters";
  return null;
}

export function FeedbackFormPage() {
  const submitFeedback = useSubmitFeedback();
  const [category, setCategory] = useState<FeedbackCategory>("general");
  const [body, setBody] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate(body);
    if (err) {
      setFieldError(err);
      return;
    }
    setFieldError(null);
    submitFeedback.mutate({ category, body });
  };

  if (submitFeedback.isSuccess) {
    return (
      <div
        className="bg-margin-50 border border-margin-200 text-margin-700 rounded-xl p-6 text-center"
        data-testid="feedback-success-banner"
      >
        <p className="text-lg">&#127881;</p>
        <p className="font-medium mt-2">Thanks for your feedback!</p>
        <p className="text-sm text-margin-600 mt-1">
          {submitFeedback.data?.confirmation_message}
        </p>
        <button
          type="button"
          onClick={() => {
            submitFeedback.reset();
            setBody("");
            setCategory("general");
          }}
          className="mt-4 text-sm text-brand-600 underline"
        >
          Send more feedback
        </button>
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      data-testid="feedback-form-page"
      className="space-y-6"
    >
      {/* Category */}
      <fieldset>
        <legend className="text-sm font-medium text-neutral-800 mb-3">
          What type of feedback?
        </legend>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {CATEGORY_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={[
                "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                category === opt.value
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-neutral-200 hover:border-neutral-300",
              ].join(" ")}
              data-testid={`feedback-category-${opt.value}`}
            >
              <input
                type="radio"
                name="category"
                value={opt.value}
                checked={category === opt.value}
                onChange={() => setCategory(opt.value)}
                className="mt-0.5 text-brand-600 focus:ring-brand-300"
              />
              <div>
                <p className="text-sm font-medium">{opt.label}</p>
                <p className="text-xs text-neutral-500 mt-0.5">
                  {opt.description}
                </p>
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Body */}
      <div>
        <label
          htmlFor="feedback-page-body"
          className="block text-sm font-medium text-neutral-800 mb-1"
        >
          Your feedback
        </label>
        <textarea
          id="feedback-page-body"
          rows={6}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Describe your feedback in detail..."
          data-testid="feedback-body-input"
          className="w-full border border-neutral-200 rounded-xl px-4 py-3 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-300 resize-none"
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
        <div className="text-sm text-alert-600 bg-alert-50 border border-alert-200 rounded-lg px-4 py-3">
          {(submitFeedback.error as Error)?.message ??
            "Submission failed. Please try again."}
        </div>
      )}

      <button
        type="submit"
        disabled={submitFeedback.isPending}
        className="px-6 py-2.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 rounded-lg transition-colors"
        data-testid="feedback-submit-btn"
      >
        {submitFeedback.isPending ? "Sending\u2026" : "Send feedback"}
      </button>
    </form>
  );
}
