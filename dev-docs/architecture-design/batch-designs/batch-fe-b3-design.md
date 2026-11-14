# Batch FE-B3 Design — Voice Quote Creation Mobile (Pass 3 Flow 1)

**Batch**: FE-B3  
**Date**: 2026-05-21  
**Architect**: Pilot Architect Mode  
**Status**: Phase 1 Complete — Ready for React Engineer Handoff  
**Design Spec**: `frontend-pass-3-flow-1-voice-quote-creation-spec.md` v1.0 (locked)  
**Impl Plan Reference**: `pilot-app-mvp-frontend-impl-plan.md` §6 FE-B3  
**Backend Gates**: BE-B1 (quote endpoints — partially live), BE-B2 (voice sessions + WebSocket streaming — NOT yet live)  
**Development Mode**: MSW mock-driven against both BE-B1 and BE-B2 until both are stable  

---

## Pre-Session Verification Findings

Before reading anything, the codebase state was confirmed:

| Check | Result |
|:---|:---|
| `useVoiceStream` exists? | ❌ Does not exist — new in FE-B3 |
| `VoiceConfirmTurn` exists? | ❌ Does not exist — new in FE-B3 |
| `VoiceQuotePreview` exists? | ❌ Does not exist — new in FE-B3 |
| `StructuredMessage` exists? | ❌ Does not exist — new in FE-B3 |
| Mobile tabs structure | 5 tabs: Home (`index.tsx`), Jobs, Customers, Calcs, Owner — confirmed from FE-B2 |
| `packages/ui/src/index.ts` | Contains FE-B0 + FE-B1 exports only; no voice exports |
| `api-schema.d.ts` voice endpoint | ✅ **Regenerated 2026-05-21** — `pnpm sync-api-types` run from `frontend/`. All voice session types now live: `SessionListResponse`, `SessionMessagesResponse`, `SessionMessageResponse`, `VoiceUploadResponse`, `api__routes__voice_sessions__SessionResponse`. |
| `api-schema.d.ts` quote endpoints | `GET/POST /api/v1/quotes`, `GET/PATCH /api/v1/quotes/{id}`, `POST /api/v1/quotes/{id}/lines` — all exist (BE-B1 complete) |
| `VoiceCommandResponse` schema | Exists in current schema |
| `SessionListResponse` | ✅ In `api-schema.d.ts` — fields: `sessions[]`, `next_cursor`, `has_more` |
| `SessionMessageResponse` | ✅ In `api-schema.d.ts` — fields: `message_id`, `session_id`, `role`, `content_text`, `structured_content_json` (JSONB object \| null), `created_at` |
| `VoiceUploadResponse` | ✅ In `api-schema.d.ts` — fields: `voice_command_log_id` (integer), `idempotency_uuid` (UUID), `processing_status` (string) |
| WebSocket `/api/v1/voice/stream` | NOT in openapi.json (WebSocket — cannot be described in OpenAPI 3.1); requires MSW `ws()` handler permanently |

**`pnpm sync-api-types` status**: ✅ Complete (run 2026-05-21). `frontend/packages/shared-types/src/api-schema.d.ts` is current. No pre-implementation setup required — developer can begin immediately.

**Development mode**: Most REST endpoints are live. Only the WebSocket `/api/v1/voice/stream` requires MSW. REST session endpoints can run integration tests against the real dev backend. The type stubs in §D should be replaced with `components['schemas'][...]` imports from `@pilot/shared-types` immediately.

---

## G. Open Questions Resolved (Decision Log)

*Resolved here, cross-referenced in sections A–F below.*

### Decision 1 — Voice session screen navigation

**Decision**: Voice quote creation lives as a **nested stack route within the Home tab**. The route path is `app/(tabs)/(home)/voice/[sessionId].tsx`. The session list view lives at `app/(tabs)/(home)/voice/index.tsx`. The Home tab gets a nested Expo Router `Stack` navigator. Voice does NOT replace the tab content — it pushes full-screen on top within the Home tab's stack.

**Expo Router file structure**:
```
apps/mobile/app/(tabs)/
├── _layout.tsx                    ← Tab navigator (existing, FE-B2)
├── index.tsx                      ← Home tab root (existing, FE-B2)
├── jobs.tsx                       ← Jobs tab (existing, FE-B2)
├── customers.tsx                  ← Customers tab (existing, FE-B2)
├── calcs.tsx                      ← Calcs tab (existing, FE-B2)
├── owner.tsx                      ← Owner tab (existing, FE-B2)
└── (home)/                        ← NEW: nested stack group for Home tab
    ├── _layout.tsx                ← NEW: Expo Router Stack navigator for Home
    └── voice/
        ├── index.tsx              ← NEW: voice session list view
        └── [sessionId].tsx        ← NEW: active voice session screen (chat UI)
```

**The index.tsx tab file** becomes a redirect into `(home)/` or renders the Home dashboard directly. If Expo Router's tab file and nested group conflict, the tab file becomes the home screen within the group.

**Rationale**: Keeps voice inside the Home tab's navigation context (correct mental model: voice is a primary field-tech action on Home). Avoids modal (which doesn't support resumable session history). Push-on-stack gives the correct "back to Home" affordance. Matches ChatGPT mobile pattern (sessions list as the root view; tap to enter full-screen chat).

---

### Decision 2 — `useVoiceStream()` hook location and platform split

**Decision**: The hook uses a **shared type interface** in `packages/ui/src/voice/types.ts` with **platform-specific implementations** following the existing web/mobile pattern (matching `packages/ui/src/notification-banner/web/` + `mobile/`).

```
packages/ui/src/voice/
├── types.ts                       ← Shared TypeScript interfaces (VoiceStreamEvent, UseVoiceStreamReturn, VoiceState)
├── web/
│   └── useVoiceStream.ts          ← Web Audio API + AudioWorkletNode implementation
├── mobile/
│   └── useVoiceStream.ts          ← expo-av Audio.Recording implementation
└── index.ts                       ← Resolves to web or mobile at build time
```

**Why platform-specific**: Voice audio capture is fundamentally platform-specific. Mobile uses `expo-av` (`Audio.Recording` with `setOnRecordingStatusUpdate` for 250ms chunk callbacks). Web uses `MediaRecorder` + `AudioWorkletNode`. The WebSocket connection and event handling logic is identical across platforms — only the audio capture mechanism differs. Sharing a single file with conditional logic would be unmaintainable.

**Rule 1 compliance**: Per §1.5 Rule 1, the hook lives in `packages/ui/src/voice/` (shared location) because FE-B6, FE-B10, FE-B16 will consume the exact same hook. The platform-specific implementations are an internal implementation detail of the shared module — the public API is identical.

**Why NOT `apps/mobile/src/hooks/`**: That location is for hooks only used by the mobile app across multiple surfaces. `useVoiceStream` is explicitly cross-platform (FE-B16 help voice is web + mobile).

---

### Decision 3 — Six-state voice indicator visual design and token mapping

**Decision**: The voice state machine tokens map as follows, derived from `packages/ui/src/tokens.ts` and the Flow 1 spec §12 (Amber-200 Mic Button, Contrast-Corrected):

