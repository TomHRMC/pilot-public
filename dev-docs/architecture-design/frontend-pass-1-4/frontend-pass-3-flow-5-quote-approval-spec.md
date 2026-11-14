# Pilot for Trades Design System — Pass 3, Flow 5: Quote Approval Workflow

**Version**: 1.0
**Status**: Locked
**Date**: April 25, 2026
**Scope**: Web and mobile owner approval workflow; tech submission status and resubmission
**Depends On**: Pass 1 (tokens), Pass 2 (IA), Pass 2 A2 (quote approval workflow), `quote-line-item-architecture.md`, Pass 3 Flow 1 (voice patterns), Pass 3 Flow 4 (preview-before-send pattern)
**Backend Reference**: A2 (Quote Approval Workflow), with refinements noted in this spec

---

## Purpose

Flow 5 designs the governance loop introduced when techs can submit quotes that require owner approval before reaching the customer. This is the operational workflow for multi-person shops where the owner wants quality control over what goes out under their company's name. For solo operators (`require_approval_for_tech_quotes = false`), this flow is bypassed entirely — quotes go straight from creation to customer.

The design's central tension is balancing **owner authority** (the owner needs to be able to fix problems, not just gate them) with **tech autonomy** (the tech who walked the site has knowledge the owner doesn't, and arbitrary owner edits without explanation become destructive). The track-changes pattern resolves this — owners can edit freely, but their changes are visible, auditable, and preserve the tech's original submission.

## Strategic Direction

### Capability parity across surfaces

Owners can do full line-item editing on both mobile and web. The capability set is identical to what techs have when creating quotes: edit any line, add a line, delete a line, edit quote-level notes, apply discounts (within configured caps). The *experience* differs by ergonomics — web is the natural home for dense edits, mobile is better for quick decisions — but neither surface restricts what the owner can do.

This was originally specced more conservatively (mobile = approve/reject only, web = full editing). On reflection, that asymmetry was wrong: if techs can do full editing on mobile during quote creation, owners can do the same during approval. The platform restriction would have been arbitrary.

### Track-changes as the primary editing metaphor

When the owner makes edits during review, those edits are visually distinct from the original submission until they're committed. This pattern is universally familiar (Word, Google Docs, GitHub PRs) and provides three benefits: the owner can review their own edits before committing, individual edits can be reverted without losing other edits, and the tech later sees a clear visual record of what changed.

