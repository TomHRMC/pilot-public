# FE-B16 Batch Design — Help System UI (Pass 4 Tier 4 #14)

**Batch**: FE-B16  
**Surface**: Help / About / Feedback  
**Date**: 2026-05-27  
**Author**: Architect  
**Status**: APPROVED — ready for React Engineer implementation  
**Design spec**: `frontend-pass-4-tier-4-flow-14-help-about-feedback-spec.md`  
**Impl plan section**: `pilot-app-mvp-frontend-impl-plan.md §6 FE-B16`  
**Backend gate**: BE-B16 (A84–A88) — backend is COMPLETE per `backend/api/routes/help.py`  
**Prerequisite batches**: FE-B3 (voice patterns LOCKED), FE-B6 (preview patterns LOCKED), FE-B11 (settings IA shell LOCKED)  
**Gates downstream**: None — FE-B16 is the final MVP frontend batch  

---

## Resolved Design Decisions

All 7 open design decisions are resolved below before the implementation sections.

### Decision 1 — Help chat panel rendering model

**Web**:  
Help is a **right-side drawer** (`w-[400px]` on desktop, full-width on tablet) that slides in from the right edge (200ms ease-out). The main app surface remains visible and interactive — users stay in context. The "?" icon in the app shell's top-right nav bar toggles this drawer open/closed from any page.

The `Settings > Help & About` sub-page (`/settings/help-and-about`) is a **full-page route** within the settings IA. It contains the combined Help + About content (see Decision 7). From that page, the "Help & support" link opens the shared `HelpDrawer` component in its non-contextual mode — same component, different entry trigger. The drawer is managed via a `useHelpPanel()` Zustand hook (global singleton) so any entry point (nav "?" icon, contextual anchor, or settings page CTA) shares a single panel state.

**Mobile**:  
Help is a **full-screen stack screen** pushed onto the navigation stack. The "Help" item in the More tab menu navigates to `/(tabs)/more/help`. Contextual anchor openers push the same route with context params in the URL. Back arrow returns to the surface the user came from.

**Context payload passing**:  
A `HelpContextProvider` wraps the authed layout. Surfaces that have contextual anchors call `useHelpContext().setContext(payload)` before opening the panel. The `HelpAnchor` component calls `setContext()` + `openPanel()` atomically. Non-contextual entry calls `clearContext()` + `openPanel()`. The context payload is stored in Zustand (ephemeral, not persisted).

**Verdict**: Web = drawer component (`HelpDrawer`). Mobile = stack screen (`HelpChatScreen`). They share `HelpChatMessages` (message list + composer) from `packages/ui`. The session history view lives **inside** the drawer/screen (a secondary view, not a separate route).

---

### Decision 2 — Voice input in help chat: single-utterance vs full session

**Voice input in the help chat composer uses `useVoiceStream` for single-utterance push-to-talk.**

The flow:
1. User taps the mic button (🎤) in the composer zone
2. `useVoiceStream` opens a WebSocket session; `VoiceState` transitions to `listening`
3. User speaks their question; stream closes on silence or manual tap
4. Transcript appears in the text input field — **user can edit before sending**
5. User taps send → dispatches to `POST /api/v1/help/chat`

This is **not** the `VoiceConfirmTurn` pattern. `VoiceConfirmTurn` is for confirming AI-proposed actions (destructive intents). In help, the user is the author — there is no AI-proposed action to confirm before sending a question. The voice input is simply dictation-to-text.

**`VoiceConfirmTurn` IS used** in exactly one place in FE-B16: the escalation confirmation. When the AI surfaces "Send this conversation as feedback?", the dismiss/confirm interaction uses `VoiceConfirmTurn` to handle voice affirmation ("yes") or cancellation.

**Voice readback of AI responses**: a small "🔊 Listen" icon renders on each AI message bubble. Tap invokes TTS via the browser `SpeechSynthesis` API (web) or `expo-speech` (mobile) with the user's effective voice persona tone (§16.5). This is thin composition — no new infrastructure.

**`useAudioCapture` vs `useVoiceStream`**: Help voice input uses `useVoiceStream` (the WebSocket hook established in FE-B3), NOT `useAudioCapture`. `useAudioCapture` is the offline-fallback recorder. Help is always online — WebSocket is appropriate.

---

### Decision 3 — Contextual help anchor placement and `context_payload` shape

**`HelpAnchor` is a shared component in `packages/ui/src/help-anchor/`.**

Justification: 14 surfaces have contextual "?" anchors (per spec Decision 1 table + arch §19.11). That exceeds the 5-surface threshold for packages/ui placement. Consistent press behavior, animation, and token usage across all 14 placements requires a single canonical component.

**14 MVP contextual anchor placements**:

| Surface | Route | Anchor location |
|:---|:---|:---|
| Settings → Integrations → QuickBooks | `/settings/integrations/quickbooks/auto-expiry` | Next to "Auto-expire" toggle AND "Sync direction" picker |
| Settings → Integrations → Calendar | `/settings/integrations/calendar` | Next to "Auto-expire" toggle |
| Settings → Notifications → Preferences | `/settings/notifications/preferences` | Inline "Why is this locked?" annotation + "?" icon |
| Settings → Sync & Storage → Background sync | `/settings/sync-storage/background-sync` | Next to "Push interval" setting |
| Settings → Voice AI → Persona tone | `/settings/voice-ai/persona-tone` | Next to the tone cards |
| Settings → Operations → Margin buckets | `/settings/operations/margin-buckets` | Next to bucket boundary editor |
| Settings → Tax configuration | (onboarding sub-flow) | Next to tax rate field |
| My Account → MFA methods | `/settings/my-account/security/mfa` | Next to each method type card |
| Field issues queue | `/dashboard/approvals/field-issues` | Next to severity class indicator |
| Calendar conflict resolution | `/settings/integrations/calendar/conflicts/[id]` | Next to deletion-conflict treatment buttons |
| QuickBooks conflict resolution | `/settings/integrations/quickbooks/conflicts/[id]` | Next to master direction indicator |
| Quote approval queue | `/quotes/pending` | Next to "Approval required" annotation |
| Onboarding — Tax setup sub-flow | `/(onboarding)/...` | Inline on jurisdiction selection |
| Settings → Subscription → SMS quota | (settings surface) | Next to "Cap policy" setting |

**`HelpContextPayload` TypeScript type** (defined in `packages/ui/src/help-anchor/types.ts`):

