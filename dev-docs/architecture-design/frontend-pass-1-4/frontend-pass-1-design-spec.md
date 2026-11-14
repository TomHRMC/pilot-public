# Pilot for Trades Design System — Pass 1: Foundation

**Version**: 1.0
**Status**: Locked
**Date**: April 22, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Color tokens, typography, spacing, voice state vocabulary, touch targets, theming strategy
**Depends On**: `mvp-arch.md` §11 (Frontend Architecture)

---

## Purpose

Pass 1 establishes the visual foundation that both `apps/web` (Next.js 16 + shadcn/ui) and `apps/mobile` (Expo SDK 54 + Gluestack-UI) consume. No screens, flows, or components are designed here — this document locks the primitives that every subsequent design pass depends on.

## Deliverables

| File | Location | Consumer |
| :--- | :--- | :--- |
| `tokens.ts` | `packages/ui/src/tokens.ts` | Both apps (runtime + build-time) |
| `tailwind.preset.ts` | `packages/ui/tailwind.preset.ts` | `apps/web` via `tailwind.config.ts` |
| `globals.css` | `packages/ui/src/styles/globals.css` | `apps/web` for shadcn/ui theme bridge |
| `gluestack-config.ts` | `apps/mobile/theme/gluestack-config.ts` | `apps/mobile` Gluestack-UI provider |

## Key Decisions

### 1. Five Semantic Color Ramps (Not Trade-Specific)

**Decision**: `brand`, `alert`, `margin`, `fault`, `neutral`.

**Rationale**: Product will expand from electrical contractors to plumbers and HVAC businesses within 6–12 months. Trade-specific token names (`voltage`, `arc`, `wire`) would bleed into codebase and break semantic readability for non-electrical developers and trade-expansion onboarding. Semantic names (`brand`, `alert`, `margin`, `fault`) survive vertical expansion without rename.

**Mapping**:

- `brand` (indigo #3B43D6 at 600) — Primary brand, CTAs, links, active nav.
- `alert` (amber #F59E0B at 400) — Voice-active state AND code/safety warnings. Same ramp, different stops for different weights.
- `margin` (emerald #059669 at 600) — Profit, success, on-budget. "Margin" is a profit concept in every trade.
- `fault` (red #DC2626 at 600) — Over-budget, overdue, errors. "Fault" is domain language across electrical, plumbing, and HVAC.
- `neutral` (warm stone #57534E at 600) — Text, surfaces, borders. Warm stone intentional — cool gray reads enterprise-SaaS; warm stone reads tool-grade.

### 2. Indigo as Primary Brand Color

**Decision**: Brand = indigo (#3B43D6).

**Rationale**: Indigo has the ramp depth needed for both light and dark UI, is distinct from the dominant blues used by incumbent contractor software (ServiceTitan, Housecall Pro, Jobber all lean on cooler corporate blues), and does not carry trade-specific baggage. Considered and rejected: sapphire (too corporate-enterprise), electric teal (too consumer-tech), amber+graphite duotone (too opinionated; fights third-party embeds like QuickBooks and Stripe).

### 3. Amber Serves Dual Semantic Purpose

**Decision**: `alert` ramp covers both voice-active state (stop 400) and NEC/code/safety warnings (stop 600+).

**Rationale**: On mobile, listening voice state occurs simultaneously with warnings often enough that using separate colors would create visual collisions. Same ramp with stop differentiation maintains semantic clarity while avoiding color-count inflation. Stop 400 (bright amber) reads as active/pulsing; stop 600 (burnt amber) reads as serious/warning — the weight difference carries the meaning distinction.

### 4. Six-State Voice State Machine

**Decision**: `idle` → `listening` → `processing` → `confirming` → `success` | `error`.

**Rationale**: Field testing of voice UI in industrial apps consistently shows that 8–10 states get reduced to 4–5 in practice because developers can't remember which state applies when. Six is the minimum viable set that captures real user-facing distinctions:

- `idle` — dormant, waiting for wake-word or tap
- `listening` — capturing audio (Whisper input)
- `processing` — Whisper transcribing + Llama parsing intent (combined; user doesn't care about the substeps)
- `confirming` — destructive action requires yes/no (deletes, completions without LOTO, irreversible state changes)
- `success` — brief flash, ~800ms, then dissolve to idle
- `error` — recoverable; always pairs with retry or fallback path

**Non-states that were considered and rejected**:
- `transcribing` + `parsing` as separate states → combined into `processing` (user doesn't distinguish)
- `speaking` (TTS output) → handled at the TTS layer, not a top-level voice state
- `muted` → a setting, not a state

### 5. Dark Mobile / Light Web, Themeable From Day One

**Decision**: Mobile ships dark-default. Web ships light-default. Both respect `prefers-color-scheme` and expose manual override in settings.

**Rationale**:
- **Mobile is used on job sites**: outdoor sunlight, attics, crawlspaces, parking lots in summer. Dark chrome with bright indigo/amber/emerald accents maintains legibility in harsh lighting. Light mobile UIs wash out under direct sun.
- **Web is used in the office**: owner doing quoting, bookkeeper doing reconciliation, AR aging review. Light chrome is correct for dense data surfaces, spreadsheets, and extended reading sessions.
- **Themeability is cheap now, expensive later**: CSS variables + Tailwind v4 + Gluestack theme tokens make this near-free to implement today. Retrofitting theme support into a single-mode app is weeks of work.

### 6. Mobile Touch Target = 56px (Not 44pt)

**Decision**: Default mobile button is 56px tall. Primary voice action is 64px. Web default remains 36px. Tablet gets its own scale at 48px.

**Rationale**: iOS Human Interface Guidelines (44pt) and Material Design (48dp) are designed for *typical* consumer use — bare thumbs, indoor lighting, undivided attention. Mike is wearing work gloves, potentially holding a tool in his other hand, and glancing at the screen between physical tasks. 56px is the empirical threshold where gloved-hand accuracy approaches bare-thumb accuracy.

### 7. Typography: Inter + JetBrains Mono, Two Weights Only

**Decision**: Inter for UI, JetBrains Mono for numerics. Only 400 and 500 weights.

**Rationale**:
- Inter handles both dense data (13px body, tabular numerals) and larger headline weights without personality breakdown.
- JetBrains Mono reserved for numeric data (prices, amperage, AWG sizes, job IDs, timestamps) where visual alignment matters. Uses tabular numerals by default.
- Two weights keeps the design honest — if weight difference doesn't express something meaningful, it shouldn't exist. No 600/700 because Inter medium already carries enough emphasis; 600+ reads aggressive on data surfaces.

### 8. Warm Stone Neutrals (Not Cool Gray)

**Decision**: Neutral ramp uses warm stone values (#FAFAF9 → #1C1917) not cool slate values.

**Rationale**: Cool grays read "corporate SaaS" and fight the tool-grade aesthetic that distinguishes Pilot from incumbent contractor software. Warm stone neutrals pair naturally with the amber alert ramp (both sit in warm hue space) and make the indigo brand color feel more confident — warm neutrals + cool brand accent is a classic industrial design pairing (think: Leatherman tools, Klein Tools packaging, Milwaukee hardware).

## What Pass 1 Does NOT Cover

Intentionally deferred:

- **Elevation/shadow tokens** — Flat-first philosophy; add later only for components that genuinely need depth cues (dropdowns, modals, command palette). Not a day-one concern.
- **Animation/motion tokens beyond voice states** — Motion belongs in Pass 3 (flow prototyping) where we have concrete user interactions to animate. Basic `motion.duration` and `motion.easing` are exported for use but not codified into a full motion system.
- **Iconography** — Lucide is already in the stack. Pass 2 will standardize stroke weight and sizing against the type scale.
- **Data visualization palette** — Charts and graphs need their own qualitative palette. Pass 2.
- **Full component library** — Pass 2 and 3 territory.

## Validation Checklist

Before moving to Pass 2, verify:

- [ ] `packages/ui/src/tokens.ts` committed and importable from both `apps/web` and `apps/mobile`
- [ ] `apps/web` renders shadcn/ui Button with brand primary in light mode
- [ ] `apps/web` renders shadcn/ui Button with brand primary in dark mode (manual toggle)
- [ ] `apps/mobile` renders Gluestack Button with correct dark-default theme
- [ ] `apps/mobile` respects `prefers-color-scheme` on first launch
- [ ] Voice state `listening` renders amber pulse on both platforms using `voiceStateTokens.listening`
- [ ] JetBrains Mono loads on both platforms; renders tabular numerals correctly

## Next: Pass 2

Pass 2 will map the 13 PRD feature domains to their persona (web-primary, mobile-primary, or shared) and produce an information architecture / sitemap for both apps. Output: a single document + two site maps.

---

## Appendix A: Token Usage Examples

### Web (React + Tailwind)
```tsx
<button className="bg-brand-600 hover:bg-brand-800 text-white h-9 px-4 rounded-md">
  Create quote
</button>

<div className="text-fault-600 bg-fault-50 border border-fault-200 rounded-md px-3 py-2">
  Quote expired 3 days ago
</div>
```

### Mobile (React Native + Gluestack)
```tsx
import { Button, ButtonText } from '@gluestack-ui/themed';

<Button
  size="lg"
  bg="$primary"
  height="$touchMd"
  onPress={handleVoiceActivate}
>
  <ButtonText color="$primaryText">Tap to speak</ButtonText>
</Button>
```

### Voice State (shared)
```tsx
import { voiceStateTokens, type VoiceState } from '@pilot/ui/tokens';

function VoiceIndicator({ state }: { state: VoiceState }) {
  const tokens = voiceStateTokens[state];
  return (
    <View style={{ backgroundColor: tokens.indicator }}>
      {/* ... */}
    </View>
  );
}
```