On web, track-changes renders inline by default. On mobile, the screen is too small for default inline diff rendering, so a "Show changes" toggle reveals which lines have pending edits with markers and color tints; the toggle defaults to on (because a mobile owner reviewing a quote almost always wants to see what's pending) but can be turned off for a clean read of the proposed result.

### Three resolution paths, owner picks based on situation

The owner has three ways to resolve a pending quote:

1. **Approve as-is** — quote moves to `approved` state with no modifications
2. **Edit and approve** — owner makes inline edits, then commits them all with approval; original tech submission preserved as version, edited version becomes the approved version
3. **Kick back to tech** — owner adds inline comments on specific lines plus an optional overall comment; quote returns to `draft` state in tech's queue with annotations visible

Rejection is a fourth path but is intended for rare cases (the quote is fundamentally wrong or the job won't happen) — comments are required when rejecting so the tech knows why.

### Tech sees what the owner approved, not the diff

When a tech opens an approved quote, the primary view is the final approved version — clean, complete, ready to send to the customer. A separate "Changes (N)" tab shows what the owner modified, with annotations explaining why if the owner provided them. This matches the GitHub PR pattern: you see the merged code by default, with a separate way to see the diff.

The rationale: techs care about "what's the final quote my customer is getting?" most of the time. The diff is learning material that's available when they want it but doesn't dominate the primary view.

## Locked Design Decisions

### 1. Web Approval Workspace Is a Quote Editor with Approval-Specific Affordances

**Decision**: The web approval surface (`/quotes/{id}/approve`) is essentially the quote editor with an additional "review mode" affordance bar at the top, action buttons at the bottom (Approve / Kick back / Reject), and track-changes rendering for any pending edits.

**Rationale**: Building a separate "approval" UI distinct from the quote editor would mean two paths for the same kind of editing work, with inevitable feature drift. Keeping them as one surface with a mode flag means improvements to either editing or approval flow benefit the other.

### 2. Track-Changes Visual Vocabulary

**Decision**: Owner edits during review are rendered with a consistent visual vocabulary across both web and mobile:

| Change type | Color | Marker | Visual treatment |
| :--- | :--- | :--- | :--- |
| Modification (existing line edited) | Amber (alert palette) | `~` | Background tint, left border, original value strike-through next to new value |
| Addition (new line added by owner) | Green (margin palette) | `+` | Background tint, left border, "Added by Owner" annotation |
| Deletion (line marked for removal) | Red (fault palette) | `−` | Strike-through text, background tint, left border, "Removed by Owner" annotation |

These colors reuse the Pass 1 design tokens and are semantically consistent with their usage elsewhere in the platform — amber for change/attention, green for new/positive, red for removal/danger.

### 3. Pending vs. Committed Edits Distinction

**Decision**: Owner edits remain "pending" until the owner clicks "Approve with N edits." Pending edits:
- Are visible to the owner only (the tech doesn't see them yet)
- Can be reverted individually (each modified line has a "revert this change" button on hover)
- Can be cancelled in bulk via "Cancel my edits" (all pending edits reverted)
- Persist across page reloads (server-side stored as draft modifications associated with the owner's session)

When the owner commits via "Approve with edits," all pending edits become part of the approved quote version, the audit trail records who changed what, and the tech is notified.

**Rationale**: An owner reviewing a multi-line quote may want to make several edits before committing. Each individual edit shouldn't be a save operation — they should be able to make changes, look at the result holistically, and commit or revert as a batch.

### 4. Mobile "Show Changes" Toggle

**Decision**: On mobile, the quote review surface displays a banner at the top indicating "N pending edits on this quote" with a toggle button — "Show changes" / "Hide changes." When showing changes, lines with pending edits get a colored marker dot and tinted background; the line content shows both old and new values inline. When hiding changes, the screen displays the proposed result as if the edits were already approved (allowing the owner to read the final form cleanly).

**Rationale**: A 6-inch screen can't render full track-changes inline without becoming visually overwhelming. Defaulting to "show changes" respects that an owner reviewing a quote almost always wants to know what's pending; the "hide" option lets them check the final form without distraction.

### 5. "Edit on Web" Deep Link from Mobile

**Decision**: Mobile owner approval surface includes a discreet "More edits to make? Open this quote on web for full editing →" link. Tapping it offers two options: open the URL in mobile Safari/Chrome (works but ergonomic for owners who want it), or copy the URL to send to themselves for laptop access.

**Rationale**: Even though mobile has capability parity, a 15-line edit on a phone is a worse experience than the same edit on a laptop. Giving the owner an explicit path to escalate to a better surface is a kindness, not a capability restriction. The owner picks the right tool for the size of work in front of them.

### 6. Kickback Uses Inline Line-Level Comments + Overall Comment

**Decision**: When the owner clicks "Kick back to Mike with comments," they enter a comment-mode UI. Each line item gets a small "comment" button on hover; clicking opens a comment thread anchored to that line. A separate "overall comment" text area at the bottom captures non-line-specific feedback. When the owner submits the kickback, the quote returns to draft state in the tech's queue with all comments visible.

**Rationale**: Per the locked decision in design discussions, this matches established annotation patterns from Figma, GitHub PRs, and Google Docs. Inline comments anchor guidance to the lines they apply to; the overall comment captures anything that doesn't fit a specific line.

### 7. Comment Requirements by Action

**Decision**:

| Action | Comment |
| :--- | :--- |
| Approve as-is | None required |
| Approve with edits | Optional per-edit annotations (the edit itself is partial explanation; the annotation adds context) |
| Kick back | Required (either inline comments on specific lines, an overall comment, or both — at least one comment must exist) |
| Reject | Required (overall comment explaining why) |

**Rationale**: The asymmetry respects what's useful. Reject and kickback need explanation because the tech needs to act on the feedback. Approve-with-edits captures the "what" via the edits themselves; the "why" is nice-to-have. Approve-as-is needs nothing.

### 8. Tech Sees Approved Quote, Changes Tab Available

**Decision**: When the tech opens an approved quote, the default view shows the final approved version cleanly — every line at its approved values, no diff markers. A tab navigation at the top of the quote detail offers:

| Tab | Content |
| :--- | :--- |
| **Quote** | The final approved quote (default view) |
| **Changes (N)** | Diff view showing what the owner modified, with annotations |
| **Activity** | Full audit log: submitted, reviewed, edited, approved, sent |

The "Changes" tab also includes a count badge showing how many changes were made, drawing attention without being intrusive.

**Rationale**: Per the locked decision in design discussions. Techs primarily want to see the final result; the changes are learning material available on demand.

### 9. Tech Submission Status Surface

**Decision**: After a tech submits a quote, the tech-facing UI shows a clear status indicator on:
- The quote detail page itself ("Submitted for approval · 14 min ago")
- The mobile Today tab (count of "Pending approval" quotes)
- The mobile Voice tab session history (sessions that resulted in pending approvals are tagged)

When the owner makes a decision (approve, kick back, reject), the tech receives:
- A push notification with the outcome and any comments
- An in-app badge on the quote
- An email summary if the tenant has email notifications enabled

**Rationale**: Techs need to know where their work stands. Without clear status communication, techs either lose track of what's pending or pester the owner for updates.

### 10. Quote Style Affects Editing UI per the Architecture Doc

**Decision**: The approval workflow honors the three quote styles defined in `quote-line-item-architecture.md`:

- **Component-style quotes**: editing surface shows all line items as a flat list, full edit/add/delete capability on every line
- **Deliverable-style quotes**: customer-visible parent lines shown prominently with their descriptions; child cost-tracking lines visible to the owner under each parent in a collapsible panel; owner can edit both customer-facing prices AND internal cost components
- **Lump-sum-style quotes**: single customer-visible line with its description prominently editable; internal cost components shown in a collapsible "Internal cost breakdown" section

The owner's edits to internal cost components (in deliverable and lump-sum styles) don't change the customer-facing total — they update the projected margin only. This is a critical distinction the UI must make clear.

### 11. Margin Display on Approval Surface

**Decision**: The approval surface prominently displays the projected margin both pre-edit and post-edit. When edits are pending, the margin display shows the projected margin given those edits, with the original margin shown as struck-through context.

Example: "Projected margin: 24.1% (was 23.3%) · target 20% ✓"

**Rationale**: An owner editing a quote needs to see the financial impact of their edits in real-time. Bumping labor from 6.5 to 8 hours might feel like the right call, but if it pushes margin below target, the owner needs to know that immediately.

### 12. Voice-Triggered Approval

**Decision**: The owner can voice-trigger approval actions from any Pilot surface:
- "Approve Mike's panel upgrade quote"
- "Show me Mike's pending quotes"
- "Kick back the panel quote — labor seems light"

Voice handlers route through `voice_action_router.py` per Pass 3 Flow 1 patterns. The disambiguation flow handles cases where multiple quotes match ("Mike has two pending quotes — the panel upgrade or the service call?").

**Rationale**: An owner driving between sites should be able to triage approvals via voice. This extends the Pilot voice-first positioning to a workflow that competitors handle only via touch.

**Important constraint**: voice cannot commit complex edits. Voice can approve, reject (with spoken comment), or kick back (with spoken comment), but inline line-level edits require touch on either mobile or web. This is a friction-by-design choice — voice-driven complex edits would be too error-prone.

## UX Patterns Established

Flow 5's design becomes the template for:

| Pattern | Reuse |
| :--- | :--- |
| Track-changes for pending edits | Any flow with pre-commit modification (settings changes, customer info updates) |
| Mobile "show changes" toggle for diff visualization | Any mobile surface displaying modified content |
| Three resolution paths (approve / modify / reject) | Any approval workflow (expense approvals, change orders, time entry approvals) |
| Inline comments + overall comment for kickback | Any review-and-comment workflow |
| Tech-facing tabbed view (result / changes / activity) | Any state-changing workflow visible to multiple actors |
| Voice triggers for approval actions | Any review/approval surface |

## Cross-Domain Considerations

### A. Quote version immutability

Per existing architecture, every approval action creates a new immutable quote version. The flow:
- Tech submits version 1
- Owner makes edits and approves → version 2 (with owner-edit metadata)
- Customer eventually receives version 2 PDF
- If the customer accepts, version 2 becomes the contractual document

The audit trail must capture the version chain so any future inquiry ("why did this go up to 8 hours?") can resolve to the specific version and the specific edit made.

### B. Approval queue scaling

A multi-tech shop may have 5+ pending quotes at any given moment. The web approval queue (Quotes > Approvals) needs to handle this gracefully — sorted by submission time, filterable by tech, clearly indicating urgency (customer waiting, time-sensitive). Out of scope for Flow 5's primary design, but worth flagging for the dev team.

### C. Concurrent owner edits

What if the same quote is being reviewed by two owners simultaneously (multi-owner tenants)? The approval workflow needs optimistic locking similar to Flow 3 (dispatch board) — last-write-wins is acceptable but conflicts must be detected and surfaced. This is a backend concern, not a primary UI design issue, but the dev team needs to address it.

### D. Approval bypass for solo operators

When `require_approval_for_tech_quotes = false`, this entire flow is bypassed. Quotes go from `draft` directly to `sent`. The voice quote creation flow's terminal action button reads "Send" instead of "Submit for approval" in this configuration. Already documented in Pass 3 Flow 1.

## Deferred Items (For Future Iteration)

- **Real-time owner notification** (push within seconds of submission) — backend infrastructure exists per Pass 2 A2; UI polish is Pass 4
- **Bulk approval** (approve all 5 pending quotes from a single tech with one action) — Phase 2
- **Approval delegation** (owner can grant temporary approval authority to a senior tech) — Phase 2
- **Approval rules engine** (auto-approve quotes under $X, auto-flag quotes with margin below Y) — Phase 2
- **Approval analytics** (which techs have highest approval rate, average revision time) — Phase 2
- **Customer comm preview after approval** (when sending the approved quote, the comm preview from Flow 4 applies) — already covered by Flow 4
- **Mobile inline comment UI for kickback** (web spec is detailed; mobile inline comment UX needs design refinement) — Pass 4

## Validation Checklist

Before implementation begins:

- [ ] Dev team aligned on capability parity (mobile owner has full editing capabilities)
- [ ] Track-changes data model defined (where pending edits live before commit)
- [ ] Quote version chain reviewed against existing immutability architecture
- [ ] Notification triggers wired to existing notification_outbox infrastructure
- [ ] Optimistic locking strategy defined for concurrent owner reviews
- [ ] Voice intent grammar for approval actions reviewed against `voice_action_router.py`
- [ ] Margin recalculation correctness verified across all three quote styles
- [ ] Solo operator bypass path tested (no approval surface shown when setting is OFF)

## Next: Pass 3 Flow 6

Recommended next per the locked sequence: **Calendar conflict resolution (web)**. This handles the case where Pilot's bi-directional sync with Google Calendar detects a conflict (event modified in both places since last sync). UI for surfacing pending conflicts, showing both versions, and letting the owner pick which version wins. Should be a focused single session — the architecture (per `mvp-arch.md` §13.5) is already defined, just needs UI design.

After Flow 6, the final flow is offline-to-online sync (Flow 7) — saved for last because it's the hardest.