```typescript
export type HelpActionType =
  | 'viewed_quote' | 'created_quote' | 'accepted_quote'
  | 'viewed_invoice' | 'paid_invoice'
  | 'assigned_job' | 'completed_job'
  | 'synced_calendar' | 'viewed_qb_conflict'
  | 'opened_settings' | 'changed_setting'
  | 'viewed_mfa' | 'enrolled_mfa'
  | 'viewed_field_issue' | 'viewed_onboarding';

export interface HelpContextPayload {
  route: string;                         // Current app route, e.g. '/settings/integrations/quickbooks'
  anchor_id?: string;                    // Optional: identifies specific anchor on the surface
  entity_type?: string | null;           // Type of entity user is viewing (no entity contents)
  recent_actions: HelpActionType[];      // Last 5 minutes of action types — client-side ephemeral
  user_role: 'owner' | 'tech' | 'office_staff' | 'operator';
  tenant_metadata: {
    size: 'small' | 'medium' | 'large';
    trade: string;
  };
}
```

Privacy rule: action *types* only, never entity contents (no quote IDs, customer names, dollar amounts, etc.). Captured client-side ephemerally in Zustand. Not stored server-side.

---

### Decision 4 — Knowledge boundary UX

**Detection is client-inferred** from the `retrieved_article_ids` field in `HelpChatResponse` + a sentinel phrase in the AI response content.

The backend `HelpChatResponse` returns `retrieved_article_ids: string[]`. When the value is `[]` (empty — no RAG chunks matched), AND the AI response contains the system-prompt-injected phrase pattern (e.g., starts with "I don't have specific documentation" or similar low-confidence phrasing), the client renders the knowledge boundary state.

The backend does NOT need to return a separate boolean flag. The `retrieved_article_ids = []` is a reliable signal that RAG found nothing relevant. The client uses:

```typescript
const isKnowledgeBoundary = (response: HelpChatResponse) =>
  response.retrieved_article_ids.length === 0;
```

**Knowledge boundary message rendering**: a `KnowledgeBoundaryMessage` component in `packages/ui` renders a distinct message bubble (alert-50 background, alert-600 text, left border) with the CTA: **"Didn't find what you needed? Tell us →"**. This CTA opens the feedback form modal pre-filled with the chat context.

`KnowledgeBoundaryMessage` lives in `packages/ui` because both the web drawer and mobile screen render it. It IS a shared component.

---

### Decision 5 — Feedback intake form: standalone vs embedded

**Feedback is a shared modal overlay**, not a separate route, for the escalation path.  
**Feedback is also a standalone settings sub-page** accessible from Settings > Help & About.

Two entry surfaces:
1. **`/settings/help-and-about/feedback` (web) / mobile Settings > Send feedback** — full-page form. This is the canonical standalone entry.
2. **Escalation from help chat** — opens the `FeedbackFormModal` as a modal overlay within the help drawer/screen. Does NOT navigate away — the chat session remains accessible behind the modal. On mobile, this is a bottom sheet modal overlay. On web, a centered dialog overlay within the drawer.

When opening from escalation, the modal pre-fills:
- `category` = `"question"` (locked radio)
- `body` = `"[Auto-filled: AI help conversation — ${sessionTitle || 'Untitled session'}]\n\nThe AI wasn't able to help with my question. Please review the conversation above.\n\n[Your additional notes here]"`
- `from_help_chat_session_id` = current `session_id` (hidden field)

**Form fields per category**:

| Field | Bug report | Feature request | Question | General |
|:---|:---|:---|:---|:---|
| Category (radio) | ✓ | ✓ | ✓ | ✓ |
| Feedback text (textarea, 5000 char) | ✓ | ✓ | ✓ | ✓ |
| Reply-to email (display-only, auto-filled) | ✓ | ✓ | ✓ | ✓ |

No category-conditional fields in MVP (per spec Decision 12 — diagnostic data attachment deferred to Phase 2).

---

### Decision 6 — Help session list and session management

**The session list is a secondary view within the help panel/screen, toggled from the header.**

On web: the drawer header has a "History" icon button (clock icon). Pressing it swaps the drawer content to the session list view. Session list has "← Back to current chat" to return. No separate route.

On mobile: the help screen header has a "History" button (top-right). Tapping navigates to a sub-screen at `/(tabs)/more/help/history` within the help screen stack.

**Session navigation**: tap a session item → opens that session's full message history. User can continue the conversation from where they left off (as long as it's within the 90-day unscrubbed window).

**Session deletion**: the `DELETE /api/v1/help/sessions/{session_id}` endpoint is implemented (soft-delete via `anonymized_at`). Each session list item has a delete action (swipe-to-delete on mobile; context menu on web). Confirmation dialog required before deletion.

**Anonymization transparency notice**: displays as a fixed footer bar at the bottom of the help chat panel/screen, below the composer zone. Always visible (not dismissable). Text: "Pilot uses help conversations to improve our help content. Personal info is removed before use. [Learn more]". NOT per-message — one notice per session, always visible.

---

### Decision 7 — About page content and placement

**Route**: `/settings/help-and-about` (web) — combined Help & About sub-page in the Settings IA tree.

The page has two sections:
- **Top section — Help entry**: "Chat with our AI assistant" CTA button that opens the `HelpDrawer`. "Browse past conversations" link that opens the drawer in history mode. "Send feedback" link.
- **Bottom section — About**: version info, legal links, support email, copyright.

**Version info surfacing**:
- Web app version: `process.env.NEXT_PUBLIC_APP_VERSION` (set at build time via CI/CD; fallback `"dev"`)
- Mobile app version: `Constants.expoConfig?.version` + `Constants.expoConfig?.ios?.buildNumber` / `android.versionCode`
- API version: read from `GET /api/v1/health` response (already returns version; cached via TanStack Query, staleTime 1 hour)
- **No git commit hash** in MVP (complexity not justified; support use-case is served by the three version strings above)

**Legal links**: open an in-app `LegalDocModal` (web) or bottom-sheet modal (mobile) rendering the approved legal markdown from S3 (or app bundle as fallback). The approved copy lives in `dev-docs/marketing-analysis/approved-copy/legal/`. For MVP, the modal can render the local markdown files directly (same content as the marketing site); no separate API call required.

Documents rendered: Terms of Service, Privacy Policy, EULA, Open-source licenses (simple text list).

**About page**: present on **both web and mobile** per spec Decision 11.

---

## A — Component Implementation Plan

### A.1 New shared components in `packages/ui/src/` — locked interfaces