| State | Background Token | Icon Token | Animation |
|:---|:---|:---|:---|
| `idle` | `colors.alert[200]` (#FDD997 amber-200) | `colors.alert[900]` (amber-900) | None — static |
| `listening` | `colors.alert[400]` (#F59E0B amber-400) | `colors.neutral[0]` (white) | Subtle pulse ring (scale 1.0→1.08, 800ms loop) |
| `processing` | `colors.brand[600]` (brand-indigo) | `colors.neutral[0]` (white) | Rotating spinner overlay |
| `speaking` | `colors.margin[500]` (emerald-500) | `colors.neutral[0]` (white) | Waveform bars (3 bars, bouncing) |
| `waiting-confirm` | `colors.alert[500]` (amber-500) | `colors.neutral[900]` | Slow pulsing (2s period) with confirm icon |
| `error` | `colors.fault[600]` (red-600) | `colors.neutral[0]` (white) | Brief shake (500ms, then static) |

**State machine transitions**:
```
idle ──tap──> listening ──audio-received──> processing ──intent-parsed──> speaking
                                                                            │
                                                                    if confirm-required
                                                                            ↓
                                                                    waiting-confirm
                                                                    (user says yes/no)
                                                                            │
                                                                           idle
Each state can → error (WebSocket close, Whisper timeout, etc.)
error ──retry/tap──> idle
```

**The `voiceStateTokens` object** is exported from `packages/ui/src/voice/types.ts` as a constant, consuming tokens directly. No hardcoded hex values.

---

### Decision 4 — Structured content message rendering strategy

**Decision**: A **single `<StructuredMessage>` component** with an internal switch on `entity_type`. It reads `render_mode` and delegates to sub-components. No separate `LiveQuotePreview` and `SnapshotQuotePreview` as top-level exports — they are internal to the `<VoiceQuotePreview>` component.

```tsx
// Rendering contract:
function StructuredMessage({ message }) {
  const { render_mode, content_type, data, entity_id, snapshot_payload } = message.structured_content;
  
  switch (content_type) {
    case 'quote_preview':
      return render_mode === 'live'
        ? <VoiceQuotePreview mode="live" entityId={entity_id} />
        : <VoiceQuotePreview mode="snapshot" payload={snapshot_payload} />;
    case 'job_etc_status':
      return <JobEtcStatusMessage data={data} renderMode={render_mode} />;
    case 'conflict_summary':
      return <ConflictSummaryMessage data={data} />;
    case 'text':
    default:
      return null; // plain text messages render as chat bubbles, not StructuredMessage
  }
}
```

**`entity_type` values** known from BE-B2/A12: `quote_preview`, `job_etc_status`, `conflict_summary`, `text`. For MVP, only `quote_preview` is fully implemented in FE-B3. `job_etc_status` and `conflict_summary` get stub renderers (render raw JSON in a styled card) to avoid blocking.

**Rendering contracts**:
- `live` mode: `<VoiceQuotePreview mode="live" entityId={entityId} />` calls `useQuery(['quotes', entityId])` — fetches live quote data. Shows refresh icon (small, subtle) in card corner.
- `snapshot` mode: `<VoiceQuotePreview mode="snapshot" payload={snapshotPayload} />` renders directly from the frozen JSONB payload. No API call. No refresh icon.
- Once `snapshot`, it can never become `live`. The UI renders whichever `render_mode` the backend sends. No client-side mode transition logic.

---

### Decision 5 — Deferred voice upload UI affordance

**Decision**: Use `<NotificationBanner>` from FE-B1 (persistent, non-auto-dismissing) for the offline voice affordance. Two distinct states:

**State A — Offline with queued audio**:
```tsx
<NotificationBanner
  severity="info"      // uses neutral/informational token treatment
  title="Voice captured"
  detail="Will process when you're back online."
  autoDismiss={false}  // persistent — stays until network returns
  showIcon="mic-offline"
/>
```

**State B — Reconnected, processing**:
```tsx
<NotificationBanner
  severity="info"
  title="Processing your voice command..."
  detail="Transcribing captured audio."
  autoDismiss={false}  // stays until processing completes
  showSpinner
/>
```

**State C — Processed, confirmation needed (destructive intent)**:
Push notification delivered by backend, then in-app: the voice session view shows a `<VoiceConfirmTurn>` at the bottom of the existing session's chat list with the pending confirmation prompt. This is the "open the session to confirm" pattern per §6.7.

**State D — Processed, non-destructive (read intent)**:
`<NotificationBanner severity="success" title="Voice processed" detail="{AI response}" autoDismiss />` (standard 6s dismiss).

**Why `<NotificationBanner>` not inline**: The deferred upload affordance must be visible regardless of which screen the user is on after reconnecting. `<NotificationBanner>` with portal rendering (already in the `NotificationQueueProvider`) satisfies this. The inline chat affordance (the "voice captured" placeholder bubble in the chat) is a secondary visual cue within the session screen itself.

---

### Decision 6 — Field Mode toggle: Zustand (ephemeral) vs backend preference

**Decision**: **Zustand with `AsyncStorage` persistence** for MVP. Not fetched from backend (BE-B2/A7 is the backend field for this preference, but it has not landed yet). The toggle lives in the voice session Zustand store at `apps/mobile/features/voice-quote-creation/store.ts`.

**Initial value resolution**:
1. Read from `AsyncStorage` key `pilot:fieldMode` on mount
2. Default to `false` if not set
3. Toggle writes back to `AsyncStorage` immediately
4. When BE-B2/A7 lands, the `useAuth()` user profile will carry `field_mode_preference` — at that point, the initial value is hydrated from the backend, with the local toggle still taking immediate effect

**Components affected by Field Mode**:
- `<MicButton>`: `size="xl"` → `size="2xl"` (48×48 → 64×64 px), larger hitbox
- `<VoiceSessionShell>`: shows only mic button + context chip, hides transcript history controls, hides session title editor
- `<VoiceStateIndicator>`: higher contrast (bg `alert[400]` at idle instead of `alert[200]`), larger pulse radius
- Text size: bumped one step up via Gluestack token (`$lg` → `$xl`)

**Toggle affordance**: A small "Field Mode" chip in the session header bar (top-right). Tap to toggle. Always visible regardless of Field Mode state (how else would you exit it?).

---

### Decision 7 — Voice session list view route and data display

**Decision**: `app/(tabs)/(home)/voice/index.tsx` — the session list screen within the Home tab stack. Accessible via the hamburger `☰` icon from the active session screen `voice/[sessionId].tsx`.

**Data displayed per session card**:
- Session title (from `conversation_session.title`, auto-generated or user-renamed)
- Session number + date ("`#3 · Today`", "`#1 · Yesterday`" — per-day-reset numbering per spec §5)
- Quote status pill (if the session produced a quote): `draft` / `pending_approval` / `approved` / `sent` / `no quote`
- Last turn timestamp

**Route relationship**:
```
(tabs)/index.tsx (Home tab root)
    → shows voice entry point CTA ("Start voice session" button)
    → taps into (home)/voice/index.tsx (session list)
(home)/voice/index.tsx
    → "+ New session" button → calls POST /api/v1/voice/sessions → pushes to [sessionId]
    → tap existing session → pushes to [sessionId] with sessionId param
(home)/voice/[sessionId].tsx
    → hamburger ☰ → opens drawer (SessionDrawer component) over the screen
    → back button → pops to voice/index.tsx
```

**Drawer vs Route**: The hamburger drawer that shows the session list within an active session is **not a route** — it is a `<SessionDrawer>` component (a Gluestack `Drawer` or bottom-sheet-style overlay) rendered inside `[sessionId].tsx`. This matches the ChatGPT mobile pattern. Tapping a session in the drawer closes the drawer AND navigates (replaces) the current session route.

---

### Decision 8 — MSW handler strategy for voice WebSocket mocking

**Decision**: Use MSW 2.x `ws()` handler for WebSocket mocking. The mock event sequence for the happy-path voice flow:

```typescript
// apps/mobile/mocks/handlers/voice.ts
import { ws } from 'msw';

export const voiceWsHandler = ws(
  `${process.env.EXPO_PUBLIC_WS_URL}/api/v1/voice/stream`,
  ({ client }) => {
    client.addEventListener('message', async (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === 'audio_chunk') {
        // Sequence 1: partial transcript
        await delay(150);
        client.send(JSON.stringify({
          type: 'transcript_partial',
          payload: { text: 'Create a quote for...' }
        }));
        
        // Sequence 2: final transcript
        await delay(200);
        client.send(JSON.stringify({
          type: 'transcript_final',
          payload: { text: 'Create a quote for Tom Johnson' }
        }));
        
        // Sequence 3: intent detected
        await delay(300);
        client.send(JSON.stringify({
          type: 'intent_detected',
          payload: { intent_type: 'create_quote', entities: { customer_name: 'Tom Johnson' } }
        }));
        
        // Sequence 4: response streaming
        await delay(100);
        client.send(JSON.stringify({
          type: 'response_streaming',
          payload: { text: 'Matched Tom Johnson at 42 Oak Street. Different one?' }
        }));
        
        // Sequence 5: response final with quote_preview (live mode)
        await delay(200);
        client.send(JSON.stringify({
          type: 'response_final',
          payload: {
            message_id: 'msg-001',
            text: 'Matched Tom Johnson at 42 Oak Street. Different one?',
            structured_content: {
              render_mode: 'live',
              content_type: 'quote_preview',
              entity_id: 'q-mock-001',
              snapshot_payload: null
            }
          }
        }));
      }
      
      if (msg.type === 'confirm_intent') {
        // User said "yes" to send/submit
        await delay(300);
        client.send(JSON.stringify({
          type: 'action_committed',
          payload: {
            intent_type: 'send_quote',
            quote_id: 'q-mock-001',
            snapshot_frozen: true  // triggers live→snapshot transition
          }
        }));
      }
    });
  }
);
```

**REST endpoint mocks** (for session CRUD and upload — field names match `api-schema.d.ts` confirmed types):
```typescript
// apps/mobile/mocks/handlers/voice.ts (HTTP portion)
import { http, HttpResponse } from 'msw';
import type { components } from '@pilot/shared-types';

type VoiceSessionResponse = components['schemas']['api__routes__voice_sessions__SessionResponse'];
type VoiceUploadResponse  = components['schemas']['VoiceUploadResponse'];

export const voiceHttpHandlers = [
  // GET /api/v1/voice/sessions/ — returns SessionListResponse
  http.get('/api/v1/voice/sessions/', () => HttpResponse.json({
    sessions: [
      {
        session_id: 's-001',              // ← session_id (not 'id')
        session_number: 1,
        title: 'Johnson panel upgrade',
        title_auto_generated: true,
        status: 'active',
        created_at: '2026-05-21T18:00:00Z',
        updated_at: '2026-05-21T18:05:00Z',
        archived_at: null,
        message_count: 6,
      } satisfies VoiceSessionResponse,
    ],
    next_cursor: null,
    has_more: false,
  })),

  // POST /api/v1/voice/upload-audio — returns VoiceUploadResponse
  http.post('/api/v1/voice/upload-audio', () => HttpResponse.json({
    voice_command_log_id: 42,            // ← integer (not string)
    idempotency_uuid: 'a1b2c3d4-0000-0000-0000-000000000001',
    processing_status: 'transcribing',
  } satisfies VoiceUploadResponse, { status: 202 })),
];
```

---

## A. Component Implementation Plan

### New shared components (`packages/ui/`) — established by FE-B3

| # | Component | File Path | Props Interface (summary) | Consumed By |
|:---|:---|:---|:---|:---|
| S1 | `useVoiceStream()` (mobile) | `packages/ui/src/voice/mobile/useVoiceStream.ts` | `(sessionId: string \| null) → { events, sendAudioChunk, connect, disconnect, isConnected }` | FE-B3, FE-B6, FE-B10, FE-B16 |
| S2 | `useVoiceStream()` (web) | `packages/ui/src/voice/web/useVoiceStream.ts` | Same interface as mobile | FE-B6, FE-B8, FE-B16 |
| S3 | `VoiceStreamEvent` types | `packages/ui/src/voice/types.ts` | Type defs: `VoiceState`, `VoiceStreamEvent`, `VoiceStreamEventType`, `UseVoiceStreamReturn`, `voiceStateTokens` | All voice surfaces |
| S4 | `<VoiceConfirmTurn>` | `packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx` | `{ prompt: string; onConfirm: () => void; onCancel: () => void; isProcessing?: boolean; testID?: string }` | FE-B3, FE-B6, FE-B8, FE-B10, FE-B16 |
| S5 | `useVoiceConfirmation()` | `packages/ui/src/voice-confirm-turn/useVoiceConfirmation.ts` | `() → { pendingConfirmation, setPendingConfirmation, confirm, cancel }` | Same as S4 |
| S6 | Voice module `index.ts` | `packages/ui/src/voice/index.ts` | Barrel export resolving to web or mobile impl | All voice surfaces |
| S7 | Voice confirm `index.ts` | `packages/ui/src/voice-confirm-turn/index.ts` | Barrel export | All voice confirm consumers |

### New surface-scoped components (`apps/mobile/features/voice-quote-creation/`)

| # | Component | File Path | Props Interface |
|:---|:---|:---|:---|
| M1 | `<VoiceSessionShell>` | `features/voice-quote-creation/components/VoiceSessionShell.tsx` | `{ sessionId: string; fieldMode: boolean }` |
| M2 | `<VoiceStateIndicator>` | `features/voice-quote-creation/components/VoiceStateIndicator.tsx` | `{ state: VoiceState; fieldMode?: boolean }` |
| M3 | `<MicButton>` | `features/voice-quote-creation/components/MicButton.tsx` | `{ voiceState: VoiceState; onPress: () => void; fieldMode?: boolean }` |
| M4 | `<VoiceMessageBubble>` | `features/voice-quote-creation/components/VoiceMessageBubble.tsx` | `{ message: ConversationMessage; role: 'user' \| 'assistant' }` |
| M5 | `<StructuredMessage>` | `features/voice-quote-creation/components/StructuredMessage.tsx` | `{ message: ConversationMessage }` — renders `structured_content` |
| M6 | `<VoiceQuotePreview>` | `features/voice-quote-creation/components/VoiceQuotePreview.tsx` | `{ mode: 'live' \| 'snapshot'; entityId?: string; payload?: SnapshotPayload }` |
| M7 | `<QuoteLineItemRow>` | `features/voice-quote-creation/components/QuoteLineItemRow.tsx` | `{ line: QuoteLineItem; isNew?: boolean }` |
| M8 | `<MarginCard>` | `features/voice-quote-creation/components/MarginCard.tsx` | `{ marginPct: number; tenantTargetPct: number }` |
| M9 | `<ContextChip>` | `features/voice-quote-creation/components/ContextChip.tsx` | `{ contextWindow: ContextWindowJson \| null }` |
| M10 | `<SessionDrawer>` | `features/voice-quote-creation/components/SessionDrawer.tsx` | `{ sessions: VoiceSession[]; onSelect: (id: string) => void; onNewSession: () => void; isOpen: boolean; onClose: () => void }` |
| M11 | `<SessionListItem>` | `features/voice-quote-creation/components/SessionListItem.tsx` | `{ session: VoiceSession; isActive: boolean; onPress: () => void }` |
| M12 | `<VoiceComposer>` | `features/voice-quote-creation/components/VoiceComposer.tsx` | `{ onSubmitText: (text: string) => void; voiceState: VoiceState; onMicPress: () => void; fieldMode?: boolean }` |
| M13 | `<DisambiguationList>` | `features/voice-quote-creation/components/DisambiguationList.tsx` | `{ options: DisambiguationOption[]; onSelect: (option: DisambiguationOption) => void }` |
| M14 | `<FieldModeToggle>` | `features/voice-quote-creation/components/FieldModeToggle.tsx` | `{ isEnabled: boolean; onToggle: () => void }` |

### New hooks (surface-scoped)

| # | Hook | File Path | Signature |
|:---|:---|:---|:---|
| H1 | `useVoiceSession` | `features/voice-quote-creation/hooks/useVoiceSession.ts` | `(sessionId: string) → { session, messages, isLoading, error }` — TanStack Query |
| H2 | `useVoiceSessions` | `features/voice-quote-creation/hooks/useVoiceSessions.ts` | `() → { sessions, isLoading, createSession, deleteSession }` — TanStack Query |
| H3 | `useVoiceQuoteSubmit` | `features/voice-quote-creation/hooks/useVoiceQuoteSubmit.ts` | `() → { submitQuote, isSubmitting }` — wraps `POST /api/v1/quotes/{id}/submit` |
| H4 | `useAudioCapture` | `features/voice-quote-creation/hooks/useAudioCapture.ts` | `() → { startRecording, stopRecording, isRecording, permissionGranted }` — expo-av wrapper |
| H5 | `useDeferredVoiceUpload` | `features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts` | `() → { queuedAudio, uploadWhenOnline, uploadStatus }` — offline queue manager |

### New Zustand stores

| # | Store | File Path |
|:---|:---|:---|
| Z1 | `useVoiceSessionStore` | `features/voice-quote-creation/store.ts` |

**`useVoiceSessionStore` shape**:
```typescript
interface VoiceSessionStore {
  voiceState: VoiceState;
  currentSessionId: string | null;
  fieldMode: boolean;
  pendingConfirmation: PendingConfirmation | null;
  transcriptBuffer: string;       // partial transcript for entity highlighting
  setVoiceState: (state: VoiceState) => void;
  setSessionId: (id: string | null) => void;
  setFieldMode: (enabled: boolean) => void;
  setPendingConfirmation: (confirmation: PendingConfirmation | null) => void;
  setTranscriptBuffer: (text: string) => void;
  reset: () => void;
}
```

### New routes

| Route | File | Description |
|:---|:---|:---|
| `/(tabs)/(home)/_layout.tsx` | `apps/mobile/app/(tabs)/(home)/_layout.tsx` | Expo Router Stack navigator for Home tab |
| `/(tabs)/(home)/voice/index` | `apps/mobile/app/(tabs)/(home)/voice/index.tsx` | Voice session list |
| `/(tabs)/(home)/voice/[sessionId]` | `apps/mobile/app/(tabs)/(home)/voice/[sessionId].tsx` | Active voice session chat |

---

## B. Execution Order

Implementation sequence with intra-batch dependency rationale:

| Step | Item | Dependency Rationale |
|:---:|:---|:---|
| 1 | **Zustand store** (`useVoiceSessionStore`) | All components read from this store; must exist first |
| 2 | **Voice types** (`packages/ui/src/voice/types.ts`) | Shared types needed by hook and all components |
| 3 | **`useAudioCapture` hook** | Needed by `useVoiceStream` mobile impl; tests audio permission flow independently |
| 4 | **`useVoiceStream()` mobile implementation** | Core data pipeline; everything else subscribes to its events |
| 5 | **MSW WebSocket + HTTP handlers** for voice | Must exist before any component integration test can run |
| 6 | **`<VoiceStateIndicator>` + `<MicButton>`** | Simplest visual components; validate token consumption and state machine before UI shell |
| 7 | **`<VoiceSessionShell>`** | Composes indicator + mic; the page-level container |
| 8 | **`<VoiceComposer>`** (text + mic) | Bottom input bar; composed into Shell |
| 9 | **`<ContextChip>`** | Read from session context_window_json; small, composable |
| 10 | **Route: `[sessionId].tsx`** | Wire shell + composer + context chip into a routed page |
| 11 | **`<VoiceMessageBubble>`** | Chat message rendering without structured content first |
| 12 | **`<StructuredMessage>` + `<VoiceQuotePreview>` (snapshot mode)** | Snapshot mode first — no API call required; validates the frozen rendering path |
| 13 | **`useVoiceSession` TanStack Query hook** | Fetches session + messages from API (or MSW) |
| 14 | **`<VoiceQuotePreview>` (live mode)** | Adds `useQuery` for live entity fetch; extends snapshot component |
| 15 | **`<QuoteLineItemRow>` + `<MarginCard>`** | Sub-components of quote preview; validate margin token colors |
| 16 | **`<VoiceConfirmTurn>` + `useVoiceConfirmation()`** (shared, `packages/ui/`) | Established as shared module; must land here for downstream batch consumption |
| 17 | **Quote submission flow** (`useVoiceQuoteSubmit`) | Calls `POST /api/v1/quotes` then triggers snapshot freeze |
| 18 | **`<SessionDrawer>` + `<SessionListItem>`** | Hamburger session history; depends on sessions data shape |
| 19 | **`useVoiceSessions` hook** + **Route: `voice/index.tsx`** | Session list view |
| 20 | **Route: `(home)/_layout.tsx`** + integration wiring | Final routing wiring |
| 21 | **`useDeferredVoiceUpload`** + offline affordance via `<NotificationBanner>` | Deferred path; depends on all online paths working first |
| 22 | **`<DisambiguationList>`** | Edge case UI; land after happy path confirmed |
| 23 | **`<FieldModeToggle>`** + Field Mode behavior pass | Thin layer atop everything else |
| 24 | **`useVoiceStream()` web implementation** | Web impl can trail mobile by 1–2 steps since FE-B3 is mobile-primary |

---

## C. New Routes

| Route | Expo Router File | Auth Required | RBAC Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/(tabs)/(home)/_layout` | `apps/mobile/app/(tabs)/(home)/_layout.tsx` | Yes | `<RequireAuth>` inherited from `(tabs)/_layout` | Stack navigator for Home subtree |
| `/(tabs)/(home)/voice` | `apps/mobile/app/(tabs)/(home)/voice/index.tsx` | Yes | `useRequiresPermission('voice.use')` | Session list — hide if no voice permission |
| `/(tabs)/(home)/voice/[sessionId]` | `apps/mobile/app/(tabs)/(home)/voice/[sessionId].tsx` | Yes | `<RoleGate role={['owner', 'technician', 'office_staff']}>` | Active voice session; all authed roles with `voice.use` |

**Permission key**: `voice.use` is defined in `packages/ui/src/role-gate/permissions.ts` and granted to `owner`, `technician`, and `office_staff` roles per `mvp-arch.md` §4.3.

**Expo Router nesting note**: Introducing `(home)/` as a nested group requires updating `apps/mobile/app/(tabs)/_layout.tsx` to reference the `(home)` group. The existing `(tabs)/index.tsx` becomes the entry point into the `(home)` group (or is replaced by `(home)/_layout.tsx` rendering the Home dashboard as its initial route). Per Expo Router conventions, the `(home)` route group is transparent in the URL — the tab still shows as "Home."

---

## D. API Endpoint Consumption

### REST endpoints (via `apiClient`)

| Endpoint | TanStack Query Hook | MSW Handler | Backend Batch |
|:---|:---|:---|:---|
| `GET /api/v1/voice/sessions` | `useVoiceSessions()` | `voiceHttpHandlers[0]` in `mocks/handlers/voice.ts` | BE-B2 (not yet live → MSW) |
| `POST /api/v1/voice/sessions` | `useVoiceSessions().createSession()` | `voiceHttpHandlers[1]` | BE-B2 (MSW) |
| `DELETE /api/v1/voice/sessions/{id}` | `useVoiceSessions().deleteSession()` | MSW stub | BE-B2 (MSW) |
| `GET /api/v1/voice/sessions/{id}/messages` | `useVoiceSession(sessionId)` | MSW — returns array of `ConversationMessage` stubs | BE-B2 (MSW) |
| `POST /api/v1/voice/upload-audio` | `useDeferredVoiceUpload().uploadWhenOnline()` | `voiceHttpHandlers[2]` — returns 202 with `processing_status` | BE-B2 (MSW) |
| `GET /api/v1/quotes/{id}` | `useQuery(['quotes', id])` inside `VoiceQuotePreview` live mode | Existing MSW handler from quote surface | BE-B1 (live) |
| `POST /api/v1/quotes` | `useVoiceQuoteSubmit().submitQuote()` | Existing MSW handler | BE-B1 (live) |
| `PATCH /api/v1/quotes/{id}` | `useVoiceQuoteSubmit()` for draft updates | Existing MSW handler | BE-B1 (live) |
| `GET /api/v1/quotes/{id}/lines` | Within `VoiceQuotePreview` live mode | Existing MSW handler | BE-B1 (live) |

### WebSocket endpoint

| Endpoint | Hook | MSW Handler | Notes |
|:---|:---|:---|:---|
| `WS /api/v1/voice/stream?session_id={id}` | `useVoiceStream(sessionId)` | `voiceWsHandler` via `msw` 2.x `ws()` | BE-B2 deliverable — 100% MSW in FE-B3 |

**Type stubs for BE-B2 endpoints** (to be deleted when `pnpm sync-api-types` delivers real types):

```typescript
// apps/mobile/features/voice-quote-creation/types-stub.ts
// ⚠️  RUN `pnpm sync-api-types` FIRST — most of these types are now live in backend/openapi.json.
// After sync, replace usages with the generated types from @pilot/shared-types:
//   components['schemas']['api__routes__voice_sessions__SessionResponse']  → VoiceSession
//   components['schemas']['SessionMessageResponse']                        → ConversationMessage
//   components['schemas']['SessionListResponse']                           → session list
//   components['schemas']['SessionMessagesResponse']                       → messages list
//   components['schemas']['VoiceUploadResponse']                           → upload response
// Only StructuredContent and SnapshotPayload (JSONB shapes) remain untyped — keep those stubs.

// ----- WILL BE GENERATED BY pnpm sync-api-types (kept here for stub phase) -----

export interface VoiceSession {
  session_id: string;           // ← confirmed field name (NOT 'id')
  session_number: number;
  title: string | null;
  title_auto_generated: boolean;
  status: string;               // ← confirmed live field
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  message_count: number;        // ← confirmed live field (default: 0)
}

export interface ConversationMessage {
  message_id: string;           // ← confirmed field name (NOT 'id')
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content_text: string;         // ← confirmed field name (NOT 'content')
  structured_content_json: StructuredContent | null;  // ← confirmed (NOT 'structured_content')
  created_at: string;
}

export interface VoiceUploadResponse {
  voice_command_log_id: number; // ← integer (NOT string UUID)
  idempotency_uuid: string;
  processing_status: string;    // 'pending_upload' | 'transcribing' | 'completed' | 'failed'
}

// ----- THESE REMAIN UNTYPED (JSONB object shapes — not in OpenAPI schema) -----

export interface StructuredContent {
  render_mode: 'live' | 'snapshot';
  content_type: 'quote_preview' | 'job_etc_status' | 'conflict_summary' | 'text';
  entity_id: string | null;
  snapshot_payload: SnapshotPayload | null;
  captured_at: string;
}

export interface SnapshotPayload {
  quote_id: string;
  customer_name: string;
  total_cents: number;
  margin_pct: number;
  line_items: QuoteLineItem[];
  style: 'component' | 'deliverable' | 'lump_sum';
}
```

---

## E. Pattern Reuse Decisions

### Patterns consumed from FE-B0/B1/B2 (already in `packages/ui/`)

| Pattern | Import Path | Usage in FE-B3 |
|:---|:---|:---|
| `useAuth()` | `@pilot/ui/auth` | Check `voice.use` permission before showing voice UI; get user role for "Submit vs Send" button text |
| `<RoleGate>` | `@pilot/ui/role-gate` | Wrap voice entry point; wrap "Send" button (owner only) vs "Submit for Approval" button (tech) |
| `useRequiresPermission('voice.use')` | `@pilot/ui/role-gate` | Hide voice tab route if user lacks `voice.use` |
| `<EmptyState type="no-data">` | `@pilot/ui/states` | Voice session list when no sessions exist |
| `<LoadingState type="full-page">` | `@pilot/ui/states` | Voice session loading initial fetch |
| `<ErrorState type="network">` | `@pilot/ui/states` | WebSocket connection failure |
| `<NotificationBanner>` + `useNotificationQueue` | `@pilot/ui/notification-banner` | Offline voice affordance (Decision 5); disambiguation disambiguation result; submission success/failure |
| `apiClient` | `@pilot/shared-api` | All REST calls; JWT header auto-attached |

### Patterns established by FE-B3 (shared modules for downstream consumption)

| Pattern | Where Established | Downstream Consumers |
|:---|:---|:---|
| `useVoiceStream()` hook + types | `packages/ui/src/voice/` | FE-B5 (voice approval), FE-B6 (comms voice), FE-B8 (calendar voice), FE-B10 (SMS reply voice), FE-B16 (help voice) |
| `<VoiceConfirmTurn>` + `useVoiceConfirmation()` | `packages/ui/src/voice-confirm-turn/` | FE-B6 (comms send confirm), FE-B8 (calendar resolve confirm), FE-B10 (SMS reply confirm), FE-B16 (help escalation confirm) |
| `VoiceState` machine type | `packages/ui/src/voice/types.ts` | All downstream voice surfaces reuse the same 6-state type |
| `voiceStateTokens` constant | `packages/ui/src/voice/types.ts` | All downstream voice indicators reuse same token mapping |
| Deferred voice upload pattern | `features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts` | FE-B7 fully wires this into the sync orchestrator; FE-B3 establishes the upload endpoint mechanics |

### Pattern NOT consumed in FE-B3 (established in later batches)

| Pattern | Established In | Why Not FE-B3 |
|:---|:---|:---|
| `<DiffView>` | FE-B5 | No diff views in voice quote creation |
| `useStalenessRetry()` | FE-B4 | Quote submission doesn't require staleness check in FE-B3 scope |
| `<MessagePreviewModal>` | FE-B6 | Not in voice quote scope (customer comms only) |
| `<PendingBadge>` | FE-B7 | Offline sync badge patterns not in FE-B3 |

---

## F. Shared Module Interfaces

### `packages/ui/src/voice/types.ts`

```typescript
// packages/ui/src/voice/types.ts

export type VoiceState =
  | 'idle'
  | 'listening'
  | 'processing'
  | 'speaking'
  | 'waiting-confirm'
  | 'error';

export type VoiceStreamEventType =
  | 'transcript_partial'
  | 'transcript_final'
  | 'intent_detected'
  | 'response_streaming'
  | 'response_final'
  | 'action_committed'
  | 'snapshot_frozen'
  | 'error';

export interface VoiceStreamEvent {
  type: VoiceStreamEventType;
  payload: {
    text?: string;
    intent_type?: string;
    entities?: Record<string, unknown>;
    message_id?: string;
    structured_content?: {
      render_mode: 'live' | 'snapshot';
      content_type: string;
      entity_id?: string | null;
      snapshot_payload?: Record<string, unknown> | null;
    };
    quote_id?: string;
    snapshot_frozen?: boolean;
    error_code?: string;
    error_message?: string;
  };
}

export interface UseVoiceStreamReturn {
  /** All events received since connection opened */
  events: VoiceStreamEvent[];
  /** Latest partial transcript text (for entity highlighting) */
  transcriptBuffer: string;
  /** Send a base64-encoded audio chunk to the WebSocket */
  sendAudioChunk: (chunkBase64: string) => void;
  /** Open the WebSocket connection */
  connect: () => void;
  /** Close the WebSocket connection */
  disconnect: () => void;
  /** Whether the WebSocket is currently open */
  isConnected: boolean;
  /** Clear all accumulated events (e.g., on new session) */
  clearEvents: () => void;
}

/**
 * Token mapping for the 6-state voice indicator.
 * Consumes tokens from packages/ui/src/tokens.ts.
 * Never hardcode these values — import voiceStateTokens instead.
 */
export const voiceStateTokens: Record<VoiceState, {
  bgToken: string;
  iconToken: string;
  label: string;
  accessibilityLabel: string;
}> = {
  'idle':           { bgToken: '$alert-200',   iconToken: '$alert-900',   label: 'Tap to talk',     accessibilityLabel: 'Start voice input' },
  'listening':      { bgToken: '$alert-400',   iconToken: '$white',       label: 'Listening...',    accessibilityLabel: 'Listening — tap to stop' },
  'processing':     { bgToken: '$brand-600',   iconToken: '$white',       label: 'Processing...',   accessibilityLabel: 'Processing your voice command' },
  'speaking':       { bgToken: '$margin-500',  iconToken: '$white',       label: 'Speaking...',     accessibilityLabel: 'AI is speaking' },
  'waiting-confirm':{ bgToken: '$alert-500',   iconToken: '$neutral-900', label: 'Confirm?',        accessibilityLabel: 'Voice command waiting for confirmation' },
  'error':          { bgToken: '$fault-600',   iconToken: '$white',       label: 'Try again',       accessibilityLabel: 'Voice error — tap to retry' },
};
```

### `packages/ui/src/voice/index.ts`

```typescript
// packages/ui/src/voice/index.ts
// Resolves to platform-specific implementation at build time

export type {
  VoiceState,
  VoiceStreamEventType,
  VoiceStreamEvent,
  UseVoiceStreamReturn,
} from './types';
export { voiceStateTokens } from './types';

// Platform-resolved hook — consumers import from '@pilot/ui/voice'
export { useVoiceStream } from './mobile/useVoiceStream';
// web build: export { useVoiceStream } from './web/useVoiceStream';
```

### `packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx`

```typescript
// packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.tsx

export interface VoiceConfirmTurnProps {
  /**
   * The confirmation prompt text to display (AI's summary of the pending action).
   * Example: "Send the Johnson panel quote to tom@johnson.example.com?"
   */
  prompt: string;
  /**
   * Called when user provides affirmative response (voice "yes" or tap).
   */
  onConfirm: () => void;
  /**
   * Called when user provides non-affirmative response (voice "no", "cancel", or dismiss tap).
   */
  onCancel: () => void;
  /**
   * Whether the confirm action is in-flight (mutation pending).
   * Disables both buttons while true.
   */
  isProcessing?: boolean;
  /** For Maestro/Detox e2e targeting */
  testID?: string;
}
```

### `packages/ui/src/voice-confirm-turn/useVoiceConfirmation.ts`

```typescript
// packages/ui/src/voice-confirm-turn/useVoiceConfirmation.ts

export interface PendingConfirmation {
  intentId: string;
  prompt: string;
  expiresAt: string;
}

export interface UseVoiceConfirmationReturn {
  pendingConfirmation: PendingConfirmation | null;
  setPendingConfirmation: (confirmation: PendingConfirmation | null) => void;
  /** Execute the confirmed action — clears pending state */
  confirm: (intentId: string, executeAction: () => Promise<void>) => Promise<void>;
  /** Cancel the pending action — clears pending state */
  cancel: () => void;
  /** Whether confirmation is currently processing */
  isConfirming: boolean;
}

export function useVoiceConfirmation(): UseVoiceConfirmationReturn;
```

### `apps/mobile/features/voice-quote-creation/components/VoiceQuotePreview.tsx`

```typescript
// Surface-scoped (not shared — FE-B5 extends this for quote approval)

export interface SnapshotPayload {
  quote_id: string;
  customer_name: string;
  customer_address?: string;
  total_cents: number;
  margin_pct: number;
  line_items: Array<{
    id: string;
    description: string;
    quantity: number;
    unit_price_cents: number;
    total_cents: number;
    is_new?: boolean;   // highlight recently-added line in "live" mode
  }>;
  style: 'component' | 'deliverable' | 'lump_sum';
  is_tech_role: boolean;  // drives "Submit for Approval" vs "Send" label
  submitted_at?: string;  // present when snapshot was frozen on submission
}

export interface VoiceQuotePreviewProps {
  mode: 'live' | 'snapshot';
  /** Present when mode === 'live' — used to fetch current quote data */
  entityId?: string;
  /** Present when mode === 'snapshot' — render from frozen payload */
  payload?: SnapshotPayload;
  /** Called when user taps submit/send button */
  onSubmit?: (quoteId: string) => void;
  /** Hide the submit button (e.g., in historical review contexts) */
  readOnly?: boolean;
}
```

### `apps/mobile/features/voice-quote-creation/components/StructuredMessage.tsx`

```typescript
// Surface-scoped — not shared (content is voice-session specific)

export interface StructuredMessageProps {
  message: {
    id: string;
    structured_content: {
      render_mode: 'live' | 'snapshot';
      content_type: 'quote_preview' | 'job_etc_status' | 'conflict_summary' | 'text';
      entity_id: string | null;
      snapshot_payload: Record<string, unknown> | null;
    };
  };
  /** Called when user taps submit/send inside a quote card */
  onQuoteSubmit?: (quoteId: string) => void;
}
```

---

## H. External Dependency Status

| Dependency | Required For | Status | Mock Strategy | Tom Action Required |
|:---|:---|:---|:---|:---|
| **BE-B2 voice sessions API** (`/api/v1/voice/sessions`, `stream` WS, `upload-audio`) | Core voice functionality | ❌ Not yet built | MSW handlers in `apps/mobile/mocks/handlers/voice.ts` | Monitor BE-B2 progress; run `pnpm sync-api-types` when BE-B2 ships |
| **BE-B1 quote endpoints** | `VoiceQuotePreview` live mode, quote submission | ✅ Live in dev | Real integration tests against dev backend | None |
| **`expo-av` microphone recording** | `useAudioCapture` on real device | ✅ Installed (Expo SDK 54) | Mocked with `jest.mock('expo-av')` in unit tests | Must test on real device — iOS simulator does not pass audio |
| **iOS microphone permission** | `expo-av` `Audio.requestPermissionsAsync()` | ⚠️ Requires real device test | Grant in simulator settings for dev; test actual grant/deny flow on device | None — EAS preview build handles this |
| **WatermelonDB** (deferred voice queue) | `useDeferredVoiceUpload` offline queueing | ❌ Not yet built (FE-B7) | Stub with `AsyncStorage` in FE-B3; FE-B7 replaces with WatermelonDB | FE-B7 owns WatermelonDB — FE-B3 stubs the queue interface |
| **Network reachability detection** | Offline/online transition for deferred upload | ⚠️ `@react-native-community/netinfo` | Mock `useNetInfo` in tests | `pnpm add @react-native-community/netinfo` if not already installed |
| **Ollama session title generation** | Auto-generated session titles | Part of BE-B2 | Mock returns fixed title `"Johnson panel upgrade"` | None (backend concern) |

### WatermelonDB stub for deferred voice (FE-B3 only)

Because FE-B7 owns WatermelonDB, FE-B3 stubs the deferred voice queue with a simple `AsyncStorage`-backed queue:

```typescript
// apps/mobile/features/voice-quote-creation/hooks/useDeferredVoiceUpload.ts
// STUB — FE-B7 will replace the queue persistence with WatermelonDB

interface QueuedAudioItem {
  id: string;
  sessionId: string;
  audioPath: string;
  capturedAt: string;
  idempotencyKey: string;
}
```

When FE-B7 ships, the `useDeferredVoiceUpload` hook's queue persistence is upgraded to WatermelonDB without changing the hook's public API. Consumers of the hook see no change.

---

## I. Test Plan

### Unit Test Targets (minimum 70)

**`packages/ui/src/voice/types.test.ts`** (4 tests):
- `voiceStateTokens` has entries for all 6 states
- Each state entry has `bgToken`, `iconToken`, `label`, `accessibilityLabel`
- No hardcoded hex values in `voiceStateTokens` (tokens start with `$`)
- Token names match expected format (`$alert-200`, `$brand-600`, etc.)

**`packages/ui/src/voice-confirm-turn/VoiceConfirmTurn.test.tsx`** (8 tests):
- Renders prompt text
- "Confirm" button calls `onConfirm`
- "Cancel" button calls `onCancel`
- Both buttons disabled when `isProcessing={true}`
- Has correct ARIA labels on both buttons
- `testID` applied to container
- Dismissing via accessibility escape calls `onCancel`
- Does not call `onConfirm` when cancelled before processing

**`packages/ui/src/voice-confirm-turn/useVoiceConfirmation.test.ts`** (6 tests):
- Initial state: `pendingConfirmation` is null, `isConfirming` is false
- `setPendingConfirmation` updates state
- `confirm` executes action and clears pending state
- `cancel` clears pending state without executing action
- `confirm` sets `isConfirming` during async action execution
- `confirm` clears `isConfirming` after action resolves

**`features/voice-quote-creation/components/VoiceStateIndicator.test.tsx`** (8 tests):
- Each of 6 states renders the correct background token class
- `idle` state renders mic icon
- `listening` state renders pulse animation element
- `processing` state renders spinner element
- `speaking` state renders waveform element
- `waiting-confirm` state renders confirm icon
- `error` state renders error icon
- `fieldMode={true}` applies larger variant

**`features/voice-quote-creation/components/MicButton.test.tsx`** (5 tests):
- Renders with correct `accessibilityLabel` per voice state
- `onPress` fires on tap
- Has `testID="voice-trigger-btn"` (Maestro e2e dependency)
- Minimum 44×44 px touch target enforced (`size` prop validation)
- `fieldMode` increases to 64×64 px

**`features/voice-quote-creation/components/VoiceQuotePreview.test.tsx`** (12 tests):
- **Snapshot mode**: renders `customer_name`, `total_cents` as currency, margin pct
- **Snapshot mode**: renders up to 5 line items (6th hidden with "+N more" indicator)
- **Snapshot mode**: margin emerald background when `margin_pct >= 20`
- **Snapshot mode**: margin amber background when `margin_pct < 20`
- **Snapshot mode**: renders "Submit for approval" when `is_tech_role = true`
- **Snapshot mode**: renders "Send" when `is_tech_role = false`
- **Snapshot mode**: no submit button when `readOnly={true}`
- **Live mode**: calls `useQuery(['quotes', entityId])` — shows `<LoadingState>` during fetch
- **Live mode**: renders live data from mock API response
- **Live mode**: shows refresh indicator icon
- **Live → snapshot invariant**: once `mode='snapshot'`, no re-render to `live` (tested via props update)
- **Component style**: flat line items visible; Deliverable style shows parent lines; Lump-sum shows single line

**`features/voice-quote-creation/components/StructuredMessage.test.tsx`** (5 tests):
- `content_type: 'quote_preview'` + `render_mode: 'live'` renders `<VoiceQuotePreview mode="live">`
- `content_type: 'quote_preview'` + `render_mode: 'snapshot'` renders `<VoiceQuotePreview mode="snapshot">`
- `content_type: 'job_etc_status'` renders stub card (no crash)
- `content_type: 'conflict_summary'` renders stub card (no crash)
- Unknown `content_type` renders null without crashing

**`features/voice-quote-creation/components/MarginCard.test.tsx`** (4 tests):
- Renders margin percentage
- Emerald background when `marginPct >= tenantTargetPct`
- Amber background when `marginPct < tenantTargetPct`
- Renders advisory note text when below target (text, non-blocking)

**`features/voice-quote-creation/components/ContextChip.test.tsx`** (4 tests):
- Renders null when `contextWindow` is null
- Renders customer name when `active_customer_id` is set
- Updates when `contextWindow` prop changes
- Has correct ARIA label

**`features/voice-quote-creation/hooks/useAudioCapture.test.ts`** (6 tests):
- `startRecording` calls `expo-av` `Audio.requestPermissionsAsync`
- `startRecording` returns `permissionGranted: false` when denied
- `startRecording` starts recording when permission granted
- `stopRecording` stops recording and returns audio URI
- `isRecording` state transitions correctly
- Cleanup: stops recording on unmount if still active

**`features/voice-quote-creation/store.test.ts`** (6 tests):
- Initial state matches defaults
- `setVoiceState` transitions state correctly
- `setFieldMode` persists to `AsyncStorage`
- `setPendingConfirmation` sets confirmation state
- `reset` returns all state to defaults
- `setTranscriptBuffer` updates buffer for entity highlighting

### Integration Test Targets (minimum 15)

**File**: `apps/mobile/__tests__/batch_fe_b3/voice-session-happy-path.integration.test.tsx`
- Full happy path: start session → MSW WebSocket fires → transcript appears → intent detected → quote_preview rendered (live) → user taps submit → quote created → snapshot frozen → navigate away

**File**: `apps/mobile/__tests__/batch_fe_b3/voice-session-offline.integration.test.tsx`
- Offline path: disconnect network → tap mic → record → `<NotificationBanner>` "Voice captured" appears → reconnect → upload fires → "Processing..." banner → success
- Deferred confirmation: offline intent requires confirm → push notification deep-link → confirmation prompt renders in session
- `useDeferredVoiceUpload` queue persists across component remount (AsyncStorage backed)

**File**: `apps/mobile/__tests__/batch_fe_b3/voice-session-list.integration.test.tsx`
- Session list renders with mock sessions
- "+ New session" creates session and navigates
- Tapping existing session navigates with correct `sessionId` param
- Empty state renders when no sessions

**File**: `apps/mobile/__tests__/batch_fe_b3/voice-confirm-turn.integration.test.tsx`
- Confirm-as-turn full flow: `response_final` with `waiting-confirm` → `<VoiceConfirmTurn>` renders → user taps Confirm → action executes → `voiceState` returns to idle
- Cancel: `<VoiceConfirmTurn>` renders → user taps Cancel → no action → idle state
- Confirmation timeout (fake timers): pending confirmation expires → `voiceState` → idle with error banner

**File**: `apps/mobile/__tests__/batch_fe_b3/live-snapshot-transition.integration.test.tsx`
- `render_mode: 'live'` message fetches from API (MSW) and renders live data
- After `action_committed` WS event with `snapshot_frozen: true`, same message re-renders as snapshot from payload
- Once in `snapshot` mode, prop change to `mode='live'` does NOT re-trigger API fetch (invariant test)

**File**: `apps/mobile/__tests__/batch_fe_b3/field-mode-toggle.integration.test.tsx`
- Toggle activates field mode → `<MicButton>` enlarges → session controls hide
- Toggle deactivates field mode → restores normal layout
- Field mode persists across navigation (AsyncStorage read on remount)

**File**: `apps/mobile/__tests__/batch_fe_b3/disambiguation.integration.test.tsx`
- Multiple customers match → `<DisambiguationList>` renders with options
- User selects option → quote creation continues with selected customer
- Zero matches → error banner "No matching customer found"

**File**: `apps/mobile/__tests__/batch_fe_b3/rbac-voice.integration.test.tsx`
- User with `voice.use` permission: voice tab entry point visible
- User without `voice.use` permission: voice entry point hidden (`<RoleGate>` behavior)
- `is_tech_role = true`: submit button reads "Submit for approval"
- `is_owner_role = true`: submit button reads "Send"

### E2E Test Targets (minimum 3)

**File**: `apps/mobile/e2e/batch_fe_b3/voice-quote-creation.flow.yaml` (Maestro)
```yaml
# Happy path: real mic on device, full voice quote creation
appId: com.pilotfortrades.mobile
---
- launchApp:
    clearState: true
- tapOn: "Home"
- tapOn:
    text: "Start a voice session"
- assertVisible:
    id: "voice-trigger-btn"
- tapOn:
    id: "voice-trigger-btn"
- assertVisible:
    id: "listening-waveform-anim"
# (Audio spoken: "Create a quote for Tom Johnson")
- waitForAnimationToEnd:
    timeout: 5000
- assertVisible:
    text: "Matched Tom Johnson"
- assertVisible:
    id: "voice-quote-preview-card"
```

**File**: `apps/mobile/e2e/batch_fe_b3/voice-session-resume.flow.yaml` (Maestro)
- Launch app → navigate to existing session → verify messages load → verify context chip shows customer name → start new voice turn within resumed session

**File**: `apps/mobile/e2e/batch_fe_b3/voice-confirm-turn.flow.yaml` (Maestro)
- Real voice → intent that requires confirmation → `<VoiceConfirmTurn>` renders → say "yes" → action executes → confirm success banner

### Accessibility Audit Checkpoints

- `<VoiceStateIndicator>`: `accessibilityLabel` changes with state; ARIA live region announces state changes
- `<MicButton>`: `accessibilityRole="button"`, `accessibilityLabel` describes current state
- `<VoiceConfirmTurn>`: two buttons with distinct `accessibilityLabel`; ARIA `role="dialog"` or equivalent
- `<VoiceQuotePreview>`: currency values read aloud correctly; margin status announced; line items as accessible list
- `<SessionDrawer>`: focus trapping when open; dismiss on accessibility escape
- `<ContextChip>`: `accessibilityHint` explains what the chip represents (not obvious visually to screen readers)
- axe-core integration test on `VoiceSessionShell` render: zero violations required

---

## Batch Dependency Summary

**FE-B3 gates downstream**:
- **FE-B5** (quote approval): imports `<VoiceConfirmTurn>` + `useVoiceStream()` from FE-B3. Cannot start FE-B5 voice approval surface until FE-B3's shared modules are exported from `packages/ui/src/index.ts`.
- **FE-B6** (customer comms): imports `<VoiceConfirmTurn>`. Imports `useVoiceStream()` for voice intent flow.
- **FE-B10** (inbound SMS): imports `<VoiceConfirmTurn>` for voice-to-text reply confirmation.
- **FE-B16** (help system): imports `useVoiceStream()` for voice help queries.

**What FE-B3 does NOT own that downstream batches need**:
- `<MessagePreviewModal>` — FE-B6 owns this
- `<DiffView>` — FE-B5 owns this
- `<PendingBadge>` / `useOptimisticMutation()` — FE-B7 owns this
- Full offline sync (WatermelonDB) — FE-B7 owns this; FE-B3 only stubs the deferred voice upload queue

**Cross-cutting completion gate for FE-B3**:

Before marking FE-B3 complete, verify:
- [ ] `useVoiceStream()` (both web and mobile implementations) exported from `packages/ui/src/index.ts`
- [ ] `<VoiceConfirmTurn>` + `useVoiceConfirmation()` exported from `packages/ui/src/index.ts`
- [ ] `VoiceState` type exported from `packages/ui/src/index.ts`
- [ ] `voiceStateTokens` exported from `packages/ui/src/index.ts`
- [ ] No hardcoded hex/pixel values — ESLint `no-hardcoded-design-values` passes with zero warnings
- [ ] axe-core: zero violations on voice session shell and confirm-turn surfaces
- [ ] MSW handlers cover all 8 happy-path WebSocket events defined in Decision 8
- [ ] Live→snapshot transition invariant test passes
- [ ] Deferred upload stub works with `AsyncStorage` (FE-B7 will upgrade to WatermelonDB)
- [ ] `VoiceConfirmTurn.tsx` has JSDoc documenting its role as the canonical confirm-as-turn UI
- [ ] `packages/ui/src/index.ts` updated with all FE-B3 shared exports
- [ ] Impl plan §7 Tracker row for FE-B3 filled in with component manifest, test files, test count delta

---

*Produced by: Pilot Architect mode (2026-05-21)*  
*Based on: `frontend-pass-3-flow-1-voice-quote-creation-spec.md` v1.0, `mvp-arch.md` v5.3 §6 + §16.3, `pilot-react-engineer-methods.md` v2.1 §12 + §8, `pilot-app-mvp-frontend-impl-plan.md` v1.0 §6 FE-B3*
