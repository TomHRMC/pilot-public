/**
 * HelpDrawer — web — FE-B16
 *
 * Location: apps/web/src/features/help/components/HelpDrawer.tsx
 *
 * Right-side drawer (w-96 desktop / full-width on small screens).
 * Slides in from the right edge (200ms ease-out).
 * Rendered once at the authed layout level (portal-rendered).
 *
 * RULE 2: No MessagePreviewModal.
 * RULE 3: No RAG/embedding code.
 */

"use client";

import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import { HelpChatMessages } from "@pilot/ui";
import { HelpDrawerHeader } from "./HelpDrawerHeader";
import { HelpSessionListView } from "./HelpSessionListView";
import { HelpArticleCard } from "./HelpArticleCard";
import { useHelpPanel } from "../store/helpPanelStore";
import { useHelpChat } from "../hooks/useHelpChat";
import { useHelpSessionFeedback } from "../hooks/useHelpSessionFeedback";
import type { HelpChatMessage, HelpFollowUpAction } from "@pilot/ui";

// Move lazy import outside render to avoid "cannot create component during render" error
const FeedbackFormModalLazy = lazy(() =>
  import("./FeedbackFormModal").then((m) => ({ default: m.FeedbackFormModal })),
);

export function HelpDrawer() {
  const {
    isOpen,
    view,
    context,
    close,
    setView,
    setActiveSession,
    clearContext,
  } = useHelpPanel();
  const {
    messages,
    session,
    isStreaming,
    error,
    sendMessage,
    sendMessageWithContext,
  } = useHelpChat();
  const sessionFeedback = useHelpSessionFeedback(session?.session_id ?? null);

  const [activeArticleId, setActiveArticleId] = useState<string | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  // Send initial message with context when panel opens with context
  const contextSentRef = useRef<string | null>(null);
  useEffect(() => {
    if (
      isOpen &&
      context &&
      contextSentRef.current !== JSON.stringify(context)
    ) {
      contextSentRef.current = JSON.stringify(context);
      sendMessageWithContext(
        `I\u2019m on the ${context.route.split("/").pop() ?? "settings"} page and need help.`,
        context,
      );
    }
    if (!isOpen) {
      contextSentRef.current = null;
    }
  }, [isOpen, context, sendMessageWithContext]);

  const handleClose = () => {
    close();
    clearContext();
  };

  const handleToggleHistory = () => {
    setView(view === "history" ? "chat" : "history");
  };

  const handleSelectSession = (sessionId: string) => {
    setActiveSession(sessionId);
    setView("chat");
  };

  const handleFollowUpAction = (
    action: HelpFollowUpAction,
    message: HelpChatMessage,
  ) => {
    if (action === "read_full_article") {
      const firstArticleId = message.retrieved_article_ids?.[0];
      if (firstArticleId) setActiveArticleId(firstArticleId);
    } else if (action === "that_answered_it") {
      sessionFeedback.mutate("resolved");
    } else if (action === "still_confused") {
      sessionFeedback.mutate("escalated");
    } else if (action === "walk_me_through_it") {
      sendMessage("Can you walk me through this step by step?");
    }
  };

  const handleEscalate = () => {
    setShowFeedbackModal(true);
  };

  const handleRequestTts = (text: string) => {
    if (!text) return;
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-neutral-900/20"
        onClick={handleClose}
        data-testid="help-drawer-overlay"
        aria-hidden="true"
      />

      {/* Drawer panel — sm:w-96 is 384px (closest 4px-grid value to design-doc 400px) */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Help panel"
        data-testid="help-drawer"
        className="fixed top-0 right-0 z-50 h-full w-full sm:w-96 bg-white shadow-xl flex flex-col transform transition-transform duration-200 ease-out translate-x-0"
      >
        <HelpDrawerHeader
          view={view}
          onClose={handleClose}
          onToggleHistory={handleToggleHistory}
        />

        {activeArticleId ? (
          <HelpArticleCard
            articleId={activeArticleId}
            onClose={() => setActiveArticleId(null)}
          />
        ) : view === "history" ? (
          <HelpSessionListView onSelectSession={handleSelectSession} />
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col">
            <HelpChatMessages
              session={session}
              messages={messages}
              isStreaming={isStreaming}
              isLoading={false}
              error={error}
              onSendMessage={sendMessage}
              onFollowUpAction={handleFollowUpAction}
              onEscalate={handleEscalate}
              onRequestTts={handleRequestTts}
            />
          </div>
        )}

        {showFeedbackModal && (
          <Suspense fallback={null}>
            <FeedbackFormModalLazy
              fromHelpChatSessionId={session?.session_id ?? undefined}
              prefilledBody={
                session?.title
                  ? `[Auto-filled: AI help conversation \u2014 ${session.title}]\n\nThe AI wasn\u2019t able to help with my question.\n\n[Your additional notes here]`
                  : undefined
              }
              onClose={() => setShowFeedbackModal(false)}
            />
          </Suspense>
        )}
      </div>
    </>
  );
}
