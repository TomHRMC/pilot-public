# 🎨 Brand Consistency: App-to-Web Guidelines

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

## 1. The "Unified Brand" Mandate
While the marketing site focuses on conversion rather than utility, it must feel like the exact same ecosystem as the Pilot web dashboard and mobile app.

## 2. Design Token Consumption
The marketing site must consume the exact same design tokens as the application.
* **Color Palette**: Strictly use the established Tailwind palette (e.g., `brand-indigo-500` for primary actions, neutral grays for backgrounds). Do not introduce new hex codes.
* **Typography**: Use the identical font family, weight scale, and tracking as the web dashboard to maintain a professional, robust feel.

## 3. UI Element Mirroring
When showcasing app features on the marketing site, UI elements should mimic the real app.
* **Buttons**: Marketing CTAs should share the same border-radius, hover states, and shadow properties as the primary buttons in the Next.js app.
* **Icons**: Each surface uses the icon library appropriate to its platform — there is no single app-wide icon library:
  * **Marketing site** ([`apps/marketing`](../../frontend/apps/marketing)): **Lucide React** (`lucide-react`) — JS SVG, good for static SSR marketing pages.
  * **Web app / dashboard** ([`apps/web`](../../frontend/apps/web)): **Heroicons** (`@heroicons/react/24/outline` + `/24/solid`) — the established web-dashboard convention.
  * **Mobile app** ([`apps/mobile`](../../frontend/apps/mobile)): **SF Symbols (iOS) + MaterialIcons (Android fallback)** via `@expo/vector-icons` / `expo-symbols` — platform-native icon systems (the React Native / Expo Router convention; native icons render sharper and respect iOS Dynamic Type).
    * **Current state**: `@expo/vector-icons` with `MaterialIcons` as the Android/web fallback and `expo-symbols` (SF Symbols) on iOS — the Expo Router template default ([`icon-symbol.tsx`](../../frontend/apps/mobile/components/ui/icon-symbol.tsx)).
    * **Target direction**: migrate to **`@expo/ui/universal/icon`** + **`expo-symbols`** — Expo's newer universal icon component that natively hooks into Apple's SF Symbols on iOS and Google's Material Symbols on Android. This is the preferred end state for true native icons/symbols across both platforms. Migration is deferred to the planned major mobile UI/UX rework; new mobile work should prefer `@expo/ui/universal/icon` where feasible, but existing `@expo/vector-icons` usage is not blocked.
  * When the marketing site showcases a web-app feature, use the **Lucide** equivalent of the web app's Heroicons glyph so the marketing page stays internally consistent with its own icon set. The visual outcome (a recognizable wallet/phone/etc. glyph) is what matters for brand consistency, not the literal library.
  * The `@pilot/ui` shared barrel exports no icons — icons are imported directly per-feature from the appropriate library for that surface.

## 4. Contrast & Accessibility
Just like the field app, the marketing site must be highly accessible.
* **WCAG Compliance**: Maintain high contrast ratios for all text, avoiding light gray text on white backgrounds. 
* **Focus States**: Ensure all links and buttons have clear, visible focus rings for keyboard navigation.