All three components below are cross-platform (web + mobile) and require locked interfaces before implementation begins.

#### `packages/ui/src/help-anchor/`
**`HelpAnchor`** — a "?" icon button that opens contextual help with a surface-specific `HelpContextPayload`.

```typescript
// packages/ui/src/help-anchor/types.ts

export interface HelpAnchorProps {
  /** The context payload to inject when this anchor opens help */
  contextPayload: HelpContextPayload;
  /** Accessible label for the "?" button (defaults to "Open contextual help") */
  label?: string;
  /** Size variant: 'sm' (14px icon, used inline) | 'md' (18px icon, used in cards) */
  size?: 'sm' | 'md';
  /** Optional additional className (web only) */
  className?: string;
  /** Optional testId */
  testId?: string;
}
```

Web implementation: `help-anchor/web/HelpAnchor.tsx` — renders a `<button>` with `aria-label`, calls `useHelpPanel().openWithContext(contextPayload)`.  
Mobile implementation: `help-anchor/mobile/HelpAnchor.tsx` — renders a `<Pressable>` with `accessibilityLabel`, navigates to `/(tabs)/more/help` with context payload as URL param.

Platform resolution: `help-anchor/index.ts` re-exports from the correct platform file via the existing `react-native` conditional pattern.

**⚠️ LOCKED at FE-B16.** 14 anchor placements across the codebase consume this component.

---

#### `packages/ui/src/help-chat-messages/`
**`HelpChatMessages`** — the shared message list + composer zone used by both the web drawer and the mobile screen.

```typescript
// packages/ui/src/help-chat-messages/types.ts

export interface HelpChatMessagesProps {
  /** The active help session (null while loading the first message) */
  session: HelpChatSession | null;
  /** Ordered array of messages to display */
  messages: HelpChatMessage[];
  /** Whether the AI is currently generating a response */
  isStreaming: boolean;
  /** Whether the initial session load is pending */
  isLoading: boolean;
  /** Error state if the last API call failed */
  error: Error | null;
  /** Called when the user submits a message (text or voice transcript) */
  onSendMessage: (text: string, voiceUsed?: boolean) => void;
  /** Called when the user taps a follow-up action button in an AI message */
  onFollowUpAction: (action: HelpFollowUpAction, message: HelpChatMessage) => void;
  /** Called when the user taps "Tell us →" on a knowledge boundary message */
  onEscalate: (session: HelpChatSession) => void;
  /** Called when the user taps 🔊 Listen on an AI message */
  onRequestTts: (text: string) => void;
  /** Platform-specific: padding bottom for keyboard avoidance (mobile only) */
  keyboardOffset?: number;
}

export type HelpFollowUpAction =
  | 'read_full_article'
  | 'walk_me_through_it'
  | 'that_answered_it'
  | 'still_confused';
```

Platform resolution: `help-chat-messages/web/HelpChatMessages.tsx` (uses Tailwind; renders inside a flex-col container) and `help-chat-messages/mobile/HelpChatMessages.tsx` (uses Gluestack; uses `KeyboardAvoidingView`).

**⚠️ LOCKED at FE-B16.**

---

#### `packages/ui/src/knowledge-boundary-message/`
**`KnowledgeBoundaryMessage`** — distinct message bubble for AI non-answers. Cross-platform.

```typescript
// packages/ui/src/knowledge-boundary-message/types.ts

export interface KnowledgeBoundaryMessageProps {
  /** The AI's "I don't know" response text to display */
  content: string;
  /** Timestamp of the message */
  timestamp: Date;
  /** Called when user taps "Didn't find what you needed? Tell us →" */
  onEscalate: () => void;
}
```

Web: renders with `bg-alert-50 border-l-4 border-alert-400 text-alert-700` styling.  
Mobile: renders with Gluestack `Box` using alert token equivalents.

**⚠️ LOCKED at FE-B16.**

---

### A.2 Web feature components — `apps/web/src/features/help/`

```
apps/web/src/features/help/
├── components/
│   ├── HelpDrawer.tsx                   # Right-side drawer shell (400px); manages open/close state
│   ├── HelpDrawerHeader.tsx             # "Help ✕" header + History toggle icon
│   ├── HelpSessionListView.tsx          # Session list inside the drawer (secondary view)
│   ├── HelpSessionListItem.tsx          # Single session row (title + time + delete action)
│   ├── HelpArticleCard.tsx              # Inline article render for "Read full article" action
│   ├── FeedbackFormModal.tsx            # Modal overlay feedback form (escalation entry point)
│   ├── FeedbackFormPage.tsx             # Full-page feedback form (settings entry point)
│   └── HelpAboutPage.tsx                # /settings/help-and-about combined page
├── hooks/
│   ├── useHelpChat.ts                   # TanStack Query: POST /api/v1/help/chat
│   ├── useHelpSessions.ts               # TanStack Query: GET /api/v1/help/sessions
│   ├── useHelpSessionDetail.ts          # TanStack Query: GET /api/v1/help/sessions/{id}
│   ├── useDeleteHelpSession.ts          # Mutation: DELETE /api/v1/help/sessions/{id}
│   ├── useSubmitFeedback.ts             # Mutation: POST /api/v1/feedback
│   ├── useHelpSessionFeedback.ts        # Mutation: POST /api/v1/help/sessions/{id}/feedback
│   ├── useHelpArticle.ts                # TanStack Query: GET /api/v1/help/articles/{id}
│   └── useHelpPanel.ts                  # Zustand: panel open/close + context payload state
├── store/
│   └── helpPanelStore.ts                # Zustand store for HelpPanel open/context state
└── types.ts                             # Web-local type aliases
```

Web routes:

| Route | File | Auth | Notes |
|:---|:---|:---|:---|
| `/settings/help-and-about` | `app/(authed)/settings/help-and-about/page.tsx` | All authenticated | Combined Help + About page |
| `/settings/help-and-about/feedback` | `app/(authed)/settings/help-and-about/feedback/page.tsx` | All authenticated | Standalone feedback form |

The "?" nav bar icon (global app shell): added to `apps/web/src/app/(authed)/layout.tsx` as a persistent button that calls `useHelpPanel().toggle()`. The `HelpDrawer` component is rendered once at the authed layout level (portal-rendered, like `NotificationPortal`).

---

### A.3 Mobile feature components — `apps/mobile/features/help/`

