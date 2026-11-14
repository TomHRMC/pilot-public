/**
 * @pilot/ui message-preview — Public API barrel
 *
 * Location: packages/ui/src/message-preview/index.ts
 *
 * Platform-resolved exports:
 *   - "react-native" condition → mobile implementations
 *   - default (web) condition → web implementations
 *
 * FE-B6: MessagePreviewModal, CustomerDisambiguationList, TimeExtractionEditor
 * ⚠️ Interfaces locked — FE-B10 depends on these.
 */

// Platform-resolved MessagePreviewModal
// The package.json exports map handles react-native vs default
export { MessagePreviewModal } from "./web/MessagePreviewModal";

// Shared components (React Native — work on both web via RN-web and mobile)
export { CustomerDisambiguationList } from "./CustomerDisambiguationList";
export { TimeExtractionEditor } from "./TimeExtractionEditor";

// Types
export type {
  MessagePreviewModalProps,
  MessagePreviewModalOverrideProps,
  FreeFormPreviewData,
  CommunicationPreviewResponse,
  CommunicationPreviewRequest,
  CommunicationSendRequest,
  CommunicationSendResponse,
  CommunicationHistoryItem,
  CommunicationHistoryResponse,
  CommTemplateTypeResponse,
  CommTemplateTypeListResponse,
  FreeFormSendResponse,
  EditableVariableResponse,
  CustomerDisambiguationListProps,
  CustomerMatch,
  TimeExtractionEditorProps,
  TimeQuickPick,
} from "./types";

export { TIME_QUICK_PICKS } from "./types";
