/**
 * HelpArticleCard — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpArticleCard.tsx
 *
 * Inline article render for "Read full article" follow-up action.
 * Fetches article markdown and renders it inline within the help drawer.
 */

"use client";

import React from "react";
import { useHelpArticle } from "../hooks/useHelpArticle";

interface HelpArticleCardProps {
  articleId: string;
  onClose: () => void;
}

export function HelpArticleCard({ articleId, onClose }: HelpArticleCardProps) {
  const { data: article, isLoading, error } = useHelpArticle(articleId);

  if (isLoading) {
    return (
      <div className="p-4" data-testid="help-article-loading">
        <div className="animate-pulse space-y-2">
          <div className="h-4 bg-neutral-200 rounded w-2/3" />
          <div className="h-3 bg-neutral-100 rounded w-full" />
          <div className="h-3 bg-neutral-100 rounded w-5/6" />
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="p-4 text-center" data-testid="help-article-error">
        <p className="text-sm text-neutral-500">
          Article temporarily unavailable.
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-2 text-xs text-brand-600 underline"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full" data-testid="help-article-card">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
        <div>
          <p className="text-xs text-neutral-400 uppercase tracking-wide">
            {article.category}
          </p>
          <h3 className="text-sm font-semibold text-neutral-800 mt-0.5">
            {article.title}
          </h3>
        </div>
        <button
          type="button"
          aria-label="Close article"
          onClick={onClose}
          className="p-1.5 text-neutral-400 hover:text-neutral-600 rounded-md transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Content — render markdown as pre-formatted text for MVP */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-700 leading-relaxed">
          {article.content_markdown}
        </pre>
        <p className="text-xs text-neutral-400 mt-4">
          Last updated: {new Date(article.last_updated).toLocaleDateString()}
        </p>
      </div>
    </div>
  );
}