```
apps/mobile/features/help/
├── components/
│   ├── HelpSessionListScreen.tsx        # History sub-screen (stack-pushed)
│   ├── HelpSessionListItem.tsx          # Single session row
│   ├── HelpArticleBottomSheet.tsx       # Bottom sheet for "Read full article"
│   ├── FeedbackBottomSheet.tsx          # Bottom-sheet modal feedback form (escalation)
│   └── HelpAboutSection.tsx             # About content for mobile settings
├── hooks/
│   └── (same hooks as web, platform-agnostic — import from features/help/hooks/)
└── types.ts
```

Mobile routes (added to existing More tab):

| Route | File | Notes |
|:---|:---|:---|
| `/(tabs)/more/help` | `app/(tabs)/more/help/index.tsx` | Full-screen help chat screen; uses `HelpChatMessages` from packages/ui |
| `/(tabs)/more/help/history` | `app/(tabs)/more/help/history.tsx` | Help session list sub-screen |
| `/(tabs)/more/help/feedback` | `app/(tabs)/more/help/feedback.tsx` | Standalone feedback form |
| `/(tabs)/more/about` | `app/(tabs)/more/about.tsx` | About sub-screen in More settings |

Mobile settings: the existing `More` tab includes Settings and Help. The Help and About items slot into the existing More nav tree.

---

### A.4 `HelpContextProvider` + `useHelpPanel` — global authed layout

```typescript
// frontend/apps/web/src/features/help/store/helpPanelStore.ts
// Zustand store — no TanStack Query (this is client UI state)

interface HelpPanelState {
  isOpen: boolean;
  view: 'chat' | 'history';
  context: HelpContextPayload | null;
  activeSessionId: string | null;

  open: () => void;
  close: () => void;
  toggle: () => void;
  openWithContext: (payload: HelpContextPayload) => void;
  clearContext: () => void;
  setActiveSession: (id: string | null) => void;
  setView: (view: 'chat' | 'history') => void;
}
```

`HelpContextProvider` wraps `(authed)/layout.tsx` to provide `useHelpContext()` on surfaces that register contextual payloads. It reads from the same `helpPanelStore`.

---

## B — Execution Order

8-item execution order per impl plan §6 FE-B16. Each item's position is justified by dependency:

| # | Item | Est. Days | Dependency |
|:---|:---|:---:|:---|
| 1 | **Help chat panel surface** — `HelpChatMessages` (packages/ui), `HelpDrawer` (web), `HelpChatScreen` (mobile), `useHelpChat`, `helpPanelStore`. Core: message list, composer, AI response bubbles, timestamps, follow-up action buttons, streaming loading state. Web + mobile. | 3 | BE-B16 backend complete |
| 2 | **Voice integration** — compose `useVoiceStream` + mic button in `HelpChatMessages` composer zone; voice transcript populates text input; user edits; user sends. TTS readback via `SpeechSynthesis`/`expo-speech`. `VoiceConfirmTurn` for escalation confirm. | 1.5 | Item 1; FE-B3 patterns LOCKED |
| 3 | **Contextual help anchors** — `HelpAnchor` (packages/ui), `HelpContextProvider` wired into authed layout, 14 anchor placements across existing surfaces. | 2 | Item 1 (HelpDrawer must exist before anchors open it) |
| 4 | **Help session list view** — secondary view within drawer/screen (`HelpSessionListView`, `HelpSessionListScreen`), `useHelpSessions`, `useHelpSessionDetail`, `useDeleteHelpSession`. Session navigation, swipe/context-menu delete. | 1.5 | Item 1 |
| 5 | **Feedback intake form** — `FeedbackFormModal` (modal overlay from chat escalation), `FeedbackFormPage` (standalone settings page), `useSubmitFeedback`. Category radio, 5000-char textarea, reply-to display, submit + confirmation state. | 2 | Item 1 |
| 6 | **Escalation path** — `KnowledgeBoundaryMessage` (packages/ui), client-side boundary detection (`retrieved_article_ids.length === 0`), "Tell us →" CTA wiring to `FeedbackFormModal`, pre-fill logic, `from_help_chat_session_id` threading. | 1 | Items 1 + 5 |
| 7 | **About page** — `HelpAboutPage` (web, `/settings/help-and-about`), `HelpAboutSection` (mobile, More tab), version info display, `LegalDocModal` inline rendering, support email link, marketing site link. | 1 | FE-B11 settings shell |
| 8 | **Anonymization transparency notice** — fixed footer bar at bottom of `HelpChatMessages`; `useHelpSessionFeedback` mutation for "That answered it / Still confused" inline signals; session outcome tracking. | 0.5 | Item 1 |

