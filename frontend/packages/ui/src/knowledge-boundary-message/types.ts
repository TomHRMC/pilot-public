/**
 * KnowledgeBoundaryMessage shared types — FE-B16
 *
 * Location: packages/ui/src/knowledge-boundary-message/types.ts
 *
 * Cross-platform types for the AI non-answer bubble.
 * Rendered when retrieved_article_ids.length === 0.
 * Interface is LOCKED after FE-B16.
 */

export interface KnowledgeBoundaryMessageProps {
  /** The AI's "I don't know" response text to display */
  content: string;
  /** Timestamp of the message */
  timestamp: Date;
  /** Called when user taps "Didn't find what you needed? Tell us →" */
  onEscalate: () => void;
}