**Total estimate**: 12.5 days (within FE-B16's 12–16 day window).

---

## C — API Contracts

All endpoints confirmed in `backend/api/routes/help.py`.

### C.1 `POST /api/v1/help/chat` — send help message

```typescript
// Request
interface HelpChatRequest {
  session_id?: string;           // UUID of existing session; null/omitted on first message
  message: string;               // User's text or voice transcript
  context_payload?: HelpContextPayload;  // Present on first message; null on continuations
}

// Response
interface HelpChatResponse {
  session_id: string;            // UUID — persisted for subsequent messages
  message_id: string;            // UUID of the assistant's response message
  role: 'assistant';
  content: string;               // AI-generated response text
  retrieved_article_ids: string[]; // Empty array = knowledge boundary trigger
  session_title: string | null;  // Auto-generated after first turn; null until generated
}
```

**Streaming**: the backend returns the full response synchronously for MVP (per spec §H / arch §19.12). HTTP streaming with token-by-token rendering is deferred to Phase 2. Client renders the full response with a typing indicator (animated dots) while polling for the response. If the backend later adds streaming, the client's `isStreaming` state supports it.

**TanStack Query key**: `['help', 'chat', session_id]`. Messages accumulated in Zustand store (local client state) and invalidated on session change.

---

### C.2 `GET /api/v1/help/sessions` — list sessions

```typescript
// Query params
interface HelpSessionsQuery {
  limit?: number;   // default 20, max 100
  offset?: number;  // default 0
}

// Response
interface HelpSessionListResponse {
  sessions: HelpSessionSummary[];
  total: number;
}

interface HelpSessionSummary {
  session_id: string;             // maps to DB field `id` (FIND-169 note)
  title: string | null;
  started_at: string;             // ISO timestamp
  last_activity_at: string;       // ISO timestamp
  message_count: number;
  outcome: 'resolved' | 'escalated' | 'abandoned' | null;
}
```

**TanStack Query key**: `['help', 'sessions']`. staleTime: 30 seconds (history doesn't change often).

---

### C.3 `GET /api/v1/help/sessions/{session_id}` — session detail

```typescript
interface HelpSessionDetailResponse {
  session_id: string;
  title: string | null;
  outcome: string | null;
  messages: HelpMessageDetail[];
}

interface HelpMessageDetail {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  context_payload: HelpContextPayload | null;
  retrieved_chunks: RetrievedChunksSummary | null;
  voice_used: boolean;
}
```

**TanStack Query key**: `['help', 'sessions', session_id]`. staleTime: 60 seconds.

---

### C.4 `DELETE /api/v1/help/sessions/{session_id}` — delete session

```typescript
interface HelpSessionDeleteResponse {
  message: 'Session deleted';
  session_id: string;
}
```

Soft-delete: sets `anonymized_at = now()`. Session disappears from list immediately via optimistic update.

---

### C.5 `POST /api/v1/help/sessions/{session_id}/feedback` — inline outcome signal

```typescript
interface HelpSessionFeedbackRequest {
  signal: 'resolved' | 'escalated' | 'abandoned';
}

interface HelpSessionFeedbackResponse {
  session_id: string;
  outcome: string;
}
```

Called when user taps "That answered it, thanks" (signal: `resolved`) or "Still confused" (signal: `escalated`). Fire-and-forget mutation; does not block UI.

---

### C.6 `GET /api/v1/help/articles/{article_id}` — full article delivery

```typescript
interface HelpArticleResponse {
  article_id: string;
  title: string;
  category: string;
  content_markdown: string;
  audience: string[];
  last_updated: string;
}
```

Called when user taps "Read full article" on an AI follow-up action button. Rendered inline in `HelpArticleCard` (web) or `HelpArticleBottomSheet` (mobile) using a markdown renderer.

**TanStack Query key**: `['help', 'articles', article_id]`. staleTime: 10 minutes (articles update infrequently).

---

### C.7 `POST /api/v1/feedback` — submit user feedback

```typescript
interface FeedbackSubmitRequest {
  category: 'bug' | 'feature_request' | 'question' | 'general';
  body: string;                              // max 5000 chars
  from_help_chat_session_id?: string;        // UUID; present when escalated from chat
}

interface FeedbackSubmitResponse {
  submission_id: string;
  category: string;
  submitted_at: string;
  confirmation_message: string;
}
```

---

## D — State Management

### D.1 Help chat UI state machine — Zustand (`helpPanelStore`)

```
idle
  ↓ user opens panel (nav icon / anchor / settings CTA)
open:chat
  ↓ user submits message
sending
  ↓ POST /api/v1/help/chat in flight
streaming                    ← UI shows animated typing indicator
  ↓ response arrives
open:chat (response rendered)
  ↓ knowledge_boundary detected
open:chat:boundary           ← KnowledgeBoundaryMessage displayed
  ↓ user taps "Tell us →"
open:escalate                ← FeedbackFormModal opens
  ↓ feedback submitted / cancelled
open:chat
  ↓ user taps "History"
open:history                 ← session list view
  ↓ user taps session
open:session-detail          ← session detail; can continue conversation
  ↓ user taps X
idle

Error states:
  sending → error:network    ← POST failed; retry CTA displayed
  streaming → error:timeout  ← stream timed out; partial response discarded
```

**TanStack Query** handles server state (sessions list, session detail, article fetch). **Zustand** handles UI panel state, active session ID, context payload, view mode.

---

### D.2 Voice dictation state in help chat — local component state

```
idle
  ↓ user taps mic
recording                    ← VoiceState: 'listening'
  ↓ silence detected or user releases mic
transcribing                 ← VoiceState: 'processing'
  ↓ transcript received
transcribed                  ← transcript inserted into text input; user can edit
  ↓ user taps send
(message dispatched — returns to sending in D.1)

error:no_speech              ← no audio detected; mic icon returns to idle
error:transcription_failed   ← NotificationBanner: "Voice capture failed. Type your question."
```

Scoped to the composer zone (`VoiceComposer` within `HelpChatMessages`). Not in Zustand. React `useState` for this local flow.

---

### D.3 Feedback form state — React Hook Form + Zod

```typescript
const feedbackSchema = z.object({
  category: z.enum(['bug', 'feature_request', 'question', 'general']),
  body: z.string().min(1, 'Please describe your feedback').max(5000, 'Maximum 5000 characters'),
  from_help_chat_session_id: z.string().uuid().optional(),
});
```

No category-conditional fields in MVP (spec Decision 12 deferred Phase 2 fields). Simple controlled form.

**Auto-save draft**: the feedback form auto-saves the draft to Zustand on blur (per Settings IA framework Decision 5 — save-on-blur pattern). Draft is cleared on successful submission.

---

### D.4 Session list pagination — TanStack Query infinite scroll

```typescript
const { data, fetchNextPage, hasNextPage } = useInfiniteQuery({
  queryKey: ['help', 'sessions'],
  queryFn: ({ pageParam = 0 }) =>
    apiClient.get('/api/v1/help/sessions', { params: { offset: pageParam, limit: 20 } }),
  getNextPageParam: (lastPage, pages) =>
    lastPage.total > pages.length * 20 ? pages.length * 20 : undefined,
});
```

Sessions grouped by recency: "Today", "Last 7 days", "Older" — same grouping as spec Decision 6.

---

## E — Error States

| Error | Trigger | UI Treatment |
|:---|:---|:---|
| AI service unavailable (Ollama down) | POST /api/v1/help/chat → 503 / 502 | `NotificationBanner` (fault severity): "Help AI is temporarily unavailable. Try again in a moment." Retry button in composer. |
| Knowledge boundary (AI has no answer) | `retrieved_article_ids.length === 0` | `KnowledgeBoundaryMessage` bubble in chat thread. CTA: "Didn't find what you needed? Tell us →". |
| Voice transcription failure | `useVoiceStream` error event | `NotificationBanner` (warning severity): "Voice capture failed. Type your question." Mic button returns to idle. |
| Feedback submission failure | POST /api/v1/feedback → 4xx/5xx | Inline form error below submit button. Draft preserved. Retry available. |
| Help session load failure | GET /api/v1/help/sessions/{id} → 404 / 5xx | `ErrorState` component within the drawer/screen chat area. "Something went wrong loading this conversation." Retry button. |
| Session list load failure | GET /api/v1/help/sessions → 5xx | `ErrorState` within the session list view. Retry button. |
| Contextual anchor — surface not recognized | `context_payload` route is null / unregistered | HelpAnchor still opens chat; payload defaults to `{ route: window.location.pathname }` without `anchor_id`. AI prompts with a generic opener. Never a hard error. |
| TTS readback failure | `SpeechSynthesis.speak()` throws / expo-speech error | Silently fails. The message text remains visible. No user-facing error (TTS is enhancement, not critical path). |
| Article fetch failure | GET /api/v1/help/articles/{id} → 4xx/5xx | Inline `ErrorState` within `HelpArticleCard`. "Article temporarily unavailable." Does not affect chat flow. |

---

## F — TypeScript Interfaces

All interfaces are non-placeholder and reflect confirmed backend schemas and locked component APIs.

```typescript
// ─── packages/ui/src/help-anchor/types.ts ─────────────────────────────────

export type HelpActionType =
  | 'viewed_quote' | 'created_quote' | 'accepted_quote'
  | 'viewed_invoice' | 'paid_invoice'
  | 'assigned_job' | 'completed_job'
  | 'synced_calendar' | 'viewed_qb_conflict'
  | 'opened_settings' | 'changed_setting'
  | 'viewed_mfa' | 'enrolled_mfa'
  | 'viewed_field_issue' | 'viewed_onboarding';

export interface HelpContextPayload {
  route: string;
  anchor_id?: string;
  entity_type?: string | null;
  recent_actions: HelpActionType[];
  user_role: 'owner' | 'tech' | 'office_staff' | 'operator';
  tenant_metadata: {
    size: 'small' | 'medium' | 'large';
    trade: string;
  };
}

export interface HelpAnchorProps {
  contextPayload: HelpContextPayload;
  label?: string;
  size?: 'sm' | 'md';
  className?: string;
  testId?: string;
}


// ─── packages/ui/src/help-chat-messages/types.ts ──────────────────────────

export type HelpFollowUpAction =
  | 'read_full_article'
  | 'walk_me_through_it'
  | 'that_answered_it'
  | 'still_confused';

export interface HelpChatMessage {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;             // ISO timestamp
  context_payload: HelpContextPayload | null;
  retrieved_article_ids?: string[]; // Derived on assistant messages; empty = knowledge boundary
  voice_used: boolean;
  is_knowledge_boundary?: boolean; // Derived client-side: true when retrieved_article_ids.length === 0
}

export interface HelpChatSession {
  session_id: string;
  title: string | null;
  started_at: string;
  last_activity_at: string;
  message_count: number;
  outcome: 'resolved' | 'escalated' | 'abandoned' | null;
}

export interface HelpChatMessagesProps {
  session: HelpChatSession | null;
  messages: HelpChatMessage[];
  isStreaming: boolean;
  isLoading: boolean;
  error: Error | null;
  onSendMessage: (text: string, voiceUsed?: boolean) => void;
  onFollowUpAction: (action: HelpFollowUpAction, message: HelpChatMessage) => void;
  onEscalate: (session: HelpChatSession) => void;
  onRequestTts: (text: string) => void;
  keyboardOffset?: number;
}


// ─── packages/ui/src/knowledge-boundary-message/types.ts ──────────────────

export interface KnowledgeBoundaryMessageProps {
  content: string;
  timestamp: Date;
  onEscalate: () => void;
}


// ─── apps/web/src/features/help/types.ts ──────────────────────────────────

export interface HelpSessionListItem {
  session_id: string;
  title: string | null;
  started_at: string;
  last_activity_at: string;
  message_count: number;
  outcome: 'resolved' | 'escalated' | 'abandoned' | null;
}

export type FeedbackCategory = 'bug' | 'feature_request' | 'question' | 'general';

export interface FeedbackSubmission {
  category: FeedbackCategory;
  body: string;
  from_help_chat_session_id?: string;
}

export interface FeedbackSubmitResult {
  submission_id: string;
  category: FeedbackCategory;
  submitted_at: string;
  confirmation_message: string;
}

export type HelpPanelView = 'chat' | 'history';

export interface HelpPanelState {
  isOpen: boolean;
  view: HelpPanelView;
  context: HelpContextPayload | null;
  activeSessionId: string | null;
  // Actions
  open: () => void;
  close: () => void;
  toggle: () => void;
  openWithContext: (payload: HelpContextPayload) => void;
  clearContext: () => void;
  setActiveSession: (id: string | null) => void;
  setView: (view: HelpPanelView) => void;
}
```

---

## G — Test Plan

**Baseline entering FE-B16** (from FE-B15):
- `@pilot/ui`: 48 files / 575 tests
- `apps/web`: 97 files / 582 tests
- `apps/mobile`: 51 suites / 324 tests

**Target delta**: +50 unit, +14 integration, +3 E2E. Final MVP totals: ~1,030 unit, ~236 integration, ~51 E2E.

### G.1 Unit tests — target 50+

**`packages/ui` tests** (Vitest):

| Test file | What it tests | Target count |
|:---|:---|:---:|
| `help-anchor/HelpAnchor.test.tsx` | renders with correct icon; calls `openWithContext` with payload; accessible label; size variants; mobile navigates with params | 8 |
| `help-chat-messages/HelpChatMessages.test.tsx` | renders message list; renders user bubble; renders AI bubble; renders `KnowledgeBoundaryMessage` when `is_knowledge_boundary`; loading skeleton; empty state (new session); follow-up action buttons; voice button present in composer | 12 |
| `knowledge-boundary-message/KnowledgeBoundaryMessage.test.tsx` | renders content; renders CTA; CTA fires `onEscalate`; correct alert token styling; timestamp displays | 5 |
| `voice/useVoiceStream-help.test.ts` | single-utterance: idle→recording→transcribed; transcript populates input; voice error → error state | 4 |

**`apps/web` tests** (Vitest):

| Test file | What it tests | Target count |
|:---|:---|:---:|
| `batch_fe_b16/helpDrawer.unit.test.tsx` | drawer opens on nav icon click; drawer closes on ✕; drawer closes on overlay click; `openWithContext` sets payload; `clearContext` on non-contextual open | 5 |
| `batch_fe_b16/helpChat.unit.test.tsx` | `useHelpChat` sends correct request; response populates messages; knowledge boundary detected on empty `retrieved_article_ids`; session_id passed on continuation; first-message session_id null | 6 |
| `batch_fe_b16/helpSessionList.unit.test.tsx` | sessions grouped Today/Last7days/Older; delete triggers confirmation; optimistic removal; empty state renders | 4 |
| `batch_fe_b16/feedbackForm.unit.test.tsx` | category radio; body max length enforced; submit disabled when empty; reply-to auto-filled; confirmation renders; from_help_chat_session_id threaded correctly | 6 |

**`apps/mobile` tests** (Jest):

| Test file | What it tests | Target count |
|:---|:---|:---:|
| `batch_fe_b16/helpChatScreen.unit.test.tsx` | screen renders; back nav; voice button accessible; composer submit | 4 |
| `batch_fe_b16/helpAbout.unit.test.tsx` | About section renders version; legal modal opens on Terms tap; support email link | 3 |

---

### G.2 Integration tests — target 14+

| Test file | Flow | Target count |
|:---|:---|:---:|
| `batch_fe_b16/helpChatFull.integration.test.tsx` | Full chat: open drawer → send message → AI responds → message renders → session persists | 4 |
| `batch_fe_b16/voiceHelpFlow.integration.test.tsx` | Mic tap → `useVoiceStream` fires → transcript in input → send → AI responds | 3 |
| `batch_fe_b16/contextualAnchor.integration.test.tsx` | Anchor on QB settings page → opens drawer → correct `context_payload` sent to API | 2 |
| `batch_fe_b16/feedbackEscalation.integration.test.tsx` | Knowledge boundary response → "Tell us →" tap → feedback modal opens pre-filled with session_id → submit → confirmation | 3 |
| `batch_fe_b16/sessionHistory.integration.test.tsx` | History button → session list renders with grouped dates → tap session → detail renders → continue conversation | 2 |

---

### G.3 E2E tests — target 3+

| Spec file | Scenario | Tooling |
|:---|:---|:---|
| `e2e/web/batch_fe_b16/help-chat-rag.e2e.spec.ts` | Open help → ask "How do I connect QuickBooks?" → real RAG response → article IDs non-empty → correct answer structure | Playwright |
| `e2e/web/batch_fe_b16/feedback-submission.e2e.spec.ts` | Open feedback form → select "Bug report" → fill text → submit → confirm email sent (Mailtrap assertion) | Playwright |
| `e2e/mobile/batch_fe_b16/help-voice-question.e2e.yaml` | Tap More → Help → tap mic → speak "How do I create a quote?" → transcript in input → tap send → AI response renders | Maestro |

---

## H — Token Audit

All colors, spacing, and typography values must use Pass 1 token classes. No hardcoded hex values. `no-hardcoded-design-values` ESLint rule is at `error` level from FE-B2 onward.

| Element | Token usage |
|:---|:---|
| **User message bubble** | `bg-brand-50 text-brand-900 rounded-lg` (right-aligned) |
| **AI message bubble** | `bg-neutral-100 text-neutral-900 rounded-lg` (left-aligned) |
| **Knowledge boundary message bubble** | `bg-alert-50 border-l-4 border-alert-400 text-alert-700` |
| **Knowledge boundary CTA link** | `text-alert-700 underline hover:text-alert-900` |
| **Streaming loading state (typing indicator)** | Animated dots using `bg-neutral-300` (3 dots, staggered scale animation) |
| **Feedback success state** | `bg-margin-50 text-margin-700` confirmation card |
| **`HelpAnchor` "?" icon — default** | `text-neutral-400 hover:text-brand-600` |
| **`HelpAnchor` "?" icon — active (panel open)** | `text-brand-600` |
| **Drawer header border** | `border-b border-neutral-200` |
| **Drawer overlay background** | `bg-neutral-900/20` (20% opacity neutral-900) |
| **Composer zone background** | `bg-white border-t border-neutral-200` |
| **Anonymization notice** | `bg-neutral-50 text-neutral-500 text-xs` |
| **"Read full article" action button** | `bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-md` |
| **"Walk me through it" action button** | `bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-md` |
| **Mic button — idle** | `text-neutral-400 hover:text-brand-600` |
| **Mic button — recording** | `text-alert-500 animate-pulse` |
| **Session list grouped header** | `text-neutral-500 text-xs font-medium uppercase tracking-wide` |
| **Session list item hover** | `hover:bg-neutral-50` |
| **Feedback category radio — selected** | `border-brand-600 text-brand-700` |
| **About page version strings** | `text-neutral-500 text-sm font-mono` |

---

## I — Final Notes (MVP Frontend Complete)

### I.1 MVP Frontend Completion Status

FE-B16 is the **final** batch. Upon completion, all 17 batches (FE-B0 through FE-B16) are complete:

| Batch | Surface | Status at FE-B16 write time |
|:---|:---|:---|
| FE-B0 | Pre-Implementation Foundation | ✅ Complete |
| FE-B1 | Component Library Foundation | ✅ Complete |
| FE-B2 | Login & Auth Shell | ✅ Complete |
| FE-B3 | Voice Quote Creation Mobile | ✅ Complete |
| FE-B4 | Dispatch Board + Profitability | ✅ Complete |
| FE-B5 | Quote Approval Workflow | ✅ Complete |
| FE-B6 | Customer Comms Outbound | ✅ Complete |
| FE-B7 | Offline Sync Mobile | ✅ Complete |
| FE-B8 | Calendar Conflict Resolution | ✅ Complete |
| FE-B9 | Tier 1 Conflict UIs + BG Sync | ✅ Complete |
| FE-B10 | Customer Comms Extension (SMS) | ✅ Complete |
| FE-B11 | Settings Foundation | ✅ Complete |
| FE-B12 | Settings Sub-Surfaces | ✅ Complete |
| FE-B13 | Onboarding & Push Permissions | ✅ Complete |
| FE-B14 | Customer-Facing Public Surfaces & Email Templates | ✅ Complete |
| FE-B15 | In-Flight Sync Indicator Refinement | ✅ Complete |
| **FE-B16** | **Help System UI** | ☐ Pending |

---

### I.2 `HelpAnchor` Placement Inventory (all 14 MVP anchors)

Each placement must be wired at implementation time. The surfaces below were implemented in earlier batches and are ready to receive `<HelpAnchor>` additions:

| # | Surface | Batch that owns the surface | `anchor_id` value |
|:---|:---|:---|:---|
| 1 | Settings → QuickBooks → Auto-expire toggle | FE-B9 / FE-B11 | `qb-auto-expire` |
| 2 | Settings → QuickBooks → Sync direction picker | FE-B9 / FE-B11 | `qb-sync-direction` |
| 3 | Settings → Integrations → Calendar → Auto-expire | FE-B8 | `calendar-auto-expire` |
| 4 | Settings → Notifications → Preferences → "Why locked?" | FE-B12 | `notification-forced-minimum` |
| 5 | Settings → Sync & Storage → Background sync → Push interval | FE-B11 | `background-sync-push-interval` |
| 6 | Settings → Voice AI → Persona tone → tone cards | FE-B12 | `voice-persona-tone` |
| 7 | Settings → Operations → Margin buckets → bucket editor | FE-B11 | `margin-bucket-editor` |
| 8 | Settings → Tax configuration → tax rate field | FE-B13 (onboarding) | `tax-rate-config` |
| 9 | My Account → MFA methods → method type card | FE-B12 | `mfa-method-type` |
| 10 | Field issues queue → severity class indicator | FE-B9 | `field-issue-severity` |
| 11 | Calendar conflict resolution → deletion-conflict buttons | FE-B8 | `calendar-deletion-conflict` |
| 12 | QuickBooks conflict resolution → master direction indicator | FE-B9 | `qb-master-direction` |
| 13 | Quote approval queue → "Approval required" annotation | FE-B5 | `quote-approval-required` |
| 14 | Onboarding → Tax setup sub-flow → jurisdiction selection | FE-B13 | `onboarding-tax-jurisdiction` |

---

### I.3 Anonymization Transparency Statement Location — LOCKED

The anonymization transparency notice is displayed as a **fixed footer bar at the bottom of the `HelpChatMessages` component**, below the composer zone and above the keyboard offset area. It is always visible while the chat panel/screen is open. It is NOT dismissable and NOT per-message. This is the single canonical location — no other surfaces show this notice.

Text (locked): `"Pilot uses help conversations to improve our help content. Personal info is removed before use."` with a `[Learn more]` link that opens the `help-article-anonymization` help article (if available in the corpus).

---

### I.4 `packages/ui/src/index.ts` Additions for FE-B16

The following exports must be appended to `frontend/packages/ui/src/index.ts` at the close of FE-B16:

```typescript
// ── FE-B16 Exports ─────────────────────────────────────────────────────────
// Help System — FINAL MVP FRONTEND BATCH
// ⚠️ HelpAnchor, HelpChatMessages, KnowledgeBoundaryMessage: LOCKED after FE-B16.

// HelpAnchor — contextual "?" icon (14 surfaces consume this)
export { HelpAnchor } from './help-anchor';
export type {
  HelpAnchorProps,
  HelpContextPayload,
  HelpActionType,
} from './help-anchor/types';

// HelpChatMessages — shared message list + composer (web drawer + mobile screen)
export { HelpChatMessages } from './help-chat-messages';
export type {
  HelpChatMessagesProps,
  HelpChatMessage,
  HelpChatSession,
  HelpFollowUpAction,
} from './help-chat-messages/types';

// KnowledgeBoundaryMessage — distinct AI non-answer bubble (web + mobile)
export { KnowledgeBoundaryMessage } from './knowledge-boundary-message';
export type {
  KnowledgeBoundaryMessageProps,
} from './knowledge-boundary-message/types';
```

---

### I.5 Phase 2 Items Deferred from FE-B16

The following items from the spec are explicitly out of FE-B16 scope. They have no stubs in the codebase unless noted:

| Deferred item | Phase 2 trigger |
|:---|:---|
| HTTP streaming with token-by-token rendering | Backend streaming infrastructure complete |
| Diagnostic data attachment on bug feedback | Product decision — volume justifies |
| Ticket system replacing email feedback intake | Volume justifies (6–12 months post-launch) |
| Multi-language help content | Multi-language UI rollout |
| Help chat session sync across devices | Observed user demand |
| Community forum | Phase 2 growth trajectory |
| AI-generated article suggestions | Help analytics pipeline available |
| Self-service help chat data deletion | `POST /api/v1/help/sessions/delete-all` stub EXISTS (returns 501 per backend) — Phase 2 wires the UI |
| Help analytics dashboard for Tom | Phase 2 tooling |
| Voice-only proactive help suggestions | Phase 2 voice system depth |
| AI confidence scoring exposed to users | Design decision pending |
| Personalized help suggestions from user history | Phase 2 recommendation engine |
| Admin UI for help content editing | S3/repo workflow for MVP; Phase 2 when authoring volume justifies |

---

### I.6 MSW Handlers Required

New MSW handler files for dev + test:

```
apps/web/src/mocks/handlers/helpHandlers.ts
  — POST /api/v1/help/chat (happy path + knowledge boundary + service error)
  — GET /api/v1/help/sessions (paginated list with grouped dates)
  — GET /api/v1/help/sessions/{id} (detail + full message history)
  — DELETE /api/v1/help/sessions/{id} (soft-delete)
  — POST /api/v1/help/sessions/{id}/feedback (resolved/escalated signals)
  — GET /api/v1/help/articles/{id} (full markdown article)
  — POST /api/v1/feedback (success + failure)

apps/mobile/mocks/handlers/helpHandlers.ts
  — Same endpoints with React Native MSW polyfill setup (mirror of web handlers)
```

Fixtures file: `apps/web/src/mocks/fixtures/helpFixtures.ts`
- 3 mock sessions (today, 3 days ago, 2 weeks ago) with titles and varied outcomes
- 10 mock messages across 2 sessions (mix of user/assistant roles)
- 1 knowledge boundary response (empty `retrieved_article_ids`)
- 1 knowledge boundary response with escalation
- 1 article with full markdown content
- Feedback submission success response

---

### I.7 Pre-Launch Hygiene Dependencies (Tom-owned)

FE-B16 implementation unblocks but does NOT complete these pre-launch items:

- **~60 help articles** authored and uploaded to `s3://pilot-help-content/en/` (Tom-owned per spec Decision 10)
- **Support email `support@pilotfortrades.com`** configured as `SUPPORT_EMAIL_ADDRESS` env var
- **`HELP_CONTENT_BUCKET`** AWS env var set to `pilot-help-content` in production environment
- **`NEXT_PUBLIC_APP_VERSION`** set in web build pipeline
- Embedding pipeline run against the initial corpus (Celery + OpenAI `text-embedding-3-small`)
- Legal document modals reviewed for accuracy against approved copy in `dev-docs/marketing-analysis/approved-copy/legal/`

---

*FE-B16 closes the MVP frontend design and implementation sequence. All 17 batches (FE-B0–FE-B16) cover the complete Pass 1–4 surface area. The implementation is ready to ship.*
